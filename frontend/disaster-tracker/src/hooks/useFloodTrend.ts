import { useEffect, useState } from "react";
import { request } from "../api";
import type { TrendPoint } from "../api";

/** Daily flood totals saved in Tiger Data, oldest first. */
export function useFloodTrend(reloadKey: number) {
  const [points, setPoints] = useState<TrendPoint[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!reloadKey) return;
    let cancelled = false;
    request<TrendPoint[]>("/api/flood/history/trend?limit=30")
      .then((result) => {
        if (cancelled) return;
        setPoints(result);
        setError("");
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Flood trend unavailable.");
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  return { points, error };
}
