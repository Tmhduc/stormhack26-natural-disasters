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
    if not os.path.exists(BOUNDARY_GEOJSON):
        gdf = gpd.read_file(BOUNDARY_SHP)
        gdf.to_file(BOUNDARY_GEOJSON, driver="GeoJSON")
    return BOUNDARY_GEOJSON


def load_clipped_flood() -> tuple:
    ensure_boundary_geojson()
    vietnam = gpd.read_file(BOUNDARY_SHP)

    with rasterio.open(LOCAL_RASTER) as src:
        vietnam = vietnam.to_crs(src.crs)
        geoms = [mapping(g) for g in vietnam.geometry]
        clipped, transform = mask(src, geoms, crop=True, all_touched=False)

    data = clipped[0]
    flood_mask = (data == FLOOD_VALUE).astype(np.uint8)

    left = transform.c
    top = transform.f
    right = left + transform.a * data.shape[1]
    bottom = top + transform.e * data.shape[0]

    return flood_mask, (left, bottom, right, top)
