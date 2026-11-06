"""Owner authentication.

AUTH_MODE=supabase (default): the bearer token is checked against Supabase and
the user's id becomes the tenant id.
AUTH_MODE=dev: LOCAL DEMO/TEST ONLY. Tokens look like `dev:<tenant>` so a
stranger can run the project without a Supabase account. Never enable in prod.
"""
import logging
import re

import httpx
from fastapi import Header

from . import config
from .errors import AuthUnavailableError, UnauthorizedError

log = logging.getLogger("app.auth")

_DEV_TOKEN = re.compile(r"^dev:([A-Za-z0-9_-]{1,64})$")


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise UnauthorizedError("Missing bearer token")
    return token


def _tenant_from_dev_token(token: str) -> str:
    match = _DEV_TOKEN.match(token)
    if not match:
        raise UnauthorizedError("Invalid or expired token")
    return match.group(1)


def _tenant_from_supabase(token: str) -> str:
    url = config.get("SUPABASE_URL")
    key = config.get("SUPABASE_ANON_KEY")
    if not url or not key:
        log.error("SUPABASE_URL / SUPABASE_ANON_KEY are not configured")
        raise AuthUnavailableError("Auth is not configured")
    try:
        response = httpx.get(
            f"{url.rstrip('/')}/auth/v1/user",
            headers={"apikey": key, "Authorization": f"Bearer {token}"},
            timeout=5.0,
        )
    except httpx.HTTPError:
        raise AuthUnavailableError()
    if response.status_code != 200:
        raise UnauthorizedError("Invalid or expired token")
    try:
        return response.json()["id"]
    except (ValueError, KeyError):
        raise UnauthorizedError("Invalid or expired token")


def get_current_tenant(authorization: str | None = Header(default=None)) -> str:
    token = _bearer_token(authorization)
    if (config.get("AUTH_MODE", "supabase") or "supabase").lower() == "dev":
        return _tenant_from_dev_token(token)
    return _tenant_from_supabase(token)
