import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import CACHE_DIR, LANCE_POLL_MINUTES
from app.core import pipeline
from app.routes import health, flood

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Keep the flood overlay in step with LANCE: fetch on startup, then poll for new/reprocessed tiles.
    poller = asyncio.create_task(pipeline.poll_forever(LANCE_POLL_MINUTES)) if LANCE_POLL_MINUTES > 0 else None
    yield
    if poller:
        poller.cancel()


app = FastAPI(title="Flood monitor API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(CACHE_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=CACHE_DIR), name="static")

app.include_router(health.router)
app.include_router(flood.router)
