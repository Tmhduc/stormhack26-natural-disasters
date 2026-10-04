"""Client for the LANCE near-real-time archive: find published flood tiles and download them."""

import logging
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import LANCE_API_URL, LANCE_ARCHIVE_URL, LANCE_PRODUCT, NASA_TOKEN, RAW_DIR

log = logging.getLogger(__name__)

# e.g. MCDWD_L3_F2_NRT.A2026276.h28v07.061.tif
_TILE_NAME = re.compile(r"\.A\d{7}\.(h\d{2}v\d{2})\.\d{3}\.tif$")


class LanceError(RuntimeError):
    pass


@dataclass(frozen=True)
class RemoteTile:
    tile: str
    name: str
    day: date
    size: int
    mtime: int  # changes whenever LANCE reprocesses the tile with newer swaths

    @property
    def url(self) -> str:
        return f"{LANCE_ARCHIVE_URL}/{LANCE_PRODUCT}/{self.day:%Y}/{self.day:%j}/{self.name}"

    @property
    def local_path(self) -> str:
        return os.path.join(RAW_DIR, f"{self.day:%Y%j}", self.name)


def _make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=4, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    if NASA_TOKEN:
        session.headers["Authorization"] = f"Bearer {NASA_TOKEN}"
    return session


_session = _make_session()


def list_day(day: date) -> dict[str, RemoteTile]:
    """Every tile LANCE has published for `day` (UTC), keyed by tile id. Empty if the day isn't online."""
    url = f"{LANCE_API_URL}/{LANCE_PRODUCT}/{day:%Y}/{day:%j}"
    r = _session.get(url, params={"fields": "all", "formats": "json"}, timeout=30)
    if r.status_code == 404:  # not published yet, or already rolled off the archive
        return {}
    r.raise_for_status()

    tiles = {}
    for item in r.json().get("content", []):
        match = _TILE_NAME.search(item["name"])
        if match and item.get("status") == "Online":
            tiles[match[1]] = RemoteTile(match[1], item["name"], day, int(item["size"]), int(item["mtime"]))
    return tiles


def tiles_for_day(day: date, tiles: list[str]) -> list[RemoteTile]:
    available = list_day(day)
    missing = [t for t in tiles if t not in available]
    if missing:
        raise LanceError(f"{LANCE_PRODUCT} for {day} is missing tiles {missing}")
    return [available[t] for t in tiles]


def find_latest(tiles: list[str], lookback_days: int) -> tuple[date, list[RemoteTile]]:
    """The newest UTC day with every one of `tiles` published, and those tiles.

    The current day fills in gradually as satellite passes are processed, so it is
    skipped until it is complete rather than mosaicking a partial day.
    """
    today = datetime.now(timezone.utc).date()
    for back in range(lookback_days + 1):
        day = today - timedelta(days=back)
        try:
            return day, tiles_for_day(day, tiles)
        except LanceError as e:
            log.info("%s, trying the day before", e)
    raise LanceError(f"No day in the last {lookback_days} days has all of {tiles} published")


def is_current(tile: RemoteTile) -> bool:
    path = tile.local_path
    return (
        os.path.exists(path)
        and os.path.getsize(path) == tile.size
        and int(os.path.getmtime(path)) == tile.mtime
    )


def download_tile(tile: RemoteTile) -> str:
    """Download `tile` unless that exact version is already on disk. Returns the local path."""
    path = tile.local_path
    if is_current(tile):
        return path

    os.makedirs(os.path.dirname(path), exist_ok=True)
    partial = path + ".part"
    with _session.get(tile.url, stream=True, timeout=120) as r:
        if r.status_code in (401, 403) or "html" in r.headers.get("Content-Type", ""):
            raise LanceError(f"LANCE refused {tile.name} (HTTP {r.status_code}); check NASA_TOKEN in .env")
        r.raise_for_status()
        with open(partial, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)
    os.replace(partial, path)
    os.utime(path, (tile.mtime, tile.mtime))  # stamp the upstream version so is_current() can spot reprocessing
    log.info("Downloaded %s (%d bytes)", tile.name, tile.size)
    return path


def prune(keep: list[str]) -> None:
    """Delete downloaded tiles other than `keep`, and any day folders left empty."""
    keep = {os.path.abspath(p) for p in keep}
    if not os.path.isdir(RAW_DIR):
        return
    for day_dir in os.listdir(RAW_DIR):
        day_path = os.path.join(RAW_DIR, day_dir)
        if not os.path.isdir(day_path):
            continue
        for name in os.listdir(day_path):
            path = os.path.join(day_path, name)
            if os.path.abspath(path) not in keep:
                os.remove(path)
        if not os.listdir(day_path):
            os.rmdir(day_path)
