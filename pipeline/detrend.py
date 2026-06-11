"""Detrend: remove stellar variability + instrument systematics, preserve transit shape.

Strategy: clip upper outliers only (flares — transits live on the lower side), then
Savitzky-Golay flatten with a window long compared to any plausible transit duration.
When an ephemeris is known (re-search after a detection), in-transit cadences are
masked out of the trend fit so the transit floor is not absorbed into the trend.
"""

from __future__ import annotations

import numpy as np

from . import config
from .ingest import LightCurveData


def transit_mask(time: np.ndarray, period: float, t0: float, duration_days: float,
                 pad: float = 1.5) -> np.ndarray:
    """True where `time` falls within pad*duration/2 of a transit center."""
    phase = (time - t0 + 0.5 * period) % period - 0.5 * period
    return np.abs(phase) < (pad * duration_days / 2.0)


def detrend(lcd: LightCurveData,
            mask_ephemeris: tuple[float, float, float] | None = None) -> LightCurveData:
    """Return a flattened copy. mask_ephemeris = (period, t0, duration_days) to protect."""
    import lightkurve as lk

    lc = lk.LightCurve(time=lcd.time, flux=lcd.flux, flux_err=lcd.flux_err)

    # Upper-side clip only: flares and pointing excursions, never transit points.
    clean, clip_mask = lc.remove_outliers(
        sigma_upper=config.OUTLIER_SIGMA_UPPER, sigma_lower=np.inf, return_mask=True
    )
    quality = lcd.quality[~clip_mask]

    cadence_days = float(np.median(np.diff(clean.time.value)))
    window = int(config.FLATTEN_WINDOW_DAYS / cadence_days)
    if window % 2 == 0:
        window += 1
    window = max(window, 11)

    mask = None
    if mask_ephemeris is not None:
        p, t0, dur = mask_ephemeris
        mask = transit_mask(clean.time.value, p, t0, dur)

    flat = clean.flatten(window_length=window, mask=mask, break_tolerance=int(0.5 / cadence_days))

    return LightCurveData(
        tic_id=lcd.tic_id,
        sector=lcd.sector,
        time=np.asarray(flat.time.value, dtype=float),
        flux=np.asarray(flat.flux.value, dtype=float),
        flux_err=np.asarray(flat.flux_err.value, dtype=float),
        quality=quality,
        meta={**lcd.meta, "detrended": True, "flatten_window_cadences": window},
    )


def bin_lightcurve(time: np.ndarray, flux: np.ndarray, flux_err: np.ndarray,
                   bin_minutes: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Time-binned (inverse-variance weighted) copy for the period search."""
    bin_days = bin_minutes / (24.0 * 60.0)
    edges = np.arange(time[0], time[-1] + bin_days, bin_days)
    idx = np.digitize(time, edges) - 1
    n_bins = len(edges) - 1

    w = 1.0 / np.clip(flux_err, 1e-10, None) ** 2
    sum_w = np.bincount(idx, weights=w, minlength=n_bins)[:n_bins]
    sum_wf = np.bincount(idx, weights=w * flux, minlength=n_bins)[:n_bins]
    sum_wt = np.bincount(idx, weights=w * time, minlength=n_bins)[:n_bins]

    filled = sum_w > 0
    return (
        sum_wt[filled] / sum_w[filled],
        sum_wf[filled] / sum_w[filled],
        1.0 / np.sqrt(sum_w[filled]),
    )


def estimate_rotation(lcd: LightCurveData) -> dict:
    """Lomb-Scargle stellar rotation estimate on the un-flattened light curve.

    Computed BEFORE flattening so spot modulation is still present.
    """
    from astropy.timeseries import LombScargle

    t, f = lcd.time, lcd.flux
    if len(t) < 100:
        return {"period_days": None, "power": None, "computed": False}
    ls = LombScargle(t, f)
    freq, power = ls.autopower(
        minimum_frequency=1.0 / 15.0, maximum_frequency=1.0 / 0.1, samples_per_peak=10
    )
    i = int(np.argmax(power))
    return {
        "period_days": float(1.0 / freq[i]),
        "power": float(power[i]),
        "computed": True,
    }
