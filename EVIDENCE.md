# Evidence

All outputs below were captured from real uvicorn processes (AUTH_MODE=dev, GEO_MOCK=1, SQLite) and the real test suite on 2026-11-06. Widget ids differ per run.


## Migrations apply from empty DB; models match migrations

Section 6: real persistence (migrations + indexes). Indexes/constraint also asserted in tests/test_persistence.py.

```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, create widgets and submissions
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, add idempotency key to submissions
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.schemas
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.tables
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.types
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.constraints
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.defaults
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.comments
No new upgrade operations detected.
```

## Auth + widget CRUD + validation

Missing/forged token -> 401; create 201; PATCH 200; bad widget 422.

```
$ curl -si http://127.0.0.1:8000/widgets | head -12
HTTP/1.1 401 Unauthorized
content-length: 33
content-type: application/json
vary: Origin

{"detail":"Missing bearer token"}
$ curl -si http://127.0.0.1:8000/widgets -H 'Authorization: Bearer forged-token' | head -12
HTTP/1.1 401 Unauthorized
content-length: 37
content-type: application/json
vary: Origin

{"detail":"Invalid or expired token"}
$ curl -si -X POST http://127.0.0.1:8000/widgets -H 'Authorization: Bearer dev:tenant-a' -H 'Content-Type: application/json' -d '{"type":"signup_form","title":"Newsletter","description":"Join our list","fields":[{"name":"email","label":"Email","type":"email","required":true},{"name":"name","label":"Name","type":"text"}],"button_text":"Subscribe"}'
HTTP/1.1 201 Created
content-length: 467
content-type: application/json
vary: Origin

{"type":"signup_form","title":"Newsletter","description":"Join our list","fields":[{"name":"email","label":"Email","type":"email","required":true},{"name":"name","label":"Name","type":"text","required":false}],"button_text":"Subscribe","display_options":{"trigger_label":"Sign up","position":"bottom-right","delay_seconds":0,"success_message":"Thanks, submitted!"},"id":"1f1266b7-ed6b-4dcc-92db-34b16
$ curl -si -X PATCH http://127.0.0.1:8000/widgets/1f1266b7-ed6b-4dcc-92db-34b1644e5773 -H 'Authorization: Bearer dev:tenant-a' -H 'Content-Type: application/json' -d '{"title":"Renamed by owner"}' | head -14
HTTP/1.1 200 OK
content-length: 473
content-type: application/json
vary: Origin

{"type":"signup_form","title":"Renamed by owner","description":"Join our list","fields":[{"name":"email","label":"Email","type":"email","required":true},{"name":"name","label":"Name","type":"text","required":false}],"button_text":"Subscribe","display_options":{"trigger_label":"Sign up","position":"bottom-right","delay_seconds":0,"success_message":"Thanks, submitted!"},"id":"1f1266b7-ed6b-4dcc-92db
$ curl -si -X POST http://127.0.0.1:8000/widgets -H 'Authorization: Bearer dev:tenant-a' -H 'Content-Type: application/json' -d '{"type":"banner","title":"x","fields":[]}' | head -14
HTTP/1.1 422 Unprocessable Content
content-length: 195
content-type: application/json
vary: Origin

{"detail":"Invalid request","errors":[{"field":"type","msg":"Input should be 'signup_form' or 'cta_popover'"},{"field":"fields","msg":"List should have at least 1 item after validation, not 0"}]}
```

## Tenant isolation

Tenant B gets 404 on every route for tenant A's widget; A's widget unchanged.

