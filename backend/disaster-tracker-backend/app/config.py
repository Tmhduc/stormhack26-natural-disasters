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
BOUNDARY_SHP = os.path.join(DATA_DIR, "vietnam_boundary", "vnm_admin0.shp")
BOUNDARY_GEOJSON = os.path.join(DATA_DIR, "vietnam_boundary", "vietnam.geojson")

# --- Domain constants ---
PIXEL_KM2 = 0.0625
FLOOD_VALUE = 3
