import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { DiagnosticsGrid } from "@/components/DiagnosticsGrid";
import { FoldedPlot } from "@/components/FoldedPlot";
import { FppBlock } from "@/components/FppBlock";
import { ProvenanceBlock } from "@/components/ProvenanceBlock";
import { StatusChip } from "@/components/StatusChip";
import { Tribunal } from "@/components/Tribunal";
import { candidates, displayName, fmt, getCandidate } from "@/lib/data";

export function generateStaticParams() {
  return candidates.map((c) => ({ id: c.id }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const c = getCandidate(id);
  return {
    title: c
      ? `${c.id} · ${displayName(c)} — PLANET BACKLOG`
      : "Dossier — PLANET BACKLOG",
  };
}

const CLASS_LABEL: Record<string, string> = {
  periodic: "Periodic transit candidate",
  "single-transit": "Single-transit event — the kind period searches can't see",
  calibration: "Calibration target — a known planet the pipeline had to re-find",
  "injection-example": "Injected synthetic — a worked example, not a real signal",
};

export default async function DossierPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const c = getCandidate(id);
  if (!c) notFound();

  return (
    <article className="mx-auto max-w-7xl px-5 pb-12 pt-32 md:px-8">
      {/* header */}
      <header className="mb-12">
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/ledger"
            className="readout text-[11px] uppercase tracking-[0.2em] text-ink-faint hover:text-ink transition-colors"
          >
            ← Ledger
          </Link>
          <span className="readout text-[11px] text-ink-faint">/</span>
          <span className="readout text-[11px] uppercase tracking-[0.2em] text-ink-dim">
            {c.id}
          </span>
        </div>
        <div className="mt-6 flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="readout mb-3 text-[11px] uppercase tracking-[0.25em] text-phosphor">
              {CLASS_LABEL[c.class] ?? c.class}
            </p>
            <h1 className="display text-4xl font-semibold leading-tight text-ink md:text-6xl">
              {displayName(c)}
            </h1>
            <p className="readout mt-3 text-sm text-ink-dim">
              TIC {c.tic_id} · sector {c.sector} · T={fmt.num(c.star.tmag, 1)} mag
              {c.star.teff_k ? ` · ${Math.round(c.star.teff_k)} K` : ""}
              {c.star.radius_rsun ? ` · ${fmt.num(c.star.radius_rsun, 2)} R☉` : ""}
            </p>
          </div>
          <StatusChip status={c.panel?.status} />
        </div>

        {c.crossmatch.verdict !== "novel" && (
          <p className="mt-6 max-w-3xl border-l-2 border-amber pl-4 text-sm leading-relaxed text-ink-dim">
            <strong className="text-amber">Not a discovery.</strong>{" "}
            {c.crossmatch.confirmed
              ? `This is ${c.crossmatch.confirmed.pl_name}, a confirmed planet`
              : c.crossmatch.toi
                ? `This object is already TOI ${c.crossmatch.toi.toi}`
                : "This object appears in archival catalogs"}
            {c.class === "calibration"
              ? " — included deliberately as a calibration target. Re-finding it blind is part of the proof that the pipeline works."
              : "."}
          </p>
        )}
      </header>

      {/* key numbers strip */}
      <dl className="readout mb-12 grid gap-px bg-hairline text-center sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Period", fmt.period(c.detection.period_days)],
          ["Depth", fmt.ppm(c.detection.depth_ppm)],
          ["Duration", `${fmt.num(c.detection.duration_hours, 2)} h`],
          [
            c.detection.sde != null ? "SDE" : "SNR",
            fmt.num(c.detection.sde ?? c.detection.snr, 1),
          ],
        ].map(([k, v]) => (
          <div key={k} className="bg-void-2 px-6 py-5">
            <dt className="text-[10px] uppercase tracking-[0.2em] text-ink-faint">{k}</dt>
            <dd className="mt-1 text-3xl font-medium text-ink">{v}</dd>
          </div>
        ))}
      </dl>

      {/* the light curve */}
      <div className="mb-20">
        <FoldedPlot
          phase={c.series.phase}
          flux={c.series.flux}
          binnedPhase={c.series.binned_phase}
          binnedFlux={c.series.binned_flux}
          modelPhase={c.series.model_phase}
          modelFlux={c.series.model_flux}
          windowTime={c.series.window_time}
          windowFlux={c.series.window_flux}
          t0={c.series.t0_btjd ?? c.detection.t0_btjd}
          periodDays={c.detection.period_days}
        />
      </div>

      {/* diagnostics */}
      <div className="mb-20">
        <DiagnosticsGrid c={c} />
      </div>

      {/* tribunal */}
      <div className="mb-20">
        {c.panel ? (
          <Tribunal panel={c.panel} />
        ) : (
          <div className="panel p-8">
            <h2 className="display text-2xl font-semibold text-ink">The Tribunal</h2>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-ink-dim">
              This candidate has not yet faced the adversarial panel. Its diagnostics are
              computed, but no survival claim is made until six skeptics have tried to
              kill it.
            </p>
          </div>
        )}
      </div>

      {/* validation + provenance */}
      <div className="mb-20 grid gap-10 lg:grid-cols-2">
        <FppBlock v={c.validation} />
        <div className="space-y-4 text-sm leading-relaxed text-ink-dim">
          <h2 className="display text-xl font-semibold text-ink">Reading this honestly</h2>
          <p>
            This dossier is a <strong className="text-ink">candidate</strong>, not a
            confirmed planet. The score on the left ranks suspicion using only the
            computed diagnostics; it is transparent and reproducible, but it is not a
            Bayesian false-positive probability.
          </p>
          <p>
            Anything the pipeline could not compute is shown as &ldquo;not
            computed&rdquo; — missing evidence is reported, never papered over. The full
            machine-readable dossier is exportable below for independent verification.
          </p>
        </div>
      </div>

      <ProvenanceBlock c={c} />
    </article>
  );
}
