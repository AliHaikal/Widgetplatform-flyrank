"""IP -> location with a provider fallback chain: A, then B, else nothing.

The chain never raises: a broken dependency degrades the row (no geo), it
never breaks the submission. For deterministic proofs, GEO_MOCK=1 replaces the
real HTTP calls with fake providers that can be switched off one by one with
GEO_A_DOWN=1 / GEO_B_DOWN=1.
"""
import ipaddress
import logging

import httpx

from . import config

log = logging.getLogger("app.geo")

TIMEOUT = 3.0


def _mock_on() -> bool:
    return config.flag("GEO_MOCK")


def _is_public(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False


def provider_a(ip: str) -> dict:
    """ip-api.com (free, no key)."""
    if _mock_on():
        if config.flag("GEO_A_DOWN"):
            raise RuntimeError("mock provider A is down")
        return {"country": "Mockland-A", "city": "A-City"}
    response = httpx.get(f"http://ip-api.com/json/{ip}", timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "success":
        raise RuntimeError("provider A returned failure")
    return {"country": data.get("country"), "city": data.get("city")}


def provider_b(ip: str) -> dict:
    """ipapi.co (free tier, no key)."""
    if _mock_on():
        if config.flag("GEO_B_DOWN"):
            raise RuntimeError("mock provider B is down")
        return {"country": "Mockland-B", "city": "B-City"}
    response = httpx.get(f"https://ipapi.co/{ip}/json/", timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RuntimeError("provider B returned failure")
    return {"country": data.get("country_name"), "city": data.get("city")}


PROVIDERS = [provider_a, provider_b]


def lookup_geo(ip: str) -> dict | None:
    """Try each provider in order. Return None if all fail. Never raises."""
    if not _mock_on() and not _is_public(ip):
        # Loopback/private addresses cannot be located; don't waste API quota.
        return None
    for provider in PROVIDERS:
        try:
            return provider(ip)
        except Exception as exc:  # noqa: BLE001 - degrade, never fail
            log.warning("[geo] %s failed: %s", provider.__name__, exc)
    return None
