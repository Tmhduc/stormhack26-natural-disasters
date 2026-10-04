"""Responder-saved flood observations stored in Tiger Data."""

from datetime import date, datetime, timezone
import math
import logging
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert

from app.core import history
from app.core.history import _engine
from db.db import FloodIncidentRow

log = logging.getLogger(__name__)


def save(payload: dict) -> dict:
    """Create one saved incident and return its normalized API representation."""
    history.ensure_schema()
    incident_id = str(uuid4())
    row = dict(
        id=incident_id,
        observed_date=(date.fromisoformat(payload["observed_date"]) if payload.get("observed_date") else None),
        lat=payload["lat"],
        lon=payload["lon"],
        address=payload.get("address"),
        admin1_name=payload.get("admin1_name"),
        admin1_type=payload.get("admin1_type"),
        class_value=payload.get("class_value"),
        class_name=payload.get("class_name"),
        flooded=payload.get("flooded"),
        nearby_radius_km=payload.get("nearby_radius_km"),
        nearby_pixels=payload.get("nearby_pixels"),
        nearby_flood_pixels=payload.get("nearby_flood_pixels"),
        severity=payload["severity"],
        status="open",
        notes=payload.get("notes"),
        data={"nearby_class_counts": payload.get("nearby_class_counts", {})},
    )
    with _engine().begin() as conn:
        existing = _nearest(conn, row["lat"], row["lon"])
        if existing:
            incident_id = existing["id"]
            row.pop("id")
            row.pop("status")
            row.pop("notes")
            row["updated_at"] = datetime.now(timezone.utc)
            conn.execute(update(FloodIncidentRow.__table__).where(FloodIncidentRow.id == incident_id).values(**row))
        else:
            conn.execute(insert(FloodIncidentRow.__table__).values(**row))
        saved = conn.execute(
            select(FloodIncidentRow.__table__).where(FloodIncidentRow.id == incident_id)
        ).mappings().one()
    return _as_dict(saved)


def list_incidents(limit: int = 50) -> list[dict]:
    """Return recent saved incidents, newest first."""
    history.ensure_schema()
    stmt = select(FloodIncidentRow.__table__).order_by(FloodIncidentRow.created_at.desc()).limit(limit)
    with _engine().connect() as conn:
        return [_as_dict(row) for row in conn.execute(stmt).mappings()]


def remove(incident_id: str) -> bool:
    """Delete one saved incident and report whether it existed."""
    history.ensure_schema()
    stmt = delete(FloodIncidentRow).where(FloodIncidentRow.id == incident_id)
    with _engine().begin() as conn:
        return conn.execute(stmt).rowcount > 0


def update_incident(incident_id: str, changes: dict) -> dict | None:
    """Update a responder's workflow status or notes."""
    history.ensure_schema()
    values = {key: value for key, value in changes.items() if value is not None}
    if not values:
        return _find(incident_id)
    values["updated_at"] = datetime.now(timezone.utc)
    with _engine().begin() as conn:
        result = conn.execute(update(FloodIncidentRow.__table__).where(FloodIncidentRow.id == incident_id).values(**values))
        if not result.rowcount:
            return None
        return _find(incident_id, conn)


def hotspots(limit: int = 10) -> list[dict]:
    """Group saved incidents by province/city for a simple responder hotspot list."""
    incidents = list_incidents(500)
    grouped = {}
    for item in incidents:
        name = item["admin1_name"] or "Unknown area"
        group = grouped.setdefault(name, {"name": name, "incidents": 0, "high": 0, "latest_date": None})
        group["incidents"] += 1
        group["high"] += item["severity"] == "High"
        group["latest_date"] = max(group["latest_date"] or "", item["observed_date"] or "")
    return sorted(grouped.values(), key=lambda item: (item["high"], item["incidents"]), reverse=True)[:limit]


def _as_dict(row: FloodIncidentRow) -> dict:
    return {
        "id": row["id"],
        "observed_date": row["observed_date"].isoformat() if row["observed_date"] else None,
        "created_at": row["created_at"].isoformat() if row["created_at"] else datetime.now(timezone.utc).isoformat(),
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else row["created_at"].isoformat(),
        "lat": row["lat"],
        "lon": row["lon"],
        "address": row["address"],
        "admin1_name": row["admin1_name"],
        "admin1_type": row["admin1_type"],
        "class_value": row["class_value"],
        "class_name": row["class_name"],
        "flooded": row["flooded"],
        "nearby_radius_km": row["nearby_radius_km"],
        "nearby_pixels": row["nearby_pixels"],
        "nearby_flood_pixels": row["nearby_flood_pixels"],
        "nearby_class_counts": (row["data"] or {}).get("nearby_class_counts", {}),
        "severity": row["severity"],
        "status": row["status"],
        "notes": row["notes"],
    }


def _find(incident_id: str, conn=None) -> dict | None:
    """Read one incident using an existing connection when available."""
    if conn is not None:
        row = conn.execute(select(FloodIncidentRow.__table__).where(FloodIncidentRow.id == incident_id)).mappings().one_or_none()
        return _as_dict(row) if row else None
    with _engine().connect() as connection:
        row = connection.execute(select(FloodIncidentRow.__table__).where(FloodIncidentRow.id == incident_id)).mappings().one_or_none()
        return _as_dict(row) if row else None


def _nearest(conn, lat: float, lon: float, radius_m: float = 100) -> dict | None:
    """Find a saved point within `radius_m` using a small geographic bounding box."""
    lat_delta = radius_m / 111_320
    lon_delta = radius_m / (111_320 * max(math.cos(math.radians(lat)), 0.2))
    rows = conn.execute(
        select(FloodIncidentRow.__table__).where(
            FloodIncidentRow.lat.between(lat - lat_delta, lat + lat_delta),
            FloodIncidentRow.lon.between(lon - lon_delta, lon + lon_delta),
        )
    ).mappings()
    closest = None
    closest_distance = radius_m
    for row in rows:
        distance = _distance_m(lat, lon, row["lat"], row["lon"])
        if distance <= closest_distance:
            closest, closest_distance = row, distance
    return closest


def _distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the approximate great-circle distance between two coordinates."""
    radius = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    value = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(value))
