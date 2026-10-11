import os
import httpx

TIMEOUT = 3.0


def _mock_on() -> bool:
    return os.getenv("GEO_MOCK") == "1"


def provider_a(ip: str) -> dict:
    """ip-api.com"""
    if _mock_on():
        if os.getenv("GEO_A_DOWN") == "1":
            raise RuntimeError("mock provider A is down")
        return {"country": "Mockland-A", "city": "A-City"}
    r = httpx.get(f"http://ip-api.com/json/{ip}", timeout=TIMEOUT)
    r.raise_for_status()
    d = r.json()
    if d.get("status") != "success":
        raise RuntimeError("provider A returned failure")
    return {"country": d.get("country"), "city": d.get("city")}


def provider_b(ip: str) -> dict:
    """ipapi.co"""
    if _mock_on():
        if os.getenv("GEO_B_DOWN") == "1":
            raise RuntimeError("mock provider B is down")
        return {"country": "Mockland-B", "city": "B-City"}
    r = httpx.get(f"https://ipapi.co/{ip}/json/", timeout=TIMEOUT)
    r.raise_for_status()
    d = r.json()
    if d.get("error"):
        raise RuntimeError("provider B returned failure")
    return {"country": d.get("country_name"), "city": d.get("city")}


PROVIDERS = [provider_a, provider_b]


def lookup_geo(ip: str):
    """Try each provider in order. Return None if all fail, never raise."""
    for provider in PROVIDERS:
        try:
            return provider(ip)
        except Exception as e:
            print(f"[geo] {provider.__name__} failed: {e}")
    return None