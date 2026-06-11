"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Sparkline } from "@/components/Sparkline";
import { StatusChip } from "@/components/StatusChip";
import type { CandidateClass, PanelStatus } from "@/lib/contract";

export interface LedgerCard {
  id: string;
  name: string;
  klass: CandidateClass;
  status: PanelStatus | null;
  verdict: string;
  periodDays: number | null;
  periodLabel: string;
  depthLabel: string;
  depthPpm: number;
  fpp: number;
  sde: number | null;
  spark: { x: number; y: number }[] | null;
}

type StatusFilter = "all" | PanelStatus;
type ClassFilter = "all" | CandidateClass;
type SortKey = "fpp" | "sde" | "period" | "depth";

const STATUS_FILTERS: { key: StatusFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "survived", label: "Survived" },
  { key: "flagged-for-review", label: "Flagged" },
  { key: "killed", label: "Killed" },
];

const CLASS_FILTERS: { key: ClassFilter; label: string }[] = [
  { key: "all", label: "All classes" },
  { key: "periodic", label: "Periodic" },
  { key: "single-transit", label: "Single transit" },
  { key: "calibration", label: "Calibration" },
];

const SORTS: { key: SortKey; label: string }[] = [
  { key: "fpp", label: "FPP ↑" },
  { key: "sde", label: "SDE ↓" },
  { key: "period", label: "Period ↑" },
  { key: "depth", label: "Depth ↓" },
];

export function LedgerGrid({ cards }: { cards: LedgerCard[] }) {
  const [status, setStatus] = useState<StatusFilter>("all");
  const [klass, setKlass] = useState<ClassFilter>("all");
  const [sort, setSort] = useState<SortKey>("fpp");
  const reduced = useReducedMotion();

  const shown = useMemo(() => {
    let out = cards.filter(
      (c) =>
        (status === "all" || c.status === status) &&
        (klass === "all" || c.klass === klass)
    );
    const val = (c: LedgerCard) => {
      switch (sort) {
        case "fpp": return c.fpp;
        case "sde": return -(c.sde ?? -Infinity);
        case "period": return c.periodDays ?? Infinity;
        case "depth": return -c.depthPpm;
      }
    };
    return out.sort((a, b) => (val(a) as number) - (val(b) as number));
  }, [cards, status, klass, sort]);

  const Group = ({
    label,
    children,
  }: {
    label: string;
    children: React.ReactNode;
  }) => (
    <fieldset className="flex flex-wrap items-center gap-1">
      <legend className="sr-only">{label}</legend>
      {children}
    </fieldset>
  );

  const chip = (active: boolean) =>
    `readout cursor-pointer border px-3 py-1.5 text-[11px] uppercase tracking-[0.15em] transition-colors ${
      active
        ? "border-phosphor/60 bg-phosphor/10 text-phosphor"
        : "border-hairline text-ink-dim hover:border-hairline-strong hover:text-ink"
    }`;

  return (
    <div>
      <div className="mb-10 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap gap-4">
          <Group label="Filter by tribunal status">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                aria-pressed={status === f.key}
                onClick={() => setStatus(f.key)}
                className={chip(status === f.key)}
              >
                {f.label}
              </button>
            ))}
          </Group>
          <Group label="Filter by candidate class">
            {CLASS_FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                aria-pressed={klass === f.key}
                onClick={() => setKlass(f.key)}
                className={chip(klass === f.key)}
              >
                {f.label}
              </button>
            ))}
          </Group>
        </div>
        <label className="readout flex items-center gap-2 text-[11px] uppercase tracking-[0.15em] text-ink-faint">
          Sort
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            className="border border-hairline bg-void-2 px-2 py-1.5 text-ink focus:border-phosphor"
          >
            {SORTS.map((s) => (
              <option key={s.key} value={s.key}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p className="readout mb-4 text-[11px] uppercase tracking-[0.2em] text-ink-faint" aria-live="polite">
        {shown.length} of {cards.length} candidates
      </p>

      <motion.ul layout={!reduced} className="grid gap-px bg-hairline sm:grid-cols-2 lg:grid-cols-3">
        <AnimatePresence mode="popLayout">
          {shown.map((c) => (
            <motion.li
              layout={!reduced}
              key={c.id}
              initial={reduced ? false : { opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={reduced ? undefined : { opacity: 0, scale: 0.97 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              className="bg-void"
            >
              <Link
                href={`/dossier/${c.id}/`}
                className="group block h-full p-6 transition-colors hover:bg-void-2 focus-visible:bg-void-2"
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="readout text-xs text-ink-faint">{c.id}</span>
                  <StatusChip status={c.status} compact />
                </div>
                <p className="display mt-3 text-lg font-medium text-ink transition-colors group-hover:text-phosphor">
                  {c.name}
                </p>
                <p className="readout mt-0.5 text-[11px] uppercase tracking-[0.15em] text-ink-faint">
                  {c.klass}
                  {c.verdict !== "novel" ? ` · ${c.verdict}` : ""}
                </p>
                <Sparkline points={c.spark} width={280} height={52} className="mt-4 w-full" />
                <dl className="readout mt-4 grid grid-cols-4 gap-2 text-[11px] text-ink-dim">
                  <div>
                    <dt className="text-ink-faint">PERIOD</dt>
                    <dd>{c.periodLabel}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-faint">DEPTH</dt>
                    <dd>{c.depthLabel}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-faint">SDE</dt>
                    <dd>{c.sde == null ? "—" : c.sde.toFixed(1)}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-faint">FPP</dt>
                    <dd>{c.fpp.toFixed(2)}</dd>
                  </div>
                </dl>
              </Link>
            </motion.li>
          ))}
        </AnimatePresence>
      </motion.ul>

      {shown.length === 0 && (
        <p className="panel mt-2 p-8 text-sm text-ink-dim">
          No candidates match this filter. That can be the honest answer — see the{" "}
          <Link href="/trust" className="text-phosphor underline-offset-4 hover:underline">
            Trust page
          </Link>{" "}
          for what the pipeline did and didn&apos;t find.
        </p>
      )}
    </div>
  );
}
