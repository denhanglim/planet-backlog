"""Injection-recovery: the completeness + reliability measurement.

Procedure (per real host light curve):
  1. Mask the host's known planet using the ephemeris the pipeline itself recovered
     (computed, not hand-typed). Hosts whose planet wasn't recovered are excluded.
  2. Inject a synthetic limb-darkened-trapezoid transit at a random (period, depth)
     drawn from a log-uniform grid, duration from circular-orbit geometry given the
     TIC stellar radius/mass.
  3. Run the production TLS search blind.
  4. Recovered = SDE >= threshold AND detected period matches injected (incl. harmonics).

Reliability comes from null trials: the same masked light curves, circularly shifted
in flux (preserves noise structure, destroys coherent signals), searched blind. Any
SDE >= threshold detection in a null trial is a false alarm.

Scope note (honesty): a few hundred injections, not thousands — bounded by one-session
compute. The grid and counts are published in calibration.json.
"""

from __future__ import annotations

import logging

import numpy as np

from pipeline import config
from pipeline.detrend import detrend, transit_mask
from pipeline.ingest import LightCurveData, fetch_lightcurve
from pipeline.search import run_tls, stellar_params, periods_agree

log = logging.getLogger("calibration.injection")

G_MSUN_DAY_RSUN = 2942.2062  # G in units of R_sun^3 / (M_sun day^2)

DEPTH_GRID_PPM = [300.0, 1000.0, 3000.0, 10000.0]
PERIOD_BINS_DAYS = [(0.5, 2.0), (2.0, 5.0), (5.0, 12.0)]


def transit_duration_days(period: float, r_star: float, m_star: float) -> float:
    """Central-transit duration for a circular orbit: T = P/pi * asin(R*/a)."""
    a = (G_MSUN_DAY_RSUN * m_star * period**2 / (4 * np.pi**2)) ** (1.0 / 3.0)
    x = min(r_star / a, 0.999)
    return float(period / np.pi * np.arcsin(x))


def inject_transit(time: np.ndarray, flux: np.ndarray, period: float, t0: float,
                   depth_frac: float, duration_days: float) -> np.ndarray:
    """Multiply in a trapezoid transit (20% ingress/egress) at the given ephemeris."""
    phase = (time - t0 + 0.5 * period) % period - 0.5 * period
    half_t = duration_days / 2.0
    half_f = 0.6 * half_t   # flat bottom = 60% of duration
    dx = np.abs(phase)
    model = np.ones_like(flux)
    model[dx < half_f] = 1.0 - depth_frac
    ingress = (dx >= half_f) & (dx < half_t)
    slope = (dx[ingress] - half_f) / (half_t - half_f)
    model[ingress] = 1.0 - depth_frac * (1.0 - slope)
    return flux * model


def prepare_host(host: str) -> tuple[LightCurveData, dict] | None:
    """Fetch + detrend a host and mask its own recovered planet. None if unusable."""
    lcd = fetch_lightcurve(host)
    if lcd is None:
        return None
    star = stellar_params(lcd.tic_id)
    flat = detrend(lcd)
    det = run_tls(flat, star=star)
    if det is None or det.sde is None or det.sde < config.DETECTION_SDE_THRESHOLD:
        # no in-data planet to mask; usable as-is (quiet host)
        return flat, star
    mask = transit_mask(flat.time, det.period_days, det.t0_btjd,
                        det.duration_hours / 24.0, pad=2.0)
    clean = LightCurveData(
        tic_id=flat.tic_id, sector=flat.sector,
        time=flat.time[~mask], flux=flat.flux[~mask],
        flux_err=flat.flux_err[~mask], quality=flat.quality[~mask],
        meta=flat.meta,
    )
    return clean, star


