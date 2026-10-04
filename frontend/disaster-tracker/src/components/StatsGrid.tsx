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
        label="Detected flooded area"
        icon="≈"
        value={
          <>
            {formatNumber(metrics?.flooded_km2)} <small>km²</small>
          </>
        }
        caption="Estimated from classified pixels"
      />
      <StatCard
        label="Flood-classified pixels"
        icon="▦"
        value={formatNumber(metrics?.flood_pixels)}
        caption="0.0625 km² per pixel"
      />
      <StatCard
        label="Satellite coverage"
        icon="◎"
        value={tiles ? `${tiles} ${tiles === 1 ? "tile" : "tiles"}` : "—"}
        caption="MODIS tiles stitched · Vietnam clipping"
      />
      <StatCard
        label="Raster last downloaded"
        icon="◷"
        valueClassName="date-stat"
        value={
          updated
            ? updated.toLocaleDateString("en-US", { month: "short", day: "numeric" })
            : "—"
        }
        caption={updated ? updated.toLocaleTimeString() : "No raster available yet"}
      />
    </section>
  );
}
