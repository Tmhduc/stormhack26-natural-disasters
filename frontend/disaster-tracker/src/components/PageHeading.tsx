import "./PageHeading.css";

type Props = { busy: boolean; onRefresh: () => void; telegramLink: string | null };

export default function PageHeading({ busy, onRefresh, telegramLink }: Props) {
  return (
    <section className="heading">
      <div>
        <div className="eyebrow">NATURAL DISASTER TRACKER</div>
        <h1>A clearer view of the ground.</h1>
        <p>Monitor satellite-detected flooding across Vietnam.</p>
      </div>
      <div className="heading-actions">
        {telegramLink && (
          <a
            className="telegram-link"
            href={telegramLink}
            target="_blank"
            rel="noreferrer"
            title="Open the DisTrack bot in Telegram and tap Start to get flood alerts. Send /stop to unsubscribe."
          >
            Get Telegram alerts
          </a>
        )}
        <button title="Ask the backend to check NASA, download new imagery if available and rebuild flood data." className="primary" disabled={busy} onClick={onRefresh}>
          {busy ? "Processing…" : "↻ Refresh satellite data"}
        </button>
      </div>
    </section>
  );
}
