import Link from "next/link";
import { Starfield } from "@/components/Starfield";
import { CountUp } from "@/components/CountUp";
import { Reveal } from "@/components/Reveal";
import { Sparkline } from "@/components/Sparkline";
import { StatusChip } from "@/components/StatusChip";
import { candidates, displayName, headlineStats, sparklineSeries, fmt } from "@/lib/data";

export default function Home() {
  const stats = headlineStats();
  const featured = [...candidates]
    .sort((a, b) => (b.detection.sde ?? 0) - (a.detection.sde ?? 0))
    .slice(0, 3);

  return (
    <>
      {/* ── HERO ─────────────────────────────────────────────────────── */}
      <section className="relative flex min-h-svh flex-col justify-end overflow-hidden">
        <Starfield className="absolute inset-0" />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-void"
        />
        <div className="relative mx-auto w-full max-w-7xl px-5 pb-16 pt-40 md:px-8 md:pb-24">
          <Reveal>
            <p className="readout mb-6 text-[11px] uppercase tracking-[0.3em] text-phosphor">
              An autonomous vetting instrument for TESS&apos;s blind spots
            </p>
          </Reveal>
          <Reveal delay={0.1}>
            <h1 className="display max-w-5xl text-[clamp(2.6rem,8vw,7rem)] font-semibold leading-[0.95] text-ink">
              Millions of stars.
              <br />
              <span className="text-ink-dim">Nobody&apos;s watching.</span>
            </h1>
          </Reveal>
          <Reveal delay={0.22}>
            <p className="mt-8 max-w-2xl text-base leading-relaxed text-ink-dim md:text-lg">
              TESS photographs the sky every few minutes. The curated targets get vetted;
              the rest fall through algorithmic cracks — especially planets that transit
              only once. This pipeline supplies the missing attention: classical
              detection, an adversarial AI tribunal, and full provenance for every claim.
              The output is <strong className="text-ink">vetted candidates</strong>, never
              &ldquo;confirmed planets.&rdquo;
            </p>
          </Reveal>

          <Reveal delay={0.34}>
            <dl className="rule mt-14 grid grid-cols-2 gap-x-6 gap-y-8 pt-8 md:grid-cols-4">
              {[
                { label: "Targets searched", value: stats.targetsSearched },
                { label: "Signals detected", value: stats.detections },
                { label: "Killed by the tribunal", value: stats.killed },
                { label: "Survived vetting", value: stats.survived },
              ].map((s) => (
                <div key={s.label}>
                  <dt className="readout text-[11px] uppercase tracking-[0.2em] text-ink-faint">
                    {s.label}
                  </dt>
                  <dd className="readout mt-2 text-4xl font-medium text-ink md:text-5xl">
                    <CountUp value={s.value} />
                  </dd>
                </div>
              ))}
            </dl>
          </Reveal>
        </div>
      </section>

      {/* ── THE GAP ──────────────────────────────────────────────────── */}
      <section className="rule">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-24 md:grid-cols-12 md:px-8">
          <Reveal className="md:col-span-4">
            <h2 className="display text-2xl font-semibold text-ink md:text-3xl">
              The backlog is real
            </h2>
          </Reveal>
          <div className="space-y-6 text-ink-dim md:col-span-7 md:col-start-6">
            <Reveal>
              <p className="leading-relaxed">
                NASA&apos;s pipelines vet a curated subset of TESS stars. Citizen
                scientists keep finding genuine planets in the leftovers — by eye. That
                isn&apos;t a data problem; it&apos;s an attention problem.
              </p>
            </Reveal>
            <Reveal delay={0.08}>
              <p className="leading-relaxed">
                Periodic searches need at least two transits. A long-period planet that
                transits once per sector is invisible to them by construction — the
                highest-value signals are the likeliest to be missed.
              </p>
            </Reveal>
            <Reveal delay={0.16}>
              <p className="leading-relaxed">
                This instrument automates the attention. Deterministic code computes
                every number; six AI skeptics then try to kill each candidate from six
                different angles. What survives is published here with its full paper
                trail — for the community to follow up, ExoFOP-style.
              </p>
            </Reveal>
          </div>
        </div>
      </section>

      {/* ── LEDGER PREVIEW ───────────────────────────────────────────── */}
      <section className="rule">
        <div className="mx-auto max-w-7xl px-5 py-24 md:px-8">
          <div className="mb-12 flex items-end justify-between">
            <Reveal>
              <h2 className="display text-2xl font-semibold text-ink md:text-3xl">
                The Ledger
              </h2>
            </Reveal>
            <Link
              href="/ledger"
              className="readout text-xs uppercase tracking-[0.2em] text-phosphor hover:text-ink transition-colors"
            >
              All candidates →
            </Link>
          </div>
          <div className="grid gap-px bg-hairline md:grid-cols-3">
            {featured.map((c, i) => (
              <Reveal key={c.id} delay={i * 0.08}>
                <Link
                  href={`/dossier/${c.id}/`}
                  className="group block h-full bg-void p-6 transition-colors hover:bg-void-2"
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className="readout text-xs text-ink-faint">{c.id}</span>
                    <StatusChip status={c.panel?.status} compact />
                  </div>
                  <p className="display mt-4 text-xl font-medium text-ink group-hover:text-phosphor transition-colors">
                    {displayName(c)}
                  </p>
                  <Sparkline points={sparklineSeries(c)} width={260} height={56} className="mt-4 w-full" />
                  <dl className="readout mt-4 grid grid-cols-3 gap-2 text-[11px] text-ink-dim">
                    <div>
                      <dt className="text-ink-faint">PERIOD</dt>
                      <dd>{fmt.period(c.detection.period_days)}</dd>
                    </div>
                    <div>
                      <dt className="text-ink-faint">DEPTH</dt>
                      <dd>{fmt.ppm(c.detection.depth_ppm)}</dd>
                    </div>
                    <div>
                      <dt className="text-ink-faint">FPP</dt>
                      <dd>{fmt.num(c.validation.fpp, 2)}</dd>
                    </div>
                  </dl>
                </Link>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── TRUST STRIP ──────────────────────────────────────────────── */}
      <section className="rule scanlines">
        <div className="mx-auto max-w-7xl px-5 py-24 md:px-8">
          <Reveal>
            <h2 className="display text-2xl font-semibold text-ink md:text-3xl">
              Why believe any of this?
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-4 max-w-2xl leading-relaxed text-ink-dim">
              Because the pipeline proves itself on planets we already know exist before
              it is allowed to claim anything new — and publishes its failure modes.
            </p>
          </Reveal>
          <Reveal delay={0.18}>
            <dl className="mt-12 grid gap-px bg-hairline sm:grid-cols-3">
              {[
                {
                  label: "Known planets re-found",
                  value: stats.recoveryRate != null ? fmt.pct(stats.recoveryRate) : "—",
                  sub: "confirmed planets, blind re-detection",
                },
                {
                  label: "Completeness",
                  value: stats.completeness != null ? fmt.pct(stats.completeness) : "—",
                  sub: "injected transits recovered",
                },
                {
                  label: "Reliability",
                  value: stats.reliability != null ? fmt.pct(stats.reliability) : "—",
                  sub: "detections that are real signals",
                },
              ].map((s) => (
                <div key={s.label} className="bg-void p-8">
                  <dt className="readout text-[11px] uppercase tracking-[0.2em] text-ink-faint">
                    {s.label}
                  </dt>
                  <dd className="readout mt-3 text-5xl font-medium text-phosphor">
                    {s.value}
                  </dd>
                  <p className="mt-2 text-xs text-ink-dim">{s.sub}</p>
                </div>
              ))}
            </dl>
          </Reveal>
          <Reveal delay={0.26}>
            <Link
              href="/trust"
              className="readout mt-8 inline-block text-xs uppercase tracking-[0.2em] text-phosphor hover:text-ink transition-colors"
            >
              Full calibration report →
            </Link>
          </Reveal>
        </div>
      </section>

      {/* ── HONESTY ──────────────────────────────────────────────────── */}
      <section className="rule">
        <div className="mx-auto max-w-7xl px-5 py-24 md:px-8">
          <Reveal>
            <div className="panel max-w-3xl p-8 md:p-10">
              <h2 className="readout text-[11px] uppercase tracking-[0.3em] text-amber">
                What this is not
              </h2>
              <ul className="mt-6 space-y-3 text-sm leading-relaxed text-ink-dim">
                <li>
                  <strong className="text-ink">Not confirmed planets.</strong> Candidates
                  only. Confirmation needs radial-velocity follow-up by real telescopes.
                </li>
                <li>
                  <strong className="text-ink">Not AI-generated numbers.</strong> The AI
                  panel never produces a quantity — it argues over numbers the
                  deterministic pipeline computed.
                </li>
                <li>
                  <strong className="text-ink">Not a discovery claim for known objects.</strong>{" "}
                  Every candidate is cross-checked against the TOI list, the
                  confirmed-planet archive, and known false positives.
                </li>
              </ul>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
