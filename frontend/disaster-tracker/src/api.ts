export type Metrics = { flood_pixels: number; flooded_km2: number; bounds: number[]; product: string | null; tiles: string[]; date: string | null; last_updated: string | null }
export type Overlay = { png_url: string; bounds: number[] }
export type HistoryDay = { id: number; date: string; png_url: string; bounds: number[]; flood_pixels: number; flooded_km2: number; tiles: string[]; processed_at: string | null }
export type Inspection = { inside: boolean; flooded: boolean | null; class_value?: number | null; class_name?: string | null; nearby_radius_km?: number | null; nearby_pixels?: number | null; nearby_flood_pixels?: number | null; nearby_class_counts?: Record<string, number>; lat: number; lon: number }
export type Geometry = { type: string; coordinates: number[][][] | number[][][][] }
export type Boundary = { type: string; features: { geometry: Geometry }[] }
export async function request<T>(path: string, method = 'GET'): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), method === 'POST' ? 180000 : 30000)
  try {
    const response = await fetch(path, { method, signal: controller.signal })
    if (!response.ok) {
      const body = await response.json().catch(() => null)
      throw new Error(body?.detail || `Request failed (${response.status}). Check backend setup.`)
    }
    return await response.json() as T
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw new Error('Request timed out. The backend may still be processing; try reconnecting shortly.', { cause: error })
    throw error
  } finally { clearTimeout(timer) }
}
export function geographic(bounds: number[]) {
  return bounds.length === 4 && bounds.every(Number.isFinite) && bounds[0] >= -180 && bounds[2] <= 180 && bounds[1] >= -90 && bounds[3] <= 90 && bounds[2] > bounds[0] && bounds[3] > bounds[1]
}
