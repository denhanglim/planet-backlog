/**
 * Build-time data access. All numbers on the site flow through here from the
 * pipeline JSON — components never hardcode a scientific quantity.
 */
import type { Calibration, Candidate, RunMeta } from "./contract";

import candidatesJson from "@/data/candidates.json";
import calibrationJson from "@/data/calibration.json";
import runMetaJson from "@/data/run-meta.json";

export const candidates = candidatesJson as unknown as Candidate[];
export const calibration = calibrationJson as unknown as Calibration;
export const runMeta = runMetaJson as unknown as RunMeta;

export function getCandidate(id: string): Candidate | undefined {
  return candidates.find((c) => c.id === id);
}

export interface HeadlineStats {
  targetsSearched: number;
  detections: number;
  survived: number;
  killed: number;
  flagged: number;
  novelSurvivors: number;
  knownRefound: number;
  recoveryRate: number | null;
  completeness: number | null;
  reliability: number | null;
}

export function headlineStats(): HeadlineStats {
  const withPanel = candidates.filter((c) => c.panel);
  const byStatus = (s: string) =>
    withPanel.filter((c) => c.panel!.status === s).length;
  return {
    targetsSearched: runMeta.counts.targets_searched,
    detections: candidates.length,
    survived: byStatus("survived"),
    killed: byStatus("killed"),
    flagged: byStatus("flagged-for-review"),
    novelSurvivors: withPanel.filter(
      (c) => c.panel!.status === "survived" && c.crossmatch.verdict === "novel"
    ).length,
    knownRefound: candidates.filter((c) => c.crossmatch.verdict === "known-planet")
      .length,
    recoveryRate: calibration.known_planet_recovery.recovery_rate,
    completeness: calibration.injection_recovery?.overall_completeness ?? null,
    reliability: calibration.injection_recovery?.reliability ?? null,
  };
}

/** Folded-curve sparkline points for a card; null when no folded series exists. */
export function sparklineSeries(c: Candidate): { x: number; y: number }[] | null {
  if (c.series.binned_phase && c.series.binned_flux) {
    return c.series.binned_phase.map((p, i) => ({ x: p, y: c.series.binned_flux![i] }));
  }
  if (c.series.window_time && c.series.window_flux) {
    const t0 = c.series.t0_btjd ?? c.series.window_time[0];
    return c.series.window_time.map((t, i) => ({ x: t - t0, y: c.series.window_flux![i] }));
  }
  return null;
}

export const fmt = {
  period(d: number | null | undefined): string {
    if (d == null) return "unconstrained";
    return d >= 10 ? `${d.toFixed(2)} d` : `${d.toFixed(3)} d`;
  },
  ppm(v: number | null | undefined): string {
    return v == null ? "—" : `${Math.round(v).toLocaleString("en-US")} ppm`;
  },
  sigma(v: number | null | undefined): string {
    return v == null ? "—" : `${v.toFixed(1)}σ`;
  },
  pct(v: number | null | undefined): string {
    return v == null ? "—" : `${(v * 100).toFixed(0)}%`;
  },
  num(v: number | null | undefined, digits = 1): string {
    return v == null ? "—" : v.toFixed(digits);
  },
};
