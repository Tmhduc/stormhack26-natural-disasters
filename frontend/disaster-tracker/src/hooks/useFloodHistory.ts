import { useEffect, useState } from "react";
import { request } from "../api";
import type { HistoryDay } from "../api";

/** Days the backend has saved to its database, newest first. Refetched whenever `reloadKey` changes. */
export function useFloodHistory(reloadKey: number) {
  const [days, setDays] = useState<HistoryDay[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!reloadKey) return; // wait until the first data load has reached the backend
    let cancelled = false;
    request<HistoryDay[]>("/api/flood/history")
      .then((result) => {
        if (cancelled) return;
        setDays(result);
        setError("");
      })
      .catch((e) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Flood history unavailable.");
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);
  return { days, error };
}