```
$ curl -si http://127.0.0.1:8000/widgets/1f1266b7-ed6b-4dcc-92db-34b1644e5773 -H 'Authorization: Bearer dev:tenant-a' | head -3
HTTP/1.1 200 OK

$ curl -si http://127.0.0.1:8000/widgets/1f1266b7-ed6b-4dcc-92db-34b1644e5773 -H 'Authorization: Bearer dev:tenant-b' | head -12
HTTP/1.1 404 Not Found
content-length: 29
content-type: application/json
vary: Origin

{"detail":"Widget not found"}
$ curl -si -X PATCH http://127.0.0.1:8000/widgets/1f1266b7-ed6b-4dcc-92db-34b1644e5773 -H 'Authorization: Bearer dev:tenant-b' -H 'Content-Type: application/json' -d '{"title":"pwned"}' | head -12
HTTP/1.1 404 Not Found
content-length: 29
content-type: application/json
vary: Origin

{"detail":"Widget not found"}
$ curl -si -X DELETE http://127.0.0.1:8000/widgets/1f1266b7-ed6b-4dcc-92db-34b1644e5773 -H 'Authorization: Bearer dev:tenant-b' | head -12
HTTP/1.1 404 Not Found
content-length: 29
content-type: application/json
vary: Origin

{"detail":"Widget not found"}
$ curl -si http://127.0.0.1:8000/dashboard/widgets/1f1266b7-ed6b-4dcc-92db-34b1644e5773/submissions -H 'Authorization: Bearer dev:tenant-b' | head -12
HTTP/1.1 404 Not Found
content-length: 29
content-type: application/json
vary: Origin

{"detail":"Widget not found"}
$ curl -si http://127.0.0.1:8000/dashboard/widgets/1f1266b7-ed6b-4dcc-92db-34b1644e5773/stats -H 'Authorization: Bearer dev:tenant-b' | head -12
HTTP/1.1 404 Not Found
content-length: 29
content-type: application/json
vary: Origin

{"detail":"Widget not found"}
$ curl -s http://127.0.0.1:8000/widgets -H 'Authorization: Bearer dev:tenant-b'
[{"type":"signup_form","title":"Newsletter","description":"Join our list","fields":[{"name":"email","label":"Email","type":"email","required":true},{"name":"name","label":"Name","type":"text","required":false}],"button_text":"Subscribe","display_options":{"trigger_label":"Sign up","position":"bottom-right","delay_seconds":0,"success_message":"Thanks, submitted!"},"id":"f5b36907-6187-4870-96db-898d
$ curl -s http://127.0.0.1:8000/widgets/1f1266b7-ed6b-4dcc-92db-34b1644e5773 -H 'Authorization: Bearer dev:tenant-a' | /tmp/claude-0/venv/bin/python -c 'import sys,json;d=json.load(sys.stdin);print(d["title"], "(tenant A widget unchanged)")'
Renamed by owner (tenant A widget unchanged)

```

## Embed snippet, public config (max-age=60), versioned bundle

Unknown version -> 404. (HEAD is 405 by design; bundle caching headers are asserted in tests/test_delivery_and_cors.py.)

```
$ curl -s http://127.0.0.1:8000/widgets/1f1266b7-ed6b-4dcc-92db-34b1644e5773/embed -H 'Authorization: Bearer dev:tenant-a'
{"snippet":"<script src=\"http://127.0.0.1:8000/widget.v2.js?id=1f1266b7-ed6b-4dcc-92db-34b1644e5773\"></script>"}
$ curl -si http://127.0.0.1:8000/widgets/1f1266b7-ed6b-4dcc-92db-34b1644e5773/config | head -12
HTTP/1.1 200 OK
content-length: 415
content-type: application/json
cache-control: public, max-age=60
vary: Origin

{"id":"1f1266b7-ed6b-4dcc-92db-34b1644e5773","type":"signup_form","title":"Renamed by owner","description":"Join our list","fields":[{"name":"email","label":"Email","type":"email","required":true},{"name":"name","label":"Name","type":"text","required":false}],"button_text":"Subscribe","display_options":{"trigger_label":"Sign up","position":"bottom-right","delay_seconds":0,"success_message":"Thanks
$ curl -sI http://127.0.0.1:8000/widget.v2.js
HTTP/1.1 405 Method Not Allowed
allow: GET
content-length: 31
content-type: application/json
vary: Origin


$ curl -sI http://127.0.0.1:8000/widget.v1.js | head -6
HTTP/1.1 405 Method Not Allowed
allow: GET
content-length: 31
content-type: application/json

$ curl -si http://127.0.0.1:8000/widget.v99.js | head -8
HTTP/1.1 404 Not Found
content-length: 35
content-type: application/json
vary: Origin

{"detail":"Unknown widget version"}
```

