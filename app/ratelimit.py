"""Fixed-window rate limiting (per IP and per widget) on the `limits` library.

Storage is in-process memory: fine for one worker. With several workers, point
`limits` at Redis instead (documented in the README limitations).
"""
import math
import time

from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import FixedWindowRateLimiter

from . import config

storage = MemoryStorage()
_strategy = FixedWindowRateLimiter(storage)


def reset() -> None:
    """Forget all counters (used by tests)."""
    storage.reset()


def _hit(namespace: str, key: str, limit: str):
    item = parse(limit)
    if _strategy.hit(item, namespace, key):
        return None
    stats = _strategy.get_window_stats(item, namespace, key)
    return max(1, math.ceil(stats.reset_time - time.time()))


def check_submission(ip: str, widget_id: str | None):
    """Return None if allowed, else the number of seconds to wait."""
    retry = _hit("ip", ip, config.get("RATE_LIMIT_PER_IP", "10/minute"))
    if retry is not None:
        return retry
    if widget_id:
        return _hit(
            "widget",
            widget_id[:64],
            config.get("RATE_LIMIT_PER_WIDGET", "120/minute"),
        )
    return None
