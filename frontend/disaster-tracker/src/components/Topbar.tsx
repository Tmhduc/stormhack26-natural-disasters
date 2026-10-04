import type { Health } from "../api";

type Props = { connected: boolean; busy: boolean; health: Health | null };

export default function Topbar({ connected, busy, health }: Props) {
  return (
    <header className="topbar">
      <span>
        Workspace <span className="slash">/</span> <strong>Overview</strong>
      </span>
      <span className={`connection ${connected ? "online" : ""}`}>
        <i />
        {busy
          ? "Connecting…"
          : connected
          ? `Backend connected${health?.database.connected ? " · Tiger Data connected" : health?.database.configured ? " · Tiger Data unavailable" : ""}`
          : "Backend offline"}
      </span>
    </header>
  );
}
