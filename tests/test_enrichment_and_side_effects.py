"""Probe 4 and Probe 5: geo provider fallback, and a failing email never breaks a
submission (it is a background job with retries and an alert)."""
import logging

import httpx

from tests.conftest import auth, submission_count


def _country(client, widget_id):
    rows = client.get(f"/dashboard/widgets/{widget_id}/submissions", headers=auth()).json()
    return rows[0]["country"], rows[0]["city"]


# --- Probe 4: geo fallback chain ---------------------------------------------

def test_probe4_provider_a_answers(client, make_widget, submit):
    wid = make_widget()["id"]
    assert submit(wid).status_code == 201
    assert _country(client, wid) == ("Mockland-A", "A-City")


def test_probe4_provider_a_down_then_provider_b_enriches(client, make_widget, submit, monkeypatch):
    monkeypatch.setenv("GEO_A_DOWN", "1")
    wid = make_widget()["id"]
    assert submit(wid).status_code == 201
    assert _country(client, wid) == ("Mockland-B", "B-City")


def test_probe4_both_providers_down_submission_still_stored_without_geo(
    client, make_widget, submit, monkeypatch, caplog
):
    monkeypatch.setenv("GEO_A_DOWN", "1")
    monkeypatch.setenv("GEO_B_DOWN", "1")
    caplog.set_level(logging.WARNING, logger="app.geo")
    wid = make_widget()["id"]
    response = submit(wid)
    assert response.status_code == 201
    assert response.json()["country"] is None and response.json()["city"] is None
    assert submission_count(wid) == 1
    failed = [r.getMessage() for r in caplog.records if "failed" in r.getMessage()]
    assert any("provider_a" in m for m in failed) and any("provider_b" in m for m in failed)


def test_real_providers_erroring_also_degrades_gracefully(client, make_widget, monkeypatch):
    """No mock: simulate both real HTTP APIs being unreachable for a public IP."""
    monkeypatch.setenv("GEO_MOCK", "0")
    monkeypatch.setenv("TRUST_FORWARDED_FOR", "1")

    def boom(*_args, **_kwargs):
        raise httpx.ConnectError("network down")

    monkeypatch.setattr("app.geo.httpx.get", boom)
    wid = make_widget()["id"]
    response = client.post(
        f"/submissions?widget_id={wid}",
        json={"data": {"email": "a@b.co"}},
        headers={"X-Forwarded-For": "8.8.8.8"},
    )
    assert response.status_code == 201
    assert response.json()["country"] is None


def test_private_addresses_do_not_call_the_real_apis(client, make_widget, submit, monkeypatch):
    monkeypatch.setenv("GEO_MOCK", "0")

    def must_not_be_called(*_a, **_k):
        raise AssertionError("loopback/private IPs must not hit the geo APIs")

    monkeypatch.setattr("app.geo.httpx.get", must_not_be_called)
    wid = make_widget()["id"]
    assert submit(wid).status_code == 201  # test client IP is not a public address


# --- Probe 5: safe side effect -----------------------------------------------

def test_confirmation_email_is_sent_after_a_successful_submission(make_widget, submit, caplog):
    caplog.set_level(logging.INFO, logger="app.notify")
    wid = make_widget()["id"]
    assert submit(wid, {"email": "ada@example.com"}).status_code == 201
    sent = [r for r in caplog.records if "Confirmation sent" in r.getMessage()]
    assert len(sent) == 1


def test_probe5_failing_email_does_not_break_the_submission(
    client, make_widget, submit, monkeypatch, caplog
):
    monkeypatch.setenv("EMAIL_FAIL", "1")
    caplog.set_level(logging.INFO, logger="app.notify")
    wid = make_widget()["id"]

    response = submit(wid)
    assert response.status_code == 201  # still success
    assert submission_count(wid) == 1  # and stored
    rows = client.get(f"/dashboard/widgets/{wid}/submissions", headers=auth()).json()
    assert len(rows) == 1


def test_failing_email_is_retried_then_alerts(make_widget, submit, monkeypatch, caplog):
    monkeypatch.setenv("EMAIL_FAIL", "1")
    caplog.set_level(logging.INFO, logger="app.notify")
    wid = make_widget()["id"]
    assert submit(wid).status_code == 201

    messages = [(r.levelname, r.getMessage()) for r in caplog.records]
    attempts = [m for lvl, m in messages if lvl == "WARNING" and "attempt" in m]
    alerts = [m for lvl, m in messages if lvl == "ERROR" and "[ALERT]" in m]
    assert len(attempts) == 3
    assert len(alerts) == 1
    assert not any("Confirmation sent" in m for _, m in messages)
