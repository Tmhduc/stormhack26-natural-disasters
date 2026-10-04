import os
import math
import zipfile
from functools import lru_cache

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.mask import raster_geometry_mask
from rasterio.transform import array_bounds
from rasterio.warp import transform as transform_coordinates
from rasterio.warp import transform_bounds, transform_geom
from rasterio.windows import Window
from shapely import clip_by_rect
from shapely.geometry import Point, box, mapping

from app.config import (
    LOCAL_RASTER,
    BOUNDARY_ADMIN1_SHP,
    BOUNDARY_SHP,
    BOUNDARY_ZIP,
    BROWSER_BOUNDARY_GEOJSON,
    BROWSER_BOUNDARY_TOLERANCE,
    FLOOD_VALUE,
)

MCDWD_CLASS_NAMES = {
    0: "no_water",
    1: "reference_water",
    2: "recurring_flood",
    3: "unusual_flood",
    255: "insufficient_data",
}
MCDWD_FLOOD_CLASSES = frozenset({2, 3})


def ensure_boundary_files() -> None:
    """Extract the country and province shapefiles from the committed archive if they're missing.

    data/ isn't in Git, so a fresh deploy starts without them.
    """
    if os.path.exists(BOUNDARY_SHP) and os.path.exists(BOUNDARY_ADMIN1_SHP):
        return
    wanted = ("vnm_admin0.", "vnm_admin1.")
    with zipfile.ZipFile(BOUNDARY_ZIP) as archive:
        members = [m for m in archive.namelist() if m.startswith(wanted)]
        # .shp last: its presence is what marks the extraction as complete.
        for member in sorted(members, key=lambda m: m.endswith(".shp")):
            archive.extract(member, os.path.dirname(BOUNDARY_SHP))


def ensure_browser_boundary_geojson() -> str:
    """Create a lightweight boundary for browser rendering on first request."""
    if not os.path.exists(BROWSER_BOUNDARY_GEOJSON):
        # Simplify the boundary already held in memory. Writing the full-resolution boundary
        # to GeoJSON and reading it back first peaked at ~660 MB, enough to kill a 512 MB server.
        boundary = _boundary_wgs84()
        simplified = gpd.GeoDataFrame(
            boundary.drop(columns="geometry"),
            geometry=boundary.geometry.simplify(BROWSER_BOUNDARY_TOLERANCE, preserve_topology=True),
            crs=boundary.crs,
        )
        os.makedirs(os.path.dirname(BROWSER_BOUNDARY_GEOJSON), exist_ok=True)
        simplified.to_file(BROWSER_BOUNDARY_GEOJSON, driver="GeoJSON")
    return BROWSER_BOUNDARY_GEOJSON


@lru_cache(maxsize=1)
def _boundary_wgs84() -> gpd.GeoDataFrame:
    return gpd.read_file(BOUNDARY_SHP).to_crs("EPSG:4326")


def boundary_bounds() -> tuple[float, float, float, float]:
    """Return the boundary as (west, south, east, north) in WGS84 degrees."""
    return tuple(float(v) for v in _boundary_wgs84().total_bounds)


def administrative_area(lat: float, lon: float) -> dict | None:
    """Find the local admin1 area containing a WGS84 coordinate."""
    # Read only the provinces whose bounding box holds the point (the shapefile is in WGS84).
    # Keeping all 63 full-resolution provinces in memory pushed a 512 MB server over its limit.
    candidates = gpd.read_file(BOUNDARY_ADMIN1_SHP, bbox=(lon, lat, lon, lat)).to_crs("EPSG:4326")
    matches = candidates[candidates.geometry.covers(Point(lon, lat))]
    if matches.empty:
        return None
    area = matches.iloc[0]
    return {
        "name": str(area["adm1_name"]),
        "type": str(area["adm1_type_"]),
        "pcode": str(area["adm1_pcode"]),
    }


