
from fastapi import Request, HTTPException, Depends
from config import settings
from services.supabase_client import get_admin_client


async def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.split("Bearer ")[1]

    try:
        sb = get_admin_client()
        user_response = sb.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")

        profile = sb.table("profiles").select("*").eq("id", user.id).single().execute()
        if not profile.data:
            raise HTTPException(status_code=404, detail="User profile not found")

        return {
            "id": str(user.id),
            "email": user.email,
            **profile.data,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
