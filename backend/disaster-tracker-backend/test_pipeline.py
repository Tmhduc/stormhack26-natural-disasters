from app.core import cache

# Đây là smoke check end-to-end nhỏ: chạy clipping, tính metrics, render và
# ghi cache bằng dữ liệu đã chuẩn bị ở local.
overlay, metrics, bounds = cache.get_or_build()
print("Metrics:", metrics)
print("Bounds:", bounds)
print("Overlay:", overlay)
