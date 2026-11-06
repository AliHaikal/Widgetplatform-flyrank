"""Confirmation email: a non-critical side effect that runs as a background job.

It runs after the HTTP response has been sent, retries with exponential
backoff, and raises an ALERT log line if every attempt fails. The submission
is already stored by then, so a failure here can never undo or block it.
"""
import logging
import time

from . import config

log = logging.getLogger("app.notify")


def send_confirmation(widget_title: str, submission_data: dict) -> None:
    """Fake email: logs to the console. EMAIL_FAIL=1 forces a failure."""
    if config.flag("EMAIL_FAIL"):
        raise RuntimeError("mock email service is down")
    log.info("[email] Confirmation sent for widget '%s': %s", widget_title, submission_data)


def send_with_retry(widget_title: str, submission_data: dict, attempts: int = 3) -> None:
    base = float(config.get("EMAIL_RETRY_BASE_SECONDS", "1") or 1)
    for attempt in range(1, attempts + 1):
        try:
            send_confirmation(widget_title, submission_data)
            return
        except Exception as exc:  # noqa: BLE001
            log.warning("[email] attempt %d/%d failed: %s", attempt, attempts, exc)
            if attempt < attempts:
                time.sleep(base * (2 ** (attempt - 1)))
    log.error("[ALERT] confirmation email permanently failed for widget '%s'", widget_title)
