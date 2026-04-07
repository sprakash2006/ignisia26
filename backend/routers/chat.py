
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from dependencies import get_current_user
from services.rag_service import get_rag_service
from services.supabase_client import get_admin_client

router = APIRouter(prefix="/chat", tags=["chat"])


class QueryRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class ConversationCreate(BaseModel):
    title: str = "New Conversation"


@router.post("/conversations")
async def create_conversation(req: ConversationCreate, user: dict = Depends(get_current_user)):
    sb = get_admin_client()
    result = sb.table("conversations").insert({
        "org_id": user["org_id"],
        "user_id": user["id"],
        "title": req.title,
    }).execute()
    return result.data[0]


@router.get("/conversations")
async def list_conversations(user: dict = Depends(get_current_user)):
    sb = get_admin_client()
    result = sb.table("conversations").select("*").eq(
        "user_id", user["id"]
    ).order("updated_at", desc=True).execute()
    return result.data


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str, user: dict = Depends(get_current_user)):
    sb = get_admin_client()

    conv = sb.table("conversations").select("user_id").eq("id", conversation_id).single().execute()
    if not conv.data or conv.data["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = sb.table("messages").select("*").eq(
        "conversation_id", conversation_id
    ).order("created_at").execute()
    return result.data


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user: dict = Depends(get_current_user)):
    sb = get_admin_client()

    conv = sb.table("conversations").select("user_id").eq("id", conversation_id).single().execute()
    if not conv.data or conv.data["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Conversation not found")

    sb.table("conversations").delete().eq("id", conversation_id).execute()
    return {"message": "Conversation deleted"}


@router.post("/query")
async def query_rag(req: QueryRequest, user: dict = Depends(get_current_user)):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    history = []
    if req.conversation_id:
        sb = get_admin_client()
        conv = sb.table("conversations").select("user_id").eq("id", req.conversation_id).single().execute()
        if not conv.data or conv.data["user_id"] != user["id"]:
            raise HTTPException(status_code=404, detail="Conversation not found")

        msgs = sb.table("messages").select("role, content").eq(
            "conversation_id", req.conversation_id
        ).order("created_at").execute()
        history = msgs.data or []

    rag = get_rag_service()
    result = await rag.query(
        question=req.question,
        org_id=user["org_id"],
        user_id=user["id"],
        conversation_id=req.conversation_id,
        history=history,
    )

    sb = get_admin_client()
    sb.table("audit_log").insert({
        "org_id": user["org_id"],
        "user_id": user["id"],
        "action": "query",
        "details": {
            "question": req.question,
            "source_count": len(result.get("sources", [])),
            "conflict_count": len(result.get("analysis", {}).get("conflicts", [])),
        },
    }).execute()

    return result
