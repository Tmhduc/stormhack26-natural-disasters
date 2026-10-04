import { useState } from "react";
import type { Inspection, Metrics, SavedIncident } from "../api";
import { floodClassLabel } from "../lib/floodLanguage";
import { severityDescription, severityFor } from "../lib/triage";

type Props = { incidents: SavedIncident[]; metrics: Metrics | null; onRemove: (id: string) => void | Promise<void>; error?: string };

function keyFor(item: SavedIncident) { return item.id; }

function buildReport(incidents: Inspection[], metrics: Metrics | null) {
  return [
    "FLOOD RESPONSE BOARD",
    `Observation date: ${metrics?.date || "Unavailable"} UTC`,
    ...incidents.map((item, index) => [
      `${index + 1}. ${severityFor(item).toUpperCase()} — ${item.address || item.admin1_name || "Location unavailable"}`,
      `   Coordinates: ${item.lat.toFixed(5)}, ${item.lon.toFixed(5)}`,
      `   Finding: ${floodClassLabel(item.class_name, item.class_value)}`,
      `   Map: https://www.google.com/maps?q=${item.lat},${item.lon}`,
    ].join("\n")),
    "Source: NASA MODIS flood observations. Verify conditions on the ground before dispatch.",
  ].join("\n");
}

export default function ResponderBoard({ incidents, metrics, onRemove, error }: Props) {
  const [copied, setCopied] = useState(false);
  if (!incidents.length) return null;
  const report = buildReport(incidents, metrics);
  async function copyReport() {
    await navigator.clipboard.writeText(report);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }
  function downloadReport() {
    const url = URL.createObjectURL(new Blob([report], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "flood-response-board.txt";
    link.click();
    URL.revokeObjectURL(url);
  }
  return (
    <section className="tool-card responder-board">
      <div className="eyebrow">RESPONSE BOARD</div>
      <div className="responder-heading"><h2>Saved locations</h2><strong>{incidents.length}</strong></div>
      <p>Prioritized observations ready to share with responders.</p>
      {error && <small className="sms-status">{error}</small>}
      <div className="incident-list">
        {incidents.map((item) => {
          const severity = severityFor(item);
          return <div className="incident-row" key={keyFor(item)}>
            <span className={`severity severity-${severity.toLowerCase()}`}>{severity}</span>
            <div><strong>{item.address || item.admin1_name || `${item.lat.toFixed(4)}, ${item.lon.toFixed(4)}`}</strong><small>{severityDescription(severity)} · {floodClassLabel(item.class_name, item.class_value)}</small></div>
            <button aria-label="Remove saved location" onClick={() => void onRemove(keyFor(item))}>×</button>
          </div>;
        })}
      </div>
      <div className="brief-actions"><button className="primary" onClick={() => void copyReport()}>{copied ? "Copied" : "Copy board"}</button><button className="brief-download" onClick={downloadReport}>Download .txt</button></div>
    </section>
  );
}