## CORS from a second origin

Preflight + POST from http://127.0.0.1:5500.

```
$ curl -si -X OPTIONS 'http://127.0.0.1:8000/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Origin: http://127.0.0.1:5500' -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: content-type,idempotency-key'
HTTP/1.1 200 OK
vary: Origin, Access-Control-Request-Method, Access-Control-Request-Headers, Access-Control-Request-Private-Network
access-control-allow-origin: *
access-control-allow-methods: GET, POST
access-control-max-age: 600
access-control-allow-headers: Accept, Accept-Language, Authorization, Content-Language, Content-Type, Idempotency-Key
content-length: 2
content-type: text/plain; charset=utf-8

OK
$ curl -si -X POST 'http://127.0.0.1:8000/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Origin: http://127.0.0.1:5500' -H 'Content-Type: application/json' -d '{"data":{"email":"cors@example.com"}}'
HTTP/1.1 201 Created
content-length: 206
content-type: application/json
access-control-allow-origin: *
access-control-expose-headers: Retry-After, Idempotent-Replay, X-Total-Count
vary: Origin

{"id":"b011ca4b-5728-4fbe-96db-767850dbd4df","widget_id":"1f1266b7-ed6b-4dcc-92db-34b1644e5773","data":{"email":"cors@example.com"},"country":"Mockland-A","city":"A-City","created_at":"2026-11-06T02:38:54"}
```

## Probe 1: dashboard

Submit, list (paginated, X-Total-Count), stats, overview.

```
$ curl -si -X POST 'http://127.0.0.1:8000/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Origin: http://127.0.0.1:5500' -H 'Content-Type: application/json' -d '{"data":{"email":"ada@example.com","name":"Ada"}}'
HTTP/1.1 201 Created
content-length: 218
content-type: application/json
access-control-allow-origin: *
access-control-expose-headers: Retry-After, Idempotent-Replay, X-Total-Count
vary: Origin

{"id":"fd97da6b-f62a-4c80-8857-1970f7bc9745","widget_id":"1f1266b7-ed6b-4dcc-92db-34b1644e5773","data":{"email":"ada@example.com","name":"Ada"},"country":"Mockland-A","city":"A-City","created_at":"2026-11-06T02:38:54"}
$ curl -si 'http://127.0.0.1:8000/dashboard/widgets/1f1266b7-ed6b-4dcc-92db-34b1644e5773/submissions?limit=2' -H 'Authorization: Bearer dev:tenant-a'
HTTP/1.1 200 OK
content-length: 427
content-type: application/json
x-total-count: 2
vary: Origin

[{"id":"b011ca4b-5728-4fbe-96db-767850dbd4df","widget_id":"1f1266b7-ed6b-4dcc-92db-34b1644e5773","data":{"email":"cors@example.com"},"country":"Mockland-A","city":"A-City","created_at":"2026-11-06T02:38:54"},{"id":"fd97da6b-f62a-4c80-8857-1970f7bc9745","widget_id":"1f1266b7-ed6b-4dcc-92db-34b1644e5773","data":{"email":"ada@example.com","name":"Ada"},"country":"Mockland-A","city":"A-City","created_
$ curl -s 'http://127.0.0.1:8000/dashboard/widgets/1f1266b7-ed6b-4dcc-92db-34b1644e5773/stats' -H 'Authorization: Bearer dev:tenant-a'
{"widget_id":"1f1266b7-ed6b-4dcc-92db-34b1644e5773","total":2,"per_day":[{"date":"2026-11-06","count":2}],"by_country":[{"country":"Mockland-A","count":2}]}
$ curl -s 'http://127.0.0.1:8000/dashboard/overview' -H 'Authorization: Bearer dev:tenant-a'
[{"widget_id":"1f1266b7-ed6b-4dcc-92db-34b1644e5773","title":"Renamed by owner","type":"signup_form","total":2,"last_submission_at":"2026-11-06T02:38:54"}]
```

