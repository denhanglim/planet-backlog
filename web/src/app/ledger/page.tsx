import type { Metadata } from "next";
import { LedgerGrid, type LedgerCard } from "@/components/LedgerGrid";
import { candidates, displayName, fmt, sparklineSeries } from "@/lib/data";

export const metadata: Metadata = {
  title: "The Ledger — PLANET BACKLOG",
  description:
    "Every signal the pipeline detected, with its tribunal verdict, false-positive " +
    "score, and full diagnostics. Sortable, filterable, honest.",
};

export default function LedgerPage() {
  const cards: LedgerCard[] = candidates.map((c) => ({
    id: c.id,
    name: displayName(c),
    klass: c.class,
    status: c.panel?.status ?? null,
    verdict: c.crossmatch.verdict,
    periodDays: c.detection.period_days,
    periodLabel: fmt.period(c.detection.period_days),
    depthLabel: fmt.ppm(c.detection.depth_ppm),
    depthPpm: c.detection.depth_ppm,
    fpp: c.validation.fpp,
    sde: c.detection.sde ?? c.detection.snr,
    spark: sparklineSeries(c),
  }));

  return (
    <div className="mx-auto max-w-7xl px-5 pb-12 pt-32 md:px-8">
      <header className="mb-14 max-w-3xl">
        <p className="readout mb-4 text-[11px] uppercase tracking-[0.3em] text-phosphor">
          Candidate ledger
        </p>
        <h1 className="display text-4xl font-semibold leading-tight text-ink md:text-6xl">
          Every signal, every verdict
        </h1>
        <p className="mt-5 leading-relaxed text-ink-dim">
          Each detection faces six adversarial skeptics before it earns a place here.
          Calibration entries are known planets the pipeline was required to re-find —
          they prove the instrument works and are clearly labeled, never claimed as
          discoveries.
        </p>
      </header>
      <LedgerGrid cards={cards} />
    </div>
  );
}
