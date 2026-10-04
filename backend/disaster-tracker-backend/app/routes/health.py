from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    # This is only a liveness check. It does not guarantee that the raster,
    # boundary, credentials, or cache are ready.
    return {"status": "ok"}
