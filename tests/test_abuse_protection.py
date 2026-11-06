"""Probe 3 and Probe 6: a flood gets 429s while the service stays up and normal
traffic is still served; a bot filling the honeypot is rejected."""
from tests.conftest import auth, submission_count


def _post(client, wid, ip, email="v@example.com"):
    return client.post(
        f"/submissions?widget_id={wid}",
        json={"data": {"email": email}},
        headers={"X-Forwarded-For": ip},
    )


def test_probe3_burst_gets_429_and_legitimate_traffic_still_succeeds(client, make_widget, monkeypatch):
    monkeypatch.setenv("TRUST_FORWARDED_FOR", "1")
    monkeypatch.setenv("RATE_LIMIT_PER_IP", "3/minute")
    wid = make_widget()["id"]

    attacker = [_post(client, wid, "203.0.113.9").status_code for _ in range(6)]
    assert attacker == [201, 201, 201, 429, 429, 429]

    limited = _post(client, wid, "203.0.113.9")
    assert limited.status_code == 429
    assert limited.json()["detail"] == "Rate limit exceeded"
    assert int(limited.headers["retry-after"]) >= 1

    # A normal visitor right after the burst is served...
    assert _post(client, wid, "198.51.100.7").status_code == 201
    # ...and so is everything else.
    assert client.get("/health").status_code == 200
    assert client.get(f"/widgets/{wid}/config").status_code == 200
    assert client.get("/widgets", headers=auth()).status_code == 200
    assert submission_count(wid) == 4  # 3 from the attacker, 1 legitimate


def test_requests_rejected_by_validation_still_count_toward_the_limit(client, make_widget, monkeypatch):
    """Otherwise an attacker could hammer the endpoint with junk for free."""
    monkeypatch.setenv("TRUST_FORWARDED_FOR", "1")
    monkeypatch.setenv("RATE_LIMIT_PER_IP", "3/minute")
    wid = make_widget()["id"]
    statuses = [
        client.post(
            f"/submissions?widget_id={wid}",
            content="{garbage",
            headers={"Content-Type": "application/json", "X-Forwarded-For": "203.0.113.50"},
        ).status_code
        for _ in range(5)
    ]
    assert statuses == [422, 422, 422, 429, 429]


def test_per_widget_limit_protects_one_widget_from_a_distributed_flood(client, make_widget, monkeypatch):
    monkeypatch.setenv("TRUST_FORWARDED_FOR", "1")
    monkeypatch.setenv("RATE_LIMIT_PER_WIDGET", "2/minute")
    flooded = make_widget(title="Flooded")["id"]
    other = make_widget(title="Other")["id"]

    codes = [_post(client, flooded, f"192.0.2.{i}").status_code for i in range(1, 5)]
    assert codes == [201, 201, 429, 429]  # different IPs, same widget
    assert _post(client, other, "192.0.2.1").status_code == 201  # other widgets unaffected


def test_forwarded_for_is_ignored_unless_explicitly_trusted(client, make_widget, monkeypatch):
    """Otherwise a spoofed header would let anyone dodge the per-IP limit."""
    monkeypatch.setenv("RATE_LIMIT_PER_IP", "2/minute")  # TRUST_FORWARDED_FOR stays off
    wid = make_widget()["id"]
    codes = [_post(client, wid, f"198.51.100.{i}").status_code for i in range(1, 5)]
    assert codes == [201, 201, 429, 429]


def test_probe6_filled_honeypot_is_rejected_and_not_stored(client, make_widget, submit):
    wid = make_widget()["id"]
    response = submit(wid, {"email": "bot@spam.example"}, honeypot="i-am-a-bot")
    assert response.status_code == 422
    assert submission_count(wid) == 0


def test_empty_honeypot_is_accepted(make_widget, submit):
    wid = make_widget()["id"]
    assert submit(wid, honeypot="").status_code == 201
