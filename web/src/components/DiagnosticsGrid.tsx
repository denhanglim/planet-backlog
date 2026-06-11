import type { Candidate } from "@/lib/contract";
import { fmt } from "@/lib/data";

/** Precise diagnostic readouts. "not computed" is shown honestly, never hidden. */

function Cell({
  label,
  value,
  sub,
  tone = "neutral",
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "neutral" | "good" | "warn" | "missing";
}) {
  const valueCls =
    tone === "good"
      ? "text-phosphor"
      : tone === "warn"
        ? "text-amber"
        : tone === "missing"
          ? "text-ink-faint"
          : "text-ink";
  return (
    <div className="bg-void p-6">
      <dt className="readout text-[10px] uppercase tracking-[0.2em] text-ink-faint">{label}</dt>
      <dd>
        <span className={`readout mt-2 block text-2xl font-medium ${valueCls}`}>{value}</span>
        {sub && <span className="mt-1.5 block text-xs leading-relaxed text-ink-dim">{sub}</span>}
      </dd>
    </div>
  );
}

export function DiagnosticsGrid({ c }: { c: Candidate }) {
  const d = c.diagnostics;
  const det = c.detection;

  return (
    <section aria-labelledby="diag-heading">
      <h2
        id="diag-heading"
        className="display mb-8 text-3xl font-semibold text-ink md:text-4xl"
      >
        The computed evidence
      </h2>
      <dl className="grid gap-px bg-hairline sm:grid-cols-2 lg:grid-cols-4">
        <Cell
          label="Depth (full cadence)"
          value={d.depth.computed ? fmt.ppm(d.depth.depth_ppm) : "not computed"}
          sub={
            d.depth.computed
              ? `± ${fmt.ppm(d.depth.depth_err_ppm)} · ${d.depth.n_in_transit} points in transit`
              : d.depth.reason
          }
          tone={d.depth.computed ? "neutral" : "missing"}
        />
        <Cell
          label="Duration"
          value={`${fmt.num(det.duration_hours, 2)} h`}
          sub={`detected by ${det.method}`}
        />
        <Cell
          label="Detection strength"
          value={det.sde != null ? `SDE ${fmt.num(det.sde)}` : `SNR ${fmt.num(det.snr)}`}
          sub={
            det.sde != null
              ? `SNR ${fmt.num(det.snr)} · ${det.distinct_transits} distinct transits`
              : `matched-filter event`
          }
          tone="good"
        />
        <Cell
          label="Odd vs even depth"
          value={d.odd_even.computed ? fmt.sigma(d.odd_even.difference_sigma) : "n/a"}
          sub={
            d.odd_even.computed
              ? `odd ${fmt.ppm(d.odd_even.depth_odd_ppm)} / even ${fmt.ppm(d.odd_even.depth_even_ppm)} — a strong mismatch betrays an eclipsing binary`
              : d.odd_even.reason
          }
          tone={
            !d.odd_even.computed
              ? "missing"
              : (d.odd_even.difference_sigma ?? 0) > 3
                ? "warn"
                : "good"
          }
        />
        <Cell
          label="Secondary eclipse"
          value={d.secondary.computed ? fmt.sigma(d.secondary.significance_sigma) : "n/a"}
          sub={
            d.secondary.computed
              ? `${fmt.ppm(d.secondary.depth_ppm)} at phase 0.5 (${d.secondary.method}) — a significant dip there means a stellar companion`
              : d.secondary.reason
          }
          tone={
            !d.secondary.computed
              ? "missing"
              : (d.secondary.significance_sigma ?? 0) > 3
                ? "warn"
                : "good"
          }
        />
        <Cell
          label="Transit shape"
          value={
            d.shape.computed
              ? d.shape.v_shaped
                ? "V-shaped"
                : "flat-bottomed"
              : "not computed"
          }
          sub={
            d.shape.computed
              ? `flat-bottom fraction ${fmt.num(d.shape.shape_param, 2)} — V-shapes suggest grazing stellar eclipses`
              : d.shape.reason
          }
          tone={!d.shape.computed ? "missing" : d.shape.v_shaped ? "warn" : "good"}
        />
        <Cell
          label="Centroid shift in transit"
          value={d.centroid.computed ? fmt.sigma(d.centroid.significance_sigma) : "not computed"}
          sub={
            d.centroid.computed
              ? `${fmt.num(d.centroid.shift_arcsec, 2)}″ — a significant shift means the dip comes from a neighbor, not this star`
              : d.centroid.reason
          }
          tone={
            !d.centroid.computed
              ? "missing"
              : (d.centroid.significance_sigma ?? 0) > 3
                ? "warn"
                : "good"
          }
        />
        <Cell
          label="Neighbors in aperture"
          value={d.neighbors.computed ? String(d.neighbors.n_neighbors ?? 0) : "not computed"}
          sub={
            d.neighbors.computed
              ? `within ${d.neighbors.search_radius_arcsec}″ · combined neighbor flux ${(100 * (d.neighbors.total_neighbor_flux_fraction ?? 0)).toFixed(2)}% of target`
              : d.neighbors.reason
          }
          tone={
            !d.neighbors.computed
              ? "missing"
              : (d.neighbors.total_neighbor_flux_fraction ?? 0) > 0.2
                ? "warn"
                : "neutral"
          }
        />
        <Cell
          label="Quality-flagged cadences in transit"
          value={
            d.systematics.computed
              ? `${(100 * (d.systematics.frac_in_transit_quality_flagged ?? 0)).toFixed(1)}%`
              : "not computed"
          }
          sub={
            d.systematics.computed
              ? `momentum dumps: ${(100 * (d.systematics.frac_in_transit_momentum_dump ?? 0)).toFixed(1)}% · ${d.systematics.n_transits_near_gap_or_edge}/${d.systematics.n_transits_in_data} transits near a gap or edge`
              : d.systematics.reason
          }
          tone={
            !d.systematics.computed
              ? "missing"
              : (d.systematics.frac_in_transit_quality_flagged ?? 0) > 0.2
                ? "warn"
                : "good"
          }
        />
        <Cell
          label="Stellar rotation"
          value={
            d.rotation.computed
              ? `${fmt.num(d.rotation.rotation_period_days, 2)} d`
              : "not computed"
          }
          sub={
            d.rotation.computed
              ? d.rotation.period_matches_rotation_harmonic
                ? "candidate period MATCHES a rotation harmonic — spot-alias risk"
                : "candidate period is not a rotation harmonic"
              : d.rotation.reason
          }
          tone={
            !d.rotation.computed
              ? "missing"
              : d.rotation.period_matches_rotation_harmonic
                ? "warn"
                : "good"
          }
        />
        {c.bls_check && (
          <Cell
            label="Independent BLS check"
            value={c.bls_check.agrees_with_tls ? "agrees" : "DISAGREES"}
            sub={`BLS period ${fmt.period(c.bls_check.period_days)} vs TLS ${fmt.period(det.period_days)}`}
            tone={c.bls_check.agrees_with_tls ? "good" : "warn"}
          />
        )}
        {det.min_period_days != null && (
          <Cell
            label="Period lower bound"
            value={`> ${fmt.num(det.min_period_days, 1)} d`}
            sub="single event — the true period exceeds the distance from the event to the nearest data edge"
          />
        )}
      </dl>
    </section>
  );
}
