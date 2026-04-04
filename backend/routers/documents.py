"""
Document routes — upload, list, delete documents.
"""

import os
import tempfile
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from dependencies import get_current_user
from services.rag_service import get_rag_service
from services.supabase_client import get_admin_client

# Reuse the existing FileIngestor
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from rag_ingestor import FileIngestor

router = APIRouter(prefix="/documents", tags=["documents"])
ingestor = FileIngestor()

ALLOWED_TYPES = {".pdf", ".docx", ".xlsx", ".csv", ".txt", ".eml"}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    visibility: str = Form("shared"),
    user: dict = Depends(get_current_user),
):
    """
    Upload and ingest a document into the RAG pipeline.
    - visibility: 'shared' (org-wide) or 'private' (owner only, role-based)
    """
    # Validate file type
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    if visibility not in ("shared", "private"):
        raise HTTPException(status_code=400, detail="visibility must be 'shared' or 'private'")

    # Save to temp file for processing
    content = await file.read()
    tmp_path = os.path.join(tempfile.gettempdir(), file.filename)
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        # 1. Parse file into chunks using existing ingestor
        chunks, filename = ingestor.process_file(tmp_path)
        if not chunks:
            raise HTTPException(status_code=422, detail="No content could be extracted from the file")

        # 2. Upload raw file to Supabase Storage
        sb = get_admin_client()
        storage_path = f"{user['org_id']}/{user['id']}/{file.filename}"
        sb.storage.from_("documents").upload(storage_path, content)

        # 3. Ingest into RAG (embeddings + store in chunks table)
        rag = get_rag_service()
        owner_id = user["id"] if visibility == "private" else None
        result = await rag.ingest_document(
            org_id=user["org_id"],
            owner_id=owner_id,
            filename=file.filename,
            file_type=ext.lstrip("."),
            file_size=len(content),
            chunks=chunks,
            visibility=visibility,
            source_type="upload",
            storage_path=storage_path,
        )

        # 4. Audit log
        sb.table("audit_log").insert({
            "org_id": user["org_id"],
            "user_id": user["id"],
            "action": "upload",
            "details": {
                "filename": file.filename,
                "visibility": visibility,
                "chunk_count": result["chunk_count"],
            },
        }).execute()

        return {
            "message": f"Document '{file.filename}' uploaded and indexed successfully",
            "document_id": result["document_id"],
            "chunk_count": result["chunk_count"],
            "visibility": visibility,
        }

    finally:
        # Clean up temp file
        try:
            os.remove(tmp_path)
        except OSError:
            pass


@router.get("/")
async def list_documents(user: dict = Depends(get_current_user)):
    """List all documents visible to the current user."""
    rag = get_rag_service()
    docs = await rag.list_documents(user["org_id"], user["id"])
    return docs


@router.delete("/{document_id}")
async def delete_document(document_id: str, user: dict = Depends(get_current_user)):
    """Delete a document (only owner or director can delete)."""
    sb = get_admin_client()

    # Check ownership
    doc = sb.table("documents").select("*").eq("id", document_id).single().execute()
    if not doc.data:
        raise HTTPException(status_code=404, detail="Document not found")

    is_owner = doc.data["owner_id"] is not None and doc.data["owner_id"] == user["id"]
    is_director = user["role"] == "director"
    is_uploader_shared = doc.data["owner_id"] is None  # shared docs can be deleted by any org member
    if not (is_owner or is_director or is_uploader_shared):
        raise HTTPException(status_code=403, detail="Only the owner or a director can delete this document")

    # Delete from storage
    if doc.data.get("storage_path"):
        try:
            sb.storage.from_("documents").remove([doc.data["storage_path"]])
        except Exception:
            pass  # Storage cleanup is best-effort

    # Delete from DB (CASCADE deletes chunks)
    rag = get_rag_service()
    await rag.delete_document(document_id)

    # Audit log
    sb.table("audit_log").insert({
        "org_id": user["org_id"],
        "user_id": user["id"],
        "action": "delete",
        "details": {"filename": doc.data["filename"], "document_id": document_id},
    }).execute()

    return {"message": f"Document '{doc.data['filename']}' deleted"}
