# Backend flow

This guide explains the flood dashboard backend in simple terms. It is meant for teammates who need to run, debug, or extend the project.

## What the backend does

1. Finds the newest complete NASA LANCE flood tiles for Vietnam.
2. Downloads and combines them into one GeoTIFF.
3. Clips the raster to Vietnam and creates an overlay plus metrics.
4. Inspects clicked coordinates and returns flood, area, and address information.
5. Builds responder briefs and sends them to Telegram or SMS when configured.

The frontend talks to FastAPI. Credentials stay in the backend `.env` file.

## Important folders

```text
app/main.py                 FastAPI app and startup lifecycle
app/config.py               Environment variables and local paths
app/routes/                 HTTP endpoints
app/core/pipeline.py        Refresh workflow and saved state
app/core/downloader.py      LANCE discovery and downloads
app/core/mosaic.py          Tile validation and GeoTIFF merging
app/core/clipper.py         Boundary clipping and point inspection
app/core/cache.py           Metrics, bounds, and overlay generation
app/core/geocoder.py        Optional Google address lookup
app/core/alerts.py          Optional Telegram and Twilio alerts
data/                       Local inputs, raster files, and pipeline state
cache/                      Generated overlays and metric files
db/                         Optional Postgres models and schema
```

Do not commit generated files, downloaded rasters, or credentials.

## Environment setup

Create `backend/disaster-tracker-backend/.env`:

```env
NASA_TOKEN=...
GOOGLE_MAPS_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=...
```

Only configure the services you use.

Pipeline settings:

| Variable | Default | Meaning |
| --- | --- | --- |
| `LANCE_PRODUCT` | `MCDWD_L3_F2_NRT` | NASA flood product |
| `LANCE_TILES` | automatic | Tile IDs; empty means every tile touching Vietnam |
| `LANCE_LOOKBACK_DAYS` | `7` | Days to search backward |
| `LANCE_DATA_LAG_DAYS` | `1` | Prefer a complete previous day |
| `LANCE_POLL_MINUTES` | `60` | Background refresh interval; `0` disables it |

## Refresh pipeline

The pipeline runs at startup when polling is enabled and can be triggered with `POST /api/flood/refresh`.

1. **Choose tiles.** If `LANCE_TILES` is empty, `boundary_tiles()` finds every 10° MCDWD tile that intersects Vietnam.
2. **Choose a complete date.** `find_latest()` checks recent UTC dates until every required tile is online.
3. **Download changed tiles.** Local files are reused when their size and upstream modification time still match.
4. **Validate downloads.** Files are written as `.part`, checked for the expected byte count, and opened with Rasterio before replacing the old file.
5. **Build the mosaic.** Compatible tiles are merged without resampling into `data/vietnam_flood.tif`.
6. **Build the cache.** The mosaic is clipped to Vietnam and converted into metrics, bounds, and a transparent flood PNG.

The pipeline writes its state to `data/pipeline_state.json`. A lock prevents a background poll and a manual refresh from running at the same time.

## Flood classes

The source raster has one `uint8` band:

| Value | Meaning |
| --- | --- |
| `0` | No water |
| `1` | Usual/reference water |
| `2` | Recurring flood area |
| `3` | Unusual flood area |
| `255` | Insufficient data |

The current binary mask treats classes `2` and `3` as flooded. The frontend converts technical names into phrases such as “Unusual flooding detected”.

For geographic rasters, area uses geodesic pixel calculations. The configured `0.0625 km²` value is only a fallback.

## Caching

- The WGS84 Vietnam boundary is cached once per process.
- The clipped flood mask is cached using the raster file size and modification time.
- Transformed boundary geometries use a four-entry LRU cache keyed by CRS.
- Disk cache files are reused while `manifest.json` still matches the raster.

Point inspection reads one GeoTIFF pixel. Neighborhood inspection reads only a small window, so neither operation needs the full mask.

## Address lookup

Local admin1 boundary data identifies the province or city for every inspected point.

If `GOOGLE_MAPS_API_KEY` is configured:

- Reverse lookup adds a formatted Vietnamese address to inspection results.
- `GET /api/flood/geocode?q=...` searches addresses.
- Repeated lookups are cached.
- The key stays on the backend.

A rural result may be a Plus Code rather than a street address.

## Responder workflow

After inspecting a point, the frontend can create an incident brief containing:

- Address and coordinates
- Plain-language flood finding
- Nearby affected-area estimate
- Observation date
- Google Maps link

Saved points appear in the responder board. Triage is only a prioritization aid:

- **High:** unusual flood class or at least 30% of nearby cells show flood signals.
- **Moderate:** at least 10% of nearby cells show flood signals.
- **Watch:** no confirmed local flood signal or insufficient evidence.

Always verify conditions on the ground before dispatching help.

## Alerts

### Telegram

`POST /api/flood/alerts/telegram` sends a manual incident brief to the configured chat. The bot must be started by the recipient or added to the target group.

Telegram is the recommended hackathon channel because it supports long briefs and map links without SMS billing.

### Twilio SMS

`POST /api/flood/alerts/sms` sends a manual brief through Twilio. Phone numbers must use E.164 format, such as `+14165551234`.

Trial accounts restrict recipients and custom message content. A paid or upgraded account is needed for custom incident briefs.

The app never sends an alert automatically just because a pixel is classified as flooded.

## HTTP endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Check that FastAPI is responding |
| GET | `/api/flood/status` | Read pipeline state and errors |
| POST | `/api/flood/refresh` | Check LANCE and rebuild when needed |
| GET | `/api/flood/metrics` | Read current metrics |
| GET | `/api/flood/overlay` | Get overlay URL and geographic bounds |
| GET | `/api/flood/boundary` | Get the simplified browser boundary |
| GET | `/api/flood/inspect` | Inspect a point and its neighborhood |
| GET | `/api/flood/geocode` | Search addresses through Google |
| POST | `/api/flood/alerts/telegram` | Send a Telegram brief |
| POST | `/api/flood/alerts/sms` | Send an SMS brief |
| GET | `/api/flood/history` | Read saved history when Postgres is enabled |

## Run locally

Backend:

```bash
cd backend/disaster-tracker-backend
uv sync
uv run uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs`

Backend regression tests:

```bash
uv run python -m unittest -v test_backend.py
```

Frontend:

```bash
cd frontend/disaster-tracker
npm install
npm run dev
npm run build
```

The pipeline smoke test contacts NASA and writes runtime data. Do not use it as a default CI unit test without mocking network and filesystem inputs.

## Limitations

- Satellite classifications are observations, not ground truth.
- The map does not include road conditions, shelters, population, or live traffic.
- Google addresses can be approximate.
- Alerts require third-party credentials and manual confirmation.
- Database history is optional and separate from the local file pipeline.
