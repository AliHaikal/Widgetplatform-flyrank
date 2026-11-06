# Build log (honest AI-usage record)

**Who did what.** I (Ali) chose the stack and design (FastAPI, SQLite, Supabase JWT, signup form + CTA popover),
created the repo, and built the first version step by step with Claude's guidance: models, widget CRUD, submissions,
geo fallback, email retry, rate limiting. After I lost my PC and laptop, Claude (Sonnet 5.5, in Claude Code on the web)
rewrote and finished most of the later code in my repo and ran the tests and live proofs. Most of the current code was
written by Claude; I reviewed behaviour via the evidence, not every line.

**Problems found and fixed in my earlier version**
- `requirements.txt` was UTF-16 (from PowerShell `pip freeze >`) so pip couldn't read it -> rewritten as UTF-8 ranges.
- Duplicate `/config` route (FastAPI "Duplicate Operation ID").
- Body-limit middleware crashed on a bad `Content-Length` and missed chunked uploads -> now 400 / 413.
- No migrations -> added Alembic (0001 schema + indexes, 0002 idempotency key). Added layered routers/services/repos.
- No idempotency, no honeypot, no stats endpoints, CORS headers missing on 429/413 -> added, with tests.
- slowapi replaced by `limits` for per-IP + per-widget windows.

**Things Claude got wrong along the way:** it first rebuilt too much when I wanted step-by-step; seed script hit
DetachedInstanceError (fixed with `expire_on_commit=False`); an evidence script bug made all outputs "command not found" (fixed, rerun).

**What I should be able to explain:** (1) why 404 not 403 across tenants; (2) why idempotency uses a DB unique
constraint instead of check-then-insert; (3) why email runs in a background task with retries and an alert.

**Environment pain (Windows):** Python 3.15 had no wheels -> use 3.11; execution policy blocks venv activation.
