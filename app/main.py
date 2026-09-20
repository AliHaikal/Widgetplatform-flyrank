from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .limiter import limiter
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from . import models
from .database import engine
from .router import widgets, submissions
from fastapi.middleware.cors import CORSMiddleware

models.Base.metadata.create_all(bind=engine)

MAX_BODY_BYTES = 10_000

app = FastAPI(title="Widget & Lead-Capture Platform")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(widgets.router)
app.include_router(submissions.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": "Payload too large"},
        )
    return await call_next(request)