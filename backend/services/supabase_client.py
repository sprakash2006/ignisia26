"""
Supabase client — provides both admin (service_role) and user-scoped clients.
"""

from supabase import create_client, Client
from config import settings


def get_admin_client() -> Client:
    """Service-role client — bypasses RLS. Use for server-side operations."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def get_user_client(access_token: str) -> Client:
    """User-scoped client — respects RLS based on the user's JWT."""
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    client.auth.set_session(access_token, "")
    return client