## Probe 2: malformed / oversized input

Bad JSON, unknown field, invalid email, missing field -> 422; 10KB+ body and chunked body -> 413.

```
$ curl -si -X POST 'http://127.0.0.1:8000/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Content-Type: application/json' -d '{not json' | head -12
HTTP/1.1 422 Unprocessable Content
content-length: 79
content-type: application/json
vary: Origin

{"detail":"Invalid request","errors":[{"field":"1","msg":"JSON decode error"}]}
$ curl -si -X POST 'http://127.0.0.1:8000/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Content-Type: application/json' -d '{"data":{"email":"a@b.co"},"evil":"x"}' | head -12
HTTP/1.1 422 Unprocessable Content
content-length: 95
content-type: application/json
vary: Origin

{"detail":"Invalid request","errors":[{"field":"evil","msg":"Extra inputs are not permitted"}]}
$ curl -si -X POST 'http://127.0.0.1:8000/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Content-Type: application/json' -d '{"data":{"email":"not-an-email"}}' | head -12
HTTP/1.1 422 Unprocessable Content
content-length: 125
content-type: application/json
vary: Origin

{"detail":"Submission does not match the widget's fields","errors":[{"field":"email","msg":"Must be a valid email address"}]}
$ curl -si -X POST 'http://127.0.0.1:8000/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Content-Type: application/json' -d '{"data":{"name":"no email"}}' | head -12
HTTP/1.1 422 Unprocessable Content
content-length: 118
content-type: application/json
vary: Origin

{"detail":"Submission does not match the widget's fields","errors":[{"field":"email","msg":"This field is required"}]}
$ curl -si -X POST 'http://127.0.0.1:8000/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Content-Type: application/json' --data-binary @/tmp/claude-0/-home-claude/186f67fb-b8a9-556c-94a8-169d4007d5d0/scratchpad/ev/big.json | head -12
HTTP/1.1 413 Content Too Large
content-type: application/json
content-length: 31
vary: Origin

{"detail": "Payload too large"}
$ curl -si -X POST 'http://127.0.0.1:8000/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Content-Type: application/json' -H 'Transfer-Encoding: chunked' --data-binary @/tmp/claude-0/-home-claude/186f67fb-b8a9-556c-94a8-169d4007d5d0/scratchpad/ev/big.json | head -12
HTTP/1.1 413 Content Too Large
content-type: application/json
content-length: 31
vary: Origin

{"detail": "Payload too large"}
$ curl -si -X POST 'http://127.0.0.1:8000/submissions?widget_id=nope' -H 'Content-Type: application/json' -d '{"data":{"email":"a@b.co"}}' | head -12
HTTP/1.1 404 Not Found
content-length: 29
content-type: application/json
vary: Origin

{"detail":"Widget not found"}
```

## Probe 3: rate limit

5 ok, then 429 with Retry-After; a different visitor and /health unaffected.

```
$ burst of 8 from one client (X-Forwarded-For 203.0.113.9), limit 5/minute
request 1 -> 201
request 2 -> 201
request 3 -> 201
request 4 -> 201
request 5 -> 201
request 6 -> 429
request 7 -> 429
request 8 -> 429

$ the 429 in full
HTTP/1.1 429 Too Many Requests
content-type: application/json
content-length: 52
retry-after: 60
vary: Origin

{"detail": "Rate limit exceeded", "retry_after": 60}
$ right after the burst, a normal visitor (198.51.100.7)
HTTP/1.1 201 Created

$ and the rest of the service
GET /health -> 200
GET config -> 200
```

## Probe 4: geo provider fallback

A up -> A; A down -> B; both down -> 201 with null country.

