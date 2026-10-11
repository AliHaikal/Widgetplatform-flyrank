import os
import httpx
from dotenv import load_dotenv
from fastapi import Header, HTTPException
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env", encoding="utf-8-sig")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

def get_current_tenant(authorization: str = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        r = httpx.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token}"},
            timeout=5.0,
        )
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return r.json()["id"]