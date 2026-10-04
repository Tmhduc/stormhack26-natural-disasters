"""SQLAlchemy ORM models and engine setup for Postgres (Tiger Cloud or any Postgres 14+).

The tables are created by db/schema.sql, which also holds what the ORM can't express on its own
(the new-image NOTIFY trigger and the optional PostGIS columns). These models map onto it;
tests/test_db.py checks the two stay in step.
"""

import configparser
import os
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Double, Engine, Integer, LargeBinary, Text, create_engine, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, column_property, mapped_column

# Tiger Cloud's console URL leaves the password out; the pg_service.conf it offers for
# download has it. Point libpq at that file so every connection picks the password up.
# (A DATABASE_URL that includes the password works too: libpq only fills in what's missing.)
PG_SERVICE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pg_service.conf")
if os.path.exists(PG_SERVICE_FILE):
    _services = configparser.ConfigParser()
    _services.read(PG_SERVICE_FILE)
    if _services.sections():
        os.environ.setdefault("PGSERVICEFILE", PG_SERVICE_FILE)
        os.environ.setdefault("PGSERVICE", _services.sections()[0])


class Base(DeclarativeBase):
    pass


class EventRow(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    type: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(Text)
    lon: Mapped[float] = mapped_column(Double)
    lat: Mapped[float] = mapped_column(Double)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data: Mapped[dict] = mapped_column(JSONB)  # the full normalized Event


class BulletinRow(Base):
    __tablename__ = "bulletins"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    event_id: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    head: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImageRow(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    product: Mapped[str] = mapped_column(Text, server_default="")
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    west: Mapped[float | None] = mapped_column(Double)
    south: Mapped[float | None] = mapped_column(Double)
    east: Mapped[float | None] = mapped_column(Double)
    north: Mapped[float | None] = mapped_column(Double)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    media_type: Mapped[str] = mapped_column(Text, server_default="image/png")
    meta: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    original_media_type: Mapped[str | None] = mapped_column(Text)
    crs: Mapped[str | None] = mapped_column(Text)
    bands: Mapped[int | None] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(Text)  # unique: one row per upstream file
    # The bytes are deferred so listing images never pulls them; load with undefer() when serving one.
    data: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)  # what browsers get (PNG/JPEG/WebP)
    original: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)  # untouched source, e.g. the GeoTIFF

    nbytes: Mapped[int | None] = column_property(func.octet_length(data))
    has_original: Mapped[bool] = column_property(original.isnot(None))


def libpq_url(url: str) -> str:
    """The plain postgresql:// form psycopg wants (used for LISTEN, which SQLAlchemy doesn't wrap)."""
    for prefix in ("postgresql+psycopg://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    return url


def _sa_url(url: str) -> str:
    # Tiger Cloud hands out postgres:// URLs; SQLAlchemy needs the dialect+driver spelled out.
    return "postgresql+psycopg://" + libpq_url(url).removeprefix("postgresql://")


_ENGINE_OPTIONS = dict(
    pool_size=5,
    max_overflow=0,
    pool_pre_ping=True,  # replace connections the server closed while idle
    # Keeps working behind PgBouncer-style poolers (Tiger Cloud connection pooler).
    connect_args={"prepare_threshold": None},
)


def make_engine(url: str) -> AsyncEngine:
    return create_async_engine(_sa_url(url), **_ENGINE_OPTIONS)


def make_sync_engine(url: str) -> Engine:
    """For code that runs outside the event loop, like the flood pipeline's worker thread."""
    return create_engine(_sa_url(url), **_ENGINE_OPTIONS)
