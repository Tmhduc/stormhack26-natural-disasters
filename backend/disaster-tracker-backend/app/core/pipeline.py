"""Pipeline ngập gần thời gian thực lấy dữ liệu từ LANCE.

    tìm ngày đủ tile -> tải tile mới -> mosaic -> clip -> metrics + overlay PNG

Chạy một lần từ thư mục backend:
    uv run python -m app.core.pipeline [--date 2026-10-03] [--force]

API chạy pipeline nền theo LANCE_POLL_MINUTES; POST /api/flood/refresh chạy thủ công.
"""

import argparse
import asyncio
import json
import logging
import os
import threading
from datetime import date, datetime, timezone

from app.config import (
    LANCE_LOOKBACK_DAYS, LANCE_PRODUCT, LANCE_TILES, LOCAL_RASTER, STATE_FILE
)
from app.core import cache, downloader
from app.core.clipper import boundary_bounds, boundary_tiles
from app.core.mosaic import build_mosaic

log = logging.getLogger(__name__)
_lock = threading.Lock()  # chỉ cho phép một poller hoặc request refresh chạy mỗi lúc


def read_state() -> dict:
    """Đọc kết quả lần chạy cuối: ngày, tile, version, metrics, thời gian và lỗi."""
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _write_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    partial = STATE_FILE + ".part"
    with open(partial, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(partial, STATE_FILE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run(day: date | None = None, force: bool = False) -> dict:
    """Đồng bộ overlay ngập local với dữ liệu LANCE.

    `day` (UTC) khóa vào một ngày cụ thể thay vì ngày đủ tile mới nhất. Nếu không
    có `force`, pipeline bỏ qua khi không có ngày mới hoặc tile được reprocess.
    Kết quả gồm state và `updated` cho biết có rebuild hay không.
    """
    with _lock:
        state = read_state()
        state["checked_at"] = _now()
        try:
            tiles = LANCE_TILES or boundary_tiles()
            if day is None:
                day, remote = downloader.find_latest(tiles, LANCE_LOOKBACK_DAYS)
            else:
                remote = downloader.tiles_for_day(day, tiles)
            versions = {t.tile: {"mtime": t.mtime, "size": t.size} for t in remote}

            unchanged = (
                state.get("product") == LANCE_PRODUCT
                and state.get("date") == day.isoformat()
                and state.get("versions") == versions
                and os.path.exists(LOCAL_RASTER)
                and cache.is_built()
            )
            if unchanged and not force:
                state["last_error"] = None
                _write_state(state)
                return {**state, "updated": False}

            log.info("Updating flood overlay to %s %s (%s)", LANCE_PRODUCT, day, ", ".join(tiles))
            paths = [downloader.download_tile(t) for t in remote]
            build_mosaic(paths, LOCAL_RASTER, boundary_bounds())
            _, metrics, bounds = cache.rebuild()
            downloader.prune(keep=paths)

            state.update(
                product=LANCE_PRODUCT,
                date=day.isoformat(),
                tiles=tiles,
                files=[t.name for t in remote],
                versions=versions,
                metrics=metrics,
                bounds=bounds,
                processed_at=_now(),
                last_error=None,
            )
            _write_state(state)
            return {**state, "updated": True}
        except Exception as e:
            state["last_error"] = f"{type(e).__name__}: {e}"
            _write_state(state)
            raise


async def poll_forever(interval_minutes: float) -> None:
    """Chạy ngay rồi lặp lại mỗi `interval_minutes`; lỗi được log và thử lại."""
    while True:
        try:
            result = await asyncio.to_thread(run)
            if result["updated"]:
                log.info("Flood overlay updated to %s: %s", result["date"], result["metrics"])
        except Exception:
            log.exception("LANCE pipeline run failed; retrying in %s min", interval_minutes)
        await asyncio.sleep(interval_minutes * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pull the newest LANCE NRT flood tiles and rebuild the overlay.")
    parser.add_argument("--date", type=date.fromisoformat, help="UTC day to fetch, YYYY-MM-DD (default: newest complete day)")
    parser.add_argument("--force", action="store_true", help="rebuild the mosaic and overlay even if nothing changed")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print(json.dumps(run(day=args.date, force=args.force), indent=2))


if __name__ == "__main__":
    main()
