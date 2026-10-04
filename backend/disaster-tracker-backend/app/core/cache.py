import json
import os
import threading

import numpy as np
from pyproj import Geod
from rasterio.transform import xy

from app.config import CACHE_DIR, FLOOD_VALUE, LOCAL_RASTER, PIXEL_KM2
from app.core.clipper import load_clipped_flood_with_metadata
from app.core.renderer import render_overlay_png

_lock = threading.Lock()
_METRICS_VERSION = 2


def compute_metrics(flood_mask, raster_transform=None, raster_crs=None) -> dict:
    """Calculate flooded area, using geodesic pixel areas when possible."""
    pixels = int(flood_mask.sum())
    if raster_transform is None or raster_crs is None or not raster_crs.is_geographic:
        # Use the configured fallback only when geographic metadata is missing.
        flooded_km2 = pixels * PIXEL_KM2
    else:
        geod = Geod(ellps="WGS84")
        flooded_km2 = 0.0
        for row, count in enumerate(np.count_nonzero(flood_mask, axis=1)):
            if count == 0:
                continue
            # Geographic pixels become smaller toward the poles. A fixed area
            # would overestimate flooding in northern Vietnam.
            left, bottom = xy(raster_transform, row, 0, offset="ul")
            right, top = xy(raster_transform, row, 1, offset="ul")
            left_bottom = xy(raster_transform, row + 1, 0, offset="ul")
            right_bottom = xy(raster_transform, row + 1, 1, offset="ul")
            area, _ = geod.polygon_area_perimeter(
                [left, right, right_bottom[0], left_bottom[0]],
                [top, top, right_bottom[1], left_bottom[1]],
            )
            flooded_km2 += count * abs(area) / 1_000_000
    return {
        "flood_pixels": pixels,
        "flooded_km2": round(flooded_km2, 2),
    }


def _cache_paths() -> dict:
    """Return all generated output paths for the current raster."""
    return {
        "overlay": os.path.join(CACHE_DIR, "flood_overlay.png"),
        "metrics": os.path.join(CACHE_DIR, "metrics.json"),
        "bounds": os.path.join(CACHE_DIR, "bounds.json"),
        "manifest": os.path.join(CACHE_DIR, "manifest.json"),
    }


def _manifest() -> dict:
    stat = os.stat(LOCAL_RASTER)
    return {
        # These values identify the source raster and classification rules used
        # to create the derived cache files.
        "raster_size": stat.st_size,
        "raster_mtime_ns": stat.st_mtime_ns,
        "flood_value": FLOOD_VALUE,
        "pixel_km2": PIXEL_KM2,
        "metrics_version": _METRICS_VERSION,
    }


def is_built() -> bool:
    paths = _cache_paths()
    if not os.path.exists(LOCAL_RASTER) or not all(os.path.exists(p) for p in paths.values()):
        return False
    try:
        with open(paths["manifest"]) as f:
            return json.load(f) == _manifest()
    except (OSError, json.JSONDecodeError):
        return False


def get_or_build():
    with _lock:
        if is_built():
            paths = _cache_paths()
            with open(paths["metrics"]) as f:
                metrics = json.load(f)
            with open(paths["bounds"]) as f:
                bounds = json.load(f)
            return paths["overlay"], metrics, bounds
        return _build()


def rebuild():
    """Rebuild the overlay and metrics from the current raster."""
    with _lock:
        invalidate()
        return _build()


def _build():
    os.makedirs(CACHE_DIR, exist_ok=True)
    paths = _cache_paths()

    # Clipping is expensive, so the same result feeds every output.
    flood_mask, raster_transform, raster_crs, bounds = load_clipped_flood_with_metadata()
    metrics = compute_metrics(flood_mask, raster_transform, raster_crs)
    render_overlay_png(flood_mask, paths["overlay"])

    with open(paths["metrics"], "w") as f:
        json.dump(metrics, f)
    with open(paths["bounds"], "w") as f:
        json.dump(list(bounds), f)
    with open(paths["manifest"], "w") as f:
        json.dump(_manifest(), f)

    return paths["overlay"], metrics, list(bounds)


def store(overlay_png: bytes, metrics: dict, bounds: list) -> None:
    """Use outputs that were built earlier (e.g. restored from the database) for the current raster."""
    with _lock:
        os.makedirs(CACHE_DIR, exist_ok=True)
        paths = _cache_paths()
        with open(paths["overlay"], "wb") as f:
            f.write(overlay_png)
        with open(paths["metrics"], "w") as f:
            json.dump(metrics, f)
        with open(paths["bounds"], "w") as f:
            json.dump(list(bounds), f)
        with open(paths["manifest"], "w") as f:
            json.dump(_manifest(), f)


def invalidate():
    """Delete generated outputs so the next request rebuilds them."""
    for p in _cache_paths().values():
        if os.path.exists(p):
            os.remove(p)
