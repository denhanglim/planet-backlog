import type { Metadata } from "next";
import { Reveal } from "@/components/Reveal";
import { calibration, fmt, runMeta } from "@/lib/data";

export const metadata: Metadata = {
  title: "Trust — PLANET BACKLOG",
  description:
    "Known-planet recovery, injection-recovery completeness and reliability — the " +
    "calibration evidence behind every claim on this site.",
};

export default function TrustPage() {
  const rec = calibration.known_planet_recovery;
  const inj = calibration.injection_recovery;

  // group completeness cells by depth for the matrix
  const depths = inj
    ? [...new Set(inj.completeness_grid.map((c) => c.depth_ppm))].sort((a, b) => a - b)
    : [];
  const periodBins = inj
    ? [...new Set(inj.completeness_grid.map((c) => JSON.stringify(c.period_bin_days)))].map(
        (s) => JSON.parse(s) as [number, number]
      ).sort((a, b) => a[0] - b[0])
    : [];

  function cell(depth: number, bin: [number, number]) {
    return inj?.completeness_grid.find(
      (c) =>
        c.depth_ppm === depth &&
        c.period_bin_days[0] === bin[0] &&
        c.period_bin_days[1] === bin[1]
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-5 pb-12 pt-32 md:px-8">
      <header className="mb-16 max-w-3xl">
        <p className="readout mb-4 text-[11px] uppercase tracking-[0.3em] text-phosphor">
          The trust layer
        </p>
        <h1 className="display text-4xl font-semibold leading-tight text-ink md:text-6xl">
          Calibrate before you claim
        </h1>
        <p className="mt-5 leading-relaxed text-ink-dim">
          No candidate appears on this site unless the pipeline first proved — on the
          same data, with the same settings — that it re-finds planets we already know
          exist, and measured how often it recovers signals injected into real noise.
          This page is that proof, including the failures.
        </p>
      </header>

      {/* known-planet recovery */}
      <Reveal>
        <section aria-labelledby="recovery-heading" className="mb-20">
          <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
            <h2 id="recovery-heading" className="display text-2xl font-semibold text-ink md:text-3xl">
              Known-planet recovery
            </h2>
            <p className="readout text-5xl font-medium text-phosphor">
              {rec.recovered}/{rec.hosts_with_data_and_truth}
              <span className="ml-3 text-lg text-ink-dim">
                {rec.recovery_rate != null ? `(${fmt.pct(rec.recovery_rate)})` : ""}
              </span>
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <caption className="sr-only">
                Blind re-detection of confirmed planets, compared to published periods
              </caption>
              <thead>
                <tr className="readout border-b border-hairline-strong text-[10px] uppercase tracking-[0.2em] text-ink-faint">
                  <th scope="col" className="py-3 pr-4 font-medium">Host</th>
                  <th scope="col" className="py-3 pr-4 font-medium">Known planet</th>
                  <th scope="col" className="py-3 pr-4 font-medium">Published period</th>
                  <th scope="col" className="py-3 pr-4 font-medium">Pipeline found</th>
                  <th scope="col" className="py-3 pr-4 font-medium">SDE</th>
                  <th scope="col" className="py-3 font-medium">Result</th>
                </tr>
              </thead>
              <tbody className="readout text-sm">
                {rec.results.map((r) => (
                  <tr key={r.host} className="border-b border-hairline">
                    <td className="py-3.5 pr-4 text-ink">{r.host}</td>
                    <td className="py-3.5 pr-4 text-ink-dim">{r.truth?.pl_name ?? "—"}</td>
                    <td className="py-3.5 pr-4 text-ink-dim">
                      {r.truth ? `${r.truth.period_days.toFixed(5)} d` : "—"}
                    </td>
                    <td className="py-3.5 pr-4 text-ink-dim">
                      {r.detected_period_days != null
                        ? `${r.detected_period_days.toFixed(5)} d`
                        : "—"}
                    </td>
                    <td className="py-3.5 pr-4 text-ink-dim">{r.sde ?? "—"}</td>
                    <td className="py-3.5">
                      {r.recovered === true ? (
                        <span className="text-phosphor">recovered ✓</span>
                      ) : r.recovered === false ? (
                        <span className="text-amber">NOT RECOVERED — {r.status}</span>
                      ) : (
                        <span className="text-ink-faint">{r.status}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-4 max-w-3xl text-xs leading-relaxed text-ink-faint">
            Ground truth comes from the NASA Exoplanet Archive, matched by TIC ID — no
            hand-typed ephemerides anywhere in the pipeline. &ldquo;Recovered&rdquo;
            requires SDE ≥ {calibration.detection_threshold_sde} and a period match
            (including harmonics) within 2%.
          </p>
        </section>
      </Reveal>

      {/* injection-recovery */}
      <Reveal>
        <section aria-labelledby="injection-heading" className="mb-20">
          <h2 id="injection-heading" className="display mb-3 text-2xl font-semibold text-ink md:text-3xl">
            Injection–recovery
          </h2>
          {inj ? (
            <>
              <p className="max-w-3xl leading-relaxed text-ink-dim">
                {inj.n_injections} synthetic transits were injected into real TESS light
                curves (known planets and their secondary eclipses masked first) and
                searched blind.{" "}
                <strong className="text-ink">
                  Completeness {fmt.pct(inj.overall_completeness)}
                </strong>{" "}
                overall;{" "}
                <strong className="text-ink">reliability {fmt.pct(inj.reliability)}</strong>{" "}
                ({inj.reliability_definition}).
              </p>

              <div className="mt-10 overflow-x-auto">
                <table className="border-collapse">
                  <caption className="readout mb-3 text-left text-[10px] uppercase tracking-[0.2em] text-ink-faint">
                    Completeness by injected depth × orbital period
                  </caption>
                  <thead>
                    <tr className="readout text-[10px] uppercase tracking-[0.15em] text-ink-faint">
                      <th scope="col" className="p-2 text-left font-medium">depth ↓ / period →</th>
                      {periodBins.map((b) => (
                        <th key={b.join()} scope="col" className="p-2 text-center font-medium">
                          {b[0]}–{b[1]} d
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {depths.map((depth) => (
                      <tr key={depth}>
                        <th scope="row" className="readout p-2 text-left text-xs font-medium text-ink-dim">
                          {depth.toLocaleString("en-US")} ppm
                        </th>
                        {periodBins.map((b) => {
                          const c = cell(depth, b);
                          const v = c?.completeness ?? null;
                          return (
                            <td key={b.join()} className="p-1">
                              <div
                                className="readout flex h-16 w-24 flex-col items-center justify-center border border-hairline"
                                style={{
                                  background:
                                    v == null
                                      ? "transparent"
                                      : `rgba(94,242,200,${0.06 + 0.5 * v})`,
                                }}
                              >
                                <span className={`text-lg ${v != null && v >= 0.5 ? "text-void" : "text-ink"}`}>
                                  {v == null ? "—" : fmt.pct(v)}
                                </span>
                                <span className={`text-[9px] ${v != null && v >= 0.5 ? "text-void/70" : "text-ink-faint"}`}>
                                  {c ? `${c.n_recovered}/${c.n_injected}` : ""}
                                </span>
                              </div>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <dl className="readout mt-10 grid gap-px bg-hairline sm:grid-cols-3">
                {[
                  ["Null trials", `${inj.n_null_trials}`, `${inj.n_null_false_alarms} false alarms`],
                  ["Wrong-period detections", `${inj.n_wrong_period_detections}`, "injections found at an unrelated period"],
                  ["Reliability", fmt.pct(inj.reliability), "of threshold detections, fraction that were real"],
                ].map(([k, v, sub]) => (
                  <div key={k} className="bg-void p-6">
                    <dt className="text-[10px] uppercase tracking-[0.2em] text-ink-faint">{k}</dt>
                    <dd className="mt-2 text-3xl text-ink">{v}</dd>
                    <p className="mt-1 text-xs normal-case tracking-normal text-ink-dim">{sub}</p>
                  </div>
                ))}
              </dl>
            </>
          ) : (
            <p className="panel max-w-2xl p-6 text-sm text-ink-dim">
              Injection-recovery has not completed for this run. Until it does, no
              novel candidate is presented as trustworthy. This message is the honest
              state of the pipeline, not a placeholder.
            </p>
          )}
        </section>
      </Reveal>

      {/* scope + honesty */}
      <Reveal>
        <section className="panel max-w-3xl p-8">
          <h2 className="readout text-[11px] uppercase tracking-[0.3em] text-amber">
            Scope and honest limitations
          </h2>
          <ul className="mt-5 list-disc space-y-2.5 pl-5 text-sm leading-relaxed text-ink-dim">
            {calibration.scope_notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
            {runMeta.honesty_notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
          <p className="readout mt-6 text-[10px] uppercase tracking-[0.18em] text-ink-faint">
            pipeline v{calibration.pipeline_version} · calibration generated{" "}
            {calibration.generated_utc?.slice(0, 10)} · threshold SDE ≥{" "}
            {calibration.detection_threshold_sde}
          </p>
        </section>
      </Reveal>
    </div>
  );
}
