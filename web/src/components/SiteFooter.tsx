import { runMeta } from "@/lib/data";

export function SiteFooter() {
  return (
    <footer className="rule mt-24">
      <div className="mx-auto max-w-7xl px-5 py-10 md:px-8">
        <p className="max-w-3xl text-sm leading-relaxed text-ink-dim">
          Everything on this site is a <strong className="text-ink">candidate</strong>,
          not a confirmed planet. Confirmation requires radial-velocity follow-up.
          Every number is computed by the open pipeline; the AI tribunal only
          interprets. Honest failures are listed on the Trust page.
        </p>
        <p className="readout mt-6 text-[11px] uppercase tracking-[0.18em] text-ink-faint">
          pipeline v{runMeta.pipeline_version} · contract v{runMeta.contract_version} ·
          data: TESS SPOC 2-min PDCSAP via MAST · generated{" "}
          {runMeta.generated_utc?.slice(0, 10)}
        </p>
      </div>
    </footer>
  );
}
