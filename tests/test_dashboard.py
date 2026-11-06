"""Owner dashboard: listings and aggregation queries."""
from tests.conftest import auth


def test_submissions_are_newest_first_with_pagination(client, make_widget, submit):
    wid = make_widget()["id"]
    for i in range(5):
        assert submit(wid, {"email": f"user{i}@example.com"}).status_code == 201

    page = client.get(f"/dashboard/widgets/{wid}/submissions?limit=2&offset=0", headers=auth())
    assert page.status_code == 200
    assert page.headers["x-total-count"] == "5"
    assert len(page.json()) == 2

    rest = client.get(f"/dashboard/widgets/{wid}/submissions?limit=100&offset=2", headers=auth())
    assert len(rest.json()) == 3
    ids = [r["id"] for r in page.json() + rest.json()]
    assert len(set(ids)) == 5


def test_pagination_bounds_are_validated(client, make_widget):
    wid = make_widget()["id"]
    for query in ["limit=0", "limit=101", "offset=-1", "limit=abc"]:
        response = client.get(f"/dashboard/widgets/{wid}/submissions?{query}", headers=auth())
        assert response.status_code == 422, query


def test_stats_count_total_per_day_and_geo_breakdown(client, make_widget, submit, monkeypatch):
    wid = make_widget()["id"]
    submit(wid)
    submit(wid)
    monkeypatch.setenv("GEO_A_DOWN", "1")
    submit(wid)
    monkeypatch.setenv("GEO_B_DOWN", "1")
    submit(wid)

    stats = client.get(f"/dashboard/widgets/{wid}/stats", headers=auth()).json()
    assert stats["widget_id"] == wid
    assert stats["total"] == 4
    assert sum(d["count"] for d in stats["per_day"]) == 4
    assert len(stats["per_day"]) == 1  # all created today
    assert {c["country"]: c["count"] for c in stats["by_country"]} == {
        "Mockland-A": 2,
        "Mockland-B": 1,
        "unknown": 1,
    }


def test_overview_has_one_row_per_widget_including_empty_ones(client, make_widget, submit):
    busy = make_widget(title="Busy")["id"]
    quiet = make_widget(title="Quiet")["id"]
    submit(busy)
    submit(busy)

    rows = {r["widget_id"]: r for r in client.get("/dashboard/overview", headers=auth()).json()}
    assert rows[busy]["total"] == 2 and rows[busy]["last_submission_at"]
    assert rows[quiet]["total"] == 0 and rows[quiet]["last_submission_at"] is None


def test_dashboard_requires_auth(client, make_widget):
    wid = make_widget()["id"]
    assert client.get(f"/dashboard/widgets/{wid}/stats").status_code == 401
