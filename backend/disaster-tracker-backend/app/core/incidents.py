"""Responder-saved flood observations stored in Tiger Data."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.core import history
from app.core.history import _engine
from db.db import FloodIncidentRow


def save(payload: dict) -> dict:
    """Create one saved incident and return its normalized API representation."""
    history.ensure_schema()
    incident_id = str(uuid4())
    row = dict(
        id=incident_id,
        observed_date=payload.get("observed_date"),
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
        data={"nearby_class_counts": payload.get("nearby_class_counts", {})},
    )
    stmt = insert(FloodIncidentRow).values(**row).returning(FloodIncidentRow)
    with _engine().begin() as conn:
        saved = conn.execute(stmt).scalar_one()
    return _as_dict(saved)


def list_incidents(limit: int = 50) -> list[dict]:
    """Return recent saved incidents, newest first."""
    history.ensure_schema()
    stmt = select(FloodIncidentRow).order_by(FloodIncidentRow.created_at.desc()).limit(limit)
    with _engine().connect() as conn:
        return [_as_dict(row) for row in conn.execute(stmt).scalars()]


def remove(incident_id: str) -> bool:
    """Delete one saved incident and report whether it existed."""
    history.ensure_schema()
    stmt = delete(FloodIncidentRow).where(FloodIncidentRow.id == incident_id)
    with _engine().begin() as conn:
        return conn.execute(stmt).rowcount > 0


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
        "id": row.id,
        "observed_date": row.observed_date.isoformat() if row.observed_date else None,
        "created_at": row.created_at.isoformat() if row.created_at else datetime.now(timezone.utc).isoformat(),
        "lat": row.lat,
        "lon": row.lon,
        "address": row.address,
        "admin1_name": row.admin1_name,
        "admin1_type": row.admin1_type,
        "class_value": row.class_value,
        "class_name": row.class_name,
        "flooded": row.flooded,
        "nearby_radius_km": row.nearby_radius_km,
        "nearby_pixels": row.nearby_pixels,
        "nearby_flood_pixels": row.nearby_flood_pixels,
        "nearby_class_counts": (row.data or {}).get("nearby_class_counts", {}),
        "severity": row.severity,
        "status": row.status,
    }
