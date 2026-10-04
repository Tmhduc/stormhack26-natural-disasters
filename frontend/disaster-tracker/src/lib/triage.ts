import type { Inspection } from "../api";

export type Severity = "High" | "Moderate" | "Watch";

export function severityFor(inspection: Inspection): Severity {
  if (!inspection.inside || inspection.flooded !== true) return "Watch";
  const share = inspection.nearby_pixels
    ? (inspection.nearby_flood_pixels ?? 0) / inspection.nearby_pixels
    : 0;
  if (share >= 0.3 || inspection.class_value === 3) return "High";
  if (share >= 0.1) return "Moderate";
  return "Watch";
}

export function severityDescription(severity: Severity) {
  return severity === "High"
    ? "Prioritize verification and response"
    : severity === "Moderate"
      ? "Review and monitor closely"
      : "Keep under observation";
}
