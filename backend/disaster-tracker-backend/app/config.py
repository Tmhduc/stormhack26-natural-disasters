import configparser
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

# Mặc định lấy ngày UTC hiện tại để refresh không bị kẹt ở một dataset cũ.
# Có thể khóa dataset khi demo bằng NASA_YEAR/NASA_DOY/NASA_TILE_ID.
NOW_UTC = datetime.now(timezone.utc)
TILE_ID = os.getenv("NASA_TILE_ID", "h28v07")
YEAR = os.getenv("NASA_YEAR", str(NOW_UTC.year))
DOY = os.getenv("NASA_DOY", str(NOW_UTC.timetuple().tm_yday).zfill(3))
TILE_FILENAME = f"MCDWD_L3_F2_NRT.A{YEAR}{DOY}.{TILE_ID}.061.tif"
TILE_URL = (
    f"https://nrt3.modaps.eosdis.nasa.gov/archive/allData/61/"
    f"MCDWD_L3_F2_NRT/{YEAR}/{DOY}/{TILE_FILENAME}"
)

# Tách dữ liệu input tải về khỏi output được sinh ra. Raster và token chỉ nằm
# local; cache có thể xóa và tạo lại bất cứ lúc nào.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_DIR = os.path.join(BASE_DIR, "cache")

load_dotenv(os.path.join(BASE_DIR, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")  # unset = keep flood history on disk only
NASA_TOKEN = os.getenv("NASA_TOKEN")

# Tiger Cloud's console URL leaves the password out; the pg_service.conf it offers for
# download has it. Point libpq at that file so every connection picks the password up.
PG_SERVICE_FILE = os.path.join(BASE_DIR, "pg_service.conf")
if os.path.exists(PG_SERVICE_FILE):
    _services = configparser.ConfigParser()
    _services.read(PG_SERVICE_FILE)
    if _services.sections():
        os.environ.setdefault("PGSERVICEFILE", PG_SERVICE_FILE)
        os.environ.setdefault("PGSERVICE", _services.sections()[0])

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

# --- LANCE near-real-time source (MODIS NRT Global Flood Product, MCDWD) ---
LANCE_ARCHIVE_URL = "https://nrt3.modaps.eosdis.nasa.gov/archive/allData/61"
LANCE_API_URL = "https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/details/allData/61"
# F1 / F2 / F3 = 1-, 2- and 3-day composites; F1C = 1-day with cloud shadow masked.
LANCE_PRODUCT = os.getenv("LANCE_PRODUCT", "MCDWD_L3_F2_NRT")
# Comma-separated tile ids, e.g. "h28v07". Empty = every tile the boundary touches.
LANCE_TILES = [t.strip() for t in os.getenv("LANCE_TILES", "").split(",") if t.strip()]
LANCE_LOOKBACK_DAYS = int(os.getenv("LANCE_LOOKBACK_DAYS", "7"))  # LANCE keeps about 8 days online
LANCE_POLL_MINUTES = float(os.getenv("LANCE_POLL_MINUTES", "60"))  # 0 turns background polling off

# Các hằng số mô tả sản phẩm raster hiện tại. FLOOD_VALUE là giá trị lớp ngập,
# sẽ được chuyển thành 1 trong binary mask mà phần còn lại của app sử dụng.
PIXEL_KM2 = 0.0625
FLOOD_VALUE = 3
