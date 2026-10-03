from pydantic import BaseModel
from typing import Optional, List

Bounds = List[float]
# Bounds có thứ tự [left, bottom, right, top], được dùng chung cho việc đặt
# overlay lên bản đồ và kiểm tra một điểm tọa độ.


class FloodMetrics(BaseModel):
    """Các chỉ số tổng hợp của raster hiện tại để dashboard hiển thị."""

    flood_pixels: int
    flooded_km2: float
    bounds: Bounds
    tile_id: str
    date: str
    last_updated: Optional[str] = None


class OverlayResponse(BaseModel):
    """URL và vị trí địa lý của ảnh overlay trong suốt đã render."""

    png_url: str
    bounds: Bounds


class InspectResponse(BaseModel):
    """Kết quả kiểm tra một cặp latitude/longitude với flood mask."""

    inside: bool
    flooded: Optional[bool] = None
    lat: float
    lon: float
