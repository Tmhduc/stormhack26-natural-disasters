from pydantic import BaseModel
from typing import Optional, List

Bounds = List[float]
# Bounds use [left, bottom, right, top] and are shared by overlay placement
# and coordinate inspection.


class FloodMetrics(BaseModel):
    """Summary metrics for the current raster displayed by the dashboard."""

    flood_pixels: int
    flooded_km2: float
    bounds: Bounds
    product: Optional[str] = None
    tiles: List[str] = []
    date: Optional[str] = None  # Satellite observation date in YYYY-MM-DD UTC.
    last_updated: Optional[str] = None


class OverlayResponse(BaseModel):
    """URL and geographic placement for the rendered transparent overlay."""

    png_url: str
    bounds: Bounds


class HistoryDay(BaseModel):
    """A saved observation day with flood metrics and its overlay."""

    id: int
    date: str  # UTC day the satellite data is from, YYYY-MM-DD
    png_url: str
    bounds: Bounds
    flood_pixels: int
    flooded_km2: float
    tiles: List[str] = []
    processed_at: Optional[str] = None


class InspectResponse(BaseModel):
    """Coordinate inspection result preserving the original MCDWD class."""

    inside: bool
    flooded: Optional[bool] = None
    class_value: Optional[int] = None
    class_name: Optional[str] = None
    admin1_name: Optional[str] = None
    admin1_type: Optional[str] = None
    admin1_pcode: Optional[str] = None
    address: Optional[str] = None
    nearby_radius_km: Optional[float] = None
    nearby_pixels: Optional[int] = None
    nearby_flood_pixels: Optional[int] = None
    nearby_class_counts: dict[str, int] = {}
    lat: float
    lon: float
