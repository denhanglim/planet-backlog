"""Pipeline orchestrator: target -> ingest -> detrend -> search -> diagnostics ->
single-transit hunt -> validation -> crossmatch -> candidate dossier.

CLI:
  python -m pipeline.run --calibration            # run the calibration host list
  python -m pipeline.run --blind                  # run the blind backlog batch
  python -m pipeline.run --target "WASP-18"       # one target
  python -m pipeline.run --calibration --blind --out data/
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

from . import config
from .catalogs import Catalogs
from .contract import make_candidate, run_meta, sanitize, write_json
from .detrend import detrend, estimate_rotation
from .diagnostics import folded_series, run_all
from .ingest import fetch_lightcurve, list_sector_targets
from .search import run_bls, run_tls, periods_agree, stellar_params
from .singletransit import find_single_transits
from .validate import heuristic_fpp

log = logging.getLogger("pipeline.run")


def process_target(target: str | int, catalogs: Catalogs, sector: int | None = None,
                   candidate_class: str = "periodic") -> tuple[list[dict], dict]:
    """Run the full pipeline on one target. Returns (candidates, target_record)."""
    record: dict = {"target": str(target), "status": "ok", "detections": 0}

    lcd = fetch_lightcurve(target, sector=sector)
    if lcd is None:
        record["status"] = "no-data"
        return [], record
    record["tic_id"] = lcd.tic_id
    record["sector"] = lcd.sector

    rotation = estimate_rotation(lcd)
    flat = detrend(lcd)
    star = stellar_params(lcd.tic_id)
    star_block = {
        "tic_id": lcd.tic_id,
        "name": lcd.meta.get("object"),
        "ra": lcd.meta.get("ra"),
        "dec": lcd.meta.get("dec"),
        "tmag": lcd.meta.get("tmag"),
        "teff_k": lcd.meta.get("teff"),
        "radius_rsun": star["radius_rsun"],
        "mass_msun": star["mass_msun"],
        "stellar_source": star["source"],
        "data_product": lcd.meta.get("data_product"),
    }

    candidates: list[dict] = []

    tls = run_tls(flat, star=star)
    detected = (
        tls is not None
        and tls.sde is not None
        and tls.sde >= config.DETECTION_SDE_THRESHOLD
        and tls.depth_ppm > 0
    )
    known_eph = None
    if detected:
        bls = run_bls(flat)
        bls_block = None
        if bls is not None:
            bls_block = bls.to_dict()
            bls_block["agrees_with_tls"] = periods_agree(bls.period_days, tls.period_days)
        dur_days = tls.duration_hours / 24.0
        known_eph = (tls.period_days, tls.t0_btjd, dur_days)

        # re-detrend with the transit masked so the trend never eats the transit floor
        flat_masked = detrend(lcd, mask_ephemeris=known_eph)
        diag = run_all(
            flat_masked, rotation, tls.period_days, tls.t0_btjd, dur_days,
            ra=lcd.meta.get("ra"), dec=lcd.meta.get("dec"), tmag=lcd.meta.get("tmag"),
            with_centroid=True,
        )
        validation = heuristic_fpp(tls.to_dict(), diag)
        xmatch = catalogs.crossmatch(lcd.tic_id, tls.period_days)
        series = folded_series(flat_masked, tls.period_days, tls.t0_btjd)
        if tls.folded_model:
            series["model_phase"] = [p - 0.5 for p in tls.folded_model["phase"]]
            series["model_flux"] = tls.folded_model["flux"]

        candidates.append(sanitize(make_candidate(
            candidate_id=f"PB-{lcd.tic_id}-{lcd.sector:02d}-P1",
            tic_id=lcd.tic_id,
            candidate_class=candidate_class,
            sector=lcd.sector,
            star=star_block,
            detection=tls.to_dict() | {"folded_model": None},  # model lives in series
            bls_check=bls_block,
            diagnostics=diag,
            validation=validation,
            crossmatch=xmatch,
            series=series,
        )))
        record["detections"] = 1
        record["period_days"] = tls.period_days
        record["sde"] = tls.sde
    elif tls is not None:
        record["status"] = "no-detection"
        record["best_sde"] = tls.sde
    else:
        record["status"] = "search-failed"

    # single-transit hunt on the residual (periodic transits masked if found)
    flat_for_st = detrend(lcd, mask_ephemeris=known_eph) if known_eph else flat
    st_events = find_single_transits(flat_for_st, known_ephemeris=known_eph)
    for j, ev in enumerate(st_events, start=1):
        dur_days = ev.duration_hours / 24.0
        diag = run_all(
            flat_for_st, rotation,
            period=flat_for_st.baseline_days * 2,  # fold is meaningless; window only
            t0=ev.t0_btjd, duration_days=dur_days,
            ra=lcd.meta.get("ra"), dec=lcd.meta.get("dec"), tmag=lcd.meta.get("tmag"),
            with_centroid=True,
        )
        # periodic-only diagnostics don't apply to a single event
        for k in ("odd_even", "secondary"):
            diag[k] = {"computed": False, "reason": "single event - no phase information"}
        det = {
            "method": "matched-filter-single",
            "period_days": None, "period_unc_days": None,
            "t0_btjd": ev.t0_btjd, "duration_hours": ev.duration_hours,
            "depth_ppm": ev.depth_ppm, "sde": None, "snr": ev.snr, "fap": None,
            "n_transits": 1, "distinct_transits": 1,
            "odd_even_mismatch_sigma": None,
            "min_period_days": ev.min_period_days,
        }
        validation = heuristic_fpp({"sde": ev.snr}, diag)
        validation["note"] = (
            f"Single-transit event: period > {ev.min_period_days:.1f} d "
            "(max distance from the event to a data edge). "
            + validation["note"])
        xmatch = catalogs.crossmatch(lcd.tic_id, None)
        window = _event_window(flat_for_st, ev.t0_btjd, dur_days)
        candidates.append(sanitize(make_candidate(
            candidate_id=f"PB-{lcd.tic_id}-{lcd.sector:02d}-S{j}",
            tic_id=lcd.tic_id,
            candidate_class="single-transit",
            sector=lcd.sector,
            star=star_block,
            detection=det,
            bls_check=None,
            diagnostics=diag,
            validation=validation,
            crossmatch=xmatch,
            series=window,
        )))
    record["single_transit_events"] = len(st_events)
    return candidates, record


def _event_window(lcd, t0: float, dur_days: float) -> dict:
    """Time-series window around a single event (for plotting; no fold exists)."""
    m = np.abs(lcd.time - t0) < max(5 * dur_days, 0.5)
    return {
        "window_time": lcd.time[m].round(5).tolist(),
        "window_flux": lcd.flux[m].round(6).tolist(),
        "t0_btjd": t0,
    }


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--calibration", action="store_true", help="run calibration hosts")
    ap.add_argument("--blind", action="store_true", help="run blind backlog batch")
    ap.add_argument("--target", action="append", default=[], help="explicit target(s)")
    ap.add_argument("--sector", type=int, default=None)
    ap.add_argument("--blind-size", type=int, default=config.BLIND_BATCH_SIZE)
    ap.add_argument("--out", type=Path, default=config.DATA_DIR)
    args = ap.parse_args(argv)

    catalogs = Catalogs().load()
    log.info("catalog status: %s", catalogs.status)

    jobs: list[tuple[str | int, str]] = []
    for t in args.target:
        jobs.append((int(t) if t.isdigit() else t, "periodic"))
    if args.calibration:
        jobs += [(name, "calibration") for name in config.CALIBRATION_HOSTS]
    if args.blind:
        known = catalogs.known_tics()
        tics = list_sector_targets(config.BLIND_SECTOR, args.blind_size,
                                   config.BLIND_SAMPLE_SEED, exclude_tics=known)
        log.info("blind batch: %d targets (known TICs excluded: %d)", len(tics), len(known))
        jobs += [(tic, "periodic") for tic in tics]

    all_candidates: list[dict] = []
    records: list[dict] = []
    for target, cls in jobs:
        log.info("=== processing %s (%s)", target, cls)
        try:
            cands, rec = process_target(target, catalogs, sector=args.sector,
                                        candidate_class=cls)
        except Exception as exc:
            log.exception("target %s crashed: %s", target, exc)
            cands, rec = [], {"target": str(target), "status": f"crashed: {exc}"}
        all_candidates += cands
        records.append(rec)

    n_cal = sum(1 for _, c in jobs if c == "calibration")
    meta = run_meta(
        n_targets_searched=len(jobs),
        n_calibration=n_cal,
        n_blind=len(jobs) - n_cal - len(args.target),
        n_detections=len(all_candidates),
        n_survivors=None,  # panel fills this in
        notes=[
            "Candidates are NOT confirmed planets; confirmation requires RV follow-up.",
            f"FPP method: see validate.py ({'TRICERATOPS available' if _tri() else 'heuristic-fpp-v1 (labeled)'}).",
        ],
    )
    args.out.mkdir(parents=True, exist_ok=True)
    write_json(args.out / "candidates.json", all_candidates)
    write_json(args.out / "run-meta.json", sanitize(meta | {"target_records": records}))
    log.info("wrote %d candidates -> %s", len(all_candidates), args.out / "candidates.json")
    return 0


def _tri() -> bool:
    from .validate import try_triceratops_available
    return try_triceratops_available()


if __name__ == "__main__":
    sys.exit(main())
