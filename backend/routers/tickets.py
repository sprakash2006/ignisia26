
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


async def get_optional_user(request: Request) -> dict | None:
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


@router.post("/raise")
async def raise_ticket(req: RaiseTicketRequest, request: Request):
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


@router.get("/")
async def list_tickets(
    status: str | None = None,
    page: int = 1,
    per_page: int = 10,
    user: dict = Depends(get_current_user),
):
    sb = get_admin_client()

    count_query = sb.table("tickets").select("id", count="exact").eq("org_id", user["org_id"])
    if status:
        count_query = count_query.eq("status", status)
    count_result = count_query.execute()
    total = count_result.count if count_result.count is not None else len(count_result.data)

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
        "total_pages": max(1, -(-total // per_page)),
    }


@router.get("/stats")
async def ticket_stats(user: dict = Depends(get_current_user)):
    sb = get_admin_client()
    result = sb.table("tickets").select("status").eq("org_id", user["org_id"]).execute()

    tickets = result.data or []
    counts = {"total": len(tickets), "open": 0, "in_progress": 0, "resolved": 0, "closed": 0}
    for t in tickets:
        s = t["status"]
        if s in counts:
            counts[s] += 1

    return counts


@router.get("/{ticket_id}")
async def get_ticket(ticket_id: str, user: dict = Depends(get_current_user)):
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


@router.patch("/{ticket_id}/assign")
async def assign_ticket(ticket_id: str, user: dict = Depends(get_current_user)):
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
            "assigned_to": user["id"],
            "status": "in_progress",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", ticket_id)
        .execute()
    )

    return {"message": "Ticket assigned", "ticket": result.data[0]}


@router.post("/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: str, user: dict = Depends(get_current_user)):
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
    customer_query = ticket_data["query"]
    customer_name = ticket_data["customer_name"]

    rag = get_rag_service()
    rag_result = await rag.query(
        question=customer_query,
        org_id=user["org_id"],
        user_id=user["id"],
        conversation_id=None,
        history=[],
    )

    ai_response = rag_result["content"]
    sources = rag_result.get("sources", [])
    analysis = rag_result.get("analysis", {})

    gpt = OpenAI(api_key=settings.OPENAI_API_KEY)

    conflict_note = ""
    if analysis.get("conflicts"):
        conflict_items = []
        for c in analysis["conflicts"]:
            resolution = c.get("resolution", "")
            if resolution:
                conflict_items.append(f"- {c.get('field', 'unknown')}: {resolution}")
            else:
                vals = ", ".join(f"'{v['value']}' from {v['source']}" for v in c.get("values", []))
                conflict_items.append(f"- {c.get('field', 'unknown')}: conflicting values — {vals}")
        conflict_note = f"""
IMPORTANT: The AI detected data conflicts in the source documents. The answer above already accounts for these.
Conflicts found:
{chr(10).join(conflict_items)}
Make sure the email reflects the resolved/latest values only — do NOT show conflicting data to the customer.
"""

    email_system_prompt = f"""You are an email formatting agent. Take the provided answer and format it into a professional customer support email.

Requirements:
- Start with a warm greeting addressing the customer by name: {customer_name}
- Include the answer in a clear, readable format
- Add a professional sign-off from the company support team
- Use proper paragraphs for readability
- The email should be in HTML format with basic tags (<p>, <br>, <strong>, <ul>, <li>) for clean rendering
- Do NOT include a subject line — only the email body
- Keep the tone professional, empathetic, and helpful
- Do NOT include internal sections like "Data Quality Notes", "Source References", or "Reasoning" — those are internal-only
- Extract ONLY the final answer and present it cleanly to the customer
{conflict_note}
"""

    email_response = gpt.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": email_system_prompt},
            {
                "role": "user",
                "content": f"Customer query: {customer_query}\n\nFull AI response (internal):\n{ai_response}",
            },
        ],
        max_tokens=settings.LLM_MAX_TOKENS,
        temperature=0.3,
    )
    email_body = email_response.choices[0].message.content.strip()

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
        "sources": sources,
        "analysis": analysis,
    }


@router.patch("/{ticket_id}/email-body")
async def update_email_body(
    ticket_id: str,
    req: UpdateEmailBodyRequest,
    user: dict = Depends(get_current_user),
):
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


@router.post("/{ticket_id}/send-email")
async def send_ticket_email(ticket_id: str, user: dict = Depends(get_current_user)):
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


@router.post("/{ticket_id}/notes")
async def add_note(
    ticket_id: str,
    req: AddNoteRequest,
    user: dict = Depends(get_current_user),
):
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

    result = sb.table("ticket_notes").insert({
        "ticket_id": ticket_id,
        "user_id": user["id"],
        "content": req.content,
    }).execute()

    return {"message": "Note added", "note": result.data[0]}


@router.get("/{ticket_id}/notes")
async def list_notes(ticket_id: str, user: dict = Depends(get_current_user)):
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
        sb.table("ticket_notes")
        .select("*")
        .eq("ticket_id", ticket_id)
        .order("created_at", desc=False)
        .execute()
    )

    return result.data
