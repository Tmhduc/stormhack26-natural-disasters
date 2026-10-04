import { useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent } from "react";
import type { Boundary, Overlay } from "../api";
import { formatDay } from "../lib/format";
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
  const [fullscreen, setFullscreen] = useState(false);
  const [fullscreenError, setFullscreenError] = useState("");
  const mapCard = useRef<HTMLElement>(null);
  const svg = useRef<SVGSVGElement>(null);
  const paths = useMemo(() => boundaryPaths(boundary), [boundary]);
  const searchResults = places.filter((place) =>
    place.name.toLowerCase().includes(search.trim().toLowerCase())
  );
  const vbWidth = MAP_WIDTH / zoom,
    vbHeight = MAP_HEIGHT / zoom;
  const vbX = (MAP_WIDTH - vbWidth) / 2,
    vbY = (MAP_HEIGHT - vbHeight) / 2;

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
            {fullscreen ? "Thoát toàn màn hình" : "Toàn màn hình"}
          </button>
        </div>
      </div>
      <div className="map-search-bar">
        <label htmlFor="map-search">Tìm địa điểm</label>
        <input
          id="map-search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Hanoi, Da Nang..."
        />
        {search.trim() && (
          <div className="search-results">
            {searchResults.length ? (
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
              ))
            ) : (
              <p>Không tìm thấy địa điểm.</p>
            )}
          </div>
        )}
      </div>
      {fullscreenError && <p className="pipeline-warning">{fullscreenError}</p>}
      <div className="map">
        <svg
          ref={svg}
          viewBox={`${vbX} ${vbY} ${vbWidth} ${vbHeight}`}
          aria-label="Vietnam geographic reference map; use the coordinate form to inspect a location"
          onClick={handleClick}
        >
          <defs>
            <pattern id="grid" width="54" height="38" patternUnits="userSpaceOnUse">
              <path d="M54 0H0V38" fill="none" stroke="#d7e1df" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width={MAP_WIDTH} height={MAP_HEIGHT} fill="#eaf1f0" />
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
              href={overlay.png_url}
              x={lonToX(overlay.bounds[0])}
              y={latToY(overlay.bounds[3])}
              width={lonToX(overlay.bounds[2]) - lonToX(overlay.bounds[0])}
              height={latToY(overlay.bounds[1]) - latToY(overlay.bounds[3])}
              preserveAspectRatio="none"
              opacity={opacity / 100}
              onError={onImageError}
            />
          )}
          {places.map((p) => (
            <g key={p.name}>
              <circle
                cx={lonToX(p.lon)}
                cy={latToY(p.lat)}
                r="4"
                fill="#326c5d"
                stroke="white"
                strokeWidth="2"
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
                r="7"
                fill="#286d5e22"
                stroke="#286d5e"
              />
              <circle cx={lonToX(Number(lon))} cy={latToY(Number(lat))} r="2.5" fill="#286d5e" />
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
        <div className="map-hint">Click the map to select coordinates</div>
      </div>
      <div className="map-footer">
        <span>NASA MODIS flood classification</span>
        <span>Geographic reference · no street basemap</span>
      </div>
    </section>
  );
}
