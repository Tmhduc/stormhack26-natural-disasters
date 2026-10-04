export const formatNumber = (value: number | undefined) =>
  value === undefined
    ? "—"
    : value.toLocaleString("en-US", { maximumFractionDigits: 2 });

/** "2026-10-04" → "Oct 4". The dates are UTC days, so format them in UTC too. */
export const formatDay = (isoDate: string) =>
  new Date(`${isoDate}T00:00:00Z`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
