import type { LocationInspector } from "../hooks/useLocationInspector";
import { places } from "../lib/map";
import { floodClassLabel } from "../lib/floodLanguage";

const PIXEL_AREA_KM2 = 0.0625;

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
  const address = inspection.address ? `${inspection.address} · ` : "";
  const area = inspection.admin1_name ? `${inspection.admin1_name} · ` : "";
  const classDetails = floodClassLabel(inspection.class_name, inspection.class_value);
  if (inspection.flooded === null) {
    return `${address}${area}${where}: ${classDetails}. ${nearbyMessage(inspection)}`;
  }
  return inspection.flooded
    ? `${address}${area}${where}: ${classDetails}. ${nearbyMessage(inspection)}`
    : `${address}${area}${where}: ${classDetails}. No unusual flooding detected here. ${nearbyMessage(inspection)}`;
}

function nearbyMessage(inspection: NonNullable<LocationInspector["inspection"]>) {
  if (inspection.nearby_radius_km == null || inspection.nearby_pixels == null) return "";
  const flagged = inspection.nearby_flood_pixels ?? 0;
  const share = inspection.nearby_pixels ? Math.round((flagged / inspection.nearby_pixels) * 100) : 0;
  const area = (flagged * PIXEL_AREA_KM2).toFixed(1);
  return `Nearby satellite signal: about ${area} km² may be affected by flooding within ${inspection.nearby_radius_km} km (${share}% of the checked area).`;
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
            <small>{p.englishName}</small>
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
