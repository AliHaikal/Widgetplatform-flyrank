"""Test harness. Environment is set BEFORE the app is imported so every test
runs against a throwaway SQLite file, dev auth, and mocked geo providers."""
import os
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="widgetplatform-tests-")
os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{_TMP}/test.db",
        "AUTH_MODE": "dev",
        "GEO_MOCK": "1",
        "GEO_A_DOWN": "0",
        "GEO_B_DOWN": "0",
        "EMAIL_FAIL": "0",
        "EMAIL_RETRY_BASE_SECONDS": "0",
        "RATE_LIMIT_PER_IP": "1000/minute",
        "RATE_LIMIT_PER_WIDGET": "1000/minute",
        "TRUST_FORWARDED_FOR": "0",
        "MAX_BODY_BYTES": "10000",
    }
)

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import ratelimit  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app import models  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """The schema comes from the real migrations, exactly as in production."""
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")


@pytest.fixture(autouse=True)
def clean_state():
    ratelimit.reset()
    with SessionLocal() as db:
        db.query(models.Submission).delete()
        db.query(models.Widget).delete()
        db.commit()
    yield


@pytest.fixture
def client():
    # raise_server_exceptions=False: a crash must surface as a 500 response,
    # which is exactly what the "never a 500" probes assert against.
    return TestClient(app, raise_server_exceptions=False)


def auth(tenant: str = "tenant-a") -> dict:
    return {"Authorization": f"Bearer dev:{tenant}"}


WIDGET_BODY = {
    "type": "signup_form",
    "title": "Newsletter",
    "description": "Join our list",
    "fields": [
        {"name": "email", "label": "Email", "type": "email", "required": True},
        {"name": "name", "label": "Name", "type": "text", "required": False},
    ],
    "button_text": "Subscribe",
}


@pytest.fixture
def make_widget(client):
    def _make(tenant: str = "tenant-a", **overrides) -> dict:
        body = {**WIDGET_BODY, **overrides}
        response = client.post("/widgets", json=body, headers=auth(tenant))
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture
def submit(client):
    def _submit(widget_id: str, data=None, headers=None, **extra):
        body = {"data": data if data is not None else {"email": "visitor@example.com"}, **extra}
        return client.post(f"/submissions?widget_id={widget_id}", json=body, headers=headers or {})

    return _submit


def submission_count(widget_id: str | None = None) -> int:
    with SessionLocal() as db:
        query = db.query(models.Submission)
        if widget_id:
            query = query.filter_by(widget_id=widget_id)
        return query.count()
