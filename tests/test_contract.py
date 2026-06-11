"""JSON contract: serializable, NaN-free, complete."""

import json
import math

import numpy as np

from pipeline.contract import make_candidate, sanitize, write_json


def test_sanitize_strips_nan_and_inf():
    dirty = {"a": float("nan"), "b": [1.0, float("inf")], "c": {"d": -float("inf"), "e": 2}}
    clean = sanitize(dirty)
    assert clean == {"a": None, "b": [1.0, None], "c": {"d": None, "e": 2}}


def test_candidate_shape_and_json_roundtrip(tmp_path):
    cand = make_candidate(
        candidate_id="PB-1-01-P1", tic_id=1, candidate_class="periodic", sector=1,
        star={"tic_id": 1, "tmag": 9.0, "data_product": "TESS SPOC 2-min PDCSAP"},
        detection={"period_days": 3.0, "sde": 12.0},
        bls_check=None,
        diagnostics={"odd_even": {"computed": False, "reason": "test"}},
        validation={"fpp": 0.1, "method": "heuristic-fpp-v1"},
        crossmatch={"verdict": "novel"},
        series={"phase": [0.0], "flux": [1.0]},
    )
    for key in ("id", "tic_id", "class", "star", "detection", "diagnostics",
                "validation", "crossmatch", "series", "panel", "provenance"):
        assert key in cand
    assert cand["panel"] is None
    assert cand["provenance"]["pipeline_version"]

    p = tmp_path / "c.json"
    write_json(p, [sanitize(cand)])
    loaded = json.loads(p.read_text())
    assert loaded[0]["id"] == "PB-1-01-P1"
    assert not _has_nan(loaded)


def _has_nan(obj) -> bool:
    if isinstance(obj, dict):
        return any(_has_nan(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_has_nan(v) for v in obj)
    return isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj))


def test_validate_heuristic_fpp_bounds():
    from pipeline.validate import heuristic_fpp

    benign = heuristic_fpp(
        {"sde": 15.0},
        {"odd_even": {"computed": True, "difference_sigma": 0.2},
         "secondary": {"computed": True, "significance_sigma": 0.1},
         "shape": {"computed": True, "v_shaped": False, "shape_param": 0.6},
         "centroid": {"computed": True, "significance_sigma": 0.5},
         "neighbors": {"computed": True, "total_neighbor_flux_fraction": 0.01},
         "depth": {"depth_ppm": 5000.0},
         "rotation": {"computed": True, "period_matches_rotation_harmonic": False},
         "systematics": {"computed": True, "frac_in_transit_quality_flagged": 0.0}},
    )
    nasty = heuristic_fpp(
        {"sde": 9.0},
        {"odd_even": {"computed": True, "difference_sigma": 8.0},
         "secondary": {"computed": True, "significance_sigma": 6.0},
         "shape": {"computed": True, "v_shaped": True, "shape_param": 0.05},
         "centroid": {"computed": True, "significance_sigma": 7.0},
         "neighbors": {"computed": True, "total_neighbor_flux_fraction": 0.5},
         "depth": {"depth_ppm": 80000.0},
         "rotation": {"computed": True, "period_matches_rotation_harmonic": True},
         "systematics": {"computed": True, "frac_in_transit_quality_flagged": 0.5}},
    )
    assert 0.0 <= benign["fpp"] < 0.3
    assert 0.7 < nasty["fpp"] <= 1.0
    assert benign["method"] == "heuristic-fpp-v1"
