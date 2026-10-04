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
    product: Optional[str] = None
    tiles: List[str] = []
    date: Optional[str] = None  # ngày UTC của dữ liệu vệ tinh, định dạng YYYY-MM-DD
    last_updated: Optional[str] = None


class OverlayResponse(BaseModel):
    """URL và vị trí địa lý của ảnh overlay trong suốt đã render."""

    png_url: str
    bounds: Bounds


class HistoryDay(BaseModel):
    """Một ngày đã lưu trong database: chỉ số ngập và overlay của ngày đó."""

    id: int
    date: str  # UTC day the satellite data is from, YYYY-MM-DD
    png_url: str
    bounds: Bounds
    flood_pixels: int
    flooded_km2: float
    tiles: List[str] = []
    processed_at: Optional[str] = None


class InspectResponse(BaseModel):
    """Kết quả kiểm tra một cặp latitude/longitude với flood mask."""

    inside: bool
    flooded: Optional[bool] = None
    lat: float
    lon: float
