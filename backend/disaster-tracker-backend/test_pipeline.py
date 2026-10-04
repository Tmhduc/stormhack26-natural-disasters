from app.core import pipeline

result = pipeline.run()
print("Updated:", result["updated"])
print("Date:", result["date"], "tiles:", ", ".join(result["tiles"]))
print("Metrics:", result["metrics"])
print("Bounds:", result["bounds"])
