import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import CACHE_DIR
from app.routes import health, flood

app = FastAPI(title="Vietnam Flood Monitor API", version="1.0.0")

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
