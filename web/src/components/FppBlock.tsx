import type { Validation } from "@/lib/contract";

/**
 * False-positive score with its full factor breakdown. The method label and the
 * "not a Bayesian probability" caveat are rendered verbatim — honesty is load-bearing.
 */
export function FppBlock({ v }: { v: Validation }) {
  const factors = [...v.factors].sort(
    (a, b) => Math.abs(b.contribution ?? 0) - Math.abs(a.contribution ?? 0)
  );
  const maxAbs = Math.max(...factors.map((f) => Math.abs(f.contribution ?? 0)), 0.01);

  return (
    <section aria-labelledby="fpp-heading" className="panel p-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 id="fpp-heading" className="display text-xl font-semibold text-ink">
            False-positive score
          </h2>
          <p className="readout mt-1 text-[10px] uppercase tracking-[0.2em] text-ink-faint">
            method: {v.method} {v.is_bayesian ? "" : "· not a Bayesian probability"}
          </p>
        </div>
        <p className="readout text-6xl font-medium text-ink">
          {v.fpp.toFixed(2)}
        </p>
      </div>

      <p className="mt-4 max-w-2xl text-xs leading-relaxed text-ink-dim">{v.note}</p>

      <ul className="mt-6 space-y-2.5">
        {factors.map((f) => {
          const val = f.contribution;
          const pct = val == null ? 0 : (Math.abs(val) / maxAbs) * 100;
          const positive = (val ?? 0) > 0;
          return (
            <li key={f.name} className="grid grid-cols-12 items-center gap-3">
              <span className="readout col-span-4 truncate text-[11px] text-ink-dim md:col-span-3">
                {f.name}
              </span>
              <span className="col-span-5 md:col-span-6">
                {val == null ? (
                  <span className="readout text-[10px] uppercase tracking-[0.15em] text-ink-faint">
                    not computed
                  </span>
                ) : (
                  <span
                    aria-hidden
                    className={`block h-1.5 ${positive ? "bg-amber/70" : "bg-phosphor/70"}`}
                    style={{ width: `${Math.max(pct, 2)}%` }}
                  />
                )}
              </span>
              <span
                className={`readout col-span-3 text-right text-[11px] ${
                  val == null ? "text-ink-faint" : positive ? "text-amber" : "text-phosphor"
                }`}
                title={f.detail}
              >
                {val == null ? "—" : val > 0 ? `+${val.toFixed(2)}` : val.toFixed(2)}
              </span>
            </li>
          );
        })}
      </ul>
      <p className="readout mt-4 text-[10px] uppercase tracking-[0.15em] text-ink-faint">
        amber raises suspicion · phosphor earns trust · formula published on the Method page
      </p>
    </section>
  );
}
