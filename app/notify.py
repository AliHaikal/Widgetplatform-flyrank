import os


def send_confirmation(widget_title: str, submission_data: dict) -> None:
    """Fake email: prints to console. Can be forced to fail for testing."""
    if os.getenv("EMAIL_FAIL") == "1":
        raise RuntimeError("mock email service is down")
    print(f"[email] Confirmation sent for widget '{widget_title}': {submission_data}")