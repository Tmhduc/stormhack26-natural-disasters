import { useEffect, useState } from "react";
import { geographic } from "./api";
import type { Metrics, Overlay } from "./api";
import DataNotice from "./components/DataNotice";
import ErrorBanner from "./components/ErrorBanner";
import FloodMap from "./components/FloodMap";
import Footer from "./components/Footer";
import HistoryTimeline from "./components/HistoryTimeline";
import IncidentBrief from "./components/IncidentBrief";
import ResponderBoard from "./components/ResponderBoard";
import type { Inspection } from "./api";
import InspectPanel from "./components/InspectPanel";
import LayerPanel from "./components/LayerPanel";
import PageHeading from "./components/PageHeading";
import Sidebar from "./components/Sidebar";
import SourceCard from "./components/SourceCard";
import StatsGrid from "./components/StatsGrid";
import Topbar from "./components/Topbar";
import { useFloodData } from "./hooks/useFloodData";
import { useFloodHistory } from "./hooks/useFloodHistory";
import { useLocationInspector } from "./hooks/useLocationInspector";
import "./App.css";

function App() {
  const flood = useFloodData();
  const history = useFloodHistory(flood.updated);
  const inspector = useLocationInspector();
  const { clearResult } = inspector;
  useEffect(() => {
    const timer = setTimeout(clearResult, 0);
    return () => clearTimeout(timer);
  }, [flood.datasetVersion, clearResult]);
  const [selectedId, setSelectedId] = useState<number | null>(null); // null = latest data
  const [showFlood, setShowFlood] = useState(true);
  const [opacity, setOpacity] = useState(75);
  const [brokenImage, setBrokenImage] = useState<string | null>(null);
  const [incidents, setIncidents] = useState<Inspection[]>([]);
  const { busy } = flood;
  const pastDay = history.days.find((d) => d.id === selectedId) ?? null;
  // The stats, notice and map show either the selected past day or the latest data.
  const metrics: Metrics | null = pastDay
    ? {
        flood_pixels: pastDay.flood_pixels,
        flooded_km2: pastDay.flooded_km2,
        bounds: pastDay.bounds,
        product: flood.metrics?.product ?? null,
        tiles: pastDay.tiles,
        date: pastDay.date,
        last_updated: pastDay.processed_at,
      }
    : flood.metrics;
  const overlay: Overlay | null = pastDay
    ? { png_url: pastDay.png_url, bounds: pastDay.bounds }
    : flood.overlay && {
        ...flood.overlay,
        // The live PNG keeps its URL across refreshes; bust the browser cache.
        png_url: `${flood.overlay.png_url}?v=${flood.updated}`,
      };
  const canPlot = !!overlay && geographic(overlay.bounds);
  const imageError = !!overlay && brokenImage === overlay.png_url;
  // New data or another day makes any earlier inspection result stale.
  function reload(refresh = false) {
    inspector.clearResult();
    void flood.load(refresh);
  }
  function selectDay(id: number | null) {
    inspector.clearResult();
    setSelectedId(id);
  }
  function saveIncident(inspection: Inspection) {
    setIncidents((current) => current.some((item) => item.lat === inspection.lat && item.lon === inspection.lon) ? current : [...current, inspection]);
  }
  function removeIncident(key: string) {
    setIncidents((current) => current.filter((item) => `${item.lat.toFixed(5)},${item.lon.toFixed(5)}` !== key));
  }
  return (
    <div className="shell">
      <Sidebar />
      <main id="overview">
        <Topbar connected={flood.connected} busy={busy} />
        <PageHeading busy={busy} onRefresh={() => reload(true)} />
        <DataNotice metrics={metrics} busy={busy} onReconnect={() => reload()} />
        <div className="reload-help"><p><strong>Reload dashboard</strong> reads saved backend data. <strong>Refresh satellite data</strong> checks NASA and processes new imagery when available.</p><label><input type="checkbox" checked={flood.autoReload} onChange={e => flood.setAutoReload(e.target.checked)} />Auto reload every 60s</label></div>
        <p className="reload-status" role="status">{busy ? flood.phase : flood.error ? 'Update failed. Previously displayed data may be out of date.' : flood.lastRead ? `Dashboard last read: ${new Date(flood.lastRead).toLocaleTimeString()}` : 'Waiting for data'}{pastDay ? ' · Viewing selected historical day' : ''}</p>
        {flood.error && <ErrorBanner message={flood.error} />}
        {(history.days.length > 0 || history.error) && (
          <HistoryTimeline
            latest={flood.metrics}
            days={history.days}
            selectedId={pastDay ? pastDay.id : null}
            onSelect={selectDay}
            error={history.error}
          />
        )}
        <StatsGrid metrics={metrics} />
        <div className="workspace">
          <FloodMap
            inspector={inspector}
            acquisitionDate={metrics?.date || null}
            inspectDisabled={busy || !flood.metrics || !geographic(flood.metrics.bounds) || !!pastDay}
            boundary={flood.boundary}
            overlay={overlay}
            archiveDate={pastDay ? pastDay.date : null}
            canPlot={canPlot}
            showFlood={showFlood}
            opacity={opacity}
            imageError={imageError}
            onImageError={() => overlay && setBrokenImage(overlay.png_url)}
            lat={inspector.lat}
            lon={inspector.lon}
            onSelect={inspector.select}
          />
          <aside className="tools">
            <InspectPanel
              inspector={inspector}
              disabled={
                busy || !flood.metrics || !geographic(flood.metrics.bounds) || !!pastDay
              }
              notice={
                pastDay
                  ? "Inspection checks the latest data. Select “Latest” under Flood history to inspect a location."
                  : undefined
              }
            />
            <LayerPanel
              showFlood={showFlood}
              onShowFloodChange={setShowFlood}
              opacity={opacity}
              onOpacityChange={setOpacity}
              hasOverlay={!!overlay}
              canPlot={canPlot}
              imageError={imageError}
            />
            <IncidentBrief inspection={inspector.inspection} metrics={metrics} onSave={saveIncident} saved={!!inspector.inspection && incidents.some((item) => item.lat === inspector.inspection?.lat && item.lon === inspector.inspection?.lon)} />
            <ResponderBoard incidents={incidents} metrics={metrics} onRemove={removeIncident} />
          </aside>
        </div>
        <SourceCard />
        <Footer />
      </main>
    </div>
  );
}
export default App;
