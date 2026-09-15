from fastapi import FastAPI
from . import models
from .database import engine
from .router import widgets, submissions

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Widget & Lead-Capture Platform")

app.include_router(widgets.router)
app.include_router(submissions.router)


@app.get("/health")
def health():
    return {"status": "ok"}