# Stormhack26 Natural Disasters

## Backend setup

The backend is on the `feature/disaster-tracker-backend` branch.

### 1. Get the code

```bash
git clone git@github.com:Tmhduc/stormhack26-natural-disasters.git
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

```bash
mkdir -p data/vietnam_boundary
unzip -o vnm_admin_boundaries.shp.zip -d data/vietnam_boundary
```

The backend expects `data/vietnam_boundary/vnm_admin0.shp` and its accompanying `.dbf`, `.shx`, `.prj`, and `.cpg` files.

### 4. Add your NASA token locally

Create `data/.token` and paste in your own NASA Earthdata token:

```bash
printf '%s\n' 'YOUR_NASA_TOKEN' > data/.token
```

Never commit or share this file. It is ignored by Git.

### 5. Run the backend

```bash
uv run uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Interactive API documentation is at `http://localhost:8000/docs`.

### 6. Test the data pipeline

```bash
uv run python test_pipeline.py
```

The pipeline downloads the flood raster when needed and creates local files under `data/` and `cache/`. These directories are intentionally ignored because they contain credentials, downloaded/generated data, and runtime cache files.

## Team workflow

Pull the latest branch before starting work:

```bash
git switch feature/disaster-tracker-backend
git pull --ff-only
```

Do not commit `data/.token`, downloaded rasters, generated GeoJSON files, or cache files. Each teammate should create those locally using the setup steps above.