import os
from functools import lru_cache

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import box, mapping

from app.config import (
    LOCAL_RASTER, BOUNDARY_SHP, BOUNDARY_GEOJSON, FLOOD_VALUE
)


def ensure_boundary_geojson() -> str:
    """Tạo file boundary dễ dùng cho browser từ shapefile gốc."""
    if not os.path.exists(BOUNDARY_GEOJSON):
        # Shapefile phù hợp cho xử lý địa lý; GeoJSON dễ để frontend request
        # và vẽ trực tiếp trên bản đồ.
        gdf = gpd.read_file(BOUNDARY_SHP)
        gdf.to_file(BOUNDARY_GEOJSON, driver="GeoJSON")
    return BOUNDARY_GEOJSON


@lru_cache(maxsize=1)
def _boundary_wgs84() -> gpd.GeoDataFrame:
    return gpd.read_file(BOUNDARY_SHP).to_crs("EPSG:4326")


def boundary_bounds() -> tuple[float, float, float, float]:
    """(west, south, east, north) of the boundary in WGS84 degrees."""
    return tuple(float(v) for v in _boundary_wgs84().total_bounds)


def boundary_tiles() -> list[str]:
    """Ids of the flood-product tiles the boundary touches.

    MCDWD uses a 10° lat/lon grid: tile hHHvVV has its top-left corner at
    (HH * 10 - 180)°E, (90 - VV * 10)°N.
    """
    boundary = _boundary_wgs84()
    west, south, east, north = boundary_bounds()
    tiles = []
    for h in range(int((west + 180) // 10), int((east + 180) // 10) + 1):
        for v in range(int((90 - north) // 10), int((90 - south) // 10) + 1):
            left, top = h * 10 - 180, 90 - v * 10
            if boundary.intersects(box(left, top - 10, left + 10, top)).any():
                tiles.append(f"h{h:02d}v{v:02d}")
    return tiles


def load_clipped_flood() -> tuple:
    if not os.path.exists(LOCAL_RASTER):
        raise FileNotFoundError(LOCAL_RASTER)
    ensure_boundary_geojson()
    vietnam = gpd.read_file(BOUNDARY_SHP)

    with rasterio.open(LOCAL_RASTER) as src:
        # Boundary phải dùng cùng CRS với raster trước khi Rasterio cắt dữ liệu.
        vietnam = vietnam.to_crs(src.crs)
        geoms = [mapping(g) for g in vietnam.geometry]
        clipped, transform = mask(src, geoms, crop=True, all_touched=False)

    data = clipped[0]
    # Chuẩn hóa dữ liệu nguồn thành format chung của app: 1 = ngập, 0 = không
    # ngập. Nhờ vậy metrics, rendering và inspect dùng cùng một quy ước.
    flood_mask = (data == FLOOD_VALUE).astype(np.uint8)

    # Transform mô tả các cạnh ngoài của array sau khi crop. Bounds này đang
    # thuộc CRS của raster và caller phải hiểu đúng CRS khi sử dụng.
    left = transform.c
    top = transform.f
    right = left + transform.a * data.shape[1]
    bottom = top + transform.e * data.shape[0]

    return flood_mask, (left, bottom, right, top)
