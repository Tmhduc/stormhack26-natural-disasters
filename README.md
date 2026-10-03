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

Create `data/.token` and paste in your own NASA Earthdata token. Use the command for your shell:

#### Linux or macOS

```sh
printf '%s\n' 'YOUR_NASA_TOKEN' > data/.token
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

## Team workflow

Pull the latest branch before starting work:

```bash
git switch feature/disaster-tracker-backend
git pull --ff-only
```

Do not commit `data/.token`, downloaded rasters, generated GeoJSON files, or cache files. Each teammate should create those locally using the setup steps above.