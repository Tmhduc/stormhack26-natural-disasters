import os
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from rasterio.transform import rowcol
from rasterio.warp import transform
from shapely.geometry import Point

from app.config import BOUNDARY_GEOJSON, LANCE_POLL_MINUTES
from app.core import cache, pipeline
from app.core.clipper import (
    _boundary_wgs84,
    ensure_boundary_geojson,
    load_clipped_flood_with_metadata,
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
    return {**pipeline.read_state(), "poll_minutes": LANCE_POLL_MINUTES}


@router.get("/inspect", response_model=InspectResponse)
def inspect(lat: float, lon: float):
    # Dùng transform thật của raster đã clip thay vì nội suy trên bounds địa lý,
    # vì cách nội suy đó sai khi raster dùng CRS chiếu.
    flood_mask, clipped_transform, raster_crs, _ = load_clipped_flood_with_metadata()
    h, w = flood_mask.shape

    # Raster sau crop luôn là hình chữ nhật; kiểm tra boundary để không trả về
    # dữ liệu Việt Nam cho điểm ở nước láng giềng hoặc ngoài biển.
    if not _boundary_wgs84().geometry.covers(Point(lon, lat)).any():
        return InspectResponse(inside=False, lat=lat, lon=lon)

    # Đổi điểm WGS84 từ API sang CRS raster trước khi lấy row/column. Nội suy
    # trực tiếp trên bounds WGS84 sẽ sai với raster chiếu.
    x_coords, y_coords = transform("EPSG:4326", raster_crs, [lon], [lat])
    row, column = rowcol(clipped_transform, x_coords[0], y_coords[0])
    if not (0 <= row < h and 0 <= column < w):
        return InspectResponse(inside=False, lat=lat, lon=lon)

    return InspectResponse(
        inside=True, flooded=bool(flood_mask[row, column] == 1), lat=lat, lon=lon
    )
