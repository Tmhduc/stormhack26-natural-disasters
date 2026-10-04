import { useEffect, useState } from "react";
import { request, type TelegramInfo } from "../api";

/** The bot's subscribe link and how many chats get alerts. Polled, because people subscribe from Telegram at any time. */
export function useTelegramAlerts() {
  const [info, setInfo] = useState<TelegramInfo | null>(null);
  useEffect(() => {
    let cancelled = false;
    const load = () => request<TelegramInfo>("/api/flood/alerts/telegram").then((result) => {
      if (!cancelled) setInfo(result);
    }).catch(() => {
      if (!cancelled) setInfo(null);
    });
    void load();
    const timer = window.setInterval(() => void load(), 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);
  return info;
}
