import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import CACHE_DIR, LANCE_POLL_MINUTES
from app.core import history, pipeline
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
    # Keep the flood overlay in step with LANCE: fetch on startup, then poll for new/reprocessed tiles.
    poller = asyncio.create_task(pipeline.poll_forever(LANCE_POLL_MINUTES)) if LANCE_POLL_MINUTES > 0 else None
    yield
    if poller:
        poller.cancel()


app = FastAPI(title="Flood monitor API", version="1.0.0", lifespan=lifespan)

# Frontend chạy ở dev server riêng nên browser cần CORS permission để gọi API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files chỉ expose artifact sinh ra như overlay PNG. Credential và dữ
# liệu nguồn vẫn nằm ngoài thư mục được mount này.
os.makedirs(CACHE_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=CACHE_DIR), name="static")

# Đăng ký route ở một nơi để entry point ngắn gọn và mỗi feature tự quản lý
# endpoint của mình.
app.include_router(health.router)
app.include_router(flood.router)
app.include_router(history_routes.router)
