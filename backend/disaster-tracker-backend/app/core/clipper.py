import os
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping

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


def load_clipped_flood() -> tuple:
    """Trả về binary flood mask của Việt Nam và bounds của raster sau khi cắt."""
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
