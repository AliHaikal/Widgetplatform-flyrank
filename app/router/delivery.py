from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["delivery"])

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
VERSIONS = {"v1", "v2"}  # v1 stays served so existing embeds keep working


@router.get("/widget.{version}.js")
def widget_bundle(version: str):
    """Versioned bundle: the version is in the URL, so it can be cached for a
    year. A new release ships under a new URL, which browsers fetch fresh."""
    if version not in VERSIONS:
        raise HTTPException(status_code=404, detail="Unknown widget version")
    return FileResponse(
        STATIC_DIR / f"widget.{version}.js",
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
