import { useCallback, useEffect, useRef, useState } from "react";
import { geographic, request } from "./api";
import type { Boundary, Inspection, Metrics, Overlay } from "./api";
import "./App.css";

const places = [
  { name: "Hanoi", lat: 21.0285, lon: 105.8542 },
  { name: "Da Nang", lat: 16.0544, lon: 108.2022 },
  { name: "Ho Chi Minh City", lat: 10.8231, lon: 106.6297 },
];
const x = (lon: number) => (lon - 101) * 54;
const y = (lat: number) => (25 - lat) * 38;
const number = (value: number | undefined) =>
  value === undefined
    ? "—"
    : value.toLocaleString("en-US", { maximumFractionDigits: 2 });
function App() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [overlay, setOverlay] = useState<Overlay | null>(null);
  const [boundary, setBoundary] = useState<Boundary | null>(null);
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [imageError, setImageError] = useState(false);
  const [showFlood, setShowFlood] = useState(true);
  const [opacity, setOpacity] = useState(75);
  const [zoom, setZoom] = useState(1);
  const [lat, setLat] = useState("16.0544");
  const [lon, setLon] = useState("108.2022");
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [inspectError, setInspectError] = useState("");
  const [inspecting, setInspecting] = useState(false);
  const [updated, setUpdated] = useState(0);
  const svg = useRef<SVGSVGElement>(null);
  const inspectingRef = useRef(false);
  const busyRef = useRef(false);
  const load = useCallback(async (refresh = false) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError("");
    setInspection(null);
    setImageError(false);
    try {
      await request("/api/health");
      setConnected(true);
      if (refresh) await request("/api/flood/refresh", "POST");
      const results = await Promise.allSettled([
        request<Metrics>("/api/flood/metrics"),
        request<Overlay>("/api/flood/overlay"),
        request<Boundary>("/api/flood/boundary"),
      ]);
      const [m, o, b] = results;
      setMetrics(m.status === "fulfilled" ? m.value : null);
      setOverlay(o.status === "fulfilled" ? o.value : null);
      setBoundary(b.status === "fulfilled" ? b.value : null);
      setUpdated(Date.now());
      const errors = results.flatMap((r) =>
        r.status === "rejected"
          ? [r.reason instanceof Error ? r.reason.message : "Data unavailable"]
          : []
      );
      if (errors.length) setError([...new Set(errors)].join(" · "));
    } catch (e) {
      if (!refresh) {
        setConnected(false);
        setMetrics(null);
        setOverlay(null);
      }
      setError(
        e instanceof Error ? e.message : "Could not connect to the backend."
      );
    } finally {
      setBusy(false);
      busyRef.current = false;
    }
  }, []);
  useEffect(() => {
    const timer = setTimeout(() => {
      void load();
    }, 0);
    return () => clearTimeout(timer);
  }, [load]);
  async function inspect(latitude = Number(lat), longitude = Number(lon)) {
    if (inspectingRef.current) return;
    if (
      !lat.trim() ||
      !lon.trim() ||
      !Number.isFinite(latitude) ||
      !Number.isFinite(longitude) ||
      Math.abs(latitude) > 90 ||
      Math.abs(longitude) > 180
    ) {
      setInspectError(
        "Enter valid latitude (−90 to 90) and longitude (−180 to 180)."
      );
      return;
    }
    inspectingRef.current = true;
    setInspecting(true);
    setInspectError("");
    setInspection(null);
    try {
      setInspection(
        await request<Inspection>(
          `/api/flood/inspect?lat=${latitude}&lon=${longitude}`
        )
      );
    } catch (e) {
      setInspectError(
        e instanceof Error ? e.message : "Could not inspect location."
      );
    } finally {
      setInspecting(false);
      inspectingRef.current = false;
    }
  }
  const canPlot = !!overlay && geographic(overlay.bounds);
  const paths =
    boundary?.features.flatMap((f) => {
      const g = f.geometry;
      if (!g || !["Polygon", "MultiPolygon"].includes(g.type)) return [];
      const polygons =
        g.type === "Polygon"
          ? [g.coordinates as number[][][]]
          : (g.coordinates as number[][][][]);
      return polygons.map((p) =>
        p
          .map(
            (ring) =>
              ring
                .map(([a, b], i) => `${i ? "L" : "M"}${x(a)},${y(b)}`)
                .join(" ") + "Z"
          )
          .join(" ")
      );
    }) || [];
  const vbWidth = 600 / zoom,
    vbHeight = 640 / zoom;
  const vbX = (600 - vbWidth) / 2,
    vbY = (640 - vbHeight) / 2;
  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="#">
          <span className="brand-mark">◈</span>
          <span>
            terra<span className="brand-dot">.</span>
            <small>DISASTER INTELLIGENCE</small>
          </span>
        </a>
        <div className="nav-label">WORKSPACE</div>
        <a className="nav active" href="#overview">
          ◫ <span>Overview</span>
          <span className="nav-dot" />
        </a>
        <a className="nav" href="#map">
          ◎ <span>Flood map</span>
        </a>
        <a className="nav" href="#inspect">
          ⌖ <span>Location inspector</span>
        </a>
        <a className="nav" href="#source">
          ▤ <span>Data & coverage</span>
        </a>
        <div className="sidebar-bottom">
          <div className="region-badge">VN</div>
          <strong>Vietnam workspace</strong>
          <p>Satellite flood monitoring</p>
          <div className="prototype">STORMHACKS 2026 · PROTOTYPE</div>
        </div>
      </aside>
      <main id="overview">
        <header className="topbar">
          <span>
            Workspace <span className="slash">/</span> <strong>Overview</strong>
          </span>
          <span className={`connection ${connected ? "online" : ""}`}>
            <i />
            {busy
              ? "Connecting…"
              : connected
              ? "Backend connected"
              : "Backend offline"}
          </span>
        </header>
        <section className="heading">
          <div>
            <div className="eyebrow">NATURAL DISASTER TRACKER</div>
            <h1>A clearer view of the ground.</h1>
            <p>Monitor satellite-detected flooding across Vietnam.</p>
          </div>
          <button
            className="primary"
            disabled={busy}
            onClick={() => void load(true)}
          >
            {busy ? "Processing…" : "↻ Refresh satellite data"}
          </button>
        </section>
        <div className="notice" role="status">
          <span className="notice-icon">◉</span>
          <div>
            <strong>Vietnam flood monitoring</strong>
            <span>
              NASA MODIS · Tile {metrics?.tile_id || "h28v07"} ·{" "}
              {metrics
                ? `Acquisition ${metrics.date} (year / day of year)`
                : "Waiting for satellite data"}
            </span>
          </div>
          <button
            className="text-button"
            disabled={busy}
            onClick={() => void load()}
          >
            Reconnect ↗
          </button>
        </div>
        {error && (
          <div className="error" role="alert">
            <strong>Data needs attention</strong>
            <p>{error}</p>
            <span>
              Start the backend, extract the boundary files and add your NASA
              token. Then refresh satellite data.
            </span>
          </div>
        )}
        <section className="stats" aria-label="Satellite metrics">
          <article>
            <div className="stat-label">
              Detected flooded area <span>≈</span>
            </div>
            <h2>
              {number(metrics?.flooded_km2)} <small>km²</small>
            </h2>
            <p>Estimated from classified pixels</p>
          </article>
          <article>
            <div className="stat-label">
              Flood-classified pixels <span>▦</span>
            </div>
            <h2>{number(metrics?.flood_pixels)}</h2>
            <p>0.0625 km² per pixel</p>
          </article>
          <article>
            <div className="stat-label">
              Satellite coverage <span>◎</span>
            </div>
            <h2>{metrics?.tile_id || "—"}</h2>
            <p>Single MODIS tile · Vietnam clipping</p>
          </article>
          <article>
            <div className="stat-label">
              Raster last downloaded <span>◷</span>
            </div>
            <h2 className="date-stat">
              {metrics?.last_updated
                ? new Date(metrics.last_updated).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  })
                : "—"}
            </h2>
            <p>
              {metrics?.last_updated
                ? new Date(metrics.last_updated).toLocaleTimeString()
                : "No raster available yet"}
            </p>
          </article>
        </section>
        <div className="workspace">
          <section className="map-card" id="map">
            <div className="card-header">
              <div>
                <h2>Flood observation map</h2>
                <p>Vietnam / geographic reference</p>
              </div>
              <span className="pill">
                {overlay ? "SATELLITE LAYER" : "AWAITING DATA"}
              </span>
            </div>
            <div className="map">
              <svg
                ref={svg}
                viewBox={`${vbX} ${vbY} ${vbWidth} ${vbHeight}`}
                aria-label="Vietnam geographic reference map; use the coordinate form to inspect a location"
                onClick={(e) => {
                  if (!svg.current) return;
                  const matrix = svg.current.getScreenCTM();
                  if (!matrix) return;
                  const point = new DOMPoint(
                    e.clientX,
                    e.clientY
                  ).matrixTransform(matrix.inverse());
                  const latitude = +(25 - point.y / 38).toFixed(4),
                    longitude = +(101 + point.x / 54).toFixed(4);
                  setLat(String(latitude));
                  setLon(String(longitude));
                  setInspection(null);
                  setInspectError("");
                }}
              >
                <defs>
                  <pattern
                    id="grid"
                    width="54"
                    height="38"
                    patternUnits="userSpaceOnUse"
                  >
                    <path
                      d="M54 0H0V38"
                      fill="none"
                      stroke="#d7e1df"
                      strokeWidth="0.5"
                    />
                  </pattern>
                </defs>
                <rect width="600" height="640" fill="#eaf1f0" />
                <rect width="600" height="640" fill="url(#grid)" />
                <text x="28" y="240" className="country-label">
                  LAOS
                </text>
                <text x="24" y="510" className="country-label">
                  CAMBODIA
                </text>
                <text x="290" y="46" className="country-label">
                  CHINA
                </text>
                <text x="393" y="360" className="sea-label">
                  SOUTH CHINA
                </text>
                <text x="422" y="380" className="sea-label">
                  SEA
                </text>
                {paths.length ? (
                  paths.map((d, i) => (
                    <path
                      key={i}
                      d={d}
                      fill="#fbfcf6"
                      stroke="#a5b7ae"
                      strokeWidth="1.4"
                      fillRule="evenodd"
                    />
                  ))
                ) : (
                  <>
                    <path
                      d="M205 92L249 55L287 70L310 93L335 85L330 128L293 167L289 194L302 219L322 247L347 266L355 304L380 342L388 391L381 436L346 471L306 503L284 540L252 570L219 559L221 531L239 510L254 476L293 450L327 420L335 384L324 342L302 313L283 292L268 258L257 218L238 187L233 153L204 131Z"
                      fill="#fbfcf6"
                      stroke="#a5b7ae"
                      strokeWidth="1.4"
                    />
                    <text x="24" y="615" className="map-note">
                      Illustrative outline · load boundary for precise geography
                    </text>
                  </>
                )}
                {overlay && canPlot && showFlood && !imageError && (
                  <image
                    href={`${overlay.png_url}?v=${updated}`}
                    x={x(overlay.bounds[0])}
                    y={y(overlay.bounds[3])}
                    width={x(overlay.bounds[2]) - x(overlay.bounds[0])}
                    height={y(overlay.bounds[1]) - y(overlay.bounds[3])}
                    preserveAspectRatio="none"
                    opacity={opacity / 100}
                    onError={() => setImageError(true)}
                  />
                )}
                {places.map((p) => (
                  <g key={p.name}>
                    <circle
                      cx={x(p.lon)}
                      cy={y(p.lat)}
                      r="4"
                      fill="#326c5d"
                      stroke="white"
                      strokeWidth="2"
                    />
                    <text
                      x={x(p.lon) + 10}
                      y={y(p.lat) + 4}
                      className="city-label"
                    >
                      {p.name}
                    </text>
                  </g>
                ))}
                {Number.isFinite(Number(lat)) &&
                  Number.isFinite(Number(lon)) && (
                    <g>
                      <circle
                        cx={x(Number(lon))}
                        cy={y(Number(lat))}
                        r="12"
                        fill="#286d5e22"
                        stroke="#286d5e"
                      />
                      <circle
                        cx={x(Number(lon))}
                        cy={y(Number(lat))}
                        r="3"
                        fill="#286d5e"
                      />
                    </g>
                  )}
              </svg>
              <div className="map-controls">
                <button
                  aria-label="Zoom in"
                  disabled={zoom >= 3}
                  onClick={() => setZoom((z) => Math.min(3, z + 0.5))}
                >
                  +
                </button>
                <button
                  aria-label="Zoom out"
                  disabled={zoom <= 1}
                  onClick={() => setZoom((z) => Math.max(1, z - 0.5))}
                >
                  −
                </button>
                <button aria-label="Reset map zoom" onClick={() => setZoom(1)}>
                  ⌂
                </button>
              </div>
              <div className="map-legend">
                <i /> Satellite-detected flood <span>● City reference</span>
              </div>
              <div className="map-hint">
                Click the map to select coordinates
              </div>
            </div>
            <div className="map-footer">
              <span>NASA MODIS flood classification</span>
              <span>Geographic reference · no street basemap</span>
            </div>
          </section>
          <aside className="tools">
            <section className="tool-card" id="inspect">
              <div className="eyebrow">EXPLORE THE DATA</div>
              <h2>Inspect a location</h2>
              <p>
                Select a city, click the map, or enter coordinates to query the
                flood raster.
              </p>
              <div className="city-buttons">
                {places.map((p) => (
                  <button
                    key={p.name}
                    onClick={() => {
                      setLat(String(p.lat));
                      setLon(String(p.lon));
                      setInspection(null);
                      setInspectError("");
                    }}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void inspect();
                }}
              >
                <div className="coordinates">
                  <label>
                    Latitude
                    <input
                      type="number"
                      required
                      step="any"
                      min="-90"
                      max="90"
                      value={lat}
                      onChange={(e) => {
                        setLat(e.target.value);
                        setInspection(null);
                      }}
                    />
                  </label>
                  <label>
                    Longitude
                    <input
                      type="number"
                      required
                      step="any"
                      min="-180"
                      max="180"
                      value={lon}
                      onChange={(e) => {
                        setLon(e.target.value);
                        setInspection(null);
                      }}
                    />
                  </label>
                </div>
                <button
                  className="primary full"
                  disabled={
                    inspecting ||
                    busy ||
                    !metrics ||
                    !geographic(metrics.bounds)
                  }
                >
                  {inspecting ? "Inspecting…" : "⌖ Inspect coordinates"}
                </button>
              </form>
              <div className="inspect-result" role="status">
                {inspectError ||
                  (inspection
                    ? `${inspection.lat.toFixed(4)}, ${inspection.lon.toFixed(
                        4
                      )}: ${
                        !inspection.inside
                          ? "Outside raster coverage."
                          : inspection.flooded
                          ? "Flood-classified pixel detected."
                          : "No flood-classified pixel at this location."
                      }`
                    : "Results will appear here. Satellite classification does not confirm conditions on the ground.")}
              </div>
            </section>
            <section className="tool-card">
              <h2>Map layers</h2>
              <label className="layer">
                <span>
                  <i className="layer-color" />
                  Flood classification<small>NASA satellite observation</small>
                </span>
                <input
                  type="checkbox"
                  checked={showFlood}
                  onChange={(e) => setShowFlood(e.target.checked)}
                />
              </label>
              <label className="range-label">
                Layer opacity <strong>{opacity}%</strong>
                <input
                  type="range"
                  min="10"
                  max="100"
                  value={opacity}
                  onChange={(e) => setOpacity(Number(e.target.value))}
                />
              </label>
              {overlay && !canPlot && (
                <p className="warning">
                  The API returned projected coordinates. Geographic overlay and
                  inspection are paused until the raster bounds are converted to
                  longitude/latitude.
                </p>
              )}
              {imageError && (
                <p className="warning">
                  Overlay image could not load. Reconnect to retry.
                </p>
              )}
              <div className="layer-info">
                {canPlot
                  ? "Overlay aligned to the bounds supplied by the API."
                  : "Flood overlay appears when geographic raster data is available."}
              </div>
            </section>
          </aside>
        </div>
        <section className="source-card" id="source">
          <div>
            <div className="eyebrow">KNOW YOUR SOURCE</div>
            <h2>Observation, with context.</h2>
            <p>
              This prototype uses a single NASA MODIS tile clipped to Vietnam.
              The backend selects a fixed acquisition date; refreshing downloads
              that configured tile. Coverage is limited to the raster footprint.
            </p>
          </div>
          <div className="source-details">
            <span>
              DATA PRODUCT<strong>MCDWD L3 F2 NRT</strong>
            </span>
            <span>
              SUPPORTED HAZARD<strong>Flooding</strong>
            </span>
            <span>
              COMMUNITY REPORTING<strong>No report API in this backend</strong>
            </span>
          </div>
        </section>
        <footer>
          terra. <span>StormHacks 2026 · Situational awareness prototype</span>
          <span>Consult official local alerts for emergency guidance.</span>
        </footer>
      </main>
    </div>
  );
}
export default App;
