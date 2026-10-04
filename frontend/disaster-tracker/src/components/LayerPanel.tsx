type Props = {
  showFlood: boolean;
  onShowFloodChange: (show: boolean) => void;
  opacity: number;
  onOpacityChange: (opacity: number) => void;
  hasOverlay: boolean;
  canPlot: boolean;
  imageError: boolean;
};

export default function LayerPanel({
  showFlood,
  onShowFloodChange,
  opacity,
  onOpacityChange,
  hasOverlay,
  canPlot,
  imageError,
}: Props) {
  return (
    <section className="tool-card">
      <h2>Map layers</h2>
      <label className="layer">
        <span>
          <i className="layer-color" />
          Flood classification<small>NASA satellite observation</small>
        </span>
        <input
          type="checkbox"
          checked={showFlood}
          onChange={(e) => onShowFloodChange(e.target.checked)}
        />
      </label>
      <label className="range-label">
        Layer opacity <strong>{opacity}%</strong>
        <input
          type="range"
          min="10"
          max="100"
          value={opacity}
          onChange={(e) => onOpacityChange(Number(e.target.value))}
        />
      </label>
      {hasOverlay && !canPlot && (
        <p className="warning">
          The API returned projected coordinates. Geographic overlay and
          inspection are paused until the raster bounds are converted to
          longitude/latitude.
        </p>
      )}
      {imageError && (
        <p className="warning">
          Overlay image could not load. Reconnect to retry.
        </p>
      )}
      <div className="layer-info">
        {canPlot
          ? "Overlay aligned to the bounds supplied by the API."
          : "Flood overlay appears when geographic raster data is available."}
      </div>
    </section>
  );
}
