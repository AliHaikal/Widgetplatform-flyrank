import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .database import engine
from .errors import AppError, FieldValidationError
from .middleware import BodyLimitMiddleware, RateLimitMiddleware
from .router import dashboard, delivery, submissions, widgets

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")
log = logging.getLogger("app")

app = FastAPI(title="Widget & Lead-Capture Platform")

# Middleware runs outermost-first in REVERSE order of registration:
# CORS -> rate limit -> body limit -> app.
app.add_middleware(BodyLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # public widget: any customer site may call us
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Idempotency-Key", "Authorization"],
    expose_headers=["Retry-After", "Idempotent-Replay", "X-Total-Count"],
)

app.include_router(widgets.router)
app.include_router(submissions.router)
app.include_router(delivery.router)
app.include_router(dashboard.router)


@app.exception_handler(FieldValidationError)
async def field_validation_handler(_request: Request, exc: FieldValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.message, "errors": exc.errors})


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_request: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "msg": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422, content={"detail": "Invalid request", "errors": errors}
    )


@app.exception_handler(Exception)
async def unhandled_handler(_request: Request, exc: Exception):
    log.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        return JSONResponse(status_code=503, content={"status": "database unavailable"})
    return {"status": "ok"}
