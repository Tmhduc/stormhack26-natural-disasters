import { useEffect, useState } from "react";
import { request, type Inspection, type Metrics, type SavedIncident } from "../api";
import { severityFor } from "../lib/triage";

/** Responder-saved locations persisted in Tiger Data. */
export function useSavedIncidents(reloadKey: number) {
  const [incidents, setIncidents] = useState<SavedIncident[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!reloadKey) return;
    let cancelled = false;
    request<SavedIncident[]>("/api/flood/history/incidents")
      .then((result) => {
        if (!cancelled) {
          setIncidents(result);
          setError("");
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Saved incidents unavailable.");
      });
    return () => { cancelled = true; };
  }, [reloadKey]);

  async function save(inspection: Inspection, metrics: Metrics | null) {
    const saved = await request<SavedIncident>("/api/flood/history/incidents", "POST", {
      ...inspection,
      observed_date: metrics?.date,
      severity: severityFor(inspection),
    });
    setIncidents((current) => [saved, ...current.filter((item) => item.id !== saved.id)]);
  }

  async function remove(id: string) {
    await request(`/api/flood/history/incidents/${encodeURIComponent(id)}`, "DELETE");
    setIncidents((current) => current.filter((item) => item.id !== id));
  }

  return { incidents, error, save, remove };
}
