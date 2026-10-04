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
  const [error, setError] = useState("");
  const [updated, setUpdated] = useState(0);
  const busyRef = useRef(false);
  const load = useCallback(async (refresh = false) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError("");
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
  return {
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
