import type { ReactNode } from "react";
import type { Metrics } from "../api";
import { formatNumber } from "../lib/format";

type StatCardProps = {
  label: string;
  icon: string;
  value: ReactNode;
  caption: string;
  valueClassName?: string;
};

function StatCard({ label, icon, value, caption, valueClassName }: StatCardProps) {
  return (
    <article>
      <div className="stat-label">
        {label} <span>{icon}</span>
      </div>
      <h2 className={valueClassName}>{value}</h2>
      <p>{caption}</p>
    </article>
  );
}

export default function StatsGrid({ metrics }: { metrics: Metrics | null }) {
  const updated = metrics?.last_updated ? new Date(metrics.last_updated) : null;
  const tiles = metrics?.tiles.length ?? 0;
  return (
    <section className="stats" aria-label="Satellite metrics">
      <StatCard
        label="Area flagged for flooding"
        icon="≈"
        value={
          <>
            {formatNumber(metrics?.flooded_km2)} <small>km²</small>
          </>
        }
        caption="Estimated from satellite observations"
      />
      <StatCard
        label="Pixels flagged for flooding"
        icon="▦"
        value={formatNumber(metrics?.flood_pixels)}
        caption="Each pixel covers about 0.0625 km²"
      />
      <StatCard
        label="Satellite coverage"
        icon="◎"
        value={tiles ? `${tiles} ${tiles === 1 ? "tile" : "tiles"}` : "—"}
        caption="Satellite tiles covering Vietnam"
      />
      <StatCard
        label="Observation date"
        icon="◷"
        valueClassName="date-stat"
        value={
          updated
            ? updated.toLocaleDateString("en-US", { month: "short", day: "numeric" })
            : "—"
        }
        caption={updated ? `Updated ${updated.toLocaleTimeString()}` : "No satellite data yet"}
      />
    </section>
  );
}
