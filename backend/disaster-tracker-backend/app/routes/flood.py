from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.config import LANCE_DATA_LAG_DAYS, LANCE_POLL_MINUTES
from app.core import cache, pipeline
from app.core.clipper import (
    MCDWD_CLASS_NAMES,
    MCDWD_FLOOD_CLASSES,
    administrative_area,
    ensure_browser_boundary_geojson,
    inspect_flood_neighborhood,
    inspect_flood_point,
)
from app.core.downloader import LanceError
from app.core.alerts import send_sms, send_telegram
from app.core.geocoder import forward_geocode, reverse_geocode
from app.models import FloodMetrics, OverlayResponse, InspectResponse

router = APIRouter(prefix="/api/flood", tags=["flood"])


class SmsAlertRequest(BaseModel):
    to: str
    body: str


@router.get("/metrics", response_model=FloodMetrics)
def get_metrics():
    # Metrics are built lazily. The first request creates the cache; later
    # requests read the JSON files until refresh invalidates them.
    try:
        _, metrics, bounds = cache.get_or_build()
    except FileNotFoundError:
        raise HTTPException(404, "Raster not downloaded. Call POST /api/flood/refresh.")

    state = pipeline.read_state()
    return FloodMetrics(
        **metrics,
        bounds=bounds,
        product=state.get("product"),
        tiles=state.get("tiles", []),
        date=state.get("date"),
        last_updated=state.get("processed_at"),
    )


@router.get("/overlay", response_model=OverlayResponse)
def get_overlay():
    # The PNG is served from /static; bounds tell the frontend where to place it
    # on the geographic map.
    try:
        _, _, bounds = cache.get_or_build()
    except FileNotFoundError:
        raise HTTPException(404, "Overlay not built.")
    return OverlayResponse(png_url="/static/flood_overlay.png", bounds=bounds)


@router.get("/boundary")
def get_boundary():
    # Serve a simplified copy; the full boundary remains backend-only.
    return FileResponse(
        ensure_browser_boundary_geojson(),
        media_type="application/geo+json",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post("/refresh")
def refresh(day: Optional[date] = None, force: bool = False):
    """Run the LANCE refresh now; pass a UTC `day` to select a specific date."""
    try:
        result = pipeline.run(day=day, force=force)
    except LanceError as e:
        raise HTTPException(502, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"status": "refreshed" if result["updated"] else "up to date", **result}


@router.get("/status")
def status():
    """Return what the LANCE pipeline loaded and when it last checked."""
    return {
        **pipeline.read_state(),
        "poll_minutes": LANCE_POLL_MINUTES,
        "data_lag_days": LANCE_DATA_LAG_DAYS,
    }


@router.get("/geocode")
def geocode(q: str = Query(..., min_length=3, max_length=200)):
    """Search Vietnamese addresses through the optional Google geocoder."""
    return forward_geocode(q)


@router.post("/alerts/sms")
def sms_alert(payload: SmsAlertRequest):
    """Send a responder-approved incident brief by SMS."""
    try:
        sid = send_sms(payload.to, payload.body)
    except ValueError as error:
        raise HTTPException(400, str(error))
    except RuntimeError as error:
        raise HTTPException(503, str(error))
    return {"status": "sent", "message_sid": sid}


class TelegramAlertRequest(BaseModel):
    body: str


@router.post("/alerts/telegram")
def telegram_alert(payload: TelegramAlertRequest):
    """Send a responder-approved incident brief to the configured Telegram chat."""
    try:
        message_id = send_telegram(payload.body)
    except ValueError as error:
        raise HTTPException(400, str(error))
    except RuntimeError as error:
        raise HTTPException(503, str(error))
    return {"status": "sent", "message_id": message_id}


@router.get("/inspect", response_model=InspectResponse)
def inspect(lat: float, lon: float, radius_km: float = Query(2.0, ge=0, le=25)):
    # Read one GeoTIFF pixel; only metrics and the overlay need the full mask.
    flooded = inspect_flood_point(lat, lon)
    if flooded is None:
        return InspectResponse(inside=False, lat=lat, lon=lon)

    class_name = MCDWD_CLASS_NAMES.get(flooded, "unknown")
    is_flood = None if flooded == 255 else flooded in MCDWD_FLOOD_CLASSES
    area = administrative_area(lat, lon)
    address = reverse_geocode(lat, lon)
    nearby = inspect_flood_neighborhood(lat, lon, radius_km)
    return InspectResponse(
        inside=True,
        flooded=is_flood,
        class_value=flooded,
        class_name=class_name,
        admin1_name=area["name"] if area else None,
        admin1_type=area["type"] if area else None,
        admin1_pcode=area["pcode"] if area else None,
        address=address,
        nearby_radius_km=nearby["radius_km"] if nearby else None,
        nearby_pixels=nearby["pixels"] if nearby else None,
        nearby_flood_pixels=nearby["flood_pixels"] if nearby else None,
        nearby_class_counts=nearby["class_counts"] if nearby else {},
        lat=lat,
        lon=lon,
    )
