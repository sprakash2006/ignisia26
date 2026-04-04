"""
Email routes — IMAP config management and email polling.
"""

import imaplib
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from dependencies import get_current_user
from services.rag_service import get_rag_service
from services.supabase_client import get_admin_client

# Reuse existing email processing logic
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from email_fetcher import EmailFetcher

router = APIRouter(prefix="/emails", tags=["emails"])


class EmailConfigRequest(BaseModel):
    imap_server: str
    email_address: str
    password: str
    folder: str = "INBOX"


class EmailConfigResponse(BaseModel):
    id: str
    imap_server: str
    email_address: str
    folder: str
    is_active: bool
    last_polled_at: str | None


# ── Email Config Management ──────────────────────────────────

@router.post("/config")
async def save_email_config(req: EmailConfigRequest, user: dict = Depends(get_current_user)):
    """Save or update IMAP email configuration for the current user."""
    sb = get_admin_client()

    config_data = {
        "user_id": user["id"],
        "org_id": user["org_id"],
        "imap_server": req.imap_server,
        "email_address": req.email_address,
        "encrypted_password": req.password,  # TODO: encrypt before storing
        "folder": req.folder,
        "is_active": True,
    }

    # Upsert (one config per user)
    existing = sb.table("email_configs").select("id").eq("user_id", user["id"]).execute()
    if existing.data:
        result = sb.table("email_configs").update(config_data).eq("user_id", user["id"]).execute()
    else:
        result = sb.table("email_configs").insert(config_data).execute()

    return {"message": "Email configuration saved", "config_id": result.data[0]["id"]}


@router.get("/config")
async def get_email_config(user: dict = Depends(get_current_user)):
    """Get the current user's email configuration."""
    sb = get_admin_client()
    result = sb.table("email_configs").select(
        "id, imap_server, email_address, folder, is_active, last_polled_at"
    ).eq("user_id", user["id"]).execute()

    if not result.data:
        return None
    return result.data[0]


@router.delete("/config")
async def delete_email_config(user: dict = Depends(get_current_user)):
    """Delete the current user's email configuration."""
    sb = get_admin_client()
    sb.table("email_configs").delete().eq("user_id", user["id"]).execute()
    return {"message": "Email configuration deleted"}


# ── Connection Test ──────────────────────────────────────────

@router.post("/test-connection")
async def test_email_connection(req: EmailConfigRequest):
    """Test IMAP connection without saving config."""
    try:
        conn = imaplib.IMAP4_SSL(req.imap_server)
        conn.login(req.email_address, req.password)
        conn.logout()
        return {"success": True, "message": f"Connected to {req.imap_server} as {req.email_address}"}
    except imaplib.IMAP4.error as e:
        return {"success": False, "message": f"IMAP auth failed: {e}"}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {e}"}


# ── Email Polling ────────────────────────────────────────────

@router.post("/poll")
async def poll_emails(user: dict = Depends(get_current_user)):
    """Fetch new emails from the configured IMAP server and ingest them."""
    sb = get_admin_client()

    # Get user's email config
    config = sb.table("email_configs").select("*").eq("user_id", user["id"]).single().execute()
    if not config.data:
        raise HTTPException(status_code=404, detail="No email configuration found")

    if not config.data["is_active"]:
        raise HTTPException(status_code=400, detail="Email polling is disabled")

    # Set up a temporary EmailFetcher with the stored config
    os.environ["EMAIL_IMAP_SERVER"] = config.data["imap_server"]
    os.environ["EMAIL_ADDRESS"] = config.data["email_address"]
    os.environ["EMAIL_PASSWORD"] = config.data["encrypted_password"]
    os.environ["EMAIL_FOLDER"] = config.data["folder"]

    fetcher = EmailFetcher()
    new_emails = fetcher.fetch_new_emails()

    if not new_emails:
        # Update last_polled_at
        sb.table("email_configs").update(
            {"last_polled_at": "now()"}
        ).eq("user_id", user["id"]).execute()
        return {"message": "No new emails found", "count": 0}

    # Ingest each email
    rag = get_rag_service()
    ingested = []
    for em in new_emails:
        if em["chunks"]:
            result = await rag.ingest_document(
                org_id=user["org_id"],
                owner_id=user["id"],
                filename=em["filename"],
                file_type="eml",
                file_size=0,
                chunks=em["chunks"],
                visibility="private",
                source_type="email",
            )
            ingested.append({
                "filename": em["filename"],
                "subject": em["subject"],
                "from": em["from"],
                "date": em["date"],
                "chunk_count": result["chunk_count"],
            })

    # Update last_polled_at
    sb.table("email_configs").update(
        {"last_polled_at": "now()"}
    ).eq("user_id", user["id"]).execute()

    # Audit log
    sb.table("audit_log").insert({
        "org_id": user["org_id"],
        "user_id": user["id"],
        "action": "email_ingest",
        "details": {"email_count": len(ingested), "emails": ingested},
    }).execute()

    return {"message": f"{len(ingested)} email(s) ingested", "count": len(ingested), "emails": ingested}
