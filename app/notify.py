import os
import time


def send_confirmation(widget_title: str, submission_data: dict) -> None:
    """Fake email: prints to console. Can be forced to fail for testing."""
    if os.getenv("EMAIL_FAIL") == "1":
        raise RuntimeError("mock email service is down")
    print(f"[email] Confirmation sent for widget '{widget_title}': {submission_data}")


def send_with_retry(widget_title: str, submission_data: dict, attempts: int = 3) -> None:
    """Runs in the background. Retries with backoff, alerts if all attempts fail."""
    for attempt in range(1, attempts + 1):
        try:
            send_confirmation(widget_title, submission_data)
            return
        except Exception as e:
            print(f"[email] attempt {attempt}/{attempts} failed: {e}")
            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))  # waits 1s, then 2s
    print(f"[ALERT] confirmation email permanently failed for widget '{widget_title}'")