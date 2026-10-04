import { useState } from "react";
import type { Inspection, Metrics } from "../api";
import { floodClassLabel } from "../lib/floodLanguage";

type Props = { inspection: Inspection | null; metrics: Metrics | null; onSave: (inspection: Inspection) => void; saved: boolean };

function buildBrief(inspection: Inspection, metrics: Metrics | null) {
  const label = floodClassLabel(inspection.class_name, inspection.class_value);
  const address = inspection.address || inspection.admin1_name || "Address unavailable";
  const nearbyArea = inspection.nearby_flood_pixels != null
    ? `${(inspection.nearby_flood_pixels * 0.0625).toFixed(1)} km² may be affected within ${inspection.nearby_radius_km ?? 2} km`
    : "Nearby area estimate unavailable";
  return [
    "FLOOD OBSERVATION BRIEF",
    `Location: ${address}`,
    `Coordinates: ${inspection.lat.toFixed(5)}, ${inspection.lon.toFixed(5)}`,
    `Satellite finding: ${label}`,
    `Nearby signal: ${nearbyArea}`,
    `Observation date: ${metrics?.date || "Unavailable"} UTC`,
    `Map: https://www.google.com/maps?q=${inspection.lat},${inspection.lon}`,
    "Source: NASA MODIS flood observations. This is a satellite signal, not a ground-verified report.",
  ].join("\n");
}

export default function IncidentBrief({ inspection, metrics, onSave, saved }: Props) {
  const [copied, setCopied] = useState(false);
  if (!inspection || !inspection.inside) return null;
  const selected = inspection;
  const brief = buildBrief(selected, metrics);

  async function copyBrief() {
    await navigator.clipboard.writeText(brief);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  function downloadBrief() {
    const blob = new Blob([brief], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `flood-brief-${selected.lat.toFixed(3)}-${selected.lon.toFixed(3)}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="tool-card incident-brief">
      <div className="eyebrow">FOR RESPONSE TEAMS</div>
      <h2>Incident brief</h2>
      <p>Share the verified coordinates and satellite finding with your team.</p>
      <div className="brief-actions">
        <button className="primary" onClick={() => void copyBrief()}>{copied ? "Copied" : "Copy brief"}</button>
        <button className="brief-download" onClick={() => onSave(selected)}>{saved ? "Saved" : "Save location"}</button>
        <button className="brief-download" onClick={downloadBrief}>Download .txt</button>
      </div>
    </section>
  );
}
