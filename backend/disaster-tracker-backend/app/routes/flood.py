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
    # Metrics được build lazy. Request đầu tiên tạo cache; các request sau đọc
    # JSON đã sinh cho tới khi refresh xóa cache.
    try:
        _, metrics, bounds = cache.get_or_build()
    except FileNotFoundError:
        raise HTTPException(404, "Raster not downloaded. Call POST /api/flood/refresh.")

    # Timestamp của raster local là tín hiệu freshness gần nhất cho demo này;
    # nó không thay thế thời gian acquisition chính thức từ nguồn dữ liệu.
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
def refresh():
    # Refresh thay raster nguồn rồi xóa output cũ để lần build tiếp theo không
    # trộn metrics cũ với ảnh dữ liệu mới.
    try:
        download_tile()
        cache.invalidate()
        _, metrics, bounds = cache.get_or_build()
        return {"status": "refreshed", **metrics, "bounds": bounds}
    except Exception as e:
        raise HTTPException(500, str(e))


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
