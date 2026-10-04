import { useEffect, useState } from "react";
import { request, type Health } from "../api";

/** Poll safe deployment diagnostics for the topbar status indicator. */
export function useSystemHealth() {
  const [health, setHealth] = useState<Health | null>(null);
  useEffect(() => {
    let cancelled = false;
    const load = () => request<Health>("/api/health").then((result) => {
      if (!cancelled) setHealth(result);
    }).catch(() => {
      if (!cancelled) setHealth(null);
    });
    void load();
    const timer = window.setInterval(() => void load(), 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);
  return health;
}
