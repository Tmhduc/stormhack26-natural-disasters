import os

import requests
from app.config import DATA_DIR, TILE_URL, TOKEN_FILE, LOCAL_RASTER


def download_tile() -> str:
    """Tải tile flood của NASA và trả về đường dẫn file local."""
    # Token chỉ nằm ở backend. Browser chỉ gọi API refresh và không bao giờ
    # nhận credential dùng để gọi NASA.
    token = os.getenv("NASA_TOKEN")
    if not token and os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, encoding="utf-8") as token_file:
            token = token_file.read().strip()
    if not token:
        raise RuntimeError("NASA token is missing. Set NASA_TOKEN or create data/.token.")

    headers = {"Authorization": f"Bearer {token}"}

    # Streaming giúp không phải nạp toàn bộ raster vào RAM trước khi ghi file.
    os.makedirs(DATA_DIR, exist_ok=True)
    temporary_raster = f"{LOCAL_RASTER}.part"
    with requests.get(TILE_URL, headers=headers, stream=True, timeout=120) as response:
        response.raise_for_status()

        # Ghi file tạm trước. Nếu mạng lỗi giữa chừng, raster cũ vẫn còn dùng
        # được thay vì bị thay bằng một file hỏng hoặc chưa hoàn chỉnh.
        with open(temporary_raster, "wb") as raster_file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    raster_file.write(chunk)

    # Chỉ thay input chính sau khi download hoàn tất thành công.
    os.replace(temporary_raster, LOCAL_RASTER)
    return LOCAL_RASTER
