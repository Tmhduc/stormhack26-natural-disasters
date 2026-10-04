import type { LocationInspector } from "../hooks/useLocationInspector";
import { places } from "../lib/map";

type Props = {
  inspector: LocationInspector;
  disabled: boolean;
  notice?: string; // shown in place of the result, e.g. why inspecting is unavailable
};

function resultMessage({ inspection, error }: LocationInspector, notice?: string) {
  if (error) return error;
  if (!inspection)
    return (
      notice ||
      "Results will appear here. Satellite classification does not confirm conditions on the ground."
    );
  const where = `${inspection.lat.toFixed(4)}, ${inspection.lon.toFixed(4)}`;
  if (!inspection.inside) return `${where}: Outside raster coverage.`;
  const area = inspection.admin1_name ? `${inspection.admin1_name} · ` : "";
  const classDetails = inspection.class_name
    ? `Class ${inspection.class_value} (${inspection.class_name})`
    : "Unknown class";
  if (inspection.flooded === null) {
    return `${area}${where}: ${classDetails}; insufficient data. ${nearbyMessage(inspection)}`;
  }
  return inspection.flooded
    ? `${area}${where}: ${classDetails}; flood detected. ${nearbyMessage(inspection)}`
    : `${area}${where}: ${classDetails}; no unusual flood. ${nearbyMessage(inspection)}`;
}

function nearbyMessage(inspection: NonNullable<LocationInspector["inspection"]>) {
  if (inspection.nearby_radius_km == null || inspection.nearby_pixels == null) return "";
  return `${inspection.nearby_flood_pixels ?? 0} flood pixels within ${inspection.nearby_radius_km} km (${inspection.nearby_pixels} pixels checked).`;
}

export default function InspectPanel({ inspector, disabled, notice }: Props) {
  const { lat, lon, setLat, setLon, select, inspect, inspecting } = inspector;
  return (
    <section className="tool-card" id="inspect">
      <div className="eyebrow">EXPLORE THE DATA</div>
      <h2>Inspect a location</h2>
      <p>
        Select a city, click the map, or enter coordinates to query the flood
        raster.
      </p>
      <div className="city-buttons">
        {places.map((p) => (
          <button key={p.name} onClick={() => select(p.lat, p.lon)}>
            {p.name}
          </button>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void inspect();
        }}
      >
        <div className="coordinates">
          <label>
            Latitude
            <input
              type="number"
              required
              step="any"
              min="-90"
              max="90"
              value={lat}
              onChange={(e) => setLat(e.target.value)}
            />
          </label>
          <label>
            Longitude
            <input
              type="number"
              required
              step="any"
              min="-180"
              max="180"
              value={lon}
              onChange={(e) => setLon(e.target.value)}
            />
          </label>
        </div>
        <button className="primary full" disabled={inspecting || disabled}>
          {inspecting ? "Inspecting…" : "⌖ Inspect coordinates"}
        </button>
      </form>
      <div className="inspect-result" role="status">
        {resultMessage(inspector, notice)}
      </div>
    </section>
  );
}
