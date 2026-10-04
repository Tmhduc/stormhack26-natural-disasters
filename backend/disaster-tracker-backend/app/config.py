import os
from dotenv import load_dotenv

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_DIR = os.path.join(BASE_DIR, "cache")

load_dotenv(os.path.join(BASE_DIR, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
NASA_TOKEN = os.getenv("NASA_TOKEN")

RAW_DIR = os.path.join(DATA_DIR, "raw")  # downloaded LANCE tiles, one folder per day
STATE_FILE = os.path.join(DATA_DIR, "pipeline_state.json")
LOCAL_RASTER = os.path.join(DATA_DIR, "vietnam_flood.tif")  # mosaic of the tiles, cropped to the boundary
BOUNDARY_SHP = os.path.join(DATA_DIR, "vietnam_boundary", "vnm_admin0.shp")
BOUNDARY_GEOJSON = os.path.join(DATA_DIR, "vietnam_boundary", "vietnam.geojson")

# --- LANCE near-real-time source (MODIS NRT Global Flood Product, MCDWD) ---
LANCE_ARCHIVE_URL = "https://nrt3.modaps.eosdis.nasa.gov/archive/allData/61"
LANCE_API_URL = "https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/details/allData/61"
# F1 / F2 / F3 = 1-, 2- and 3-day composites; F1C = 1-day with cloud shadow masked.
LANCE_PRODUCT = os.getenv("LANCE_PRODUCT", "MCDWD_L3_F2_NRT")
# Comma-separated tile ids, e.g. "h28v07". Empty = every tile the boundary touches.
LANCE_TILES = [t.strip() for t in os.getenv("LANCE_TILES", "").split(",") if t.strip()]
LANCE_LOOKBACK_DAYS = int(os.getenv("LANCE_LOOKBACK_DAYS", "7"))  # LANCE keeps about 8 days online
LANCE_POLL_MINUTES = float(os.getenv("LANCE_POLL_MINUTES", "60"))  # 0 turns background polling off

# --- Domain constants ---
PIXEL_KM2 = 0.0625
FLOOD_VALUE = 3
