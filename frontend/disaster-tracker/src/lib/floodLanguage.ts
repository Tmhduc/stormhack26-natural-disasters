const FLOOD_CLASS_LABELS: Record<string, string> = {
  no_water: "No water detected",
  reference_water: "Usual water detected",
  recurring_flood: "Recurring flooding detected",
  unusual_flood: "Unusual flooding detected",
  insufficient_data: "Not enough satellite data",
};

export function floodClassLabel(className?: string | null, classValue?: number | null) {
  if (className && FLOOD_CLASS_LABELS[className]) return FLOOD_CLASS_LABELS[className];
  if (classValue === 0) return "No water detected";
  if (classValue === 1) return "Usual water detected";
  if (classValue === 2) return "Recurring flooding detected";
  if (classValue === 3) return "Unusual flooding detected";
  if (classValue === 255) return "Not enough satellite data";
  return "Classification unavailable";
}
