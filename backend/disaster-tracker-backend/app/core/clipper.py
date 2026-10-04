import os
import math
from functools import lru_cache

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.mask import mask
from rasterio.transform import array_bounds
from rasterio.warp import transform as transform_coordinates
from rasterio.warp import transform_bounds, transform_geom
from rasterio.windows import Window
from shapely.geometry import Point, box, mapping
from shapely.ops import unary_union

from app.config import (
    LOCAL_RASTER, BOUNDARY_ADMIN1_SHP, BOUNDARY_SHP, BOUNDARY_GEOJSON, FLOOD_VALUE
)

MCDWD_CLASS_NAMES = {
    0: "no_water",
    1: "reference_water",
    2: "recurring_flood",
    3: "unusual_flood",
    255: "insufficient_data",
}
MCDWD_FLOOD_CLASSES = frozenset({2, 3})


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
    """Trả về (tây, nam, đông, bắc) của boundary theo độ WGS84."""
    return tuple(float(v) for v in _boundary_wgs84().total_bounds)


@lru_cache(maxsize=1)
def _admin1_wgs84() -> gpd.GeoDataFrame:
    return gpd.read_file(BOUNDARY_ADMIN1_SHP).to_crs("EPSG:4326")


def administrative_area(lat: float, lon: float) -> dict | None:
    """Tìm tỉnh/thành chứa tọa độ WGS84 bằng boundary admin1 local."""
    matches = _admin1_wgs84()[_admin1_wgs84().geometry.covers(Point(lon, lat))]
    if matches.empty:
        return None
    area = matches.iloc[0]
    return {
        "name": str(area["adm1_name"]),
        "type": str(area["adm1_type_"]),
        "pcode": str(area["adm1_pcode"]),
    }


def boundary_tiles() -> list[str]:
    """Tìm ID các tile của sản phẩm ngập giao với boundary.

    MCDWD dùng lưới kinh/vĩ độ 10 độ: tile hHHvVV có góc trên-trái tại
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


def _load_clipped_flood() -> tuple:
    if not os.path.exists(LOCAL_RASTER):
        raise FileNotFoundError(LOCAL_RASTER)
    ensure_boundary_geojson()
    vietnam = gpd.read_file(BOUNDARY_SHP)

    with rasterio.open(LOCAL_RASTER) as src:
        # Boundary phải dùng cùng CRS với raster trước khi Rasterio cắt dữ liệu.
        vietnam = vietnam.to_crs(src.crs)
        geoms = [mapping(g) for g in vietnam.geometry]
        clipped, transform = mask(src, geoms, crop=True, all_touched=False)
        raster_crs = src.crs

    data = clipped[0]
    # Chuẩn hóa dữ liệu nguồn thành format chung của app: 1 = ngập, 0 = không
    # ngập. Nhờ vậy metrics, rendering và inspect dùng cùng một quy ước.
    flood_mask = (data == FLOOD_VALUE).astype(np.uint8)

    # Transform mô tả các cạnh ngoài của array sau khi crop trong CRS của raster.
    raster_bounds = array_bounds(data.shape[0], data.shape[1], transform)

    # API nhận latitude/longitude, vì vậy bounds phải trả về WGS84 ngay cả khi
    # raster nguồn dùng một CRS chiếu khác.
    bounds = transform_bounds(raster_crs, "EPSG:4326", *raster_bounds)
    return flood_mask, transform, raster_crs, tuple(float(value) for value in bounds)


@lru_cache(maxsize=1)
def _load_clipped_flood_cached(raster_signature: tuple[int, int]) -> tuple:
    """Cache bước crop tốn thời gian cho đến khi file mosaic thay đổi."""
    return _load_clipped_flood()


def _raster_signature() -> tuple[int, int]:
    stat = os.stat(LOCAL_RASTER)
    return stat.st_size, stat.st_mtime_ns


def load_clipped_flood() -> tuple:
    flood_mask, _, _, bounds = _load_clipped_flood_cached(_raster_signature())
    return flood_mask, bounds


def load_clipped_flood_with_metadata() -> tuple:
    """Trả về mask cùng transform và CRS cần cho việc tra cứu tọa độ."""
    return _load_clipped_flood_cached(_raster_signature())


def inspect_flood_point(lat: float, lon: float) -> int | None:
    """Đọc và giữ nguyên class gốc của pixel chứa điểm WGS84."""
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
    """Thống kê class trong một vùng lân cận nhỏ quanh tọa độ WGS84."""
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
        boundary = unary_union(_boundary_wgs84().geometry)
        boundary_in_raster = transform_geom(
            "EPSG:4326",
            src.crs,
            mapping(boundary),
        )
        inside = geometry_mask(
            [boundary_in_raster],
            out_shape=data.shape,
            transform=source_transform,
            invert=True,
            all_touched=False,
        )

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
