import os
from datetime import datetime, timezone
from dotenv import load_dotenv

# Use the current UTC date by default so refreshes do not stay on an old dataset.
# A demo can pin a dataset with NASA_YEAR/NASA_DOY/NASA_TILE_ID.
NOW_UTC = datetime.now(timezone.utc)
TILE_ID = os.getenv("NASA_TILE_ID", "h28v07")
YEAR = os.getenv("NASA_YEAR", str(NOW_UTC.year))
DOY = os.getenv("NASA_DOY", str(NOW_UTC.timetuple().tm_yday).zfill(3))
TILE_FILENAME = f"MCDWD_L3_F2_NRT.A{YEAR}{DOY}.{TILE_ID}.061.tif"
TILE_URL = (
    f"https://nrt3.modaps.eosdis.nasa.gov/archive/allData/61/"
    f"MCDWD_L3_F2_NRT/{YEAR}/{DOY}/{TILE_FILENAME}"
)

# Keep downloaded inputs separate from generated outputs. Raster files and tokens
# remain local; generated cache files can be deleted and rebuilt at any time.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_DIR = os.path.join(BASE_DIR, "cache")

load_dotenv(os.path.join(BASE_DIR, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")  # unset = keep flood history on disk only
NASA_TOKEN = os.getenv("NASA_TOKEN")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RAW_DIR = os.path.join(DATA_DIR, "raw")  # Downloaded LANCE tiles, grouped by day.
STATE_FILE = os.path.join(DATA_DIR, "pipeline_state.json")
LOCAL_RASTER = os.path.join(DATA_DIR, "vietnam_flood.tif")  # Boundary-limited tile mosaic.
BOUNDARY_SHP = os.path.join(DATA_DIR, "vietnam_boundary", "vnm_admin0.shp")
BOUNDARY_ADMIN1_SHP = os.path.join(DATA_DIR, "vietnam_boundary", "vnm_admin1.shp")
BOUNDARY_GEOJSON = os.path.join(DATA_DIR, "vietnam_boundary", "vietnam.geojson")
# Browser-only boundary: simplified enough for fast SVG rendering. The full
# boundary remains the source for backend geospatial calculations.
BROWSER_BOUNDARY_GEOJSON = os.path.join(CACHE_DIR, "vietnam_boundary_simplified.geojson")
BROWSER_BOUNDARY_TOLERANCE = float(os.getenv("BROWSER_BOUNDARY_TOLERANCE", "0.005"))

# --- LANCE near-real-time source (MODIS NRT Global Flood Product, MCDWD) ---
LANCE_ARCHIVE_URL = "https://nrt3.modaps.eosdis.nasa.gov/archive/allData/61"
LANCE_API_URL = "https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/details/allData/61"
# F1 / F2 / F3 are one-, two-, and three-day composites; F1C masks cloud shadow.
LANCE_PRODUCT = os.getenv("LANCE_PRODUCT", "MCDWD_L3_F2_NRT")
# Comma-separated tile IDs, for example "h28v07". Empty means all boundary tiles.
LANCE_TILES = [t.strip() for t in os.getenv("LANCE_TILES", "").split(",") if t.strip()]
LANCE_LOOKBACK_DAYS = int(os.getenv("LANCE_LOOKBACK_DAYS", "7"))  # LANCE keeps roughly eight days online.
LANCE_DATA_LAG_DAYS = int(os.getenv("LANCE_DATA_LAG_DAYS", "1"))  # Prefer a more complete day over the newest partial day.
LANCE_POLL_MINUTES = float(os.getenv("LANCE_POLL_MINUTES", "60"))  # Set to 0 to disable the background poller.

# --- LANCE near-real-time source (MODIS NRT Global Flood Product, MCDWD) ---
LANCE_ARCHIVE_URL = "https://nrt3.modaps.eosdis.nasa.gov/archive/allData/61"
LANCE_API_URL = "https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/details/allData/61"
# F1 / F2 / F3 are one-, two-, and three-day composites; F1C masks cloud shadow.
LANCE_PRODUCT = os.getenv("LANCE_PRODUCT", "MCDWD_L3_F2_NRT")
# Comma-separated tile IDs, for example "h28v07". Empty means all boundary tiles.
LANCE_TILES = [t.strip() for t in os.getenv("LANCE_TILES", "").split(",") if t.strip()]
LANCE_LOOKBACK_DAYS = int(os.getenv("LANCE_LOOKBACK_DAYS", "7"))  # LANCE keeps roughly eight days online.
LANCE_DATA_LAG_DAYS = int(os.getenv("LANCE_DATA_LAG_DAYS", "1"))  # Prefer a more complete day over the newest partial day.
LANCE_POLL_MINUTES = float(os.getenv("LANCE_POLL_MINUTES", "60"))  # Set to 0 to disable the background poller.

# Product constants for the current raster. FLOOD_VALUE is converted to 1 in
# the binary flood mask used by the rest of the application.
PIXEL_KM2 = 0.0625
FLOOD_VALUE = 3
