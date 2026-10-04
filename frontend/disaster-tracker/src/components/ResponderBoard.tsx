import { useState } from "react";
import type { IncidentStatus, Inspection, Metrics, SavedIncident } from "../api";
import { floodClassLabel } from "../lib/floodLanguage";
import { severityFor } from "../lib/triage";

type Props = { incidents: SavedIncident[]; metrics: Metrics | null; onRemove: (id: string) => void | Promise<void>; onUpdate: (id: string, changes: { status?: IncidentStatus; notes?: string }) => void | Promise<void>; error?: string };

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

export default function ResponderBoard({ incidents, metrics, onRemove, onUpdate, error }: Props) {
  const [copied, setCopied] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
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
          const expanded = expandedId === item.id;
          return <div className={`incident-row${expanded ? " is-expanded" : ""}`} key={keyFor(item)}>
            <div className="incident-summary">
              <span className={`severity severity-${severity.toLowerCase()}`}>{severity}</span>
              <div className="incident-summary-copy"><strong>{item.address || item.admin1_name || `${item.lat.toFixed(4)}, ${item.lon.toFixed(4)}`}</strong><small>{item.status} · {floodClassLabel(item.class_name, item.class_value)}</small></div>
              <button className="incident-expand" onClick={() => setExpandedId(expanded ? null : item.id)}>{expanded ? "Hide" : "Details"}</button>
            </div>
            {expanded && <div className="incident-details">
              <label className="incident-status">Status
                <select value={item.status} onChange={(event) => void onUpdate(item.id, { status: event.target.value as IncidentStatus })}>
                  <option value="open">Open</option>
                  <option value="verified">Verified</option>
                  <option value="dispatched">Dispatched</option>
                  <option value="resolved">Resolved</option>
                </select>
              </label>
              <label className="incident-notes">Responder notes
                <textarea defaultValue={item.notes || ""} placeholder="Add a short field note" onBlur={(event) => {
                  if (event.target.value !== (item.notes || "")) void onUpdate(item.id, { notes: event.target.value });
                }} />
              </label>
              <button className="incident-delete" onClick={() => void onRemove(keyFor(item))}>Remove location</button>
            </div>}
          </div>;
        })}
      </div>
      <div className="brief-actions"><button className="primary" onClick={() => void copyReport()}>{copied ? "Copied" : "Copy board"}</button><button className="brief-download" onClick={downloadReport}>Download .txt</button></div>
    </section>
  );
}
