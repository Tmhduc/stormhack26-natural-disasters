import requests
from app.config import TILE_URL, TOKEN_FILE, LOCAL_RASTER


def download_tile() -> str:
    """Tải tile flood của NASA và trả về đường dẫn file local."""
    # Token chỉ nằm ở backend. Browser chỉ gọi API refresh và không bao giờ
    # nhận credential dùng để gọi NASA.
    token = open(TOKEN_FILE).read().strip()
    headers = {"Authorization": f"Bearer {token}"}

    # Streaming giúp không phải nạp toàn bộ raster vào RAM trước khi ghi file.
    r = requests.get(TILE_URL, headers=headers, stream=True)
    r.raise_for_status()

    # Raster local là input cho việc cắt dữ liệu, tính metrics và kiểm tra điểm.
    with open(LOCAL_RASTER, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return LOCAL_RASTER
