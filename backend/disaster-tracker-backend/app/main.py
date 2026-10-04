import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import CACHE_DIR, LANCE_POLL_MINUTES
from app.core import history, pipeline, telegram
from app.routes import health, flood
from app.routes import history as history_routes

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if history.enabled():
        try:
            await asyncio.to_thread(history.ensure_schema)
        except Exception:
            # The app still serves files; the pipeline retries the schema before its next save.
            log.exception("Could not apply db/schema.sql")
    try:
        # Boundary files, and the newest saved day when the disk is empty (fresh deploy or wake-up).
        await asyncio.to_thread(pipeline.prepare)
    except Exception:
        log.exception("Could not prepare boundary files")
    # Keep the flood overlay in step with LANCE: fetch on startup, then poll for new/reprocessed tiles.
    # Keep the overlay current with LANCE: run at startup, then poll for new or
    # reprocessed tiles.
    poller = asyncio.create_task(pipeline.poll_forever(LANCE_POLL_MINUTES)) if LANCE_POLL_MINUTES > 0 else None
    # Let people subscribe to Telegram alerts by messaging the bot /start: by webhook when
    # deployed with a public URL, by long polling locally.
    listener = await telegram.start() if telegram.enabled() else None
    yield
    for task in (poller, listener):
        if task:
            task.cancel()


app = FastAPI(title="Flood monitor API", version="1.0.0", lifespan=lifespan)

# The frontend runs on a separate dev server, so browsers need CORS permission.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://distrack.tech",
        "https://www.distrack.tech",
        "https://distrack-frontend.onrender.com",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files expose generated artifacts such as the overlay PNG. Credentials
# and source data remain outside the mounted directory.
os.makedirs(CACHE_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=CACHE_DIR), name="static")

# Register routes in one place so the entry point stays small and each feature
# owns its endpoints.
app.include_router(health.router)
app.include_router(flood.router)
app.include_router(history_routes.router)
