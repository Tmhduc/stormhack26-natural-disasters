"""LANCE near-real-time flood pipeline.

    find newest complete day -> download new/reprocessed tiles -> mosaic -> clip -> metrics + overlay PNG
    -> one row per day in the Postgres `images` table (only when DATABASE_URL is set)

Run once from the backend folder:
    uv run python -m app.core.pipeline [--date 2026-10-03] [--force]

The API runs it in the background every LANCE_POLL_MINUTES, and POST /api/flood/refresh runs it on demand.
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
from app.core import cache, downloader, history
from app.core.clipper import boundary_bounds, boundary_tiles
from app.core.mosaic import build_mosaic

log = logging.getLogger(__name__)
_lock = threading.Lock()  # one run at a time, whether from the poller or a refresh request


def read_state() -> dict:
    """What the last run produced: day, tiles and their versions, metrics, timestamps, last error."""
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


def _save_history(state: dict) -> None:
    """Copy the processed day into Postgres, when one is configured.

    A database problem is recorded in the state but never fails the run:
    the files the API serves are already up to date by this point.
    """
    if not history.enabled():
        return
    try:
        overlay, _, _ = cache.get_or_build()
        state["db_image_id"] = history.save_day(state, overlay, LOCAL_RASTER)
        state["db_saved"], state["db_error"] = True, None
    except Exception as e:
        log.exception("Could not save %s to the database", state.get("date"))
        state["db_saved"], state["db_error"] = False, f"{type(e).__name__}: {e}"


def run(day: date | None = None, force: bool = False) -> dict:
    """Bring the local flood overlay up to date with LANCE.

    `day` (UTC) pins a specific day instead of the newest complete one. Unless `force`,
    nothing is downloaded or rebuilt when LANCE has no new day and no reprocessed tiles.
    Returns the pipeline state plus `updated`, whether anything was rebuilt.
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
                if not state.get("db_saved"):  # e.g. the database was set up after this day was processed
                    _save_history(state)
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
                db_saved=False,
            )
            _save_history(state)
            _write_state(state)
            return {**state, "updated": True}
        except Exception as e:
            state["last_error"] = f"{type(e).__name__}: {e}"
            _write_state(state)
            raise


async def poll_forever(interval_minutes: float) -> None:
    """Run the pipeline now and then every `interval_minutes`, logging (not raising) failures."""
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
