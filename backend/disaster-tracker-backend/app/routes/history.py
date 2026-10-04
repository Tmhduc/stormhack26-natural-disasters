from typing import List
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.core import history
from app.models import HistoryDay

router = APIRouter(prefix="/api/flood/history", tags=["history"])


@router.get("", response_model=List[HistoryDay])
def list_history(limit: int = Query(30, ge=1, le=365)):
    """Days the pipeline has saved to the database, newest first. Empty when no database is configured."""
    if not history.enabled():
        return []
    try:
        days = history.list_days(limit)
    except Exception as e:
        raise HTTPException(503, f"Flood history database unavailable: {e}")
    # `v` changes when LANCE reprocesses a day, so browsers don't keep showing the old overlay.
    return [
        HistoryDay(**day, png_url=f"/api/flood/history/{day['id']}/overlay.png?v={quote(day['processed_at'] or '')}")
        for day in days
    ]


@router.get("/{image_id}/overlay.png")
def history_overlay(image_id: int):
    try:
        png = history.overlay_png(image_id) if history.enabled() else None
    except Exception as e:
        raise HTTPException(503, f"Flood history database unavailable: {e}")
    if png is None:
        raise HTTPException(404, "No overlay saved for that day.")
    return Response(png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
