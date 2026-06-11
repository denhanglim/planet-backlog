"""The JSON contract between the science pipeline and everything downstream
(AI panel, website). Versioned; the frontend types are generated against this shape.

Files written to data/:
  candidates.json   — list of candidate dossiers (schema below)
  calibration.json  — known-planet recovery + injection-recovery results
  run-meta.json     — pipeline version, timestamps, environment, honesty notes
"""

from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, config

CONTRACT_VERSION = "1.0.0"


def make_candidate(*, candidate_id: str, tic_id: int, candidate_class: str,
                   sector: int, star: dict, detection: dict, bls_check: dict | None,
                   diagnostics: dict, validation: dict, crossmatch: dict,
                   series: dict, provenance_extra: dict | None = None) -> dict:
    """Assemble one candidate dossier. Panel verdicts are attached later by panel/run.py."""
    return {
        "id": candidate_id,
        "tic_id": tic_id,
        "class": candidate_class,   # periodic | single-transit | calibration | injection-example
        "sector": sector,
        "star": star,
        "detection": detection,
        "bls_check": bls_check,
        "diagnostics": diagnostics,
        "validation": validation,
        "crossmatch": crossmatch,
        "series": series,
        "panel": None,
        "provenance": {
            "pipeline": "planet-backlog",
            "pipeline_version": __version__,
            "contract_version": CONTRACT_VERSION,
            "data_product": star.get("data_product", "TESS SPOC 2-min PDCSAP"),
            "created_utc": datetime.now(timezone.utc).isoformat(),
            **(provenance_extra or {}),
        },
    }


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, allow_nan=False, default=_jsonable))


def _jsonable(o):
    import numpy as np
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        v = float(o)
        return v if v == v and abs(v) != float("inf") else None
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"not JSON-serializable: {type(o)}")


def sanitize(obj):
    """Replace NaN/Inf floats with None recursively (JSON has no NaN)."""
    import math
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def run_meta(*, n_targets_searched: int, n_calibration: int, n_blind: int,
             n_detections: int, n_survivors: int | None, notes: list[str]) -> dict:
    return {
        "pipeline": "planet-backlog",
        "pipeline_version": __version__,
        "contract_version": CONTRACT_VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "search": {
            "period_min_days": config.PERIOD_MIN_DAYS,
            "period_max_days": config.PERIOD_MAX_DAYS,
            "sde_threshold": config.DETECTION_SDE_THRESHOLD,
            "search_bin_minutes": config.SEARCH_BIN_MINUTES,
        },
        "counts": {
            "targets_searched": n_targets_searched,
            "calibration_targets": n_calibration,
            "blind_targets": n_blind,
            "detections": n_detections,
            "panel_survivors": n_survivors,
        },
        "honesty_notes": notes,
    }
