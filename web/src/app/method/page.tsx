import type { Metadata } from "next";
import Link from "next/link";
import { Reveal } from "@/components/Reveal";
import { runMeta } from "@/lib/data";

export const metadata: Metadata = {
  title: "Method — PLANET BACKLOG",
  description:
    "How the pipeline works: detect with classical algorithms, vet with an adversarial " +
    "AI tribunal, validate statistically, publish with provenance.",
};

const STEPS = [
  {
    n: "01",
    title: "Ingest",
    body:
      "TESS 2-minute-cadence photometry comes straight from NASA's MAST archive — the " +
      "same calibrated SPOC light curves professionals use. Every dossier records its " +
      "exact data product and sector.",
    detail: "lightkurve · SPOC PDCSAP flux",
  },
  {
    n: "02",
    title: "Detrend",
    body:
      "Stars flicker and spacecraft drift. A Savitzky–Golay filter removes slow trends " +
      "while preserving sharp transit shapes; flares are clipped from above only, " +
      "because transits live below the baseline. When an ephemeris is known, in-transit " +
      "points are masked so the filter can never erase the very signal we're hunting.",
    detail: "transit-safe flattening",
  },
  {
    n: "03",
    title: "Search",
    body:
      "Two independent algorithms hunt periodic dips: Box Least Squares (fast, box-shaped " +
      "model) and Transit Least Squares (realistic limb-darkened shape, better for small " +
      "planets). They must agree on the period — disagreement is itself a red flag the " +
      "skeptics see.",
    detail: `BLS + TLS · periods ${runMeta.search.period_min_days}–${runMeta.search.period_max_days} d · detection at SDE ≥ ${runMeta.search.sde_threshold}`,
  },
  {
    n: "04",
    title: "Hunt single transits",
    body:
      "A planet on a long orbit may transit once per sector — invisible to periodic " +
      "searches, which need two events. A matched filter slides transit-shaped templates " +
      "across the light curve hunting for convincing solitary dips. These are the " +
      "highest-novelty candidates and are labeled as their own class, period unconstrained.",
    detail: "matched filter · 2–16 h templates",
  },
  {
    n: "05",
    title: "Diagnose",
    body:
      "For every signal the pipeline computes the classic false-positive tells: odd-even " +
      "depth differences and secondary eclipses (eclipsing binaries), V-shapes (grazing " +
      "geometry), in-transit centroid shifts and aperture neighbors (blends), overlap with " +
      "spacecraft events (instrumental artifacts), and rotation-period aliases (starspots).",
    detail: "8 diagnostics per candidate",
  },
  {
    n: "06",
    title: "The Tribunal",
    body:
      "Six AI skeptics each receive the computed diagnostics — and nothing else — and try " +
      "to kill the candidate from one assigned angle: binary, blend, instrument, stellar, " +
      "alias, catalog. They cannot invent numbers; every claim must cite a computed field. " +
      "A judge synthesizes the verdicts, but survival is enforced by a mechanical rule in " +
      "code: any fatal kill is final. Skeptic disagreement flags the candidate for human review.",
    detail: "6 skeptics + 1 judge · structured verdicts",
  },
  {
    n: "07",
    title: "Validate & cross-check",
    body:
      "Each survivor gets a transparent false-positive score combining its diagnostic " +
      "z-scores (formula below), and is matched against the TOI list, the confirmed-planet " +
      "archive, and known false positives. Known objects are never presented as discoveries.",
    detail: "heuristic-fpp-v1 · TOI + NASA archive dedup",
  },
  {
    n: "08",
    title: "Publish with provenance",
    body:
      "Every dossier traces to its TIC ID, sector, data product, pipeline version, every " +
      "diagnostic, and every skeptic's full reasoning — exportable as machine-readable " +
      "JSON so anyone can verify or refute it. Candidates, never confirmed planets: " +
      "confirmation requires radial-velocity follow-up by real telescopes.",
    detail: "full JSON export per candidate",
  },
];

