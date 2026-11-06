# Embeddable Widget & Lead-Capture Platform

FlyRank Backend capstone. Owners create widgets (signup form or CTA popover), paste one
`<script>` tag on any site, and visitors' submissions land in an owner dashboard API.

## Architecture

```
 Third-party site (any origin)              Owner (JWT)
        |  <script src=/widget.v2.js?id=>        |
        v                                        v
 +-------------------------- FastAPI ---------------------------+
 | middleware: CORS > RateLimit (IP + widget) > BodyLimit (10KB) |
 |  routers   widgets | submissions | dashboard | delivery       |
 |     |  (HTTP only: parse, status codes, headers)              |
 |  services  widget | submission | dashboard                    |
 |     |  (rules: field validation, geo, idempotency, tenancy)   |
 |  repositories  widget_repo | submission_repo (all SQL)        |
 +------+---------------------------+---------------------------+
        |                           | BackgroundTasks
   SQLite (Alembic migrations)   send_with_retry: 3 tries, backoff, [ALERT] log
        ^                           geo: ip-api.com -> ipapi.co -> null
   Supabase /auth/v1/user (or AUTH_MODE=dev)
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                   # AUTH_MODE=dev works with no Supabase
alembic upgrade head                                   # create schema
python -m scripts.seed                                 # 2 tenants, 3 widgets, prints ids + tokens
uvicorn app.main:app --host 127.0.0.1 --port 8000      # API + /docs
python -m http.server 5500 --directory test_site       # second origin
# open http://127.0.0.1:5500/?id=<widget id from seed>
pytest                                                 # 70 tests
```

## API

Owner endpoints need `Authorization: Bearer <token>` (Supabase access token, or `dev:<tenant>` when `AUTH_MODE=dev`).
The user id is the tenant: every query filters on it, other tenants get **404**, never 403.

| Method | Path | Notes |
|---|---|---|
| POST/GET | `/widgets` | create / list own |
| GET/PATCH/DELETE | `/widgets/{id}` | own only |
| GET | `/widgets/{id}/embed` | script snippet |
| GET | `/widgets/{id}/config` | public, `max-age=60`, no tenant id |
| GET | `/widget.v1.js`, `/widget.v2.js` | public, `max-age=31536000, immutable`; unknown version 404 |
| POST | `/submissions?widget_id=` | public. Optional `Idempotency-Key`. 201 new, 200 replay (`Idempotent-Replay: true`), 422 invalid, 413 too big, 429 rate limited |
| GET | `/dashboard/overview` | one row per widget |
| GET | `/dashboard/widgets/{id}/submissions` | `limit` 1-100, `offset`, `X-Total-Count` |
| GET | `/dashboard/widgets/{id}/stats` | total, per day, by country |
| GET | `/health` | pings DB |

## Probe toggles (deterministic proofs)

`GEO_MOCK=1` fake geo; `GEO_A_DOWN=1` / `GEO_B_DOWN=1` fail a provider; `EMAIL_FAIL=1` force email failure;
`RATE_LIMIT_PER_IP=5/minute`; `TRUST_FORWARDED_FOR=1` honour X-Forwarded-For (only behind a trusted proxy).

## Design decisions

- Rate limit counts requests *before* validation, so garbage can't be used to dodge it; per IP and per widget.
- Idempotency: unique `(widget_id, idempotency_key)`; a race loses on the constraint and returns the winner's row.
- Email is a background job so a slow/failed send never fails the visitor's submission; failures log `[ALERT]`.
- Widget uses shadow DOM so host-site CSS can't break it; bundles are versioned so they can be cached forever.

## Honest limitations

- Rate limiter is in-memory, per process: with several workers the limit multiplies. Needs Redis for production.
- SQLite, single node. The email "provider" is a logged stub, no real SMTP.
- Background retries live in the process: a crash mid-retry loses the job (no durable queue).
- Geo providers are free, unauthenticated tiers; their ToS/limits are not handled beyond fallback.
- `AUTH_MODE=dev` is for demos/tests only and must never be enabled in production.
- Not deployed publicly; everything runs on localhost (two ports to prove cross-origin).
