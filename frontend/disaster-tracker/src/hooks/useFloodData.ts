import { useCallback, useEffect, useRef, useState } from "react";
import { request } from "../api";
import type { Boundary, Metrics, Overlay } from "../api";

/** Backend connection plus the flood metrics, overlay and boundary it serves. */
export function useFloodData() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [overlay, setOverlay] = useState<Overlay | null>(null);
  const [boundary, setBoundary] = useState<Boundary | null>(null);
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState('');
  const [autoReload, setAutoReload] = useState(true);
  const [lastRead, setLastRead] = useState<string | null>(null);
  const [datasetVersion, setDatasetVersion] = useState('');
  const boundaryRef = useRef<Boundary | null>(null);
  const [error, setError] = useState("");
  const [updated, setUpdated] = useState(0);
  const busyRef = useRef(false);
  const load = useCallback(async (refresh = false, background = false) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    if (!background) setError("");
    setPhase("Connecting to backend…");
    try {
      await request("/api/health");
      setConnected(true);
      if (refresh) {
        setPhase('Checking NASA for new imagery…');
        await request('/api/flood/refresh', 'POST');
      }
      setPhase('Reading saved dashboard data…');
      const results = await Promise.allSettled([
        request<Metrics>("/api/flood/metrics"),
        request<Overlay>("/api/flood/overlay"),
        boundaryRef.current ? Promise.resolve(boundaryRef.current) : request<Boundary>("/api/flood/boundary"),
      ]);
      const [m, o, b] = results;
      if (m.status === 'fulfilled') {
        setMetrics(m.value);
        setDatasetVersion(`${m.value.date}|${m.value.last_updated}|${m.value.flood_pixels}`);
      } else if (!background) setMetrics(null);
      if (o.status === 'fulfilled') setOverlay(o.value); else if (!background) setOverlay(null);
      if (b.status === 'fulfilled') { setBoundary(b.value); boundaryRef.current = b.value; }
      setUpdated(v => v + 1);
      const errors = results.flatMap((r) =>
        r.status === "rejected"
          ? [r.reason instanceof Error ? r.reason.message : "Data unavailable"]
          : []
      );
      setError(errors.length ? [...new Set(errors)].join(' · ') : '');
      if (!errors.length) setLastRead(new Date().toISOString());
    } catch (e) {
      if (!refresh) {
        setConnected(false);
        if (!background) { setMetrics(null); setOverlay(null); }
      }
      setError(
        e instanceof Error ? e.message : "Could not connect to the backend."
      );
    } finally {
      setBusy(false);
      setPhase("");
      busyRef.current = false;
    }
  }, []);
  useEffect(() => {
    const timer = setTimeout(() => {
      void load();                         
    }, 0);
    return () => clearTimeout(timer); 
  }, [load]);
  useEffect(() => {
    if (!autoReload) return;
    const read = () => { if (document.visibilityState === 'visible') void load(false, true); };
    const timer = setInterval(read, 60000);
    document.addEventListener('visibilitychange', read);
    return () => { clearInterval(timer); document.removeEventListener('visibilitychange', read); };
  }, [autoReload, load]);
  return {
    phase, autoReload, setAutoReload, lastRead, datasetVersion,
    metrics,
    overlay,
    boundary,
    connected,
    busy,
    error,
    updated,
    load,
  };
}
