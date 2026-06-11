/**
 * Inline SVG folded-light-curve sparkline. Pure render of real pipeline series —
 * no smoothing or invention; gaps stay gaps.
 */
export function Sparkline({
  points,
  width = 160,
  height = 44,
  className = "",
}: {
  points: { x: number; y: number }[] | null;
  width?: number;
  height?: number;
  className?: string;
}) {
  if (!points || points.length < 4) {
    return (
      <div
        className={`readout flex items-center justify-center text-[10px] text-ink-faint ${className}`}
        style={{ width, height }}
      >
        no series
      </div>
    );
  }
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMin = Math.min(...ys), yMax = Math.max(...ys);
  const pad = 3;
  const yPad = (yMax - yMin || 1e-6) * 0.1;
  const sx = (x: number) =>
    pad + ((x - xMin) / (xMax - xMin || 1)) * (width - 2 * pad);
  const sy = (y: number) =>
    height - pad - ((y - (yMin - yPad)) / (yMax + yPad - (yMin - yPad))) * (height - 2 * pad);

  const d = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`)
    .join("");

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="Folded light curve sparkline"
      className={className}
    >
      <path d={d} fill="none" stroke="var(--phosphor)" strokeWidth="1.2" opacity="0.9" />
    </svg>
  );
}
