type Props = { connected: boolean; busy: boolean };

export default function Topbar({ connected, busy }: Props) {
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
          ? "Backend connected"
          : "Backend offline"}
      </span>
    </header>
  );
}
