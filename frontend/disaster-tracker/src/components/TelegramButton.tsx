import { useState } from "react";
import { request, type Inspection } from "../api";
import { floodClassLabel } from "../lib/floodLanguage";

type Props = {
  inspection: Inspection | null;
  observedDate: string | null;
  recipients: number | null; // chats subscribed to the bot; null while unknown
};

const subscribers = (n: number) => `${n} ${n === 1 ? "subscriber" : "subscribers"}`;

function buildMessage(inspection: Inspection, observedDate: string | null) {
  const label = floodClassLabel(inspection.class_name, inspection.class_value);
  const address = inspection.address || inspection.admin1_name || "Address unavailable";
  const nearbyArea = inspection.nearby_flood_pixels != null
    ? `${(inspection.nearby_flood_pixels * 0.0625).toFixed(1)} km² may be affected within ${inspection.nearby_radius_km ?? 2} km`
    : "Nearby area estimate unavailable";
  return [
    "FLOOD OBSERVATION BRIEF",
    `Location: ${address}`,
    `Coordinates: ${inspection.lat.toFixed(5)}, ${inspection.lon.toFixed(5)}`,
    `Satellite finding: ${label}`,
    `Nearby signal: ${nearbyArea}`,
    `Observation date: ${observedDate || "Unavailable"} UTC`,
    `Map: https://www.google.com/maps?q=${inspection.lat},${inspection.lon}`,
    "Source: NASA MODIS flood observations. This is a satellite signal, not a ground-verified report.",
  ].join("\n");
}

/** Sends the inspected location to everyone subscribed to the Telegram bot. Hidden until a point inside coverage is inspected. */
export default function TelegramButton({ inspection, observedDate, recipients }: Props) {
  const [status, setStatus] = useState("");
  const [sentFor, setSentFor] = useState<Inspection | null>(null);
  if (!inspection || !inspection.inside) return null;
  const selected = inspection;
  // A status message belongs to the inspection it was sent for.
  const shownStatus = sentFor === selected ? status : "";

  async function send() {
    setSentFor(selected);
    setStatus("Sending…");
    try {
      const result = await request<{ recipients: number }>("/api/flood/alerts/telegram", "POST", {
        body: buildMessage(selected, observedDate),
      });
      setStatus(`Sent to ${subscribers(result.recipients)}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Telegram message could not be sent.");
    }
  }

  const caption =
    recipients === null
      ? null
      : recipients === 0
      ? "No subscribers yet. Use “Get Telegram alerts” at the top to subscribe."
      : `Goes to ${subscribers(recipients)}`;
  return (
    <>
      <button
        className="telegram-button full"
        disabled={shownStatus === "Sending…" || recipients === 0}
        onClick={() => void send()}
      >
        {shownStatus === "Sending…" ? "Sending…" : "Send to Telegram"}
      </button>
      {(shownStatus || caption) && (
        <small className="sms-status" role="status">{shownStatus || caption}</small>
      )}
    </>
  );
}
