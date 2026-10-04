"""Flood history in Postgres: one row in `images` for each day the pipeline processes.

Optional: with DATABASE_URL unset nothing here runs, and the app works from files alone.
"""

import os
import threading
import logging
from datetime import date, datetime, timezone
from functools import lru_cache

import psycopg
import rasterio
from PIL import Image
from sqlalchemy import Engine, select, text
from sqlalchemy.dialects.postgresql import insert

from app.config import BASE_DIR, DATABASE_URL, LANCE_PRODUCT
from db.db import ImageRow, libpq_url, make_sync_engine

SCHEMA_FILE = os.path.join(BASE_DIR, "db", "schema.sql")
SOURCE = "NASA LANCE"  # images.source for rows the pipeline writes
_schema_lock = threading.Lock()
_schema_ready = False
log = logging.getLogger(__name__)


def enabled() -> bool:
    return bool(DATABASE_URL)


def database_status() -> dict:
    """Return a safe connection check without exposing the database URL."""
    if not enabled():
        return {"configured": False, "connected": False}
    try:
        with _engine().connect() as conn:
            conn.execute(text("select 1"))
        return {"configured": True, "connected": True}
    except Exception as error:
        log.exception("Tiger Data health check failed")
        return {"configured": True, "connected": False, "error": f"{type(error).__name__}: {error}"}


def ensure_schema() -> None:
    """Apply db/schema.sql once per process. The script is idempotent and never drops data."""
    global _schema_ready
    with _schema_lock:
        if _schema_ready:
            return
        with open(SCHEMA_FILE, encoding="utf-8") as f:
            schema = f.read()
        # Straight through psycopg: with no parameters it runs the multi-statement script in one go.
        with psycopg.connect(
            libpq_url(DATABASE_URL), autocommit=True, prepare_threshold=None, connect_timeout=15
        ) as conn:
            conn.execute(schema)
        _schema_ready = True


@lru_cache(maxsize=1)
def _engine() -> Engine:
    return make_sync_engine(DATABASE_URL)


def save_day(state: dict, overlay_png: str, raster: str) -> int:
    """Store the day the pipeline just processed (see pipeline.read_state()). Returns the row id.

    One row per product and day: when LANCE reprocesses that day's tiles, the row is updated in place.
    """
    ensure_schema()
    day = date.fromisoformat(state["date"])
    with open(overlay_png, "rb") as f:
        png = f.read()
    with open(raster, "rb") as f:
        tif = f.read()
    with Image.open(overlay_png) as image:
        width, height = image.size
    with rasterio.open(raster) as src:
        crs, bands = src.crs.to_string(), src.count
    west, south, east, north = state["bounds"]

    row = dict(
        source=SOURCE,
        product=state["product"],
        captured_at=datetime(day.year, day.month, day.day, tzinfo=timezone.utc),
        west=west,
        south=south,
        east=east,
        north=north,
        width=width,                 
        height=height,
        media_type="image/png",
        data=png,
        original=tif,
        original_media_type="image/tiff",
        crs=crs,
        bands=bands,
        meta={k: state[k] for k in ("metrics", "tiles", "files", "versions", "processed_at")},
        source_file=f"{state['product']}.A{day:%Y%j}.{os.path.basename(raster)}",
    )
    stmt = insert(ImageRow).values(**row)
    stmt = stmt.on_conflict_do_update(
        index_elements=[ImageRow.source_file],
        set_={k: stmt.excluded[k] for k in row if k != "source_file"},
    ).returning(ImageRow.id)
    with _engine().begin() as conn:
        return conn.execute(stmt).scalar_one()


def list_days(limit: int) -> list[dict]:
    """Saved days of the current LANCE product, newest first, without the image bytes."""
    ensure_schema()
    stmt = (
        select(ImageRow.id, ImageRow.captured_at, ImageRow.west, ImageRow.south,
               ImageRow.east, ImageRow.north, ImageRow.meta)
        .where(ImageRow.source == SOURCE, ImageRow.product == LANCE_PRODUCT)
        .order_by(ImageRow.captured_at.desc())
        .limit(limit)
    )
    with _engine().connect() as conn:
        rows = conn.execute(stmt).all()
    return [
        {
            "id": r.id,
            "date": r.captured_at.date().isoformat(),
            "bounds": [r.west, r.south, r.east, r.north],
            "flood_pixels": r.meta["metrics"]["flood_pixels"],
            "flooded_km2": r.meta["metrics"]["flooded_km2"],
            "tiles": r.meta.get("tiles", []),
            "processed_at": r.meta.get("processed_at"),
        }
        for r in rows
    ]


def trend(limit: int = 30) -> list[dict]:
    """Return daily flood totals in oldest-to-newest order for charting."""
    days = list_days(limit)
    points = []
    previous_area = None
    for day in reversed(days):
        area = float(day["flooded_km2"])
        change = None if previous_area in (None, 0) else round((area - previous_area) / previous_area * 100, 1)
        points.append({
            "date": day["date"],
            "flood_pixels": day["flood_pixels"],
            "flooded_km2": area,
            "change_percent": change,
        })
        previous_area = area
    return points


def overlay_png(image_id: int) -> bytes | None:
    """The overlay PNG saved for one day, or None if there's no such row."""
    stmt = select(ImageRow.data).where(ImageRow.id == image_id, ImageRow.source == SOURCE)
    with _engine().connect() as conn:
        return conn.execute(stmt).scalar_one_or_none()


def original_raster(image_id: int) -> bytes | None:
    """Return the source GeoTIFF for one saved LANCE day, if available."""
    ensure_schema()
    stmt = select(ImageRow.original).where(
        ImageRow.id == image_id,
        ImageRow.source == SOURCE,
        ImageRow.product == LANCE_PRODUCT,
    )
    with _engine().connect() as conn:
        return conn.execute(stmt).scalar_one_or_none()


def latest_day() -> dict | None:
    """The newest saved day of the current product with its GeoTIFF and overlay, or None if there isn't one."""
    ensure_schema()
    stmt = (
        select(ImageRow.id, ImageRow.product, ImageRow.captured_at, ImageRow.west, ImageRow.south,
               ImageRow.east, ImageRow.north, ImageRow.meta, ImageRow.data, ImageRow.original)
        .where(ImageRow.source == SOURCE, ImageRow.product == LANCE_PRODUCT,
               ImageRow.data.isnot(None), ImageRow.original.isnot(None))
        .order_by(ImageRow.captured_at.desc())
        .limit(1)
    )
    with _engine().connect() as conn:
        row = conn.execute(stmt).first()
    if row is None:
        return None
    return {
        "id": row.id,
        "product": row.product,
        "date": row.captured_at.date().isoformat(),
        "bounds": [row.west, row.south, row.east, row.north],
        "meta": row.meta,
        "overlay_png": row.data,
        "raster": row.original,
    }