```
$ echo '--- provider A up (port 8000)'; curl -s -X POST 'http://127.0.0.1:8000/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Content-Type: application/json' -d '{"data":{"email":"geo-a@example.com"}}'
--- provider A up (port 8000)
{"id":"375c055c-a133-4e07-bd67-0fe4950b723c","widget_id":"1f1266b7-ed6b-4dcc-92db-34b1644e5773","data":{"email":"geo-a@example.com"},"country":"Mockland-A","city":"A-City","created_at":"2026-11-06T02:38:54"}
$ echo '--- provider A DOWN (port 8002, GEO_A_DOWN=1)'; curl -s -X POST 'http://127.0.0.1:8002/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Content-Type: application/json' -d '{"data":{"email":"geo-b@example.com"}}'
--- provider A DOWN (port 8002, GEO_A_DOWN=1)
{"id":"1ca631ea-fe8e-40e3-aa7c-879dbae99046","widget_id":"1f1266b7-ed6b-4dcc-92db-34b1644e5773","data":{"email":"geo-b@example.com"},"country":"Mockland-B","city":"B-City","created_at":"2026-11-06T02:38:54"}
$ echo '--- BOTH DOWN (port 8003, GEO_A_DOWN=1 GEO_B_DOWN=1)'; curl -si -X POST 'http://127.0.0.1:8003/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Content-Type: application/json' -d '{"data":{"email":"geo-none@example.com"}}' | head -12
--- BOTH DOWN (port 8003, GEO_A_DOWN=1 GEO_B_DOWN=1)
HTTP/1.1 201 Created
content-length: 198
content-type: application/json
vary: Origin

{"id":"20766acc-b857-4ed5-8506-998e281792c6","widget_id":"1f1266b7-ed6b-4dcc-92db-34b1644e5773","data":{"email":"geo-none@example.com"},"country":null,"city":null,"created_at":"2026-11-06T02:38:54"}
```

## Probe 5: email failure

Submission still 201 and stored; background job retries then logs [ALERT] (server log below).

```
$ echo '--- EMAIL_FAIL=1 (port 8004)'; curl -si -X POST 'http://127.0.0.1:8004/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Content-Type: application/json' -d '{"data":{"email":"mail-fail@example.com"}}' | head -12
--- EMAIL_FAIL=1 (port 8004)
HTTP/1.1 201 Created
content-length: 211
content-type: application/json
vary: Origin

{"id":"6d615a2b-2b94-4684-8d78-33875f4e4d98","widget_id":"1f1266b7-ed6b-4dcc-92db-34b1644e5773","data":{"email":"mail-fail@example.com"},"country":"Mockland-A","city":"A-City","created_at":"2026-11-06T02:38:54"}
$ echo '--- the submission is stored anyway'; curl -s 'http://127.0.0.1:8000/dashboard/widgets/1f1266b7-ed6b-4dcc-92db-34b1644e5773/submissions?limit=100' -H 'Authorization: Bearer dev:tenant-a' | /tmp/claude-0/venv/bin/python -c 'import sys,json;[print(r["data"]["email"]) for r in json.load(sys.stdin) if "mail-fail" in r["data"]["email"]]'
--- the submission is stored anyway
mail-fail@example.com

```

```
WARNING:     app.notify: [email] attempt 1/3 failed: mock email service is down
WARNING:     app.notify: [email] attempt 2/3 failed: mock email service is down
WARNING:     app.notify: [email] attempt 3/3 failed: mock email service is down
ERROR:     app.notify: [ALERT] confirmation email permanently failed for widget 'Renamed by owner'
```

## Probe 6: honeypot

Filled honeypot -> 422, nothing stored.

```
$ curl -si -X POST 'http://127.0.0.1:8000/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Content-Type: application/json' -d '{"data":{"email":"bot@spam.example"},"honeypot":"i-am-a-bot"}' | head -12
HTTP/1.1 422 Unprocessable Content
content-length: 108
content-type: application/json
vary: Origin

{"detail":"Invalid request","errors":[{"field":"honeypot","msg":"String should have at most 0 characters"}]}
```

## Idempotency

Same key x3: 201, 200, 200 with Idempotent-Replay; exactly 1 row.

