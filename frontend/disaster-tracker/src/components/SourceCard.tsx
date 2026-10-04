export default function SourceCard() {
  return (
    <section className="source-card" id="source">
      <div>
        <div className="eyebrow">KNOW YOUR SOURCE</div>
        <h2>Observation, with context.</h2>
        <p>
          This prototype uses NASA MODIS satellite observations clipped to
          Vietnam. The backend combines the tiles needed to cover the country
          and compares each pixel with the product’s flood classification.
        </p>
      </div>
      <div className="source-details">
        <span>
          DATA PRODUCT<strong>MODIS flood observations</strong>
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
