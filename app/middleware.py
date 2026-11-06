"""Pure-ASGI middleware guarding the public submission endpoint.

Order (outermost first): CORS -> rate limit -> body limit -> app.
CORS is outermost so that 429/413 responses still carry CORS headers and the
browser lets the widget read them.
"""
import json
from urllib.parse import parse_qs

from . import config, ratelimit
from .net import client_ip


async def send_json(send, status: int, body: dict, headers: dict | None = None):
    payload = json.dumps(body).encode()
    raw_headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(payload)).encode()),
    ]
    for key, value in (headers or {}).items():
        raw_headers.append((key.lower().encode(), str(value).encode()))
    await send({"type": "http.response.start", "status": status, "headers": raw_headers})
    await send({"type": "http.response.body", "body": payload})


class RateLimitMiddleware:
    """Counts every POST /submissions, valid or not, before any parsing."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] == "http"
            and scope["method"] == "POST"
            and scope["path"] == "/submissions"
        ):
            query = parse_qs(scope.get("query_string", b"").decode("latin-1"))
            widget_id = (query.get("widget_id") or [None])[0]
            retry_after = ratelimit.check_submission(client_ip(scope), widget_id)
            if retry_after is not None:
                await send_json(
                    send,
                    429,
                    {"detail": "Rate limit exceeded", "retry_after": retry_after},
                    {"Retry-After": retry_after},
                )
                return
        await self.app(scope, receive, send)


class BodyLimitMiddleware:
    """Rejects oversized bodies with 413, including chunked uploads that lie
    about (or omit) Content-Length, and malformed Content-Length with 400."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PUT", "PATCH"):
            await self.app(scope, receive, send)
            return

        max_bytes = config.get_int("MAX_BODY_BYTES", 10_000)

        for key, value in scope.get("headers", []):
            if key == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    await send_json(send, 400, {"detail": "Invalid Content-Length"})
                    return
                if declared > max_bytes:
                    await send_json(send, 413, {"detail": "Payload too large"})
                    return

        # Read the body up to the limit, then replay it to the app.
        chunks: list[bytes] = []
        total = 0
        more = True
        while more:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            total += len(body)
            if total > max_bytes:
                await send_json(send, 413, {"detail": "Payload too large"})
                return
            chunks.append(body)
            more = message.get("more_body", False)

        replayed = False

        async def replay():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
