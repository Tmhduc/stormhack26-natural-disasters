import os
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from app.config import BOUNDARY_GEOJSON, LANCE_DATA_LAG_DAYS, LANCE_POLL_MINUTES
from app.core import cache, pipeline
from app.core.clipper import (
    MCDWD_CLASS_NAMES,
    MCDWD_FLOOD_CLASSES,
    administrative_area,
    ensure_boundary_geojson,
    inspect_flood_neighborhood,
    inspect_flood_point,
)
from app.core.downloader import LanceError
from app.models import FloodMetrics, OverlayResponse, InspectResponse

router = APIRouter(prefix="/api/flood", tags=["flood"])


@router.get("/metrics", response_model=FloodMetrics)
def get_metrics():
    # Metrics được build lazy. Request đầu tiên tạo cache; các request sau đọc
    # JSON đã sinh cho tới khi refresh xóa cache.
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
    # PNG được serve qua /static; bounds cho frontend biết đặt ảnh ở đâu trên
    # mặt phẳng địa lý.
    try:
        _, _, bounds = cache.get_or_build()
    except FileNotFoundError:
        raise HTTPException(404, "Overlay not built.")
    return OverlayResponse(png_url="/static/flood_overlay.png", bounds=bounds)


@router.get("/boundary")
def get_boundary():
    # Chỉ tạo boundary dạng dễ dùng cho browser khi có request đầu tiên.
    if not os.path.exists(BOUNDARY_GEOJSON):
        ensure_boundary_geojson()
    return FileResponse(BOUNDARY_GEOJSON, media_type="application/geo+json")


@router.post("/refresh")
def refresh(day: Optional[date] = None, force: bool = False):
    """Tải từ LANCE ngay; truyền `day` UTC để chọn ngày cụ thể thay vì ngày mới nhất."""
    try:
        result = pipeline.run(day=day, force=force)
    except LanceError as e:
        raise HTTPException(502, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"status": "refreshed" if result["updated"] else "up to date", **result}


@router.get("/status")
def status():
    """Cho biết pipeline LANCE đã tải gì và kiểm tra lần cuối lúc nào."""
    return {
        **pipeline.read_state(),
        "poll_minutes": LANCE_POLL_MINUTES,
        "data_lag_days": LANCE_DATA_LAG_DAYS,
    }


@router.get("/inspect", response_model=InspectResponse)
def inspect(lat: float, lon: float, radius_km: float = Query(2.0, ge=0, le=25)):
    # Chỉ đọc một pixel trong GeoTIFF; metrics và overlay mới cần toàn bộ mask.
    flooded = inspect_flood_point(lat, lon)
    if flooded is None:
        return InspectResponse(inside=False, lat=lat, lon=lon)

    class_name = MCDWD_CLASS_NAMES.get(flooded, "unknown")
    is_flood = None if flooded == 255 else flooded in MCDWD_FLOOD_CLASSES
    area = administrative_area(lat, lon)
    nearby = inspect_flood_neighborhood(lat, lon, radius_km)
    return InspectResponse(
        inside=True,
        flooded=is_flood,
        class_value=flooded,
        class_name=class_name,
        admin1_name=area["name"] if area else None,
        admin1_type=area["type"] if area else None,
        admin1_pcode=area["pcode"] if area else None,
        nearby_radius_km=nearby["radius_km"] if nearby else None,
        nearby_pixels=nearby["pixels"] if nearby else None,
        nearby_flood_pixels=nearby["flood_pixels"] if nearby else None,
        nearby_class_counts=nearby["class_counts"] if nearby else {},
        lat=lat,
        lon=lon,
    )
