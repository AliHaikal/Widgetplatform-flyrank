"""Section 6: widget management, multi-tenant isolation, embed snippet."""
from unittest.mock import patch

from tests.conftest import auth, submission_count


# --- authentication ----------------------------------------------------------

def test_requests_without_a_token_are_rejected(client):
    for method, path in [
        ("get", "/widgets"),
        ("post", "/widgets"),
        ("get", "/dashboard/overview"),
        ("get", "/widgets/abc/embed"),
    ]:
        response = getattr(client, method)(path)
        assert response.status_code == 401, (method, path)
        assert "detail" in response.json()


def test_invalid_tokens_are_rejected(client):
    for header in ["Bearer", "Bearer ", "Bearer nope", "Bearer dev:bad token!", "Basic abc"]:
        response = client.get("/widgets", headers={"Authorization": header})
        assert response.status_code == 401, header


def test_supabase_mode_rejects_a_token_supabase_does_not_accept(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "k")

    class Rejected:
        status_code = 401

    with patch("app.auth.httpx.get", return_value=Rejected()):
        response = client.get("/widgets", headers={"Authorization": "Bearer forged"})
    assert response.status_code == 401


def test_supabase_user_id_becomes_the_tenant(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "k")

    class Accepted:
        status_code = 200

        @staticmethod
        def json():
            return {"id": "7158c5da-7d0f-4c2c-8c11-0eea8f014122"}

    body = {
        "type": "signup_form",
        "title": "T",
        "fields": [{"name": "email", "label": "Email", "type": "email"}],
    }
    with patch("app.auth.httpx.get", return_value=Accepted()):
        response = client.post("/widgets", json=body, headers={"Authorization": "Bearer real"})
    assert response.status_code == 201
    assert response.json()["tenant_id"] == "7158c5da-7d0f-4c2c-8c11-0eea8f014122"


def test_supabase_mode_without_config_is_a_clean_503_not_a_crash(client, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "supabase")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    response = client.get("/widgets", headers={"Authorization": "Bearer x"})
    assert response.status_code == 503
    assert response.json()["detail"]


# --- CRUD --------------------------------------------------------------------

def test_crud_lifecycle_with_correct_status_codes(client, make_widget):
    widget = make_widget()
    assert widget["tenant_id"] == "tenant-a"
    wid = widget["id"]

    assert client.get(f"/widgets/{wid}", headers=auth()).status_code == 200
    assert [w["id"] for w in client.get("/widgets", headers=auth()).json()] == [wid]

    patched = client.patch(f"/widgets/{wid}", json={"title": "Renamed"}, headers=auth())
    assert patched.status_code == 200
    assert patched.json()["title"] == "Renamed"
    assert patched.json()["button_text"] == "Subscribe"  # untouched fields survive

    assert client.delete(f"/widgets/{wid}", headers=auth()).status_code == 204
    assert client.get(f"/widgets/{wid}", headers=auth()).status_code == 404
    assert client.delete(f"/widgets/{wid}", headers=auth()).status_code == 404


def test_patch_cannot_null_out_required_columns(client, make_widget):
    wid = make_widget()["id"]
    response = client.patch(f"/widgets/{wid}", json={"title": None}, headers=auth())
    assert response.status_code == 200
    assert response.json()["title"] == "Newsletter"


def test_widget_definitions_are_validated(client):
    bad_bodies = [
        {"type": "banner", "title": "T", "fields": [{"name": "e", "label": "E"}]},
        {"type": "signup_form", "title": "", "fields": [{"name": "e", "label": "E"}]},
        {"type": "signup_form", "title": "T", "fields": []},
        {"type": "signup_form", "title": "T", "fields": [{"name": "1bad", "label": "E"}]},
        {"type": "signup_form", "title": "T", "fields": [{"name": "e", "label": "E", "type": "color"}]},
        {"type": "signup_form", "title": "T", "fields": [{"name": "e", "label": "E"}], "tenant_id": "evil"},
    ]
    for body in bad_bodies:
        response = client.post("/widgets", json=body, headers=auth())
        assert response.status_code == 422, body
        assert "detail" in response.json()


def test_deleting_a_widget_removes_its_submissions(client, make_widget, submit):
    wid = make_widget()["id"]
    assert submit(wid).status_code == 201
    assert submission_count(wid) == 1
    client.delete(f"/widgets/{wid}", headers=auth())
    assert submission_count(wid) == 0


# --- tenant isolation --------------------------------------------------------

def test_tenant_b_cannot_read_or_modify_tenant_a(client, make_widget, submit):
    wid = make_widget("tenant-a")["id"]
    assert submit(wid).status_code == 201
    b = auth("tenant-b")

    assert client.get(f"/widgets/{wid}", headers=b).status_code == 404
    assert client.patch(f"/widgets/{wid}", json={"title": "pwned"}, headers=b).status_code == 404
    assert client.delete(f"/widgets/{wid}", headers=b).status_code == 404
    assert client.get(f"/widgets/{wid}/embed", headers=b).status_code == 404
    assert client.get(f"/dashboard/widgets/{wid}/submissions", headers=b).status_code == 404
    assert client.get(f"/dashboard/widgets/{wid}/stats", headers=b).status_code == 404
    assert client.get("/widgets", headers=b).json() == []
    assert client.get("/dashboard/overview", headers=b).json() == []

    # ...and tenant A is untouched by all of that.
    mine = client.get(f"/widgets/{wid}", headers=auth("tenant-a")).json()
    assert mine["title"] == "Newsletter"
    rows = client.get(f"/dashboard/widgets/{wid}/submissions", headers=auth("tenant-a")).json()
    assert len(rows) == 1


def test_each_tenant_only_sees_their_own_widgets(client, make_widget):
    a = make_widget("tenant-a", title="A-widget")["id"]
    b = make_widget("tenant-b", title="B-widget")["id"]
    assert [w["id"] for w in client.get("/widgets", headers=auth("tenant-a")).json()] == [a]
    assert [w["id"] for w in client.get("/widgets", headers=auth("tenant-b")).json()] == [b]


# --- embed snippet -----------------------------------------------------------

def test_embed_snippet_is_one_script_tag_with_the_widget_id(client, make_widget):
    wid = make_widget()["id"]
    response = client.get(f"/widgets/{wid}/embed", headers=auth())
    assert response.status_code == 200
    snippet = response.json()["snippet"]
    assert snippet.startswith("<script src=") and snippet.endswith("></script>")
    assert f"?id={wid}" in snippet and "/widget.v2.js" in snippet
