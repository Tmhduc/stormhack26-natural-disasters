import { useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent } from "react";
import { request, type Boundary, type GeocodeResult, type Overlay } from "../api";
import type { LocationInspector } from "../hooks/useLocationInspector";
import { formatDay } from "../lib/format";
import { floodClassLabel } from "../lib/floodLanguage";
import {
  MAP_HEIGHT,
  MAP_WIDTH,
  boundaryPaths,
  latToY,
  lonToX,
  places,
  xToLon,
  yToLat,
} from "../lib/map";

type Props = {
  inspector: LocationInspector;
  inspectDisabled: boolean;
  acquisitionDate: string | null;
  boundary: Boundary | null;
  overlay: Overlay | null;
  archiveDate: string | null; // set when showing a past day instead of the latest data
  canPlot: boolean;
  showFlood: boolean;
  opacity: number;
  imageError: boolean;
  onImageError: () => void;
  lat: string;
  lon: string;
  onSelect: (lat: number, lon: number) => void;
};

export default function FloodMap({
  inspector,
  inspectDisabled,
  acquisitionDate,
  boundary,
  overlay,
  archiveDate,
  canPlot,
  showFlood,
  opacity,
  imageError,
  onImageError,
  lat,
  lon,
  onSelect,
}: Props) {
  const [zoom, setZoom] = useState(1);
  const [search, setSearch] = useState("");
  const [addressResults, setAddressResults] = useState<GeocodeResult[]>([]);
  const [searchingAddress, setSearchingAddress] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [center, setCenter] = useState({ x: MAP_WIDTH / 2, y: MAP_HEIGHT / 2 });
  const [dragging, setDragging] = useState(false);
  const drag = useRef<{ id: number; x: number; y: number; cx: number; cy: number; inverse: DOMMatrix; moved: boolean } | null>(null);
  const suppressClick = useRef(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [fullscreenError, setFullscreenError] = useState("");
  const mapCard = useRef<HTMLElement>(null);
  const svg = useRef<SVGSVGElement>(null);
  const paths = useMemo(() => boundaryPaths(boundary), [boundary]);
  const searchResults = places.filter((place) =>
    `${place.name} ${place.englishName}`.toLowerCase().includes(search.trim().toLowerCase())
  );
  async function searchAddress() {
    const query = search.trim();
    if (query.length < 3) return;
    setSearchingAddress(true);
    setSearchError("");
    try {
      setAddressResults(await request<GeocodeResult[]>(`/api/flood/geocode?q=${encodeURIComponent(query)}`));
    } catch (error) {
      setAddressResults([]);
      setSearchError(error instanceof Error ? error.message : "Address search unavailable.");
    } finally {
      setSearchingAddress(false);
    }
  }
  const vbWidth = MAP_WIDTH / zoom,
    vbHeight = MAP_HEIGHT / zoom;
  const result = !archiveDate && inspector.inspection?.lat === Number(lat) && inspector.inspection?.lon === Number(lon) ? inspector.inspection : null;
  const vbX = center.x - vbWidth / 2,
    vbY = center.y - vbHeight / 2;

  useEffect(() => {
    const handleFullscreenChange = () => {
      setFullscreen(document.fullscreenElement === mapCard.current);
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  async function toggleFullscreen() {
    setFullscreenError("");
    try {
      if (document.fullscreenElement === mapCard.current) {
        await document.exitFullscreen();
      } else if (mapCard.current?.requestFullscreen) {
        await mapCard.current.requestFullscreen();
      } else {
        setFullscreenError("Fullscreen không khả dụng trên trình duyệt này.");
      }
    } catch {
      setFullscreenError("Không thể mở fullscreen trên cửa sổ hiện tại.");
    }
  }

  function handleClick(e: MouseEvent<SVGSVGElement>) {
    if (suppressClick.current) { suppressClick.current = false; return; }
    if (!svg.current) return;
    const matrix = svg.current.getScreenCTM();
    if (!matrix) return;
    const point = new DOMPoint(e.clientX, e.clientY).matrixTransform(
      matrix.inverse()
    );
    onSelect(+yToLat(point.y).toFixed(4), +xToLon(point.x).toFixed(4));
  }

  return (
    <section ref={mapCard} className="map-card" id="map">
      <div className="card-header">
        <div>
          <h2>Flood observation map</h2>
          <p>Vietnam / geographic reference</p>
        </div>
        <div className="map-header-actions">
          <span className="pill">
            {archiveDate
              ? `ARCHIVE · ${formatDay(archiveDate).toUpperCase()}`
              : overlay
              ? "SATELLITE LAYER"
              : "AWAITING DATA"}
          </span>
          <button className="fullscreen-button" onClick={() => void toggleFullscreen()}>
            {fullscreen ? "Exit full screen" : "Full screen"}
          </button>
        </div>
      </div>
      <div className="map-search-bar">
        <label htmlFor="map-search">Tìm địa điểm</label>
        <input
          id="map-search"
          value={search}
          onChange={(event) => { setSearch(event.target.value); setAddressResults([]); setSearchError(""); }}
          onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void searchAddress(); } }}
          placeholder="Search city or street address..."
        />
        <button className="address-search-button" type="button" disabled={searchingAddress || search.trim().length < 3} onClick={() => void searchAddress()}>
          {searchingAddress ? "…" : "Search"}
        </button>
        {search.trim() && (
          <div className="search-results">
            {searchResults.length || addressResults.length ? (
              searchResults.map((place) => (
                <button
                  key={place.name}
                  onClick={() => {
                    onSelect(place.lat, place.lon);
                    setSearch("");
                  }}
                >
                  {place.name}
                  <small>
                    {place.lat.toFixed(4)}, {place.lon.toFixed(4)}
                  </small>
                </button>
              )).concat(addressResults.map((result) => (
                <button key={`${result.lat},${result.lon}`} onClick={() => { onSelect(result.lat, result.lon); setSearch(result.address); setAddressResults([]); }}>
                  {result.address}
                  <small>{result.lat.toFixed(4)}, {result.lon.toFixed(4)}</small>
                </button>
              )))
            ) : (
              <p>{searchError || "Press Search or Enter to find an address."}</p>
            )}
            {searchError && <p>{searchError}</p>}
          </div>
        )}
      </div>
      {fullscreenError && <p className="pipeline-warning">{fullscreenError}</p>}
      <div className="map">
        <svg
          ref={svg}
          className={dragging ? 'is-dragging' : ''}
          style={{ touchAction: 'none', userSelect: 'none', cursor: dragging ? 'grabbing' : 'grab' }}
          onPointerDown={e => {
            if (e.button !== 0 || drag.current) return;
            const matrix = e.currentTarget.getScreenCTM(); if (!matrix) return;
            suppressClick.current = false;
            drag.current = { id: e.pointerId, x: e.clientX, y: e.clientY, cx: center.x, cy: center.y, inverse: matrix.inverse(), moved: false };
            e.currentTarget.setPointerCapture(e.pointerId);
          }}
          onPointerMove={e => {
            const start = drag.current; if (!start || start.id !== e.pointerId) return;
            if (!start.moved && Math.hypot(e.clientX - start.x, e.clientY - start.y) < 5) return;
            start.moved = true; suppressClick.current = true; setDragging(true);
            const from = new DOMPoint(start.x, start.y).matrixTransform(start.inverse);
            const to = new DOMPoint(e.clientX, e.clientY).matrixTransform(start.inverse);
            setCenter({ x: start.cx - (to.x - from.x), y: start.cy - (to.y - from.y) });
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
          onClick={handleClick}
        >
          <defs>
            <pattern id="grid" width="54" height="38" patternUnits="userSpaceOnUse">
              <path d="M54 0H0V38" fill="none" stroke="#c3d5da" strokeWidth="0.6" />
            </pattern>
          </defs>
          <rect width={MAP_WIDTH} height={MAP_HEIGHT} fill="#dcebef" />
          <rect width={MAP_WIDTH} height={MAP_HEIGHT} fill="url(#grid)" />
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
                fill="#f8fbf3"
                stroke="#527463"
                strokeWidth="2.2"
                fillRule="evenodd"
              />
            ))
          ) : (
            <>
              <path
                d="M205 92L249 55L287 70L310 93L335 85L330 128L293 167L289 194L302 219L322 247L347 266L355 304L380 342L388 391L381 436L346 471L306 503L284 540L252 570L219 559L221 531L239 510L254 476L293 450L327 420L335 384L324 342L302 313L283 292L268 258L257 218L238 187L233 153L204 131Z"
                fill="#f8fbf3"
                stroke="#527463"
                strokeWidth="2.2"
              />
              <text x="24" y="615" className="map-note">
                Illustrative outline · load boundary for precise geography
              </text>
            </>
          )}
          {overlay && canPlot && showFlood && !imageError && (
            <image
              href={overlay.png_url}
              x={lonToX(overlay.bounds[0])}
              y={latToY(overlay.bounds[3])}
              width={lonToX(overlay.bounds[2]) - lonToX(overlay.bounds[0])}
              height={latToY(overlay.bounds[1]) - latToY(overlay.bounds[3])}
              preserveAspectRatio="none"
              opacity={opacity / 100}
              style={{ filter: "saturate(1.45) contrast(1.2)" }}
              onError={onImageError}
            />
          )}
          {places.map((p) => (
            <g key={p.name}>
              <circle
                cx={lonToX(p.lon)}
                cy={latToY(p.lat)}
                r="5"
                fill="#173f5f"
                stroke="#ffffff"
                strokeWidth="2.5"
              />
              <text x={lonToX(p.lon) + 10} y={latToY(p.lat) + 4} className="city-label">
                {p.name}
              </text>
            </g>
          ))}
          {Number.isFinite(Number(lat)) && Number.isFinite(Number(lon)) && (
            <g>
              <circle
                cx={lonToX(Number(lon))}
                cy={latToY(Number(lat))}
                r="9"
                fill="#f4b94255"
                stroke="#a85b00"
                strokeWidth="2"
              />
              <circle cx={lonToX(Number(lon))} cy={latToY(Number(lat))} r="3.5" fill="#a85b00" stroke="#fff" strokeWidth="1.5" />
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
          <button aria-label="Reset map zoom" onClick={() => { setZoom(1); setCenter({ x: MAP_WIDTH / 2, y: MAP_HEIGHT / 2 }); }}>
            ⌂
          </button>
        </div>
        <div className="map-legend">
          <i /> Satellite-detected flood <span>● City reference</span>
        </div>
        {fullscreen && <div className="selected-location" aria-live="polite">
          <div className="eyebrow">SELECTED LOCATION</div>
          <strong>{lat.trim() && lon.trim() && Number.isFinite(Number(lat)) && Number.isFinite(Number(lon)) ? `${Number(lat).toFixed(4)} lat / ${Number(lon).toFixed(4)} lon` : 'Select a point on the map'}</strong>
          {result?.admin1_name && <div className="selected-place">📍 {result.admin1_type || 'Khu vực'}: <strong>{result.admin1_name}</strong></div>}
          {result?.address && <div className="selected-address">{result.address}</div>}
          <p>{archiveDate ? 'Historical view · inspection is available for Latest only.' : inspector.inspecting ? 'Inspecting satellite pixel…' : result ? !result.inside ? 'Outside raster coverage' : result.flooded === null ? 'Classification unavailable' : result.flooded ? 'Flood-classified pixel detected' : 'No flood-classified pixel detected' : 'Not inspected yet'}</p>
          {result && <small>What the satellite saw: {floodClassLabel(result.class_name, result.class_value)}</small>}
          <small>Acquisition: {acquisitionDate || 'unavailable'} · UTC</small>
          <button disabled={inspectDisabled || inspector.inspecting} onClick={() => void inspector.inspect()}>{inspector.inspecting ? 'Inspecting…' : '⌖ Inspect this location'}</button>
          {!archiveDate && inspector.error && <p role="alert">{inspector.error}</p>}
          <small>Satellite classification does not confirm ground conditions.</small>
        </div>}
        <div className="map-hint">Drag to move · Use + / − to zoom · Click to select</div>
      </div>
      <div className="map-footer">
        <span>NASA MODIS flood classification</span>
        <span>Geographic reference · no street basemap</span>
      </div>
    </section>
  );
}
