"""
Auth routes — signup, login, profile management.
Delegates to Supabase Auth (no custom JWT logic needed).
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from services.supabase_client import get_admin_client
from dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    org_id: str
    role: str = "employee"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    reports_to: str | None = None
    avatar_url: str | None = None


# ── Signup ──

@router.post("/signup")
async def signup(req: SignupRequest):
    """Register a new user. Creates auth user + profile (via DB trigger)."""
    sb = get_admin_client()
    try:
        result = sb.auth.sign_up({
            "email": req.email,
            "password": req.password,
            "options": {
                "data": {
                    "full_name": req.full_name,
                    "org_id": req.org_id,
                    "role": req.role,
                },
            },
        })
        if result.user:
            return {
                "message": "User created successfully",
                "user_id": str(result.user.id),
                "email": result.user.email,
            }
        raise HTTPException(status_code=400, detail="Signup failed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Login ──

@router.post("/login")
async def login(req: LoginRequest):
    """Sign in and receive access + refresh tokens."""
    sb = get_admin_client()
    try:
        result = sb.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password,
        })
        if result.session:
            # Fetch profile
            profile = sb.table("profiles").select("*").eq("id", result.user.id).single().execute()
            return {
                "access_token": result.session.access_token,
                "refresh_token": result.session.refresh_token,
                "expires_in": result.session.expires_in,
                "user": {
                    "id": str(result.user.id),
                    "email": result.user.email,
                    **profile.data,
                },
            }
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


# ── Get Current User Profile ──

@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get the authenticated user's profile."""
    return user


# ── Update Profile ──

@router.patch("/me")
async def update_profile(req: UpdateProfileRequest, user: dict = Depends(get_current_user)):
    """Update the authenticated user's profile."""
    sb = get_admin_client()
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = sb.table("profiles").update(updates).eq("id", user["id"]).execute()
    return result.data[0] if result.data else user


# ── List Org Members ──

@router.get("/org/members")
async def list_org_members(user: dict = Depends(get_current_user)):
    """List all members of the user's organization."""
    sb = get_admin_client()
    result = sb.table("profiles").select("id, full_name, role, reports_to, email, avatar_url").eq(
        "org_id", user["org_id"]
    ).execute()
    return result.data
