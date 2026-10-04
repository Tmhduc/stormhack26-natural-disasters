import type { Metrics } from "../api";

type Props = { metrics: Metrics | null; busy: boolean; onReconnect: () => void };

export default function DataNotice({ metrics, busy, onReconnect }: Props) {
  const details = metrics
    ? [
        metrics.tiles.length && `Coverage: ${metrics.tiles.length} satellite areas`,
        metrics.date && `Observed: ${metrics.date} UTC`,
      ]
        .filter(Boolean)
        .join(" · ")
    : "Waiting for satellite data";
  return (
    <div className="notice" role="status">
      <span className="notice-icon">◉</span>
      <div>
        <strong>Vietnam flood monitoring</strong>
        <span>Satellite flood observations · {details}</span>
      </div>
      <button title="Read data already available on the backend; no NASA download requested." className="text-button" disabled={busy} onClick={onReconnect}>
        Reload dashboard ↗
      </button>
    </div>
  );
}
