"""Statistical validation: false-positive probability per candidate.

Primary path: TRICERATOPS (if importable) — published Bayesian FPP for TESS.
Fallback (default): a documented heuristic, `heuristic-fpp-v1`, clearly labeled in
all output. It maps computed diagnostic z-scores through a logistic function. It is
NOT a Bayesian probability; it is a transparent, reproducible ranking score in [0,1]
whose factor contributions are published alongside the number.

heuristic-fpp-v1, in full (also rendered on the site's Method page):

    risk = 1.2 * clip(max(odd_even_sigma - 1, 0) / 3, 0, 2)   # EB tell (1-sigma noise floor)
         + 1.2 * clip(max(secondary_sigma - 1, 0) / 3, 0, 2)  # EB tell (1-sigma noise floor)
         + 0.8 * (1 if v_shaped else 0)                  # grazing/EB geometry
         + 1.0 * clip(centroid_sigma / 3, 0, 2)          # blend tell
         + 0.8 * clip(neighbor_flux_fraction / 0.2, 0, 2)# crowding prior
         + 0.6 * (1 if depth_ppm > 30000 else 0)         # too deep for planet
         + 0.8 * (1 if rotation_harmonic_match else 0)   # stellar variability alias
         + 0.6 * clip(frac_quality_flagged / 0.3, 0, 2)  # systematics overlap
    trust = clip((sde - 7) / 8, 0, 1.5)                  # detection strength
    fpp   = sigmoid(risk - trust - 1.0)

Missing diagnostics contribute 0 risk but are listed as "not computed" so the panel
and the reader can see what was NOT checked.
"""

from __future__ import annotations

import numpy as np

FPP_METHOD = "heuristic-fpp-v1"


def _sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-x)))


def _clip(x: float, lo: float, hi: float) -> float:
    return float(np.clip(x, lo, hi))


def heuristic_fpp(detection: dict, diagnostics: dict) -> dict:
    """Compute heuristic-fpp-v1 from the candidate's computed diagnostics."""
    factors = []

    def factor(name: str, value: float, weight: float, detail: str):
        factors.append({"name": name, "contribution": round(weight * value, 4), "detail": detail})
        return weight * value

    risk = 0.0
    oe = diagnostics.get("odd_even", {})
    if oe.get("computed"):
        s = oe.get("difference_sigma") or 0.0
        risk += factor("odd_even", _clip(max(s - 1, 0) / 3, 0, 2), 1.2,
                       f"odd/even depth differ by {s:.1f} sigma")
    else:
        factors.append({"name": "odd_even", "contribution": None, "detail": "not computed"})

    sec = diagnostics.get("secondary", {})
    if sec.get("computed"):
        s = max(sec.get("significance_sigma") or 0.0, 0.0)
        risk += factor("secondary_eclipse", _clip(max(s - 1, 0) / 3, 0, 2), 1.2,
                       f"secondary depth significance {s:.1f} sigma")
    else:
        factors.append({"name": "secondary_eclipse", "contribution": None, "detail": "not computed"})

    shape = diagnostics.get("shape", {})
    if shape.get("computed"):
        risk += factor("v_shape", 1.0 if shape.get("v_shaped") else 0.0, 0.8,
                       f"shape_param={shape.get('shape_param'):.2f} (<0.15 = V-shaped)")
    else:
        factors.append({"name": "v_shape", "contribution": None, "detail": "not computed"})

    cen = diagnostics.get("centroid", {})
    if cen.get("computed"):
        s = max(cen.get("significance_sigma") or 0.0, 0.0)
        risk += factor("centroid_shift", _clip(s / 3, 0, 2), 1.0,
                       f"in-transit centroid shift {s:.1f} sigma")
    else:
        factors.append({"name": "centroid_shift", "contribution": None, "detail": "not computed"})

    nb = diagnostics.get("neighbors", {})
    if nb.get("computed"):
        f = nb.get("total_neighbor_flux_fraction") or 0.0
        risk += factor("crowding", _clip(f / 0.2, 0, 2), 0.8,
                       f"neighbor flux fraction {f:.3f} within 63 arcsec")
    else:
        factors.append({"name": "crowding", "contribution": None, "detail": "not computed"})

    depth = (diagnostics.get("depth", {}) or {}).get("depth_ppm")
    if depth is not None and np.isfinite(depth):
        risk += factor("depth_too_deep", 1.0 if depth > 30000 else 0.0, 0.6,
                       f"measured depth {depth:.0f} ppm (>30000 suggests stellar companion)")

    rot = diagnostics.get("rotation", {})
    if rot.get("computed"):
        risk += factor("rotation_alias", 1.0 if rot.get("period_matches_rotation_harmonic") else 0.0,
                       0.8, f"P_rot={rot.get('rotation_period_days')} d")

    sysf = diagnostics.get("systematics", {})
    if sysf.get("computed"):
        f = sysf.get("frac_in_transit_quality_flagged") or 0.0
        risk += factor("systematics_overlap", _clip(f / 0.3, 0, 2), 0.6,
                       f"{100*f:.1f}% of in-transit cadences quality-flagged")

    sde = detection.get("sde") or 0.0
    trust = _clip((sde - 7) / 8, 0, 1.5)
    factors.append({"name": "detection_strength", "contribution": round(-trust, 4),
                    "detail": f"TLS SDE {sde:.1f}"})

    fpp = _sigmoid(risk - trust - 1.0)
    return {
        "fpp": round(fpp, 4),
        "method": FPP_METHOD,
        "is_bayesian": False,
        "note": ("Transparent diagnostic-based ranking score, not a Bayesian probability. "
                 "Formula published in pipeline/validate.py and on the Method page."),
        "factors": factors,
    }


def try_triceratops_available() -> bool:
    try:
        import triceratops  # noqa: F401
        return True
    except Exception:
        return False
