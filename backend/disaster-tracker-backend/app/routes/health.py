from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    # Đây chỉ là liveness check: xác nhận FastAPI đang response, không đảm bảo
    # raster, boundary, token hoặc cache đã sẵn sàng.
    return {"status": "ok"}
