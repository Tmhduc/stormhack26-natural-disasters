export default function SourceCard() {
  return (
    <section className="source-card" id="source">
      <div>
        <div className="eyebrow">KNOW YOUR SOURCE</div>
        <h2>Observation, with context.</h2>
        <p>
          This prototype uses a single NASA MODIS tile clipped to Vietnam. The
          backend selects a fixed acquisition date; refreshing downloads that
          configured tile. Coverage is limited to the raster footprint.
        </p>
      </div>
      <div className="source-details">
        <span>
          DATA PRODUCT<strong>MCDWD L3 F2 NRT</strong>
        </span>
        <span>
          SUPPORTED HAZARD<strong>Flooding</strong>
        </span>
        <span>
          COMMUNITY REPORTING<strong>No report API in this backend</strong>
        </span>
      </div>
    </section>
  );
}
