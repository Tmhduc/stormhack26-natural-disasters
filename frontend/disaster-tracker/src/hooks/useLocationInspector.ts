import { useCallback, useRef, useState } from "react";
import { request } from "../api";
import type { Inspection } from "../api";

/** The selected coordinates and the result of asking the backend whether they're flooded. */
export function useLocationInspector() {
  const [lat, setLatValue] = useState("16.0544");
  const [lon, setLonValue] = useState("108.2022");
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [error, setError] = useState("");
  const [inspecting, setInspecting] = useState(false);
  const inspectingRef = useRef(false);
  // Editing a coordinate makes the previous result stale.
  function setLat(value: string) {
    setLatValue(value);
    setInspection(null);
  }
  function setLon(value: string) {
    setLonValue(value);
    setInspection(null);
  }
  // Picking a point (map click or city button) starts over.
  function select(latitude: number, longitude: number) {
    setLatValue(String(latitude));
    setLonValue(String(longitude));
    setInspection(null);
    setError("");
  }
  async function inspect() {
    const latitude = Number(lat),
      longitude = Number(lon);
    if (inspectingRef.current) return;
    if (
      !lat.trim() ||
      !lon.trim() ||
      !Number.isFinite(latitude) ||
      !Number.isFinite(longitude) ||
      Math.abs(latitude) > 90 ||
      Math.abs(longitude) > 180
    ) {
      setError("Enter valid latitude (−90 to 90) and longitude (−180 to 180).");
      return;
    }
    inspectingRef.current = true;
    setInspecting(true);
    setError("");
    setInspection(null);
    try {
      setInspection(
        await request<Inspection>(
          `/api/flood/inspect?lat=${latitude}&lon=${longitude}`
        )
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not inspect location.");
    } finally {
      setInspecting(false);
      inspectingRef.current = false;
    }
  }
  const clearResult = useCallback(() => setInspection(null), []);
  return {
    lat,
    lon,
    setLat,
    setLon,
    select,
    inspect,
    inspection,
    error,
    inspecting,
    clearResult,
  };
}

export type LocationInspector = ReturnType<typeof useLocationInspector>;
