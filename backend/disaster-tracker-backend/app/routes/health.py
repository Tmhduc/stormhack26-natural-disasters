from fastapi import APIRouter

from app.config import GOOGLE_MAPS_API_KEY, TELEGRAM_BOT_TOKEN, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
from app.core import history, pipeline

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    """Return safe deployment diagnostics without exposing credentials."""
    database = history.database_status()
    state = pipeline.read_state()
    integrations = {
        "google_geocoding": bool(GOOGLE_MAPS_API_KEY),
        "telegram": bool(TELEGRAM_BOT_TOKEN),  # recipients subscribe through the bot
        "twilio": bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN),
    }
    return {
        "status": "ok" if database["connected"] or not database["configured"] else "degraded",
        "database": database,
        "pipeline": {
            "loaded": bool(state.get("date")),
            "date": state.get("date"),
            "last_checked": state.get("checked_at"),
            "last_processed": state.get("processed_at"),
        },
        "integrations": integrations,
    }
