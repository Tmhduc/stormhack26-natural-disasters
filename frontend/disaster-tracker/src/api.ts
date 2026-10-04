export type Metrics = { flood_pixels: number; flooded_km2: number; bounds: number[]; product: string | null; tiles: string[]; date: string | null; last_updated: string | null }
export type Overlay = { png_url: string; bounds: number[] }
export type HistoryDay = { id: number; date: string; png_url: string; bounds: number[]; flood_pixels: number; flooded_km2: number; tiles: string[]; processed_at: string | null }
export type TrendPoint = { date: string; flood_pixels: number; flooded_km2: number; change_percent: number | null }
export type IncidentStatus = "open" | "verified" | "dispatched" | "resolved"
export type SavedIncident = Inspection & { id: string; observed_date: string | null; created_at: string; updated_at: string; severity: string; status: IncidentStatus; notes: string | null }
export type Hotspot = { name: string; incidents: number; high: number; latest_date: string | null }
export type Health = { status: string; database: { configured: boolean; connected: boolean; error?: string }; pipeline: { loaded: boolean; date: string | null; last_checked: string | null; last_processed: string | null }; integrations: { google_geocoding: boolean; telegram: boolean; twilio: boolean } }
export type Inspection = { inside: boolean; flooded: boolean | null; class_value?: number | null; class_name?: string | null; admin1_name?: string | null; admin1_type?: string | null; admin1_pcode?: string | null; address?: string | null; nearby_radius_km?: number | null; nearby_pixels?: number | null; nearby_flood_pixels?: number | null; nearby_class_counts?: Record<string, number>; lat: number; lon: number }
export type GeocodeResult = { address: string; lat: number; lon: number }
export type TelegramInfo = { configured: boolean; link: string | null; recipients: number }
export type Geometry = { type: string; coordinates: number[][][] | number[][][][] }
export type Boundary = { type: string; features: { geometry: Geometry }[] }
const API_BASE_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "")
export async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), method === 'POST' ? 180000 : 30000)
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { method, signal: controller.signal, ...(body ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}) })
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
