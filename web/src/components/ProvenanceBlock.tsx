"use client";

import type { Candidate } from "@/lib/contract";

/** Archival crossmatch + full provenance trail + ExoFOP-style JSON export. */
export function ProvenanceBlock({ c }: { c: Candidate }) {
  const x = c.crossmatch;

  function exportJson() {
    const blob = new Blob([JSON.stringify(c, null, 1)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${c.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section aria-labelledby="prov-heading" className="grid gap-px bg-hairline lg:grid-cols-2">
      <div className="bg-void p-8">
        <h2 id="prov-heading" className="display text-xl font-semibold text-ink">
          Archival cross-checks
        </h2>
        <dl className="readout mt-5 space-y-3 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-ink-faint">Verdict</dt>
            <dd className={x.verdict === "novel" ? "text-phosphor" : "text-amber"}>
              {x.verdict}
            </dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-ink-faint">TOI list (ExoFOP)</dt>
            <dd className="text-right text-ink-dim">
              {x.toi
                ? `TOI ${x.toi.toi} · ${x.toi.tfopwg_disposition || "no disposition"} · period ${x.toi.period_match ? "matches" : "differs"}`
                : "no match"}
            </dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-ink-faint">Confirmed planets (NASA)</dt>
            <dd className="text-right text-ink-dim">
              {x.confirmed
                ? `${x.confirmed.pl_name} · period ${x.confirmed.period_match ? "matches" : "differs"}`
                : "no match"}
            </dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-ink-faint">Known EB catalogs</dt>
            <dd className="text-right text-ink-dim">
              {x.eb ? `matched (${x.eb.source})` : "no match"}
            </dd>
          </div>
        </dl>
        <div className="mt-5 border-t border-hairline pt-4">
          <h3 className="readout text-[10px] uppercase tracking-[0.2em] text-ink-faint">
            Catalog load status (missing catalogs weaken any novelty claim)
          </h3>
          <ul className="readout mt-2 space-y-1 text-[11px] text-ink-dim">
            {Object.entries(x.catalog_status ?? {}).map(([k, v]) => (
              <li key={k}>
                <span className="text-ink-faint">{k}:</span> {v}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="bg-void p-8">
        <h2 className="display text-xl font-semibold text-ink">Provenance</h2>
        <dl className="readout mt-5 space-y-3 text-sm">
          {[
            ["TIC ID", String(c.tic_id)],
            ["Sector", String(c.sector)],
            ["Data product", c.provenance.data_product],
            ["Pipeline", `${c.provenance.pipeline} v${c.provenance.pipeline_version}`],
            ["Contract", `v${c.provenance.contract_version}`],
            ["Generated", c.provenance.created_utc?.slice(0, 19).replace("T", " ") + " UTC"],
            ["Stellar params", c.star.stellar_source],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4">
              <dt className="text-ink-faint">{k}</dt>
              <dd className="text-right text-ink-dim">{v}</dd>
            </div>
          ))}
        </dl>
        <button
          type="button"
          onClick={exportJson}
          className="readout mt-6 cursor-pointer border border-phosphor/50 px-4 py-2.5 text-[11px] uppercase tracking-[0.2em] text-phosphor transition-colors hover:bg-phosphor/10"
        >
          Export full dossier (JSON) ↓
        </button>
        <p className="mt-3 text-xs leading-relaxed text-ink-faint">
          The export contains every diagnostic, every skeptic verdict, and the light-curve
          series — everything needed to reproduce or refute this candidate.
        </p>
      </div>
    </section>
  );
}
