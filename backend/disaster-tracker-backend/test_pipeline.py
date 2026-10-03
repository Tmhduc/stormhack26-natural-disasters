from app.core import cache

overlay, metrics, bounds = cache.get_or_build()
print("Metrics:", metrics)
print("Bounds:", bounds)
print("Overlay:", overlay)
