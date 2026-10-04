import type { TrendPoint } from "../api";
import { formatDay, formatNumber } from "../lib/format";

export default function FloodTrend({ points, error }: { points: TrendPoint[]; error: string }) {
  if (error || points.length < 2) return null;
  const max = Math.max(...points.map((point) => point.flooded_km2), 1);
  const latest = points[points.length - 1];
  const first = points[0];
  const overallChange = first.flooded_km2 === 0
    ? null
    : ((latest.flooded_km2 - first.flooded_km2) / first.flooded_km2) * 100;

  return (
    <section className="trend-panel" aria-label="Flood trend">
      <div className="trend-heading">
        <div>
          <div className="eyebrow">HISTORICAL VIEW</div>
          <h2>Flood trend</h2>
          <p>Estimated flooded area from the last {points.length} saved observations.</p>
        </div>
        <div className="trend-summary">
          <strong>{formatNumber(latest.flooded_km2)} km²</strong>
          <span>{overallChange === null ? "Latest saved observation" : `${overallChange >= 0 ? "+" : ""}${overallChange.toFixed(1)}% since first observation`}</span>
        </div>
      </div>
      <div className="trend-chart">
        {points.map((point) => (
          <div className="trend-column" key={point.date} title={`${formatDay(point.date)}: ${formatNumber(point.flooded_km2)} km²`}>
            <div className="trend-bar" style={{ height: `${Math.max(8, (point.flooded_km2 / max) * 100)}%` }} />
            <small>{formatDay(point.date)}</small>
          </div>
        ))}
      </div>
    </section>
  );
}
