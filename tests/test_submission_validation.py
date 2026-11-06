"""Probe 1 and Probe 2: valid submissions are stored and visible; malformed and
oversized payloads get clean 4xx JSON errors, never a 500."""
import asyncio

import pytest

from app.middleware import BodyLimitMiddleware
from tests.conftest import auth, submission_count


def test_probe1_valid_submission_is_stored_and_visible_in_the_dashboard(client, make_widget, submit):
    widget = make_widget()
    response = submit(widget["id"], {"email": "ada@example.com", "name": "Ada"})
    assert response.status_code == 201
    body = response.json()
    assert body["widget_id"] == widget["id"]
    assert body["data"] == {"email": "ada@example.com", "name": "Ada"}
    assert body["country"] == "Mockland-A"  # enriched

    rows = client.get(f"/dashboard/widgets/{widget['id']}/submissions", headers=auth()).json()
    assert [r["id"] for r in rows] == [body["id"]]


def test_submission_is_linked_to_the_right_widget_and_tenant(client, make_widget, submit):
    a = make_widget("tenant-a")
    b = make_widget("tenant-b")
    submit(a["id"])
    submit(b["id"])
    from app.database import SessionLocal
    from app import models

    with SessionLocal() as db:
        by_widget = {s.widget_id: s.tenant_id for s in db.query(models.Submission)}
    assert by_widget == {a["id"]: "tenant-a", b["id"]: "tenant-b"}


def test_unknown_widget_is_a_clean_404(submit):
    response = submit("no-such-widget")
    assert response.status_code == 404
    assert response.json()["detail"] == "Widget not found"


MALFORMED = [
    ("not json at all", {"content": "{this is not json", "headers": {"Content-Type": "application/json"}}),
    ("empty body", {"content": "", "headers": {"Content-Type": "application/json"}}),
    ("json array", {"json": []}),
    ("json null", {"json": None}),
    ("missing data", {"json": {}}),
    ("data is a string", {"json": {"data": "x"}}),
    ("data is a list", {"json": {"data": ["a"]}}),
    ("nested object value", {"json": {"data": {"email": {"a": 1}}}}),
    ("unexpected top-level key", {"json": {"data": {"email": "a@b.co"}, "evil": "x"}}),
    ("too many fields", {"json": {"data": {f"f{i}": "x" for i in range(21)}}}),
    ("value too long", {"json": {"data": {"email": "x" * 2001}}}),
    ("field name too long", {"json": {"data": {"k" * 65: "x"}}}),
]


@pytest.mark.parametrize("name,kwargs", MALFORMED, ids=[m[0] for m in MALFORMED])
def test_probe2_malformed_payloads_get_a_json_422(client, make_widget, name, kwargs):
    wid = make_widget()["id"]
    response = client.post(f"/submissions?widget_id={wid}", **kwargs)
    assert response.status_code == 422, response.text
    assert "detail" in response.json()
    assert submission_count(wid) == 0


def test_values_are_checked_against_the_widgets_field_definitions(client, make_widget, submit):
    wid = make_widget()["id"]
    cases = {
        "missing required field": {"name": "No Email"},
        "blank required field": {"email": "   "},
        "invalid email": {"email": "not-an-email"},
        "unknown field": {"email": "a@b.co", "extra": "x"},
        "email as number": {"email": 12345},
    }
    for label, data in cases.items():
        response = submit(wid, data)
        assert response.status_code == 422, label
        body = response.json()
        assert body["errors"], label
    assert submission_count(wid) == 0


def test_number_and_phone_fields(client, make_widget, submit):
    wid = make_widget(
        fields=[
            {"name": "age", "label": "Age", "type": "number"},
            {"name": "phone", "label": "Phone", "type": "tel"},
        ]
    )["id"]
    assert submit(wid, {"age": 33, "phone": "+92 300 1234567"}).status_code == 201
    assert submit(wid, {"age": "abc"}).status_code == 422
    assert submit(wid, {"phone": "call me maybe"}).status_code == 422


def test_probe2_oversized_payload_gets_a_json_413(client, make_widget):
    wid = make_widget()["id"]
    response = client.post(
        f"/submissions?widget_id={wid}", json={"data": {"email": "a" * 11_000}}
    )
    assert response.status_code == 413
    assert response.json() == {"detail": "Payload too large"}
    assert submission_count(wid) == 0


def test_oversized_chunked_body_without_content_length_is_still_413(client, make_widget):
    wid = make_widget()["id"]

    def chunks():
        for _ in range(5):
            yield b"x" * 4000  # 20 KB total, streamed with no Content-Length

    response = client.post(
        f"/submissions?widget_id={wid}",
        content=chunks(),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413


def test_garbage_content_length_header_is_a_400_not_a_500():
    sent = []

    async def app(scope, receive, send):  # never reached
        raise AssertionError("request should have been rejected")

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/submissions",
        "headers": [(b"content-length", b"not-a-number")],
    }
    asyncio.run(BodyLimitMiddleware(app)(scope, receive, send))
    assert sent[0]["status"] == 400


def test_no_server_errors_on_hostile_but_well_formed_input(client, make_widget):
    wid = make_widget()["id"]
    hostile = [
        {"data": {"email": "a@b.co", "name": "'; DROP TABLE submissions;--"}},
        {"data": {"email": "a@b.co", "name": "<script>alert(1)</script>"}},
        {"data": {"email": "a@b.co", "name": "\u0000‮ emoji \U0001f600"}},
    ]
    for body in hostile:
        response = client.post(f"/submissions?widget_id={wid}", json=body)
        assert response.status_code < 500, body
    assert client.get("/health").status_code == 200
