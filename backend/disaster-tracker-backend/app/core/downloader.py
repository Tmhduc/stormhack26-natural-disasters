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
