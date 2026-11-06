"""Shared requirement: the retried action happens once."""
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import submission_count

KEY = {"Idempotency-Key": "retry-key-0001"}


def test_same_key_stores_one_row_and_returns_the_original(make_widget, submit):
    wid = make_widget()["id"]
    first = submit(wid, headers=KEY)
    second = submit(wid, headers=KEY)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.headers["idempotent-replay"] == "true"
    assert second.json()["id"] == first.json()["id"]
    assert submission_count(wid) == 1


def test_the_side_effect_also_happens_once(make_widget, submit, caplog):
    caplog.set_level(logging.INFO, logger="app.notify")
    wid = make_widget()["id"]
    for _ in range(3):
        submit(wid, headers=KEY)
    sent = [r for r in caplog.records if "Confirmation sent" in r.getMessage()]
    assert len(sent) == 1


def test_different_keys_and_missing_keys_are_independent(make_widget, submit):
    wid = make_widget()["id"]
    assert submit(wid, headers={"Idempotency-Key": "key-aaaaaaaa"}).status_code == 201
    assert submit(wid, headers={"Idempotency-Key": "key-bbbbbbbb"}).status_code == 201
    assert submit(wid).status_code == 201
    assert submit(wid).status_code == 201  # no key = no dedupe
    assert submission_count(wid) == 4


def test_the_same_key_on_a_different_widget_is_not_a_replay(make_widget, submit):
    one = make_widget(title="One")["id"]
    two = make_widget(title="Two")["id"]
    assert submit(one, headers=KEY).status_code == 201
    assert submit(two, headers=KEY).status_code == 201


def test_malformed_keys_are_rejected(make_widget, submit):
    wid = make_widget()["id"]
    for bad in ["short", "has spaces in it", "x" * 129, "semi;colon-key"]:
        assert submit(wid, headers={"Idempotency-Key": bad}).status_code == 422, bad
    assert submission_count(wid) == 0


def test_simultaneous_retries_still_store_exactly_one_row(make_widget):
    wid = make_widget()["id"]

    def fire(_):
        with TestClient(app, raise_server_exceptions=False) as c:
            return c.post(
                f"/submissions?widget_id={wid}",
                json={"data": {"email": "race@example.com"}},
                headers=KEY,
            ).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(fire, range(8)))

    assert statuses.count(201) == 1
    assert set(statuses) <= {200, 201}
    assert submission_count(wid) == 1
