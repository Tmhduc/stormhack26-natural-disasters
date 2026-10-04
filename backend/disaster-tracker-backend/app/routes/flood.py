import os
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import BOUNDARY_GEOJSON, LANCE_POLL_MINUTES
from app.core import cache, pipeline
from app.core.clipper import ensure_boundary_geojson, load_clipped_flood
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
    """Pull from LANCE now. Pass `day` (UTC, YYYY-MM-DD) to load a specific day instead of the newest."""
    try:
        result = pipeline.run(day=day, force=force)
    except LanceError as e:
        raise HTTPException(502, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"status": "refreshed" if result["updated"] else "up to date", **result}


@router.get("/status")
def status():
    """What the LANCE pipeline last loaded and when it last checked."""
    return {**pipeline.read_state(), "poll_minutes": LANCE_POLL_MINUTES}


@router.get("/inspect", response_model=InspectResponse)
def inspect(lat: float, lon: float):
    # Demo đọc trực tiếp array đã clip thay vì query raster gốc cho mỗi click.
    flood_mask, bounds = load_clipped_flood()
    left, bottom, right, top = bounds
    h, w = flood_mask.shape

    # Phép đổi bên dưới giả định bounds của mask và tọa độ input dùng cùng CRS.
    # Cần kiểm tra lại assumption này nếu đổi sản phẩm NASA hoặc boundary.
    if not (left <= lon <= right and bottom <= lat <= top):
        return InspectResponse(inside=False, lat=lat, lon=lon)

    # Column tăng về phía đông; row tăng xuống dưới, nên latitude được tính từ
    # cạnh phía bắc khi chuyển thành row index.
    x = max(0, min(int((lon - left) / (right - left) * w), w - 1))
    y = max(0, min(int((top - lat) / (top - bottom) * h), h - 1))
    return InspectResponse(
        inside=True, flooded=bool(flood_mask[y, x] == 1), lat=lat, lon=lon
    )
