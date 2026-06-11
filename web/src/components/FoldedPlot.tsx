"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";

/**
 * Interactive light-curve plot. Two modes:
 *  - folded: raw phase points (faint) + binned curve + fitted model overlay
 *  - window: time-series around a single-transit event
 * Wheel/drag to zoom & pan on x; hover for exact readouts; double-click resets.
 * All series are verbatim pipeline output.
 */

export interface FoldedPlotProps {
  phase?: number[];
  flux?: number[];
  binnedPhase?: number[];
  binnedFlux?: number[];
  modelPhase?: number[];
  modelFlux?: number[];
  windowTime?: number[];
  windowFlux?: number[];
  t0?: number;
  periodDays?: number | null;
}

const M = { top: 16, right: 16, bottom: 44, left: 64 };

export function FoldedPlot(props: FoldedPlotProps) {
  const holderRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [width, setWidth] = useState(800);
  const height = 420;
  const [hover, setHover] = useState<{ x: number; y: number } | null>(null);

  const mode: "folded" | "window" =
    props.phase && props.phase.length ? "folded" : "window";

  const data = useMemo(() => {
    if (mode === "folded") {
      return {
        raw: (props.phase ?? []).map((p, i) => [p, props.flux![i]] as [number, number]),
        binned: (props.binnedPhase ?? []).map(
          (p, i) => [p, props.binnedFlux![i]] as [number, number]
        ),
        model: (props.modelPhase ?? []).map(
          (p, i) => [p, props.modelFlux![i]] as [number, number]
        ),
      };
    }
    const t0 = props.t0 ?? props.windowTime?.[0] ?? 0;
    return {
      raw: (props.windowTime ?? []).map(
        (t, i) => [(t - t0) * 24, props.windowFlux![i]] as [number, number]
      ),
      binned: [] as [number, number][],
      model: [] as [number, number][],
    };
  }, [props, mode]);

  useEffect(() => {
    if (!holderRef.current) return;
    const ro = new ResizeObserver(([e]) => setWidth(Math.max(e.contentRect.width, 320)));
    ro.observe(holderRef.current);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const svgEl = svgRef.current;
    if (!svgEl) return;
    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();
    if (!data.raw.length) return;

    const innerW = width - M.left - M.right;
    const innerH = height - M.top - M.bottom;

    const xExtent = d3.extent(data.raw, (d) => d[0]) as [number, number];
    const yExtent = d3.extent(data.raw, (d) => d[1]) as [number, number];
    const yPad = (yExtent[1] - yExtent[0]) * 0.08 || 1e-5;

    const x0 = d3.scaleLinear().domain(xExtent).range([0, innerW]);
    const y = d3
      .scaleLinear()
      .domain([yExtent[0] - yPad, yExtent[1] + yPad])
      .range([innerH, 0]);

    const g = svg
      .append("g")
      .attr("transform", `translate(${M.left},${M.top})`);

    const defs = svg.append("defs");
    defs
      .append("clipPath")
      .attr("id", "plot-clip")
      .append("rect")
      .attr("width", innerW)
      .attr("height", innerH);

    const xAxisG = g
      .append("g")
      .attr("transform", `translate(0,${innerH})`)
      .attr("class", "x-axis");
    const yAxisG = g.append("g").attr("class", "y-axis");

    const plotArea = g.append("g").attr("clip-path", "url(#plot-clip)");

    const rawSel = plotArea
      .append("g")
      .selectAll("circle")
      .data(data.raw)
      .join("circle")
      .attr("r", 1.3)
      .attr("fill", "rgba(232,236,233,0.28)");

    const binnedSel = plotArea
      .append("g")
      .selectAll("circle")
      .data(data.binned)
      .join("circle")
      .attr("r", 2.8)
      .attr("fill", "#e8ece9");

    const modelPath = plotArea
      .append("path")
      .datum(data.model)
      .attr("fill", "none")
      .attr("stroke", "#5ef2c8")
      .attr("stroke-width", 1.8)
      .attr("opacity", 0.95);

    const crosshair = g
      .append("line")
      .attr("y1", 0)
      .attr("y2", innerH)
      .attr("stroke", "rgba(94,242,200,0.35)")
      .attr("stroke-dasharray", "3 3")
      .style("display", "none");

    function render(x: d3.ScaleLinear<number, number>) {
      const fmtX = mode === "folded" ? d3.format(".3f") : (v: d3.NumberValue) => `${d3.format(".1f")(v)}h`;
      xAxisG
        .call(d3.axisBottom(x).ticks(7).tickFormat(fmtX as never))
        .call((sel) => {
          sel.selectAll("text").attr("fill", "#a8b3ac").style("font-family", "var(--font-plex-mono)");
          sel.selectAll("line,path").attr("stroke", "rgba(232,236,233,0.22)");
        });
      yAxisG
        .call(
          d3
            .axisLeft(y)
            .ticks(6)
            .tickFormat((v) => d3.format(".4f")(v))
        )
        .call((sel) => {
          sel.selectAll("text").attr("fill", "#a8b3ac").style("font-family", "var(--font-plex-mono)");
          sel.selectAll("line,path").attr("stroke", "rgba(232,236,233,0.22)");
        });

      rawSel.attr("cx", (d) => x(d[0])).attr("cy", (d) => y(d[1]));
      binnedSel.attr("cx", (d) => x(d[0])).attr("cy", (d) => y(d[1]));
      modelPath.attr(
        "d",
        d3
          .line<[number, number]>()
          .x((d) => x(d[0]))
          .y((d) => y(d[1]))
      );
    }

    render(x0);

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 40])
      .translateExtent([
        [0, 0],
        [innerW, innerH],
      ])
      .extent([
        [0, 0],
        [innerW, innerH],
      ])
      .on("zoom", (ev) => {
        const zx = ev.transform.rescaleX(x0);
        render(zx);
        currentX = zx;
      });

    let currentX = x0;
    svg.call(zoom).on("dblclick.zoom", () => {
      svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity);
    });

    const ref = data.binned.length ? data.binned : data.raw;
    svg
      .on("pointermove", (ev) => {
        const [mx] = d3.pointer(ev, g.node());
        const px = currentX.invert(mx);
        const nearest = ref.reduce((a, b) =>
          Math.abs(b[0] - px) < Math.abs(a[0] - px) ? b : a
        );
        crosshair
          .style("display", null)
          .attr("x1", currentX(nearest[0]))
          .attr("x2", currentX(nearest[0]));
        setHover({ x: nearest[0], y: nearest[1] });
      })
      .on("pointerleave", () => {
        crosshair.style("display", "none");
        setHover(null);
      });
  }, [data, width, mode]);

  const depthPpm = hover ? Math.round((1 - hover.y) * 1e6) : null;

  return (
    <figure ref={holderRef} className="panel relative p-4">
      <figcaption className="mb-2 flex flex-wrap items-center justify-between gap-2 px-2">
        <span className="readout text-[11px] uppercase tracking-[0.2em] text-ink-faint">
          {mode === "folded"
            ? `Folded light curve · P = ${props.periodDays?.toFixed(5) ?? "—"} d`
            : "Event window · hours from event center"}
        </span>
        <span className="readout text-[11px] text-ink-dim">
          {hover
            ? `${mode === "folded" ? "phase" : "t"} ${hover.x.toFixed(4)} · flux ${hover.y.toFixed(5)} · ${depthPpm! >= 0 ? `${depthPpm} ppm below baseline` : "above baseline"}`
            : "hover for readout · scroll to zoom · double-click to reset"}
        </span>
      </figcaption>
      <svg
        ref={svgRef}
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={
          mode === "folded"
            ? "Folded light curve with binned points and fitted transit model"
            : "Light curve around the single transit event"
        }
        className="cursor-crosshair touch-none select-none"
      />
      <div className="mt-2 flex gap-5 px-2">
        <LegendSwatch color="rgba(232,236,233,0.35)" label="2-min cadence" dot />
        {data.binned.length > 0 && <LegendSwatch color="#e8ece9" label="binned" dot />}
        {data.model.length > 0 && <LegendSwatch color="#5ef2c8" label="TLS model" />}
      </div>
    </figure>
  );
}

function LegendSwatch({ color, label, dot }: { color: string; label: string; dot?: boolean }) {
  return (
    <span className="readout flex items-center gap-1.5 text-[10px] uppercase tracking-[0.15em] text-ink-faint">
      <span
        aria-hidden
        style={{ background: color }}
        className={dot ? "h-1.5 w-1.5 rounded-full" : "h-0.5 w-4"}
      />
      {label}
    </span>
  );
}
