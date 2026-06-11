"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { Panel, SkepticVerdict } from "@/lib/contract";

/**
 * The Tribunal — six skeptics, each rendered as a distinct voice with its
 * attempted kill, the evidence it weighed, and its verdict; then the judge.
 */

const SKEPTIC_META: Record<
  SkepticVerdict["skeptic"],
  { title: string; angle: string }
> = {
  binary: { title: "The Binary Skeptic", angle: "Is this a stellar eclipse, not a planet?" },
  blend: { title: "The Blend Skeptic", angle: "Does the dip even come from this star?" },
  instrument: { title: "The Instrument Skeptic", angle: "Is this the spacecraft, not the sky?" },
  stellar: { title: "The Stellar Skeptic", angle: "Is the star itself doing this?" },
  alias: { title: "The Alias Skeptic", angle: "Is the period even right?" },
  catalog: { title: "The Catalog Skeptic", angle: "Hasn't someone already found this?" },
};

const VERDICT_STAMP: Record<
  string,
  { label: string; cls: string }
> = {
  killed: { label: "KILL", cls: "border-amber text-amber" },
  failed_to_kill: { label: "FAILED TO KILL", cls: "border-phosphor text-phosphor" },
  inconclusive: { label: "INCONCLUSIVE", cls: "border-hairline-strong text-ink-dim" },
  error: { label: "DID NOT RUN", cls: "border-blood text-blood" },
};

const LETHALITY_LABEL: Record<string, string> = {
  fatal: "fatal",
  "serious-concern": "serious concern",
  "minor-concern": "minor concern",
  none: "no concern",
};

export function Tribunal({ panel }: { panel: Panel }) {
  const reduced = useReducedMotion();

  return (
    <section aria-labelledby="tribunal-heading">
      <div className="mb-10 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="readout mb-3 text-[11px] uppercase tracking-[0.3em] text-phosphor">
            The Tribunal
          </p>
          <h2 id="tribunal-heading" className="display text-3xl font-semibold text-ink md:text-4xl">
            Six skeptics. One job: kill it.
          </h2>
        </div>
        <p className="readout text-[11px] uppercase tracking-[0.15em] text-ink-faint">
          panel v{panel.panel_version} · model {panel.model} ·{" "}
          {panel.ran_utc?.slice(0, 10)}
        </p>
      </div>

      <ol className="grid gap-px bg-hairline md:grid-cols-2">
        {panel.skeptics.map((s, i) => {
          const meta = SKEPTIC_META[s.skeptic];
          const stamp = VERDICT_STAMP[s.error ? "error" : s.verdict ?? "error"];
          return (
            <motion.li
              key={s.skeptic}
              initial={reduced ? false : { opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: reduced ? 0 : i * 0.06 }}
              className="relative bg-void p-7"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="display text-lg font-medium text-ink">{meta.title}</h3>
                  <p className="mt-1 text-xs italic text-ink-faint">{meta.angle}</p>
                </div>
                <span
                  className={`readout shrink-0 -rotate-3 border-2 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${stamp.cls}`}
                >
                  {stamp.label}
                </span>
              </div>

              {s.error ? (
                <p className="mt-5 text-sm leading-relaxed text-blood">
                  This skeptic failed to run ({s.error}). Incomplete vetting — the
                  candidate cannot fully survive without it.
                </p>
              ) : (
                <>
                  <p className="readout mt-2 text-[10px] uppercase tracking-[0.18em] text-ink-faint">
                    lethality: {LETHALITY_LABEL[s.lethality ?? "none"]}
                  </p>
                  <p className="mt-4 text-sm leading-relaxed text-ink-dim">{s.reasoning}</p>
                  {s.evidence_cited && s.evidence_cited.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-1.5">
                      {s.evidence_cited.map((e) => (
                        <code
                          key={e}
                          className="readout border border-hairline bg-void-2 px-1.5 py-0.5 text-[10px] text-ink-faint"
                        >
                          {e}
                        </code>
                      ))}
                    </div>
                  )}
                  {s.what_would_change_my_mind && (
                    <p className="mt-4 border-l-2 border-hairline pl-3 text-xs leading-relaxed text-ink-faint">
                      Would change my mind: {s.what_would_change_my_mind}
                    </p>
                  )}
                </>
              )}
            </motion.li>
          );
        })}
      </ol>

      {/* Judge */}
      {(!panel.judge || panel.judge.error) && (
        <div className="mt-px border border-blood/30 bg-void-2 p-8">
          <h3 className="display text-xl font-semibold text-ink">The Judge&apos;s synthesis</h3>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-blood">
            The judge agent failed to run for this candidate
            {panel.judge?.error ? ` (${panel.judge.error})` : ""}. The survival status
            shown comes from the mechanical rule over the skeptic verdicts alone —
            reported honestly rather than papered over.
          </p>
        </div>
      )}
      {panel.judge && !panel.judge.error && (
        <motion.div
          initial={reduced ? false : { opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.6 }}
          className="scanlines mt-px border border-phosphor/25 bg-void-2 p-8 md:p-10"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="display text-xl font-semibold text-ink">The Judge&apos;s synthesis</h3>
            <p className="readout text-[11px] uppercase tracking-[0.18em] text-ink-faint">
              decision: <span className="text-ink">{panel.judge.decision}</span> ·
              confidence: <span className="text-ink">{panel.judge.confidence}</span>
            </p>
          </div>
          <p className="mt-5 max-w-3xl leading-relaxed text-ink">
            {panel.judge.summary_plain_english}
          </p>
          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <div>
              <h4 className="readout text-[10px] uppercase tracking-[0.2em] text-phosphor">
                Why it might be real
              </h4>
              <p className="mt-2 text-sm leading-relaxed text-ink-dim">
                {panel.judge.why_it_might_be_real}
              </p>
            </div>
            <div>
              <h4 className="readout text-[10px] uppercase tracking-[0.2em] text-amber">
                Why we&apos;re cautious
              </h4>
              <p className="mt-2 text-sm leading-relaxed text-ink-dim">
                {panel.judge.why_we_are_cautious}
              </p>
            </div>
          </div>
          <p className="mt-6 border-t border-hairline pt-4 text-sm text-ink-dim">
            <span className="readout text-[10px] uppercase tracking-[0.2em] text-ink-faint">
              Recommended follow-up:{" "}
            </span>
            {panel.judge.recommended_followup}
          </p>
        </motion.div>
      )}

      <p className="readout mt-4 text-[11px] leading-relaxed text-ink-faint">
        Survival is enforced by a mechanical rule in code — any fatal kill is final and
        the judge cannot override it.{" "}
        {panel.judge_agrees_with_mechanical_rule
          ? "The judge and the mechanical rule agree here."
          : "The judge disagreed with the mechanical rule here, so the candidate was flagged for human review."}{" "}
        Tally: {panel.tally.killed} kill{panel.tally.killed === 1 ? "" : "s"},{" "}
        {panel.tally.failed_to_kill} failed, {panel.tally.inconclusive} inconclusive
        {panel.tally.errors > 0 ? `, ${panel.tally.errors} errored` : ""}.
      </p>
    </section>
  );
}