def boundary_tiles() -> list[str]:
    """Find flood-product tile IDs intersecting the national boundary.

    MCDWD uses a 10-degree latitude/longitude grid. Tile hHHvVV has its
    top-left corner at (HH * 10 - 180)°E, (90 - VV * 10)°N.
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


def _load_clipped_flood() -> tuple:
    if not os.path.exists(LOCAL_RASTER):
        raise FileNotFoundError(LOCAL_RASTER)
    vietnam = gpd.read_file(BOUNDARY_SHP)

    with rasterio.open(LOCAL_RASTER) as src:
        # Rasterio requires the boundary and raster to use the same CRS.
        vietnam = vietnam.to_crs(src.crs)
        # The same window and pixels as rasterio.mask.mask(crop=True), without the masked-array
        # copies of the whole raster it makes, which pushed a 512 MB server over its limit.
        outside, transform, window = raster_geometry_mask(src, vietnam.geometry, crop=True, all_touched=False)
        data = src.read(1, window=window)
        raster_crs = src.crs

    # Normalize source data into the app convention: 1 = flood, 0 = not flood.
    # Metrics, rendering, and inspection then share the same representation.
    flood = data == FLOOD_VALUE
    np.logical_not(outside, out=outside)  # in place: now True inside the boundary
    flood &= outside
    flood_mask = flood.view(np.uint8)  # bool is already 0/1 bytes; no copy needed

    # The transform describes the cropped array's outer edges in the raster CRS.
    raster_bounds = array_bounds(flood_mask.shape[0], flood_mask.shape[1], transform)

    # The API accepts latitude/longitude, so bounds must be returned in WGS84
    # even when the source raster uses a projected CRS.
    bounds = transform_bounds(raster_crs, "EPSG:4326", *raster_bounds)
    return flood_mask, transform, raster_crs, tuple(float(value) for value in bounds)


@lru_cache(maxsize=1)
def _load_clipped_flood_cached(raster_signature: tuple[int, int]) -> tuple:
    """Cache the expensive crop step until the mosaic file changes."""
    return _load_clipped_flood()


def _raster_signature() -> tuple[int, int]:
    stat = os.stat(LOCAL_RASTER)
    return stat.st_size, stat.st_mtime_ns


def load_clipped_flood() -> tuple:
    flood_mask, _, _, bounds = _load_clipped_flood_cached(_raster_signature())
    return flood_mask, bounds


def load_clipped_flood_with_metadata() -> tuple:
    """Return the mask plus transform and CRS needed for coordinate lookup."""
    return _load_clipped_flood_cached(_raster_signature())


def inspect_flood_point(lat: float, lon: float) -> int | None:
    """Read the original product class at a WGS84 coordinate."""
    if not _boundary_wgs84().geometry.covers(Point(lon, lat)).any():
        return None

    with rasterio.open(LOCAL_RASTER) as src:
        x, y = transform_coordinates("EPSG:4326", src.crs, [lon], [lat])
        row, column = src.index(x[0], y[0])
        if not (0 <= row < src.height and 0 <= column < src.width):
            return None
        value = src.read(1, window=Window(column, row, 1, 1))[0, 0]
    return int(value)


def inspect_flood_neighborhood(lat: float, lon: float, radius_km: float) -> dict | None:
    """Count product classes in a small neighborhood around a WGS84 point."""
    if not _boundary_wgs84().geometry.covers(Point(lon, lat)).any():
        return None

    with rasterio.open(LOCAL_RASTER) as src:
        x, y = transform_coordinates("EPSG:4326", src.crs, [lon], [lat])
        row, column = src.index(x[0], y[0])
        if not (0 <= row < src.height and 0 <= column < src.width):
            return None

        meters_per_pixel = abs(src.res[1]) * 111_320
        pixel_radius = max(1, math.ceil(radius_km * 1000 / meters_per_pixel))
        window = Window(
            column - pixel_radius,
            row - pixel_radius,
            pixel_radius * 2 + 1,
            pixel_radius * 2 + 1,
        ).intersection(Window(0, 0, src.width, src.height))
        data = src.read(1, window=window)
        source_transform = src.window_transform(window)
        # Rasterize only the boundary around this window (plus a margin). Converting and caching
        # the whole country's ~700k points instead kept ~120 MB in memory for good.
        margin = 2 * abs(src.res[0])
        west, south, east, north = transform_bounds(src.crs, "EPSG:4326", *src.window_bounds(window))
        nearby = [
            clip_by_rect(geometry, west - margin, south - margin, east + margin, north + margin)
            for geometry in _boundary_wgs84().geometry
        ]
        shapes = [transform_geom("EPSG:4326", src.crs.to_string(), mapping(g)) for g in nearby if not g.is_empty]
        inside = geometry_mask(
            shapes,
            out_shape=data.shape,
            transform=source_transform,
            invert=True,
            all_touched=False,
        ) if shapes else np.zeros(data.shape, dtype=bool)

    class_counts = {
        name: int(((data == value) & inside).sum())
        for value, name in MCDWD_CLASS_NAMES.items()
    }
    return {
        "radius_km": radius_km,
        "pixels": int(inside.sum()),
        "class_counts": class_counts,
        "flood_pixels": sum(class_counts.get(MCDWD_CLASS_NAMES[value], 0) for value in MCDWD_FLOOD_CLASSES),
    }
