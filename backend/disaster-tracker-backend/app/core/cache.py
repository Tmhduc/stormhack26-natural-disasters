import json
import os
import threading
from app.config import CACHE_DIR, PIXEL_KM2
from app.core.clipper import load_clipped_flood
from app.core.renderer import render_overlay_png

_lock = threading.Lock()


def compute_metrics(flood_mask) -> dict:
    pixels = int(flood_mask.sum())
    return {
        "flood_pixels": pixels,
        "flooded_km2": round(pixels * PIXEL_KM2, 2),
    }


def _cache_paths() -> dict:
    return {
        "overlay": os.path.join(CACHE_DIR, "flood_overlay.png"),
        "metrics": os.path.join(CACHE_DIR, "metrics.json"),
        "bounds": os.path.join(CACHE_DIR, "bounds.json"),
    }


def is_built() -> bool:
    return all(os.path.exists(p) for p in _cache_paths().values())


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

    flood_mask, bounds = load_clipped_flood()
    metrics = compute_metrics(flood_mask)
    render_overlay_png(flood_mask, paths["overlay"])

    with open(paths["metrics"], "w") as f:
        json.dump(metrics, f)
    with open(paths["bounds"], "w") as f:
        json.dump(list(bounds), f)

    return paths["overlay"], metrics, list(bounds)


def invalidate():
    for p in _cache_paths().values():
        if os.path.exists(p):
            os.remove(p)
