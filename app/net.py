from . import config


def client_ip(scope) -> str:
    """Caller's IP from an ASGI scope.

    X-Forwarded-For is only honoured when TRUST_FORWARDED_FOR=1, i.e. when the
    app really sits behind a proxy you control. Otherwise any visitor could
    spoof it to dodge the rate limiter.
    """
    if config.flag("TRUST_FORWARDED_FOR"):
        for key, value in scope.get("headers", []):
            if key == b"x-forwarded-for":
                first = value.decode("latin-1").split(",")[0].strip()
                if first:
                    return first
    client = scope.get("client")
    return client[0] if client else "unknown"
