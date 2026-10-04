export default function Sidebar() {
  return (
    <aside className="sidebar">
      <a className="brand" href="#">
        <span className="brand-mark">◈</span>
        <span>
          terra<span className="brand-dot">.</span>
          <small>DISASTER INTELLIGENCE</small>
        </span>
      </a>
      <div className="nav-label">WORKSPACE</div>
      <a className="nav active" href="#overview">
        ◫ <span>Overview</span>
        <span className="nav-dot" />
      </a>
      <a className="nav" href="#map">
        ◎ <span>Flood map</span>
      </a>
      <a className="nav" href="#inspect">
        ⌖ <span>Location inspector</span>
      </a>
      <a className="nav" href="#source">
        ▤ <span>Data & coverage</span>
      </a>
      <div className="sidebar-bottom">
        <div className="region-badge">VN</div>
        <strong>Vietnam workspace</strong>
        <p>Satellite flood monitoring</p>
        <div className="prototype">STORMHACKS 2026 · PROTOTYPE</div>
      </div>
    </aside>
  );
}
