import os
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import CACHE_DIR, LOCAL_RASTER, BOUNDARY_GEOJSON, TILE_ID, YEAR, DOY
from app.core import cache
from app.core.clipper import ensure_boundary_geojson, load_clipped_flood
from app.core.downloader import download_tile
from app.models import FloodMetrics, OverlayResponse, InspectResponse

router = APIRouter(prefix="/api/flood", tags=["flood"])


@router.get("/metrics", response_model=FloodMetrics)
def get_metrics():
    try:
        _, metrics, bounds = cache.get_or_build()
    except FileNotFoundError:
        raise HTTPException(404, "Raster not downloaded. Call POST /api/flood/refresh.")

    mtime = os.path.getmtime(LOCAL_RASTER) if os.path.exists(LOCAL_RASTER) else None
    return FloodMetrics(
        **metrics,
        bounds=bounds,
        tile_id=TILE_ID,
        date=f"{YEAR}-{DOY}",
        last_updated=datetime.fromtimestamp(mtime).isoformat() if mtime else None,
    )


@router.get("/overlay", response_model=OverlayResponse)
def get_overlay():
    try:
        _, _, bounds = cache.get_or_build()
    except FileNotFoundError:
        raise HTTPException(404, "Overlay not built.")
    return OverlayResponse(png_url="/static/flood_overlay.png", bounds=bounds)


@router.get("/boundary")
def get_boundary():
    if not os.path.exists(BOUNDARY_GEOJSON):
        ensure_boundary_geojson()
    return FileResponse(BOUNDARY_GEOJSON, media_type="application/geo+json")


@router.post("/refresh")
def refresh():
    try:
        download_tile()
        cache.invalidate()
        _, metrics, bounds = cache.get_or_build()
        return {"status": "refreshed", **metrics, "bounds": bounds}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/inspect", response_model=InspectResponse)
def inspect(lat: float, lon: float):
    flood_mask, bounds = load_clipped_flood()
    left, bottom, right, top = bounds
    h, w = flood_mask.shape

    if not (left <= lon <= right and bottom <= lat <= top):
        return InspectResponse(inside=False, lat=lat, lon=lon)

    x = max(0, min(int((lon - left) / (right - left) * w), w - 1))
    y = max(0, min(int((top - lat) / (top - bottom) * h), h - 1))
    return InspectResponse(
        inside=True, flooded=bool(flood_mask[y, x] == 1), lat=lat, lon=lon
    )
