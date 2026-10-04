type Props = { busy: boolean; onRefresh: () => void };

export default function PageHeading({ busy, onRefresh }: Props) {
  return (
    <section className="heading">
      <div>
        <div className="eyebrow">NATURAL DISASTER TRACKER</div>
        <h1>A clearer view of the ground.</h1>
        <p>Monitor satellite-detected flooding across Vietnam.</p>
      </div>
      <button className="primary" disabled={busy} onClick={onRefresh}>
        {busy ? "Processing…" : "↻ Refresh satellite data"}
      </button>
    </section>
  );
}