def run(hosts: list[str] | None = None, n_injections_per_host: int = 24,
        n_null_per_host: int = 4, seed: int = 7) -> dict:
    hosts = hosts or config.CALIBRATION_HOSTS
    rng = np.random.default_rng(seed)

    trials: list[dict] = []
    null_trials: list[dict] = []

    for host in hosts:
        prep = prepare_host(host)
        if prep is None:
            log.warning("%s: no data; skipped", host)
            continue
        clean, star = prep
        baseline = clean.baseline_days
        log.info("%s: TIC %s, %d points, baseline %.1f d",
                 host, clean.tic_id, len(clean.time), baseline)

        for i in range(n_injections_per_host):
            depth_ppm = float(rng.choice(DEPTH_GRID_PPM))
            lo, hi = PERIOD_BINS_DAYS[i % len(PERIOD_BINS_DAYS)]
            period = float(np.exp(rng.uniform(np.log(lo), np.log(min(hi, baseline / 2)))))
            t0 = float(clean.time[0] + rng.uniform(0, period))
            dur = transit_duration_days(period, star["radius_rsun"], star["mass_msun"])

            injected = LightCurveData(
                tic_id=clean.tic_id, sector=clean.sector, time=clean.time,
                flux=inject_transit(clean.time, clean.flux, period, t0, depth_ppm / 1e6, dur),
                flux_err=clean.flux_err, quality=clean.quality, meta=clean.meta,
            )
            det = run_tls(injected, star=star)
            recovered = bool(
                det is not None and det.sde is not None
                and det.sde >= config.DETECTION_SDE_THRESHOLD
                and periods_agree(det.period_days, period)
            )
            trials.append({
                "host": host, "tic_id": clean.tic_id,
                "injected_period_days": round(period, 4),
                "injected_depth_ppm": depth_ppm,
                "injected_duration_hours": round(dur * 24, 2),
                "recovered": recovered,
                "detected_sde": round(det.sde, 2) if det and det.sde is not None else None,
                "detected_period_days": round(det.period_days, 4) if det else None,
            })
            log.info("  inj %02d: P=%.2fd depth=%.0fppm -> %s",
                     i, period, depth_ppm, "RECOVERED" if recovered else "missed")

        for k in range(n_null_per_host):
            shift = int(rng.integers(len(clean.flux) // 4, 3 * len(clean.flux) // 4))
            null = LightCurveData(
                tic_id=clean.tic_id, sector=clean.sector, time=clean.time,
                flux=np.roll(clean.flux, shift), flux_err=clean.flux_err,
                quality=clean.quality, meta=clean.meta,
            )
            det = run_tls(null, star=star)
            false_alarm = bool(det is not None and det.sde is not None
                               and det.sde >= config.DETECTION_SDE_THRESHOLD)
            null_trials.append({
                "host": host, "shift": shift, "false_alarm": false_alarm,
                "sde": round(det.sde, 2) if det and det.sde is not None else None,
            })
            log.info("  null %d: %s", k, "FALSE ALARM" if false_alarm else "clean")

    return _summarize(trials, null_trials)


def _summarize(trials: list[dict], null_trials: list[dict]) -> dict:
    completeness_grid = []
    for depth in DEPTH_GRID_PPM:
        for lo, hi in PERIOD_BINS_DAYS:
            cell = [t for t in trials
                    if t["injected_depth_ppm"] == depth and lo <= t["injected_period_days"] < hi]
            if cell:
                completeness_grid.append({
                    "depth_ppm": depth,
                    "period_bin_days": [lo, hi],
                    "n_injected": len(cell),
                    "n_recovered": sum(t["recovered"] for t in cell),
                    "completeness": round(sum(t["recovered"] for t in cell) / len(cell), 3),
                })

    n_rec = sum(t["recovered"] for t in trials)
    n_false_period = sum(
        1 for t in trials
        if not t["recovered"] and t["detected_sde"] is not None
        and t["detected_sde"] >= config.DETECTION_SDE_THRESHOLD
    )
    n_null_fa = sum(t["false_alarm"] for t in null_trials)
    n_detections_total = n_rec + n_false_period + n_null_fa

    return {
        "n_injections": len(trials),
        "n_recovered": n_rec,
        "overall_completeness": round(n_rec / len(trials), 3) if trials else None,
        "completeness_grid": completeness_grid,
        "n_null_trials": len(null_trials),
        "n_null_false_alarms": n_null_fa,
        "n_wrong_period_detections": n_false_period,
        "reliability": round(n_rec / n_detections_total, 3) if n_detections_total else None,
        "reliability_definition": (
            "recovered injections / all SDE>=threshold detections "
            "(recovered + wrong-period + null-trial false alarms)"
        ),
        "trials": trials,
        "null_trials": null_trials,
    }
