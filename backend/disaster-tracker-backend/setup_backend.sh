#!/usr/bin/env bash
set -e

BE="$HOME/repos/stormhack26-natural-disasters/backend/disaster-tracker-backend"
cd "$BE"

echo "🏗️  Setting up backend at $BE"

# =========================================================
# FOLDERS
# =========================================================
mkdir -p app/core app/routes data/vietnam_boundary cache

touch app/__init__.py
touch app/core/__init__.py
touch app/routes/__init__.py

# =========================================================
# app/config.py
# =========================================================
cat > app/config.py << 'EOF'
import os

# --- Tile selection ---
TILE_ID = "h28v07"
YEAR = "2026"
DOY = "276"
TILE_FILENAME = f"MCDWD_L3_F2_NRT.A{YEAR}{DOY}.{TILE_ID}.061.tif"
TILE_URL = (
    f"https://nrt3.modaps.eosdis.nasa.gov/archive/allData/61/"
    f"MCDWD_L3_F2_NRT/{YEAR}/{DOY}/{TILE_FILENAME}"
)

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_DIR = os.path.join(BASE_DIR, "cache")

TOKEN_FILE = os.path.join(DATA_DIR, ".token")
LOCAL_RASTER = os.path.join(DATA_DIR, "vietnam_flood.tif")
BOUNDARY_SHP = os.path.join(DATA_DIR, "vietnam_boundary", "vnm_admbnda_adm0_2022.shp")
BOUNDARY_GEOJSON = os.path.join(DATA_DIR, "vietnam_boundary", "vietnam.geojson")

# --- Domain constants ---
PIXEL_KM2 = 0.0625
FLOOD_VALUE = 3
EOF

# =========================================================
# app/models.py
# =========================================================
cat > app/models.py << 'EOF'
from pydantic import BaseModel
from typing import Optional, List

Bounds = List[float]


class FloodMetrics(BaseModel):
    flood_pixels: int
    flooded_km2: float
    bounds: Bounds
    tile_id: str
    date: str
    last_updated: Optional[str] = None


class OverlayResponse(BaseModel):
    png_url: str
    bounds: Bounds


class InspectResponse(BaseModel):
    inside: bool
    flooded: Optional[bool] = None
    lat: float
    lon: float
EOF

# =========================================================
# app/core/downloader.py
# =========================================================
cat > app/core/downloader.py << 'EOF'
import requests
from app.config import TILE_URL, TOKEN_FILE, LOCAL_RASTER