export default function MethodPage() {
  return (
    <div className="mx-auto max-w-7xl px-5 pb-12 pt-32 md:px-8">
      <header className="mb-20 max-w-3xl">
        <p className="readout mb-4 text-[11px] uppercase tracking-[0.3em] text-phosphor">
          The method
        </p>
        <h1 className="display text-4xl font-semibold leading-tight text-ink md:text-6xl">
          Detect classically.
          <br />
          Vet adversarially.
          <br />
          <span className="text-ink-dim">Claim honestly.</span>
        </h1>
        <p className="mt-6 leading-relaxed text-ink-dim">
          The division of labor is absolute: deterministic code computes every number;
          the AI layer only argues about numbers that already exist. If a quantity
          wasn&apos;t computed, it doesn&apos;t exist anywhere in this system.
        </p>
      </header>

      <ol className="relative space-y-0">
        {STEPS.map((s, i) => (
          <Reveal key={s.n} delay={0.04 * (i % 3)}>
            <li className="rule grid gap-6 py-12 md:grid-cols-12">
              <div className="md:col-span-2">
                <span className="display text-5xl font-semibold text-void-3 [-webkit-text-stroke:1px_var(--hairline-strong)] md:text-6xl">
                  {s.n}
                </span>
              </div>
              <div className="md:col-span-6">
                <h2 className="display text-2xl font-semibold text-ink">{s.title}</h2>
                <p className="mt-3 max-w-xl leading-relaxed text-ink-dim">{s.body}</p>
              </div>
              <div className="md:col-span-4 md:text-right">
                <span className="readout text-[11px] uppercase tracking-[0.18em] text-phosphor">
                  {s.detail}
                </span>
              </div>
            </li>
          </Reveal>
        ))}
      </ol>

      {/* the FPP formula, in full */}
      <Reveal>
        <section aria-labelledby="formula-heading" className="panel scanlines mt-20 p-8 md:p-10">
          <h2 id="formula-heading" className="display text-2xl font-semibold text-ink">
            The false-positive score, in full
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-ink-dim">
            Published verbatim because trust requires it. This is a transparent,
            reproducible ranking score in [0,1] built from the computed diagnostics —
            <strong className="text-ink"> not</strong> a Bayesian probability. Missing
            diagnostics contribute zero risk but are listed as &ldquo;not computed&rdquo;
            on every dossier.
          </p>
          <pre className="readout mt-6 overflow-x-auto border border-hairline bg-void p-6 text-xs leading-relaxed text-ink-dim">
{`risk = 1.2 * clip(max(odd_even_sigma - 1, 0) / 3, 0, 2)   # eclipsing-binary tell
     + 1.2 * clip(max(secondary_sigma - 1, 0) / 3, 0, 2)  # eclipsing-binary tell
     + 0.8 * (1 if v_shaped else 0)                       # grazing geometry
     + 1.0 * clip(centroid_sigma / 3, 0, 2)               # blend tell
     + 0.8 * clip(neighbor_flux_fraction / 0.2, 0, 2)     # crowding prior
     + 0.6 * (1 if depth_ppm > 30000 else 0)              # too deep for a planet
     + 0.8 * (1 if rotation_harmonic_match else 0)        # starspot alias
     + 0.6 * clip(frac_quality_flagged / 0.3, 0, 2)       # systematics overlap

trust = clip((sde - 7) / 8, 0, 1.5)                       # detection strength

fpp   = sigmoid(risk - trust - 1.0)`}
          </pre>
        </section>
      </Reveal>

      <Reveal>
        <div className="mt-16 flex flex-wrap gap-6">
          <Link
            href="/trust"
            className="readout border border-phosphor/50 px-5 py-3 text-[11px] uppercase tracking-[0.2em] text-phosphor transition-colors hover:bg-phosphor/10"
          >
            See the calibration proof →
          </Link>
          <Link
            href="/ledger"
            className="readout border border-hairline px-5 py-3 text-[11px] uppercase tracking-[0.2em] text-ink-dim transition-colors hover:border-hairline-strong hover:text-ink"
          >
            Browse the ledger →
          </Link>
        </div>
      </Reveal>
    </div>
  );
}
