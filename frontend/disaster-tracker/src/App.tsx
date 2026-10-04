import { useCallback, useEffect, useRef, useState } from "react";
import { geographic, request } from "./api";
import type { Boundary, Inspection, Metrics, Overlay, PipelineStatus } from "./api";
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
const formatTime = (value?: string | null) => value ? new Date(value).toLocaleString() : 'Not available yet';
function App() {
  const [search, setSearch] = useState('');
  const [fullscreen, setFullscreen] = useState(false);
  const [fullscreenError, setFullscreenError] = useState('');
  const mapCard = useRef<HTMLElement>(null);
  const normalize = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').toLowerCase();
  const matches = places.filter(p => normalize(p.name + ' ' + (p.name === 'Hanoi' ? 'Hà Nội' : p.name === 'Da Nang' ? 'Đà Nẵng' : 'Hồ Chí Minh Sài Gòn')).includes(normalize(search.trim())));
  useEffect(() => {
    const changed = () => setFullscreen(document.fullscreenElement === mapCard.current);
    document.addEventListener('fullscreenchange', changed);
    return () => document.removeEventListener('fullscreenchange', changed);
  }, []);
  async function toggleFullscreen() {
    setFullscreenError('');
    try {
      if (document.fullscreenElement === mapCard.current) await document.exitFullscreen();
      else if (mapCard.current?.requestFullscreen) await mapCard.current.requestFullscreen();
      else setFullscreenError('Fullscreen is unavailable in this browser.');
    } catch { setFullscreenError('Could not open fullscreen. Try a regular browser window.'); }
  }
  function selectPlace(p: typeof places[number]) {
    setLat(String(p.lat)); setLon(String(p.lon)); setInspection(null); setInspectError(''); setSearch('');
    setView({ zoom: 2, cx: x(p.lon), cy: y(p.lat) });
  }

  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [statusError, setStatusError] = useState('');
  const [reportMessage, setReportMessage] = useState('');

  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [overlay, setOverlay] = useState<Overlay | null>(null);
  const [boundary, setBoundary] = useState<Boundary | null>(null);
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [imageError, setImageError] = useState(false);
  const [showFlood, setShowFlood] = useState(true);
  const [opacity, setOpacity] = useState(75);
  const [view, setView] = useState({ zoom: 1, cx: 300, cy: 320 });
  const zoom = view.zoom;
  const [dragging, setDragging] = useState(false);
  const drag = useRef<{ id: number; x: number; y: number; cx: number; cy: number; inverse: DOMMatrix; moved: boolean } | null>(null);
  const suppressClick = useRef(false);
  function changeZoom(next: number) { setView(v => ({ ...v, zoom: Math.max(1, Math.min(5, next)) })); }
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
        request<PipelineStatus>("/api/flood/status"),
      ]);
      const [m, o, b, status] = results;
      setPipeline(status.status === 'fulfilled' ? status.value : null);
      setStatusError(status.status === 'rejected' ? 'Pipeline status is unavailable on this backend.' : '');
      setMetrics(m.status === "fulfilled" ? m.value : null);
      setOverlay(o.status === "fulfilled" ? o.value : null);
      setBoundary(b.status === "fulfilled" ? b.value : null);
      setUpdated(v => v + 1);
      const errors = results.slice(0, 3).flatMap((r) =>
        r.status === "rejected"
          ? [r.reason instanceof Error ? r.reason.message : "Data unavailable"]
          : []
      );
      if (errors.length) setError([...new Set(errors)].join(" · "));
    } catch (e) {
      if (!refresh) {
        setConnected(false);
        setPipeline(null);
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
  const tiles = metrics?.tiles || (metrics?.tile_id ? [metrics.tile_id] : pipeline?.tiles || []);
  function downloadReport() {
    if (!metrics) return;
    const report = { project: 'Distrack', exported_at: new Date().toISOString(), metrics, pipeline, note: 'Satellite flood classification; not an official emergency alert.' };
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a'); link.href = url; link.download = `distrack-${metrics.date || 'observation'}.json`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000); setReportMessage('Observation report downloaded.');
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
  const vbX = view.cx - vbWidth / 2,
    vbY = view.cy - vbHeight / 2;
  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="#">
          <span className="brand-mark">◈</span>
          <span>
            Distrack<span className="brand-dot">.</span>
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
              NASA MODIS · {tiles.length ? `${tiles.length} tiles` : "Coverage pending"} ·{" "}
              {metrics
                ? `Acquisition ${metrics.date || "pending"} (UTC)`
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
        <section className="pipeline-panel" aria-label="Data pipeline status">
          <div className="pipeline-heading"><div><div className="eyebrow">OBSERVATION STATUS</div><h2>Know when your data was captured.</h2></div><button className="report-button" disabled={!metrics || busy} onClick={downloadReport}>↓ Download report</button></div>
          <div className="pipeline-grid"><div><span>ACQUISITION DAY · UTC</span><strong>{metrics?.date || pipeline?.date || 'Awaiting imagery'}</strong></div><div><span>LAST ARCHIVE CHECK</span><strong>{formatTime(pipeline?.checked_at)}</strong></div><div><span>AUTOMATIC CHECKS</span><strong>{pipeline?.poll_minutes === undefined ? 'Unavailable' : pipeline.poll_minutes === 0 ? 'Disabled' : `Every ${pipeline.poll_minutes} minutes`}</strong></div></div>
          <div className="tile-list">{tiles.length ? tiles.map(tile => <span key={tile}>{tile}</span>) : <span>No tiles loaded yet</span>}</div>
          {pipeline?.last_error && <p className="pipeline-warning" role="alert">Latest pipeline error: {pipeline.last_error}</p>}
          {statusError && <p className="pipeline-warning">{statusError}</p>}
          <p className="export-status" role="status">{reportMessage || 'Satellite acquisition time may differ from the latest processing time.'}</p>
        </section>
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
            <h2>{tiles.length || "—"} <small>tiles</small></h2>
            <p>Multi-tile mosaic · Vietnam clipping</p>
          </article>
          <article>
            <div className="stat-label">
              Raster last processed <span>◷</span>
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
          <section className="map-card" id="map" ref={mapCard}>
            <div className="card-header">
              <div>
                <h2>Flood observation map</h2>
                <p>Vietnam / geographic reference</p>
              </div>
              <div className="map-header-actions"><span className="pill">{overlay ? "SATELLITE LAYER" : "AWAITING DATA"}</span><button className="fullscreen-button" onClick={() => void toggleFullscreen()} aria-label={fullscreen ? 'Exit fullscreen map' : 'Open fullscreen map'}>{fullscreen ? '↙ Exit fullscreen' : '⛶ Fullscreen'}</button></div>
            </div>
            <div className="map-search-bar">
              <label htmlFor="place-search">Find a city</label>
              <input id="place-search" type="search" placeholder="Hà Nội, Đà Nẵng, Hồ Chí Minh…" value={search} onChange={e => setSearch(e.target.value)} />
              {search.trim() && <div className="search-results" aria-label="Matching cities">{matches.length ? matches.map(p => <button key={p.name} onClick={() => selectPlace(p)}>⌖ {p.name}<small>{p.lat.toFixed(4)}, {p.lon.toFixed(4)}</small></button>) : <p>No matching city. Search supports Hanoi, Da Nang and Ho Chi Minh City; other locations can be selected on the map.</p>}</div>}
              {fullscreenError && <p className="pipeline-warning" role="alert">{fullscreenError}</p>}
            </div>
            <div className="map">
              <svg
                ref={svg}
                className={dragging ? 'is-dragging' : ''}
                onPointerDown={e => {
                  if (e.button !== 0 || drag.current) return;
                  const matrix = e.currentTarget.getScreenCTM(); if (!matrix) return;
                  suppressClick.current = false;
                  drag.current = { id: e.pointerId, x: e.clientX, y: e.clientY, cx: view.cx, cy: view.cy, inverse: matrix.inverse(), moved: false };
                  e.currentTarget.setPointerCapture(e.pointerId);
                }}
                onPointerMove={e => {
                  const start = drag.current; if (!start || start.id !== e.pointerId) return;
                  if (Math.hypot(e.clientX - start.x, e.clientY - start.y) < 5 && !start.moved) return;
                  start.moved = true; suppressClick.current = true; setDragging(true);
                  const from = new DOMPoint(start.x, start.y).matrixTransform(start.inverse);
                  const to = new DOMPoint(e.clientX, e.clientY).matrixTransform(start.inverse);
                  setView(v => ({ ...v, cx: start.cx - (to.x - from.x), cy: start.cy - (to.y - from.y) }));
                }}
                onPointerUp={e => {
                  if (drag.current?.id !== e.pointerId) return;
                  drag.current = null; setDragging(false);
                  if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
                }}
                onPointerCancel={() => { drag.current = null; suppressClick.current = true; setDragging(false); }}
                onLostPointerCapture={() => { drag.current = null; setDragging(false); }}
                viewBox={`${vbX} ${vbY} ${vbWidth} ${vbHeight}`}
                aria-label="Vietnam geographic reference map; use the coordinate form to inspect a location"
                onClick={(e) => {
                  if (suppressClick.current) { suppressClick.current = false; return; }
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
                  disabled={zoom >= 5}
                  onClick={() => changeZoom(zoom + 0.5)}
                >
                  +
                </button>
                <button
                  aria-label="Zoom out"
                  disabled={zoom <= 1}
                  onClick={() => changeZoom(zoom - 0.5)}
                >
                  −
                </button>
                <button aria-label="Reset map zoom" onClick={() => setView({ zoom: 1, cx: 300, cy: 320 })}>
                  ⌂
                </button>
              </div>
              <div className="map-legend">
                <i /> Satellite-detected flood <span>● City reference</span>
              </div>
              <div className="selected-location" aria-live="polite"><div className="eyebrow">SELECTED LOCATION</div><strong>{lat && lon ? `${Number(lat).toFixed(4)} lat / ${Number(lon).toFixed(4)} lon` : 'Select a location'}</strong><p>{inspecting ? 'Inspecting satellite pixel…' : inspection ? !inspection.inside ? 'Outside raster coverage' : inspection.flooded === null ? 'Classification unavailable' : inspection.flooded ? 'Flood-classified pixel detected' : 'No flood-classified pixel detected' : 'Coordinates selected · not inspected yet'}</p><small>Acquisition: {metrics?.date || 'unavailable'} · UTC</small><button disabled={inspecting || busy || !metrics || !geographic(metrics.bounds)} onClick={() => void inspect()}>⌖ Inspect this location</button>{inspectError && <p role="alert">{inspectError}</p>}</div>
              <div className="map-hint">
                Drag to move · Use + / − to zoom · Click to select
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
                    onClick={() => selectPlace(p)}
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
              NASA MODIS tiles are mosaicked and clipped to Vietnam. The backend searches for the newest complete UTC day and checks for updates on its configured schedule. Observation coverage is limited to the loaded raster.
            </p>
          </div>
          <div className="source-details">
            <span>
              DATA PRODUCT<strong>{metrics?.product || pipeline?.product || "NASA MODIS"}</strong>
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
          Distrack. <span>StormHacks 2026 · Situational awareness prototype</span>
          <span>Consult official local alerts for emergency guidance.</span>
        </footer>
      </main>
    </div>
  );
}
export default App;
