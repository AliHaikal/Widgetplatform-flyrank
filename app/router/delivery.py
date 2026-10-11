from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["delivery"])

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@router.get("/widget.v1.js")
def widget_bundle():
    return FileResponse(
        STATIC_DIR / "widget.v1.js",
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )