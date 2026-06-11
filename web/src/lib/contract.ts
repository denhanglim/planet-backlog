/**
 * TypeScript mirror of the pipeline JSON contract (contract_version 1.0.0).
 * Source of truth: pipeline/contract.py. The site renders ONLY these shapes.
 */

export type CandidateClass =
  | "periodic"
  | "single-transit"
  | "calibration"
  | "injection-example";

export type CrossmatchVerdict =
  | "novel"
  | "known-planet"
  | "known-toi"
  | "known-eb"
  | "known-fp";

export type PanelStatus = "survived" | "killed" | "flagged-for-review";

export interface Star {
  tic_id: number;
  name: string | null;
  ra: number | null;
  dec: number | null;
  tmag: number | null;
  teff_k: number | null;
  radius_rsun: number | null;
  mass_msun: number | null;
  stellar_source: string;
  data_product: string;
}

export interface Detection {
  method: string;
  period_days: number | null;
  period_unc_days: number | null;
  t0_btjd: number;
  duration_hours: number;
  depth_ppm: number;
  sde: number | null;
  snr: number | null;
  fap: number | null;
  n_transits: number;
  distinct_transits: number;
  odd_even_mismatch_sigma: number | null;
  min_period_days?: number;
}

export interface BlsCheck extends Detection {
  agrees_with_tls: boolean;
}

export interface DiagnosticBase {
  computed: boolean;
  reason?: string;
}

export interface Diagnostics {
  depth: DiagnosticBase & { depth_ppm?: number; depth_err_ppm?: number; n_in_transit?: number };
  odd_even: DiagnosticBase & {
    depth_odd_ppm?: number;
    depth_even_ppm?: number;
    difference_sigma?: number;
    n_odd?: number;
    n_even?: number;
  };
  secondary: DiagnosticBase & {
    depth_ppm?: number;
    significance_sigma?: number;
    n_points?: number;
    method?: string;
  };
  shape: DiagnosticBase & {
    shape_param?: number;
    fitted_depth_ppm?: number;
    fitted_duration_hours?: number;
    v_shaped?: boolean;
  };
  centroid: DiagnosticBase & {
    shift_pixels?: number;
    shift_arcsec?: number;
    significance_sigma?: number;
    n_in_transit_cadences?: number;
  };
  neighbors: DiagnosticBase & {
    n_neighbors?: number;
    neighbors?: Array<{
      tic_id: number;
      sep_arcsec: number;
      tmag: number;
      flux_ratio_vs_target: number | null;
    }>;
    total_neighbor_flux_fraction?: number;
    search_radius_arcsec?: number;
  };
  systematics: DiagnosticBase & {
    frac_in_transit_quality_flagged?: number;
    frac_in_transit_momentum_dump?: number;
    n_transits_in_data?: number;
    n_transits_near_gap_or_edge?: number;
  };
  rotation: DiagnosticBase & {
    rotation_period_days?: number;
    rotation_power?: number;
    period_matches_rotation_harmonic?: boolean;
    matched_ratios?: number[];
  };
}

export interface ValidationFactor {
  name: string;
  contribution: number | null;
  detail: string;
}

export interface Validation {
  fpp: number;
  method: string;
  is_bayesian: boolean;
  note: string;
  factors: ValidationFactor[];
}

export interface Crossmatch {
  toi: {
    toi: string;
    period_days: number | null;
    tfopwg_disposition: string;
    period_match: boolean;
  } | null;
  confirmed: {
    pl_name: string;
    period_days: number | null;
    radius_rearth: number | null;
    period_match: boolean;
  } | null;
  eb: { matched: boolean; source: string } | null;
  verdict: CrossmatchVerdict;
  catalog_status: Record<string, string>;
}

export interface Series {
  phase?: number[];
  flux?: number[];
  binned_phase?: number[];
  binned_flux?: number[];
  model_phase?: number[];
  model_flux?: number[];
  window_time?: number[];
  window_flux?: number[];
  t0_btjd?: number;
}

export interface SkepticVerdict {
  skeptic: "binary" | "blend" | "instrument" | "stellar" | "alias" | "catalog";
  verdict?: "killed" | "failed_to_kill" | "inconclusive";
  lethality?: "fatal" | "serious-concern" | "minor-concern" | "none";
  reasoning?: string;
  evidence_cited?: string[];
  what_would_change_my_mind?: string;
  error?: string;
}

export interface Judge {
  decision?: "survives" | "killed" | "needs-human-review";
  confidence?: "high" | "medium" | "low";
  summary_plain_english?: string;
  why_it_might_be_real?: string;
  why_we_are_cautious?: string;
  recommended_followup?: string;
  error?: string;
}

export interface Panel {
  panel_version: string;
  model: string;
  ran_utc: string;
  skeptics: SkepticVerdict[];
  tally: { killed: number; failed_to_kill: number; inconclusive: number; errors: number };
  mechanical_status: PanelStatus;
  judge: Judge | null;
  judge_agrees_with_mechanical_rule: boolean;
  status: PanelStatus;
}

export interface Candidate {
  id: string;
  tic_id: number;
  class: CandidateClass;
  sector: number;
  star: Star;
  detection: Detection;
  bls_check: BlsCheck | null;
  diagnostics: Diagnostics;
  validation: Validation;
  crossmatch: Crossmatch;
  series: Series;
  panel: Panel | null;
  provenance: {
    pipeline: string;
    pipeline_version: string;
    contract_version: string;
    data_product: string;
    created_utc: string;
  };
}

export interface RecoveryResult {
  host: string;
  status: string;
  tic_id?: number;
  sector?: number;
  truth?: { pl_name: string; period_days: number };
  detected_period_days?: number;
  sde?: number | null;
  depth_ppm?: number;
  recovered?: boolean;
}

export interface CompletenessCell {
  depth_ppm: number;
  period_bin_days: [number, number];
  n_injected: number;
  n_recovered: number;
  completeness: number;
}

export interface Calibration {
  pipeline_version: string;
  generated_utc: string;
  detection_threshold_sde: number;
  known_planet_recovery: {
    hosts_requested: number;
    hosts_with_data_and_truth: number;
    recovered: number;
    recovery_rate: number | null;
    results: RecoveryResult[];
  };
  injection_recovery: {
    n_injections: number;
    n_recovered: number;
    overall_completeness: number | null;
    completeness_grid: CompletenessCell[];
    n_null_trials: number;
    n_null_false_alarms: number;
    n_wrong_period_detections: number;
    reliability: number | null;
    reliability_definition: string;
    trials: unknown[];
    null_trials: unknown[];
  } | null;
  scope_notes: string[];
}

export interface RunMeta {
  pipeline: string;
  pipeline_version: string;
  contract_version: string;
  generated_utc: string;
  environment: { python: string; platform: string };
  search: {
    period_min_days: number;
    period_max_days: number;
    sde_threshold: number;
    search_bin_minutes: number;
  };
  counts: {
    targets_searched: number;
    calibration_targets: number;
    blind_targets: number;
    detections: number;
    panel_survivors: number | null;
  };
  honesty_notes: string[];
  target_records?: Array<Record<string, unknown>>;
}
