# Stormhack26 Natural Disasters

## Backend setup

The backend is on the `feature/disaster-tracker-backend` branch.

### 1. Get the code

These Git commands work on Linux, macOS, and Windows. HTTPS avoids requiring an SSH key.

```text
git clone https://github.com/Tmhduc/stormhack26-natural-disasters.git
cd stormhack26-natural-disasters
git switch feature/disaster-tracker-backend
cd backend/disaster-tracker-backend
```

### 2. Install dependencies

Python `3.14+` and `uv` are required.

```bash
uv sync
```

### 3. Extract the boundary data

The repository includes the boundary archive, but the extracted files are kept out of Git because they are large generated/local data files.

#### Linux or macOS

Run from `backend/disaster-tracker-backend` in a terminal with `unzip` installed:

```sh
mkdir -p data/vietnam_boundary
unzip -o vnm_admin_boundaries.shp.zip -d data/vietnam_boundary
```

#### Windows PowerShell

Run from `backend/disaster-tracker-backend`:

```powershell
New-Item -ItemType Directory -Force data/vietnam_boundary | Out-Null
Expand-Archive -Path vnm_admin_boundaries.shp.zip -DestinationPath data/vietnam_boundary -Force
```

If the archive was previously extracted, rerunning either command is safe.

The backend expects `data/vietnam_boundary/vnm_admin0.shp` and its accompanying `.dbf`, `.shx`, `.prj`, and `.cpg` files.

### 4. Add your NASA token locally

Create `.env` in `backend/disaster-tracker-backend` and add your own NASA Earthdata token:

```bash
printf 'NASA_TOKEN=%s\n' 'YOUR_NASA_TOKEN' >> .env
```

#### Windows PowerShell

```powershell
Set-Content -Path data/.token -Value 'YOUR_NASA_TOKEN' -NoNewline
```

You can also create `data/.token` manually in any editor and paste the token as a single line.

Never commit or share this file. It is ignored by Git.

### 5. Run the backend

```text
uv run uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Interactive API documentation is at `http://localhost:8000/docs`.

### 6. Test the data pipeline

```text
uv run python test_pipeline.py
```

The pipeline downloads the flood raster when needed and creates local files under `data/` and `cache/`. These directories are intentionally ignored because they contain credentials, downloaded/generated data, and runtime cache files.

## Flood data pipeline

Flood data comes from NASA LANCE's near-real-time MODIS Global Flood Product (`MCDWD_L3_F2_NRT`). The pipeline (`app/core/pipeline.py`):

1. Works out which 10° tiles the Vietnam boundary touches (`h28v06`, `h28v07`, `h28v08`, `h29v07`, `h29v08`).
2. Finds the newest UTC day on which LANCE has published all of them. The current day fills in over several hours, so it is used only once it is complete.
3. Downloads only new tiles, or tiles LANCE has reprocessed since the last run, into `data/raw/`.
4. Mosaics them into `data/vietnam_flood.tif`, clips to the boundary, and rebuilds the metrics and overlay PNG in `cache/`.

While the API is running, it runs the pipeline on startup and then every 60 minutes. Runs where nothing has changed upstream only list the archive. You can also run it by hand:

```bash
uv run python -m app.core.pipeline                    # newest complete day
uv run python -m app.core.pipeline --date 2026-10-01  # a specific UTC day (LANCE keeps about 8 days online)
```

API endpoints:

- `POST /api/flood/refresh`: run the pipeline now. Optional query parameters: `?day=YYYY-MM-DD` and `?force=true`.
- `GET /api/flood/status`: shows which day and tiles are loaded, when the pipeline last checked, and the last error.

Optional `.env` settings:

| Variable | Default | Meaning |
| --- | --- | --- |
| `LANCE_POLL_MINUTES` | `60` | Background polling interval. `0` turns polling off. |
| `LANCE_PRODUCT` | `MCDWD_L3_F2_NRT` | Composite to use: `F1` (1-day), `F1C` (1-day, cloud-shadow masked), `F2` (2-day) or `F3` (3-day). |
| `LANCE_TILES` | every tile the boundary touches | Comma-separated tile IDs, e.g. `h28v07`. |
| `LANCE_LOOKBACK_DAYS` | `7` | How many days back to search for a complete day. |

## Flood history database (optional)

If `DATABASE_URL` is set in `.env`, the backend keeps a day-by-day flood history in Postgres:

- On startup, it applies `db/schema.sql`. The script is safe to re-run and never deletes data.
- Each pipeline run saves the processed day to the `images` table: the overlay PNG, the stitched GeoTIFF, the map bounds and the flood metrics.
- There is one row per product per day. If LANCE reprocesses a day, that day's row is updated rather than duplicated.

If `DATABASE_URL` isn't set, everything still works from local files.

The connection URL Tiger Cloud shows doesn't include the password. Either add the password to `DATABASE_URL`, or download `pg_service.conf` from the Tiger console into `backend/disaster-tracker-backend/`; the backend reads the password from that file. Git ignores both files.

To check whether the last run was saved, look at `db_saved` and `db_error` in `GET /api/flood/status`. A database problem never stops the pipeline: the next run retries saving the day.

The dashboard's **Flood history** strip reads the saved days through:

- `GET /api/flood/history?limit=30`: saved days, newest first, each with its date, flood metrics, map bounds and `png_url`. Returns an empty list when no database is configured.
- `GET /api/flood/history/{id}/overlay.png`: the overlay image for one saved day.

LANCE keeps only about 8 days online. To save days the pipeline missed, run it for each one, then once more without `--date` to go back to the newest day:

```bash
uv run python -m app.core.pipeline --date 2026-10-01
uv run python -m app.core.pipeline
```

## Team workflow

Pull the latest branch before starting work:

```bash
git switch feature/disaster-tracker-backend
git pull --ff-only
```

Do not commit `data/.token`, downloaded rasters, generated GeoJSON files, or cache files. Each teammate should create those locally using the setup steps above.