import { useEffect, useState } from "react";
import { request, type Hotspot } from "../api";

/** Province/city groups built from responder-saved incidents. */
export function useHotspots(reloadKey: number) {
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!reloadKey) return;
    let cancelled = false;
    request<Hotspot[]>("/api/flood/history/hotspots")
      .then((result) => {
        if (!cancelled) {
          setHotspots(result);
          setError("");
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Hotspots unavailable.");
      });
    return () => { cancelled = true; };
  }, [reloadKey]);
  return { hotspots, error };
}
