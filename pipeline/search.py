"""Period search: Box Least Squares (fast, box model) + Transit Least Squares
(realistic limb-darkened shape, better small-planet recovery).

The search runs on time-binned flux for speed; all diagnostics downstream re-measure
on the full 2-min cadence. Detection statistic of record is the TLS SDE.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict

import numpy as np

from . import config
from .detrend import bin_lightcurve
from .ingest import LightCurveData

log = logging.getLogger(__name__)


@dataclass
class Detection:
    method: str               # "TLS" | "BLS"
    period_days: float
    period_unc_days: float | None
    t0_btjd: float
    duration_hours: float
    depth_ppm: float
    sde: float | None         # TLS signal detection efficiency
    snr: float | None
    fap: float | None         # TLS false-alarm probability (vs noise only)
    n_transits: int
    distinct_transits: int
    odd_even_mismatch_sigma: float | None
    folded_model: dict | None = None   # phase/flux arrays of the fitted TLS model

    def to_dict(self) -> dict:
        return asdict(self)


def stellar_params(tic_id: int) -> dict:
    """Limb darkening + mass/radius from the TIC via TLS's catalog_info. Fallbacks: solar."""
    from transitleastsquares import catalog_info

    try:
        ab, mass, _, _, radius, _, _ = catalog_info(TIC_ID=int(tic_id))
        out = {
            "limb_darkening": [float(ab[0]), float(ab[1])],
            "mass_msun": float(mass) if np.isfinite(mass) else 1.0,
            "radius_rsun": float(radius) if np.isfinite(radius) else 1.0,
            "source": "TIC via transitleastsquares.catalog_info",
        }
    except Exception as exc:
        log.warning("catalog_info failed for TIC %s (%s); using solar fallback", tic_id, exc)
        out = {
            "limb_darkening": [0.4804, 0.1867],
            "mass_msun": 1.0,
            "radius_rsun": 1.0,
            "source": "solar fallback (catalog_info unavailable)",
        }
    if not np.isfinite(out["mass_msun"]) or out["mass_msun"] <= 0:
        out["mass_msun"] = 1.0
    if not np.isfinite(out["radius_rsun"]) or out["radius_rsun"] <= 0:
        out["radius_rsun"] = 1.0
    return out


def run_tls(lcd: LightCurveData, star: dict | None = None,
            period_min: float = config.PERIOD_MIN_DAYS,
            period_max: float = config.PERIOD_MAX_DAYS) -> Detection | None:
    """Transit Least Squares search on binned flux. Returns the top detection."""
    from transitleastsquares import transitleastsquares

    t, f, _ = bin_lightcurve(lcd.time, lcd.flux, lcd.flux_err, config.SEARCH_BIN_MINUTES)
    if len(t) < 200:
        log.info("TIC %s: too few points after binning (%d)", lcd.tic_id, len(t))
        return None
    star = star or stellar_params(lcd.tic_id)
    period_max = min(period_max, (t[-1] - t[0]) / 2.0)  # need >= 2 transits

    model = transitleastsquares(t, f)
    try:
        r = model.power(
            period_min=period_min,
            period_max=period_max,
            u=star["limb_darkening"],
            M_star=star["mass_msun"],
            M_star_min=0.5 * star["mass_msun"],
            M_star_max=2.0 * star["mass_msun"],
            R_star=star["radius_rsun"],
            R_star_min=0.5 * star["radius_rsun"],
            R_star_max=2.0 * star["radius_rsun"],
            show_progress_bar=False,
            use_threads=4,
        )
    except Exception as exc:
        log.warning("TLS failed for TIC %s: %s", lcd.tic_id, exc)
        return None

    if not np.isfinite(r.period):
        return None

    folded_model = None
    if r.model_folded_phase is not None and len(r.model_folded_phase) > 0:
        keep = np.linspace(0, len(r.model_folded_phase) - 1, min(400, len(r.model_folded_phase))).astype(int)
        folded_model = {
            "phase": np.asarray(r.model_folded_phase)[keep].round(5).tolist(),
            "flux": np.asarray(r.model_folded_model)[keep].round(6).tolist(),
        }

    return Detection(
        method="TLS",
        period_days=float(r.period),
        period_unc_days=float(r.period_uncertainty) if np.isfinite(r.period_uncertainty) else None,
        t0_btjd=float(r.T0),
        duration_hours=float(r.duration * 24.0),
        depth_ppm=float((1.0 - r.depth) * 1e6),
        sde=float(r.SDE),
        snr=float(r.snr) if np.isfinite(r.snr) else None,
        fap=float(r.FAP) if np.isfinite(r.FAP) else None,
        n_transits=int(r.transit_count),
        distinct_transits=int(r.distinct_transit_count),
        odd_even_mismatch_sigma=float(r.odd_even_mismatch) if np.isfinite(r.odd_even_mismatch) else None,
        folded_model=folded_model,
    )


def run_bls(lcd: LightCurveData,
            period_min: float = config.PERIOD_MIN_DAYS,
            period_max: float = config.PERIOD_MAX_DAYS) -> Detection | None:
    """Box Least Squares cross-check via astropy. Independent of TLS."""
    from astropy.timeseries import BoxLeastSquares

    t, f, e = bin_lightcurve(lcd.time, lcd.flux, lcd.flux_err, config.SEARCH_BIN_MINUTES)
    if len(t) < 200:
        return None
    period_max = min(period_max, (t[-1] - t[0]) / 2.0)
    durations = np.array([0.05, 0.1, 0.15, 0.2, 0.3]) # days
    bls = BoxLeastSquares(t, f, e)
    periods = np.exp(np.linspace(np.log(period_min), np.log(period_max), 8000))
    try:
        pg = bls.power(periods, durations, objective="snr")
    except Exception as exc:
        log.warning("BLS failed for TIC %s: %s", lcd.tic_id, exc)
        return None

    i = int(np.argmax(pg.power))
    power = np.asarray(pg.power)
    sde = float((power[i] - np.median(power)) / (1.4826 * np.median(np.abs(power - np.median(power))) + 1e-12))
    stats = bls.compute_stats(pg.period[i], pg.duration[i], pg.transit_time[i])

    return Detection(
        method="BLS",
        period_days=float(pg.period[i]),
        period_unc_days=None,
        t0_btjd=float(pg.transit_time[i]),
        duration_hours=float(pg.duration[i] * 24.0),
        depth_ppm=float(pg.depth[i] * 1e6),
        sde=sde,
        snr=float(pg.depth_snr[i]),
        fap=None,
        n_transits=int(len(stats["transit_times"])),
        distinct_transits=int(len(stats["transit_times"])),
        odd_even_mismatch_sigma=None,
        folded_model=None,
    )


def periods_agree(p1: float, p2: float, tol: float = 0.02) -> bool:
    """True if periods match directly or at a harmonic ratio."""
    for ratio in config.HARMONIC_RATIOS:
        if abs(p1 - p2 * ratio) / (p2 * ratio) < tol:
            return True
    return False
