"""
Ticket routes — customer ticket management, RAG resolution, and email dispatch.
"""

import os
import smtplib
import logging
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from openai import OpenAI

from config import settings
from dependencies import get_current_user
from services.supabase_client import get_admin_client
from services.rag_service import get_rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["tickets"])

DEMO_ORG_ID = "a0000000-0000-0000-0000-000000000001"


# ── Request / Response Models ───────────────────────────────

class RaiseTicketRequest(BaseModel):
    customer_name: str
    customer_email: str
    customer_phone: str | None = None
    subject: str
    query: str
    category: str
    priority: str


class UpdateEmailBodyRequest(BaseModel):
    email_body: str


class AddNoteRequest(BaseModel):
    content: str


# ── Helper: Optional Auth ───────────────────────────────────

async def get_optional_user(request: Request) -> dict | None:
    """Try to extract user from Authorization header; return None if absent."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split("Bearer ")[1]
    try:
        sb = get_admin_client()
        user_response = sb.auth.get_user(token)
        user = user_response.user
        if not user:
            return None
        profile = sb.table("profiles").select("*").eq("id", user.id).single().execute()
        if not profile.data:
            return None
        return {"id": str(user.id), "email": user.email, **profile.data}
    except Exception:
        return None


# ── 1. POST /raise — Public ticket creation ─────────────────

@router.post("/raise")
async def raise_ticket(req: RaiseTicketRequest, request: Request):
    """Create a new support ticket. Works for both logged-in and anonymous users."""
    user = await get_optional_user(request)

    ticket_data = {
        "customer_name": req.customer_name,
        "customer_email": req.customer_email,
        "customer_phone": req.customer_phone,
        "subject": req.subject,
        "query": req.query,
        "category": req.category,
        "priority": req.priority,
        "status": "open",
    }

    if user:
        ticket_data["raised_by"] = user["id"]
        ticket_data["org_id"] = user["org_id"]
        ticket_data["is_logged_in"] = True
    else:
        ticket_data["org_id"] = DEMO_ORG_ID
        ticket_data["is_logged_in"] = False

    sb = get_admin_client()
    result = sb.table("tickets").insert(ticket_data).execute()

    return {"message": "Ticket created", "ticket": result.data[0]}


# ── 2. GET / — List tickets ─────────────────────────────────

@router.get("/")
async def list_tickets(
    status: str | None = None,
    page: int = 1,
    per_page: int = 10,
    user: dict = Depends(get_current_user),
):
    """List tickets for the user's org with pagination."""
    sb = get_admin_client()

    # Get total count
    count_query = sb.table("tickets").select("id", count="exact").eq("org_id", user["org_id"])
    if status:
        count_query = count_query.eq("status", status)
    count_result = count_query.execute()
    total = count_result.count if count_result.count is not None else len(count_result.data)

    # Get paginated data
    offset = (page - 1) * per_page
    query = sb.table("tickets").select("*").eq("org_id", user["org_id"])
    if status:
        query = query.eq("status", status)
    query = query.order("created_at", desc=True).range(offset, offset + per_page - 1)
    result = query.execute()

    return {
        "tickets": result.data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, -(-total // per_page)),  # ceil division
    }


# ── 3. GET /stats — Ticket statistics ───────────────────────
# NOTE: Defined before /{ticket_id} to avoid route shadowing.

@router.get("/stats")
async def ticket_stats(user: dict = Depends(get_current_user)):
    """Return ticket count breakdown by status for the user's org."""
    sb = get_admin_client()
    result = sb.table("tickets").select("status").eq("org_id", user["org_id"]).execute()

    tickets = result.data or []
    counts = {"total": len(tickets), "open": 0, "in_progress": 0, "resolved": 0, "closed": 0}
    for t in tickets:
        s = t["status"]
        if s in counts:
            counts[s] += 1

    return counts


# ── 4. GET /{ticket_id} — Single ticket ─────────────────────

@router.get("/{ticket_id}")
async def get_ticket(ticket_id: str, user: dict = Depends(get_current_user)):
    """Get a single ticket by ID (must belong to user's org)."""
    sb = get_admin_client()
    result = (
        sb.table("tickets")
        .select("*")
        .eq("id", ticket_id)
        .eq("org_id", user["org_id"])
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return result.data


# ── 5. PATCH /{ticket_id}/assign — Assign to self ───────────

@router.patch("/{ticket_id}/assign")
async def assign_ticket(ticket_id: str, user: dict = Depends(get_current_user)):
    """Assign the ticket to the current user and set status to in_progress."""
    sb = get_admin_client()

    # Verify ticket belongs to org
    ticket = (
        sb.table("tickets")
        .select("id")
        .eq("id", ticket_id)
        .eq("org_id", user["org_id"])
        .single()
        .execute()
    )
    if not ticket.data:
        raise HTTPException(status_code=404, detail="Ticket not found")

    result = (
        sb.table("tickets")
        .update({
            "assigned_to": user["id"],
            "status": "in_progress",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", ticket_id)
        .execute()
    )

    return {"message": "Ticket assigned", "ticket": result.data[0]}


# ── 6. POST /{ticket_id}/resolve — RAG resolution ───────────

@router.post("/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: str, user: dict = Depends(get_current_user)):
    """
    Resolve a ticket using RAG:
    1. Search relevant chunks for the ticket query.
    2. Generate an AI answer grounded in those chunks.
    3. Format the answer into a professional email body.
    """
    sb = get_admin_client()

    # Fetch ticket
    ticket = (
        sb.table("tickets")
        .select("*")
        .eq("id", ticket_id)
        .eq("org_id", user["org_id"])
        .single()
        .execute()
    )
    if not ticket.data:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket_data = ticket.data
    customer_query = ticket_data["query"]
    customer_name = ticket_data["customer_name"]

    # Step 1: RAG search
    rag = get_rag_service()
    chunks = await rag.search_chunks(customer_query, user["org_id"], user["id"])

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="No relevant documents found to answer this query",
        )

    # Build context from chunks
    context_parts = []
    for c in chunks:
        section_str = f", Section: {c.get('section', '')}" if c.get("section") else ""
        context_parts.append(
            f"[Source: {c['filename']}, Page: {c['page_number']}, "
            f"Line/Row: {c['line_number']}{section_str}]\n{c['content']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    # Step 2: Generate AI answer (gpt-4o)
    gpt = OpenAI(api_key=settings.OPENAI_API_KEY)

    rag_system_prompt = f"""You are a knowledgeable customer support agent. Answer the customer's question ONLY based on the provided document context. Be clear, helpful, and concise.

If the answer is not available in the context, say so honestly.

## Document Context
{context}
"""

    rag_response = gpt.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": rag_system_prompt},
            {"role": "user", "content": customer_query},
        ],
        max_tokens=settings.LLM_MAX_TOKENS,
        temperature=settings.LLM_TEMPERATURE,
    )
    ai_response = rag_response.choices[0].message.content.strip()

    # Step 3: Format into professional email (gpt-4o-mini)
    email_system_prompt = f"""You are an email formatting agent. Take the provided answer and format it into a professional customer support email.

Requirements:
- Start with a warm greeting addressing the customer by name: {customer_name}
- Include the answer in a clear, readable format
- Add a professional sign-off from the company support team
- Use proper paragraphs for readability
- The email should be in HTML format with basic tags (<p>, <br>, <strong>, <ul>, <li>) for clean rendering
- Do NOT include a subject line — only the email body
- Keep the tone professional, empathetic, and helpful
"""

    email_response = gpt.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": email_system_prompt},
            {
                "role": "user",
                "content": f"Customer query: {customer_query}\n\nAnswer to format:\n{ai_response}",
            },
        ],
        max_tokens=settings.LLM_MAX_TOKENS,
        temperature=0.3,
    )
    email_body = email_response.choices[0].message.content.strip()

    # Step 4: Update ticket
    now = datetime.now(timezone.utc).isoformat()
    sb.table("tickets").update({
        "ai_response": ai_response,
        "email_body": email_body,
        "status": "resolved",
        "resolved_by": user["id"],
        "resolved_at": now,
        "updated_at": now,
    }).eq("id", ticket_id).execute()

    return {
        "message": "Ticket resolved",
        "ai_response": ai_response,
        "email_body": email_body,
    }


# ── 7. PATCH /{ticket_id}/email-body — Edit email draft ─────

@router.patch("/{ticket_id}/email-body")
async def update_email_body(
    ticket_id: str,
    req: UpdateEmailBodyRequest,
    user: dict = Depends(get_current_user),
):
    """Update the email body before sending (employee review / edit)."""
    sb = get_admin_client()

    ticket = (
        sb.table("tickets")
        .select("id")
        .eq("id", ticket_id)
        .eq("org_id", user["org_id"])
        .single()
        .execute()
    )
    if not ticket.data:
        raise HTTPException(status_code=404, detail="Ticket not found")

    result = (
        sb.table("tickets")
        .update({
            "email_body": req.email_body,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", ticket_id)
        .execute()
    )

    return {"message": "Email body updated", "ticket": result.data[0]}


# ── 8. POST /{ticket_id}/send-email — Send via SMTP ─────────

@router.post("/{ticket_id}/send-email")
async def send_ticket_email(ticket_id: str, user: dict = Depends(get_current_user)):
    """Send the resolved email to the customer via Gmail SMTP."""
    sb = get_admin_client()

    ticket = (
        sb.table("tickets")
        .select("*")
        .eq("id", ticket_id)
        .eq("org_id", user["org_id"])
        .single()
        .execute()
    )
    if not ticket.data:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket_data = ticket.data

    if not ticket_data.get("email_body"):
        raise HTTPException(status_code=400, detail="No email body to send. Resolve the ticket first.")

    if ticket_data.get("email_sent"):
        raise HTTPException(status_code=400, detail="Email has already been sent for this ticket.")

    # Build the email
    sender_email = os.environ.get("EMAIL_ADDRESS")
    sender_password = os.environ.get("EMAIL_PASSWORD")

    if not sender_email or not sender_password:
        raise HTTPException(status_code=500, detail="Email credentials not configured on server")

    recipient_email = ticket_data["customer_email"]
    subject = f"Re: {ticket_data['subject']}"

    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(ticket_data["email_body"], "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
    except Exception as e:
        logger.error(f"Failed to send email for ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

    # Update ticket
    now = datetime.now(timezone.utc).isoformat()
    result = (
        sb.table("tickets")
        .update({
            "email_sent": True,
            "email_sent_at": now,
            "status": "closed",
            "updated_at": now,
        })
        .eq("id", ticket_id)
        .execute()
    )

    return {"message": "Email sent successfully", "ticket": result.data[0]}


# ── 9. POST /{ticket_id}/notes — Add internal note ──────────

@router.post("/{ticket_id}/notes")
async def add_note(
    ticket_id: str,
    req: AddNoteRequest,
    user: dict = Depends(get_current_user),
):
    """Add an internal note to a ticket."""
    sb = get_admin_client()

    # Verify ticket belongs to org
    ticket = (
        sb.table("tickets")
        .select("id")
        .eq("id", ticket_id)
        .eq("org_id", user["org_id"])
        .single()
        .execute()
    )
    if not ticket.data:
        raise HTTPException(status_code=404, detail="Ticket not found")

    result = sb.table("ticket_notes").insert({
        "ticket_id": ticket_id,
        "user_id": user["id"],
        "content": req.content,
    }).execute()

    return {"message": "Note added", "note": result.data[0]}


# ── 10. GET /{ticket_id}/notes — List notes ─────────────────

@router.get("/{ticket_id}/notes")
async def list_notes(ticket_id: str, user: dict = Depends(get_current_user)):
    """List all internal notes for a ticket."""
    sb = get_admin_client()

    # Verify ticket belongs to org
    ticket = (
        sb.table("tickets")
        .select("id")
        .eq("id", ticket_id)
        .eq("org_id", user["org_id"])
        .single()
        .execute()
    )
    if not ticket.data:
        raise HTTPException(status_code=404, detail="Ticket not found")

    result = (
        sb.table("ticket_notes")
        .select("*")
        .eq("ticket_id", ticket_id)
        .order("created_at", desc=False)
        .execute()
    )

    return result.data
