import type { Boundary } from "../api";

// The map is a 600×640 SVG with a plain lat/lon projection:
// 54 px per degree of longitude from 101°E, 38 px per degree of latitude from 25°N.
export const MAP_WIDTH = 600;
export const MAP_HEIGHT = 640;
export const lonToX = (lon: number) => (lon - 101) * 54;
export const latToY = (lat: number) => (25 - lat) * 38;
export const xToLon = (x: number) => 101 + x / 54;
export const yToLat = (y: number) => 25 - y / 38;

export const places = [
  { name: "Hà Nội", englishName: "Hanoi", lat: 21.0285, lon: 105.8542 },
  { name: "Đà Nẵng", englishName: "Da Nang", lat: 16.0544, lon: 108.2022 },
  { name: "TP. Hồ Chí Minh", englishName: "Ho Chi Minh City", lat: 10.8231, lon: 106.6297 },
];

/** One SVG path per polygon in the boundary GeoJSON. */
export function boundaryPaths(boundary: Boundary | null): string[] {
  return (
    boundary?.features.flatMap((f) => {
      const g = f.geometry;
      if (!g || !["Polygon", "MultiPolygon"].includes(g.type)) return [];
      const polygons =
        g.type === "Polygon"
          ? [g.coordinates as number[][][]]
          : (g.coordinates as number[][][][]);
      return polygons.map((p) =>
        p
          .map(
            (ring) =>
              ring
                .map(([a, b], i) => `${i ? "L" : "M"}${lonToX(a)},${latToY(b)}`)
                .join(" ") + "Z"
          )
          .join(" ")
      );
    }) || []
  );
}
