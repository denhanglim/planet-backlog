"""Known-planet recovery: run the production pipeline on hosts of confirmed transiting
planets and check the search re-finds each planet's published period.

Ground truth comes from the NASA Exoplanet Archive (pscomppars), matched by the TIC ID
recorded in the downloaded data product — never hand-typed ephemerides.
"""

from __future__ import annotations

import logging

import numpy as np

from pipeline import config
from pipeline.catalogs import Catalogs
from pipeline.detrend import detrend
from pipeline.ingest import fetch_lightcurve
from pipeline.search import run_tls, stellar_params, periods_agree

log = logging.getLogger("calibration.known_recovery")


def recover_one(host: str, catalogs: Catalogs) -> dict:
    """Run search on one confirmed-planet host; compare to archive period."""
    rec: dict = {"host": host, "status": "ok"}
    lcd = fetch_lightcurve(host)
    if lcd is None:
        rec["status"] = "no-data"
        return rec
    rec["tic_id"] = lcd.tic_id
    rec["sector"] = lcd.sector

    truth = None
    if catalogs.confirmed is not None:
        rows = catalogs.confirmed[catalogs.confirmed["tic_int"] == lcd.tic_id]
        rows = rows[rows["tran_flag"] == 1] if "tran_flag" in rows.columns else rows
        if len(rows):
            # shortest-period transiting planet is what one sector most easily shows
            rows = rows.sort_values("pl_orbper")
            truth = {
                "pl_name": str(rows.iloc[0]["pl_name"]),
                "period_days": float(rows.iloc[0]["pl_orbper"]),
            }
    if truth is None:
        rec["status"] = "no-archive-truth"
        return rec
    rec["truth"] = truth

    flat = detrend(lcd)
    star = stellar_params(lcd.tic_id)
    det = run_tls(flat, star=star)
    if det is None:
        rec["status"] = "search-failed"
        rec["recovered"] = False
        return rec

    rec["detected_period_days"] = round(det.period_days, 6)
    rec["sde"] = round(det.sde, 2) if det.sde is not None else None
    rec["depth_ppm"] = round(det.depth_ppm, 1)
    rec["recovered"] = bool(
        det.sde is not None
        and det.sde >= config.DETECTION_SDE_THRESHOLD
        and periods_agree(det.period_days, truth["period_days"])
    )
    if not rec["recovered"]:
        rec["status"] = "not-recovered"
    return rec


def run(hosts: list[str] | None = None) -> dict:
    catalogs = Catalogs().load()
    hosts = hosts or config.CALIBRATION_HOSTS
    results = [recover_one(h, catalogs) for h in hosts]
    attempted = [r for r in results if r["status"] not in ("no-data", "no-archive-truth")]
    recovered = [r for r in attempted if r.get("recovered")]
    return {
        "hosts_requested": len(hosts),
        "hosts_with_data_and_truth": len(attempted),
        "recovered": len(recovered),
        "recovery_rate": round(len(recovered) / len(attempted), 3) if attempted else None,
        "results": results,
    }
