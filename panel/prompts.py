"""Skeptic + judge prompts, and the deterministic candidate digest each agent receives.

Ground rules baked into every prompt:
- Reason ONLY over the computed diagnostics provided. Never invent or estimate a number.
- Cite the exact diagnostic fields weighed.
- A diagnostic marked computed=false is missing evidence, not evidence.
- The physical skeptics never see catalog crossmatch results (kept blind so the
  physical vetting cannot lean on 'it's already known to be real').
"""

from __future__ import annotations

import json

COMMON_RULES = """You are one skeptic on an adversarial exoplanet-vetting panel.
Your single job is to try to KILL this transit candidate from your assigned angle.

Hard rules:
1. Reason ONLY over the computed diagnostics in the CANDIDATE DIGEST below. Every number
   you mention must appear verbatim in the digest. NEVER invent, estimate, or extrapolate
   a numeric value.
2. In "evidence_cited", list the exact field paths you weighed (e.g. "odd_even.difference_sigma").
3. A diagnostic with computed=false is MISSING evidence. You may cite the gap as a reason
   for caution ("inconclusive"), but never as positive evidence of a false positive.
4. "killed" + lethality "fatal" is reserved for decisive computed evidence. If your case
   is suggestive but not decisive, use "failed_to_kill" or "inconclusive" with
   lethality "serious-concern" or "minor-concern".
5. Output ONLY a JSON object matching the schema. No markdown fences, no prose outside JSON.
"""

SKEPTIC_BRIEFS = {
    "binary": """Angle: ECLIPSING BINARY. Is this 'transit' actually a stellar eclipse?
Weigh: secondary eclipse depth/significance (a significant secondary at this depth scale
means a stellar companion); odd-even depth mismatch (alternating eclipse depths at half
the true period); V-shaped transit geometry (shape.v_shaped, shape.shape_param); absolute
depth (depth.depth_ppm > ~30000 ppm is deeper than almost any planet); transit duration
vs period plausibility.""",
    "blend": """Angle: BLENDED BACKGROUND/NEARBY ECLIPSING BINARY. Does the dip even come
from the target star? Weigh: centroid shift during transit (centroid.shift_arcsec,
centroid.significance_sigma — a significant in-transit centroid displacement means the
signal source is off-target); neighbor stars in the aperture (neighbors.n_neighbors,
neighbors.total_neighbor_flux_fraction, individual neighbor flux ratios — a bright close
neighbor can host the eclipse, diluted into this aperture).""",
    "instrument": """Angle: INSTRUMENTAL ARTIFACT. Is this a systematic, not an astrophysical
signal? Weigh: systematics.frac_in_transit_quality_flagged and frac_in_transit_momentum_dump
(transits coinciding with flagged cadences / reaction-wheel desaturations);
systematics.n_transits_near_gap_or_edge vs n_transits_in_data (events stacked on downlink
gaps or sector edges are classic scattered-light artifacts); detection strength
(detection.sde, detection.snr) and number of distinct transits (a 2-transit detection
rides on far thinner evidence than a 7-transit one).""",
    "stellar": """Angle: STELLAR VARIABILITY. Is this starspots, pulsation, or rotation —
not a transit? Weigh: rotation.period_matches_rotation_harmonic and rotation.rotation_period_days
vs detection.period_days (candidate period at a rotation harmonic is a classic spot alias);
rotation.rotation_power (strong rotational modulation makes spot artifacts likelier);
transit shape (a real transit is flat-bottomed with sharp ingress/egress — shape.shape_param;
sinusoidal-ish dips are variability); duration vs period plausibility.""",
    "alias": """Angle: WRONG PERIOD / HARMONIC / WINDOW ALIAS. Is the detected period the
true one? Weigh: BLS-vs-TLS agreement (bls_check.agrees_with_tls — independent methods
disagreeing on period is a red flag); detection.n_transits and distinct_transits (period
built from few events is fragile; for class single-transit the period is UNCONSTRAINED by
construction — say so); odd-even mismatch (true period may be 2x — that makes it an EB);
secondary eclipse at phase 0.5 (could mean the true period is half). For single-transit
candidates, focus on whether one event can be trusted at all: detection.snr,
systematics flags, n_points_in_event.""",
    "catalog": """Angle: ALREADY KNOWN. Is this object in the TOI list, the confirmed-planet
archive, or a known-EB/false-positive list? You receive the pipeline's catalog crossmatch.
If crossmatch.verdict is anything other than "novel", this candidate must be KILLED for
novelty (lethality fatal) — presenting a known object as a discovery is the project's #1
failure mode. Quote the matched name/TOI and whether the period matched. If the candidate's
class is "calibration", note that this kill is expected and is exactly what the calibration
run is designed to demonstrate. If verdict is "novel", check catalog_status for catalogs
that failed to load — a missing catalog weakens the novelty claim (inconclusive at best).""",
}

