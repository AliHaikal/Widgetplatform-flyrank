"""Seed demo data: two tenants, each with a signup form and a CTA popover.

    python -m scripts.seed

Safe to run repeatedly. Prints the widget ids, ready-to-use demo tokens
(AUTH_MODE=dev) and the embed snippets.
"""
from app import models
from app.database import SessionLocal

DEMO = {
    "tenant-a": [
        {
            "type": "signup_form",
            "title": "Newsletter Signup",
            "description": "Join our list",
            "fields": [
                {"name": "email", "label": "Email", "type": "email", "required": True},
                {"name": "name", "label": "Name", "type": "text", "required": False},
            ],
            "button_text": "Subscribe",
            "display_options": {},
        },
        {
            "type": "cta_popover",
            "title": "Get the free guide",
            "description": "One email, no spam",
            "fields": [{"name": "email", "label": "Email", "type": "email", "required": True}],
            "button_text": "Send it to me",
            "display_options": {
                "trigger_label": "Free guide",
                "position": "bottom-right",
                "delay_seconds": 1,
                "success_message": "Check your inbox!",
            },
        },
    ],
    "tenant-b": [
        {
            "type": "signup_form",
            "title": "Beta Waitlist",
            "description": "Be first in line",
            "fields": [{"name": "email", "label": "Email", "type": "email", "required": True}],
            "button_text": "Join waitlist",
            "display_options": {},
        },
    ],
}


def seed() -> list[models.Widget]:
    created: list[models.Widget] = []
    # expire_on_commit=False: callers read the widgets after the session closes.
    with SessionLocal(expire_on_commit=False) as db:
        for tenant, widgets in DEMO.items():
            for spec in widgets:
                widget = (
                    db.query(models.Widget)
                    .filter_by(tenant_id=tenant, title=spec["title"])
                    .first()
                )
                if widget is None:
                    widget = models.Widget(tenant_id=tenant, **spec)
                    db.add(widget)
                    db.commit()
                    db.refresh(widget)
                created.append(widget)
    return created


def main() -> None:
    widgets = seed()
    print("Seeded demo data (run with AUTH_MODE=dev to use the demo tokens):\n")
    for w in widgets:
        print(f"  {w.tenant_id:9} {w.type:12} {w.id}  {w.title}")
        print(f'    <script src="http://127.0.0.1:8000/widget.v1.js?id={w.id}"></script>')
    print("\nDemo tokens:  Authorization: Bearer dev:tenant-a   |   Bearer dev:tenant-b")


if __name__ == "__main__":
    main()
