import type { PanelStatus } from "@/lib/contract";

const STYLES: Record<PanelStatus | "unvetted", { label: string; cls: string }> = {
  survived: {
    label: "SURVIVED THE TRIBUNAL",
    cls: "text-phosphor border-phosphor/40 bg-phosphor/5",
  },
  killed: {
    label: "KILLED",
    cls: "text-amber border-amber/40 bg-amber/5",
  },
  "flagged-for-review": {
    label: "FLAGGED FOR HUMAN REVIEW",
    cls: "text-ink-dim border-hairline-strong bg-void-3",
  },
  unvetted: {
    label: "AWAITING TRIBUNAL",
    cls: "text-ink-faint border-hairline bg-void-2",
  },
};

export function StatusChip({
  status,
  compact = false,
}: {
  status: PanelStatus | null | undefined;
  compact?: boolean;
}) {
  const s = STYLES[status ?? "unvetted"];
  const label = compact ? s.label.split(" ")[0] : s.label;
  return (
    <span
      className={`readout inline-flex items-center gap-1.5 border px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] ${s.cls}`}
    >
      <span aria-hidden className="inline-block h-1.5 w-1.5 rounded-full bg-current" />
      {label}
    </span>
  );
}
