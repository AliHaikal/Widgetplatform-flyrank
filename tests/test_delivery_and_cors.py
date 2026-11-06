"""Section 6: widget delivery (cache headers, versioned bundle) and CORS."""
ORIGIN = {"Origin": "http://customer-site.example"}


def test_public_config_needs_no_auth_and_leaks_no_tenant(client, make_widget):
    wid = make_widget()["id"]
    response = client.get(f"/widgets/{wid}/config")
    assert response.status_code == 200
    body = response.json()
    assert "tenant_id" not in body
    assert body["id"] == wid and body["fields"][0]["name"] == "email"


def test_config_has_a_short_lived_cache_header(client, make_widget):
    wid = make_widget()["id"]
    response = client.get(f"/widgets/{wid}/config")
    assert response.headers["cache-control"] == "public, max-age=60"


def test_unknown_widget_config_is_a_json_404(client):
    response = client.get("/widgets/does-not-exist/config")
    assert response.status_code == 404
    assert response.json()["detail"] == "Widget not found"


def test_bundle_is_versioned_with_a_long_immutable_cache(client):
    for version in ("v1", "v2"):
        response = client.get(f"/widget.{version}.js")
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]
        assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert client.get("/widget.v99.js").status_code == 404


def test_bundle_sends_an_idempotency_key_and_a_honeypot(client):
    script = client.get("/widget.v2.js").text
    assert "Idempotency-Key" in script and "honeypot" in script


def test_preflight_is_handled(client, make_widget):
    wid = make_widget()["id"]
    response = client.options(
        f"/submissions?widget_id={wid}",
        headers={
            **ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,idempotency-key",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "POST" in response.headers["access-control-allow-methods"]
    allowed = response.headers["access-control-allow-headers"].lower()
    assert "content-type" in allowed and "idempotency-key" in allowed


def test_cross_origin_submission_carries_cors_headers(client, make_widget, submit):
    wid = make_widget()["id"]
    response = submit(wid, headers=ORIGIN)
    assert response.status_code == 201
    assert response.headers["access-control-allow-origin"] == "*"


def test_error_responses_are_readable_cross_origin_too(client, make_widget, monkeypatch):
    """A browser hides 429/413 bodies unless they carry CORS headers."""
    monkeypatch.setenv("RATE_LIMIT_PER_IP", "1/minute")
    wid = make_widget()["id"]
    url = f"/submissions?widget_id={wid}"
    client.post(url, json={"data": {"email": "a@b.co"}}, headers=ORIGIN)
    limited = client.post(url, json={"data": {"email": "a@b.co"}}, headers=ORIGIN)
    assert limited.status_code == 429
    assert limited.headers["access-control-allow-origin"] == "*"
    assert limited.headers["access-control-expose-headers"].lower().find("retry-after") >= 0