def download_tile() -> str:
    """Download the NASA MODIS flood tile. Returns the local path."""
    token = open(TOKEN_FILE).read().strip()
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(TILE_URL, headers=headers, stream=True)
    r.raise_for_status()

    with open(LOCAL_RASTER, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return LOCAL_RASTER
EOF

# =========================================================
# app/core/clipper.py
# =========================================================
cat > app/core/clipper.py << 'EOF'
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
EOF

# =========================================================
# app/core/renderer.py
# =========================================================
cat > app/core/renderer.py << 'EOF'
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np


def render_overlay_png(flood_mask: np.ndarray, output_path: str) -> str:
    cmap = ListedColormap([
        (0, 0, 0, 0),
        (0.85, 0, 0, 1),
    ])

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(flood_mask, cmap=cmap, interpolation="nearest")
    ax.axis("off")
    plt.savefig(
        output_path,
        transparent=True,
        bbox_inches="tight",
        pad_inches=0,
        dpi=150,
        facecolor="none",
    )
    plt.close()
    return output_path
EOF

# =========================================================
# app/core/cache.py
# =========================================================
cat > app/core/cache.py << 'EOF'
import json
import os
from app.config import CACHE_DIR, PIXEL_KM2
from app.core.clipper import load_clipped_flood
from app.core.renderer import render_overlay_png


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


def get_or_build():
    os.makedirs(CACHE_DIR, exist_ok=True)
    paths = _cache_paths()

    if all(os.path.exists(p) for p in paths.values()):
        with open(paths["metrics"]) as f:
            metrics = json.load(f)
        with open(paths["bounds"]) as f:
            bounds = json.load(f)
        return paths["overlay"], metrics, bounds

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
EOF

# =========================================================
# app/routes/health.py
# =========================================================
cat > app/routes/health.py << 'EOF'
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    return {"status": "ok"}
EOF

# =========================================================
# app/routes/flood.py
# =========================================================
cat > app/routes/flood.py << 'EOF'
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import CACHE_DIR, LOCAL_RASTER, BOUNDARY_GEOJSON, TILE_ID, YEAR, DOY
from app.core import cache
from app.core.clipper import ensure_boundary_geojson, load_clipped_flood
from app.core.downloader import download_tile
from app.models import FloodMetrics, OverlayResponse, InspectResponse

router = APIRouter(prefix="/api/flood", tags=["flood"])


@router.get("/metrics", response_model=FloodMetrics)
def get_metrics():
    try:
        _, metrics, bounds = cache.get_or_build()
    except FileNotFoundError:
        raise HTTPException(404, "Raster not downloaded. Call POST /api/flood/refresh.")

    mtime = os.path.getmtime(LOCAL_RASTER) if os.path.exists(LOCAL_RASTER) else None
    return FloodMetrics(
        **metrics,
        bounds=bounds,
        tile_id=TILE_ID,
        date=f"{YEAR}-{DOY}",
        last_updated=datetime.fromtimestamp(mtime).isoformat() if mtime else None,
    )


@router.get("/overlay", response_model=OverlayResponse)
def get_overlay():
    try:
        _, _, bounds = cache.get_or_build()
    except FileNotFoundError:
        raise HTTPException(404, "Overlay not built.")
    return OverlayResponse(png_url="/static/flood_overlay.png", bounds=bounds)


@router.get("/boundary")
def get_boundary():
    if not os.path.exists(BOUNDARY_GEOJSON):
        ensure_boundary_geojson()
    return FileResponse(BOUNDARY_GEOJSON, media_type="application/geo+json")


@router.post("/refresh")
def refresh():
    try:
        download_tile()
        cache.invalidate()
        _, metrics, bounds = cache.get_or_build()
        return {"status": "refreshed", **metrics, "bounds": bounds}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/inspect", response_model=InspectResponse)
def inspect(lat: float, lon: float):
    flood_mask, bounds = load_clipped_flood()
    left, bottom, right, top = bounds
    h, w = flood_mask.shape

    if not (left <= lon <= right and bottom <= lat <= top):
        return InspectResponse(inside=False, lat=lat, lon=lon)

    x = max(0, min(int((lon - left) / (right - left) * w), w - 1))
    y = max(0, min(int((top - lat) / (top - bottom) * h), h - 1))
    return InspectResponse(
        inside=True, flooded=bool(flood_mask[y, x] == 1), lat=lat, lon=lon
    )
EOF

# =========================================================
# app/main.py
# =========================================================
cat > app/main.py << 'EOF'
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import CACHE_DIR
from app.routes import health, flood

app = FastAPI(title="Vietnam Flood Monitor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(CACHE_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=CACHE_DIR), name="static")

app.include_router(health.router)
app.include_router(flood.router)
EOF

# =========================================================
# .gitignore
# =========================================================
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.pyc
.venv/
venv/

# Secrets
.token
*.env

# Data
data/
cache/

# IDE
.vscode/
.idea/
.DS_Store
EOF

echo ""
echo "✅ Backend architecture created at $BE"
echo ""
echo "Structure:"
find app -type f | sort
echo ""
echo "Next steps:"
echo "  1. cd $BE"
echo "  2. echo 'YOUR_EARTHDATA_TOKEN' > data/.token"
echo "  3. Download NASA tile → data/vietnam_flood.tif"
echo "  4. Download + unzip Vietnam boundary → data/vietnam_boundary/"
echo "  5. Fix BOUNDARY_SHP filename in app/config.py"
echo "  6. uv run uvicorn app.main:app --reload --port 8000"
