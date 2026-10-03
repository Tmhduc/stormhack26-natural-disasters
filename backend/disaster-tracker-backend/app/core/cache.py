import json
import os
from app.config import CACHE_DIR, PIXEL_KM2
from app.core.clipper import load_clipped_flood
from app.core.renderer import render_overlay_png


def compute_metrics(flood_mask) -> dict:
    """Chuyển binary flood mask thành các giá trị dashboard hiển thị."""
    pixels = int(flood_mask.sum())
    return {
        "flood_pixels": pixels,
        "flooded_km2": round(pixels * PIXEL_KM2, 2),
    }


def _cache_paths() -> dict:
    """Trả về toàn bộ đường dẫn output được sinh ra cho một raster."""
    return {
        "overlay": os.path.join(CACHE_DIR, "flood_overlay.png"),
        "metrics": os.path.join(CACHE_DIR, "metrics.json"),
        "bounds": os.path.join(CACHE_DIR, "bounds.json"),
    }


def get_or_build():
    """Dùng cache nếu có hoặc build lại output từ raster local."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    paths = _cache_paths()

    # Chỉ xem cache là sẵn sàng khi đủ mọi artifact. Nếu thiếu một file thì
    # build lại toàn bộ để metrics và overlay luôn khớp với nhau.
    if all(os.path.exists(p) for p in paths.values()):
        with open(paths["metrics"]) as f:
            metrics = json.load(f)
        with open(paths["bounds"]) as f:
            bounds = json.load(f)
        return paths["overlay"], metrics, bounds

    # Clipping là bước tốn thời gian; kết quả của nó được dùng cho mọi output.
    flood_mask, bounds = load_clipped_flood()
    metrics = compute_metrics(flood_mask)
    render_overlay_png(flood_mask, paths["overlay"])

    with open(paths["metrics"], "w") as f:
        json.dump(metrics, f)
    with open(paths["bounds"], "w") as f:
        json.dump(list(bounds), f)

    return paths["overlay"], metrics, list(bounds)


def invalidate():
    """Xóa output để request tiếp theo build lại từ raster mới."""
    for p in _cache_paths().values():
        if os.path.exists(p):
            os.remove(p)