JUDGE_PROMPT = """You are the judge of an adversarial exoplanet-vetting panel. Six skeptics
each tried to kill this candidate from one angle. Synthesize their verdicts.

Hard rules:
1. Use ONLY the skeptic verdicts and the candidate digest provided. Never invent numbers.
2. Your "confidence" is a qualitative judgment (high/medium/low) of how decisive the panel's
   evidence is — it is NOT a measured probability. The computed false-positive metric is
   validation.fpp and you must defer to it as the only quantitative risk number.
3. Decision guide: any fatal kill -> "killed". No fatal kills but serious concerns or
   missing key diagnostics -> "needs-human-review". Clean sweep (skeptics failed to kill,
   concerns minor) -> "survives".
4. Write for a smart general audience: plain English, no jargon left unexplained.
5. Output ONLY a JSON object matching the schema. No markdown fences.
"""


def candidate_digest(cand: dict, include_crossmatch: bool) -> dict:
    """Deterministic, compact view of a candidate for the agents. No light-curve arrays."""
    digest = {
        "id": cand["id"],
        "class": cand["class"],
        "sector": cand["sector"],
        "star": cand["star"],
        "detection": {k: v for k, v in cand["detection"].items() if k != "folded_model"},
        "bls_check": (
            {k: cand["bls_check"][k] for k in
             ("period_days", "depth_ppm", "duration_hours", "sde", "snr", "agrees_with_tls")
             if k in cand["bls_check"]}
            if cand.get("bls_check") else None
        ),
        "diagnostics": cand["diagnostics"],
        "validation": cand["validation"],
    }
    if include_crossmatch:
        digest["crossmatch"] = cand["crossmatch"]
    return digest


def skeptic_prompt(name: str, cand: dict, schema: dict) -> str:
    digest = candidate_digest(cand, include_crossmatch=(name == "catalog"))
    return (
        f"{COMMON_RULES}\n"
        f"Your assigned angle:\n{SKEPTIC_BRIEFS[name]}\n\n"
        f'Set "skeptic" to "{name}".\n\n'
        f"OUTPUT JSON SCHEMA:\n{json.dumps(schema)}\n\n"
        f"CANDIDATE DIGEST:\n{json.dumps(digest, indent=1)}"
    )


def judge_prompt(cand: dict, skeptic_verdicts: list[dict], tally: dict, schema: dict) -> str:
    digest = candidate_digest(cand, include_crossmatch=True)
    return (
        f"{JUDGE_PROMPT}\n"
        f"OUTPUT JSON SCHEMA:\n{json.dumps(schema)}\n\n"
        f"SKEPTIC VERDICTS:\n{json.dumps(skeptic_verdicts, indent=1)}\n\n"
        f"MECHANICAL TALLY (computed, trust this): {json.dumps(tally)}\n\n"
        f"CANDIDATE DIGEST:\n{json.dumps(digest, indent=1)}"
    )
