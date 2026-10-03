import os
from datetime import datetime, timezone

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

TOKEN_FILE = os.path.join(DATA_DIR, ".token")
LOCAL_RASTER = os.path.join(DATA_DIR, "vietnam_flood.tif")
BOUNDARY_SHP = os.path.join(DATA_DIR, "vietnam_boundary", "vnm_admin0.shp")
BOUNDARY_GEOJSON = os.path.join(DATA_DIR, "vietnam_boundary", "vietnam.geojson")

# Các hằng số mô tả sản phẩm raster hiện tại. FLOOD_VALUE là giá trị lớp ngập,
# sẽ được chuyển thành 1 trong binary mask mà phần còn lại của app sử dụng.
PIXEL_KM2 = 0.0625
FLOOD_VALUE = 3
