import logging
from typing import List
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.core import history, incidents
from app.models import HistoryDay, Hotspot, IncidentCreate, IncidentUpdate, SavedIncident, TrendPoint

router = APIRouter(prefix="/api/flood/history", tags=["history"])
log = logging.getLogger(__name__)


@router.get("/incidents", response_model=List[SavedIncident])
def list_incidents(limit: int = Query(50, ge=1, le=500)):
    """Return responder-saved inspection points."""
    if not history.enabled():
        return []
    try:
        return incidents.list_incidents(limit)
    except Exception as e:
        raise HTTPException(503, f"Flood history database unavailable: {e}")


@router.post("/incidents", response_model=SavedIncident, status_code=201)
def save_incident(payload: IncidentCreate):
    """Save an inspection point for the response team."""
    if not history.enabled():
        raise HTTPException(503, "Tiger Data is not configured.")
    try:
        return incidents.save(payload.model_dump())
    except Exception as e:
        log.exception("Could not save responder incident")
        raise HTTPException(503, f"Flood history database unavailable: {e}")


@router.delete("/incidents/{incident_id}")
def delete_incident(incident_id: str):
    """Remove one responder-saved inspection point."""
    if not history.enabled():
        raise HTTPException(503, "Tiger Data is not configured.")
    try:
        if not incidents.remove(incident_id):
            raise HTTPException(404, "Incident not found.")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Flood history database unavailable: {e}")


@router.patch("/incidents/{incident_id}", response_model=SavedIncident)
def update_incident(incident_id: str, payload: IncidentUpdate):
    """Update an incident's response status or responder notes."""
    if not history.enabled():
        raise HTTPException(503, "Tiger Data is not configured.")
    try:
        updated = incidents.update_incident(incident_id, payload.model_dump(exclude_unset=True))
        if updated is None:
            raise HTTPException(404, "Incident not found.")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Could not update responder incident")
        raise HTTPException(503, f"Flood history database unavailable: {e}")


@router.get("/hotspots", response_model=List[Hotspot])
def incident_hotspots(limit: int = Query(10, ge=1, le=50)):
    """Group saved incidents by province or city."""
    if not history.enabled():
        return []
    try:
        return incidents.hotspots(limit)
    except Exception as e:
        raise HTTPException(503, f"Flood history database unavailable: {e}")


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


@router.get("/trend", response_model=List[TrendPoint])
def flood_trend(limit: int = Query(30, ge=2, le=365)):
    """Return saved daily totals from oldest to newest for the trend chart."""
    if not history.enabled():
        return []
    try:
        return history.trend(limit)
    except Exception as e:
        raise HTTPException(503, f"Flood history database unavailable: {e}")


@router.get("/{image_id}/overlay.png")
def history_overlay(image_id: int):
    try:
        png = history.overlay_png(image_id) if history.enabled() else None
    except Exception as e:
        raise HTTPException(503, f"Flood history database unavailable: {e}")
    if png is None:
        raise HTTPException(404, "No overlay saved for that day.")
    return Response(png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