```
$ curl -si -X POST 'http://127.0.0.1:8000/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Content-Type: application/json' -H 'Idempotency-Key: demo-retry-0001' -d '{"data":{"email":"once@example.com"}}'
HTTP/1.1 201 Created
content-length: 206
content-type: application/json
vary: Origin

{"id":"3f983c92-9121-4f2e-b037-f9c88436040c","widget_id":"1f1266b7-ed6b-4dcc-92db-34b1644e5773","data":{"email":"once@example.com"},"country":"Mockland-A","city":"A-City","created_at":"2026-11-06T02:38:58"}
$ curl -si -X POST 'http://127.0.0.1:8000/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Content-Type: application/json' -H 'Idempotency-Key: demo-retry-0001' -d '{"data":{"email":"once@example.com"}}'
HTTP/1.1 200 OK
content-length: 206
content-type: application/json
idempotent-replay: true
vary: Origin

{"id":"3f983c92-9121-4f2e-b037-f9c88436040c","widget_id":"1f1266b7-ed6b-4dcc-92db-34b1644e5773","data":{"email":"once@example.com"},"country":"Mockland-A","city":"A-City","created_at":"2026-11-06T02:38:58"}
$ curl -si -X POST 'http://127.0.0.1:8000/submissions?widget_id=1f1266b7-ed6b-4dcc-92db-34b1644e5773' -H 'Content-Type: application/json' -H 'Idempotency-Key: demo-retry-0001' -d '{"data":{"email":"once@example.com"}}'
HTTP/1.1 200 OK
content-length: 206
content-type: application/json
idempotent-replay: true
vary: Origin

{"id":"3f983c92-9121-4f2e-b037-f9c88436040c","widget_id":"1f1266b7-ed6b-4dcc-92db-34b1644e5773","data":{"email":"once@example.com"},"country":"Mockland-A","city":"A-City","created_at":"2026-11-06T02:38:58"}
$ echo 'rows stored for once@example.com:'; curl -s 'http://127.0.0.1:8000/dashboard/widgets/1f1266b7-ed6b-4dcc-92db-34b1644e5773/submissions?limit=100' -H 'Authorization: Bearer dev:tenant-a' | /tmp/claude-0/venv/bin/python -c 'import sys,json;print(sum(1 for r in json.load(sys.stdin) if r["data"]["email"]=="once@example.com"))'
rows stored for once@example.com:
1

```

## Tests

70 passed (includes concurrent same-key race test, rollback of migrations, seed idempotency).

```
============================= test session starts ==============================
platform linux -- Python 3.13.16, pytest-9.2.0, pluggy-1.7.0
rootdir: /home/claude/widgetplatform-flyrank
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.16.0
collected 70 items

tests/test_abuse_protection.py ......                                    [  8%]
tests/test_dashboard.py .....                                            [ 15%]
tests/test_delivery_and_cors.py ........                                 [ 27%]
tests/test_enrichment_and_side_effects.py ........                       [ 38%]
tests/test_idempotency.py ......                                         [ 47%]
tests/test_management_and_isolation.py ............                      [ 64%]
tests/test_persistence.py ....                                           [ 70%]
tests/test_submission_validation.py .....................                [100%]

=============================== warnings summary ===============================
../../../tmp/claude-0/venv/lib/python3.13/site-packages/fastapi/testclient.py:1
  /tmp/claude-0/venv/lib/python3.13/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 70 passed, 1 warning in 1.88s =========================
```

## Secrets clean

.env, tokens.ps1 and *.db ignored; no keys in tracked files.

```
$ git check-ignore -v .env tokens.ps1 widgetplatform.db
.gitignore:6:.env	.env
.gitignore:8:tokens.ps1	tokens.ps1
.gitignore:7:*.db	widgetplatform.db
$ git ls-files | grep -E "\.env$|\.db$"  (expect nothing)
$ grep -rnE "eyJ|sb_secret|sb_publishable|service_role" (tracked files, expect nothing)
(exit done)
```
