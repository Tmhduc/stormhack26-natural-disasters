import type { Hotspot } from "../api";
import { formatDay } from "../lib/format";

export default function HotspotPanel({ hotspots, error }: { hotspots: Hotspot[]; error: string }) {
  if (error || !hotspots.length) return null;
  return (
    <section className="hotspot-panel" aria-label="Responder hotspots">
      <div className="eyebrow">RESPONDER PRIORITIES</div>
      <div className="hotspot-heading">
        <div>
          <h2>Saved incident hotspots</h2>
          <p>Areas with the most saved observations from the response team.</p>
        </div>
        <span>Based on saved points</span>
      </div>
      <div className="hotspot-list">
        {hotspots.map((hotspot) => (
          <div className="hotspot-row" key={hotspot.name}>
            <div><strong>{hotspot.name}</strong><small>Latest observation: {hotspot.latest_date ? formatDay(hotspot.latest_date) : "Unknown"}</small></div>
            <div className="hotspot-count"><strong>{hotspot.incidents}</strong><small>{hotspot.high} high priority</small></div>
          </div>
        ))}
      </div>
    </section>
  );
}
