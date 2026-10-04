import type { HistoryDay, Metrics } from "../api";
import { formatDay, formatNumber } from "../lib/format";
import "./HistoryTimeline.css";

type Props = {
  latest: Metrics | null;
  days: HistoryDay[];
  selectedId: number | null; // null = the latest, live data
  onSelect: (id: number | null) => void;
  error: string;
};

export default function HistoryTimeline({ latest, days, selectedId, onSelect, error }: Props) {
  // The newest saved day is usually the live one; show it once, as "Latest".
  const older = days.filter((d) => d.date !== latest?.date);
  return (
    <section className="history" aria-label="Flood history">
      <div className="history-head">
        <strong>Flood history</strong>
        <span>Daily snapshots saved by the pipeline</span>
      </div>
      {error ? (
        <p className="history-error">{error}</p>
      ) : (
        <div className="history-days">
          {latest && (
            <button
              className="history-day"
              aria-pressed={selectedId === null}
              onClick={() => onSelect(null)}
            >
              {latest.date ? `${formatDay(latest.date)} · Latest` : "Latest"}
              <small>{formatNumber(latest.flooded_km2)} km²</small>
            </button>
          )}
          {older.map((d) => (
            <button
              key={d.id}
              className="history-day"
              aria-pressed={selectedId === d.id}
              onClick={() => onSelect(d.id)}
            >
              {formatDay(d.date)}
              <small>{formatNumber(d.flooded_km2)} km²</small>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
