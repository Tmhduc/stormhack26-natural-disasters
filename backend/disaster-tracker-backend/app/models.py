from pydantic import BaseModel
from typing import Optional, List

Bounds = List[float]


class FloodMetrics(BaseModel):
    flood_pixels: int
    flooded_km2: float
    bounds: Bounds
    product: Optional[str] = None
    tiles: List[str] = []
    date: Optional[str] = None  # UTC day the satellite data is from, YYYY-MM-DD
    last_updated: Optional[str] = None


class OverlayResponse(BaseModel):
    png_url: str
    bounds: Bounds


class InspectResponse(BaseModel):
    inside: bool
    flooded: Optional[bool] = None
    lat: float
    lon: float
