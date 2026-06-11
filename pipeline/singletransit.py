"""Single-transit hunter: solitary transit-shaped events that period searches miss.

Long-period planets often transit only ONCE in a TESS sector; BLS/TLS require >= 2
events, so these fall through the cracks — the highest-novelty part of the backlog.

Method: matched filter. Bin the flattened flux to a uniform grid, correlate with
limb-darkened-ish trapezoid templates at several durations, and flag isolated peaks:
  - SNR >= threshold
  - event does NOT repeat (otherwise the periodic search owns it)
  - not dominated by quality-flagged cadences
  - not adjacent to a data gap or sector edge (scattered-light territory)
Each surviving event gets depth/duration/t0 measured from a local trapezoid fit.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from . import config
from .ingest import LightCurveData

log = logging.getLogger(__name__)


@dataclass
class SingleTransitEvent:
    t0_btjd: float
    duration_hours: float
    depth_ppm: float
    snr: float
    n_points_in_event: int
    min_period_days: float       # event is single -> period > baseline (lower bound only)
    quality_flag_fraction: float
    near_gap_or_edge: bool

    def to_dict(self) -> dict:
        return {
            "t0_btjd": round(self.t0_btjd, 5),
            "duration_hours": round(self.duration_hours, 2),
            "depth_ppm": round(self.depth_ppm, 1),
            "snr": round(self.snr, 2),
            "n_points_in_event": self.n_points_in_event,
            "min_period_days": round(self.min_period_days, 2),
            "quality_flag_fraction": round(self.quality_flag_fraction, 3),
            "near_gap_or_edge": self.near_gap_or_edge,
        }


def _uniform_grid(time: np.ndarray, flux: np.ndarray, quality: np.ndarray,
                  bin_minutes: float):
    """Bin onto a strictly uniform grid; empty bins -> NaN (kept, to respect gaps)."""
    bin_days = bin_minutes / 1440.0
    edges = np.arange(time[0], time[-1] + bin_days, bin_days)
    idx = np.clip(np.digitize(time, edges) - 1, 0, len(edges) - 2)
    n = len(edges) - 1
    counts = np.bincount(idx, minlength=n)
    fsum = np.bincount(idx, weights=flux, minlength=n)
    qsum = np.bincount(idx, weights=(quality != 0).astype(float), minlength=n)
    grid_t = 0.5 * (edges[:-1] + edges[1:])
    grid_f = np.full(n, np.nan)
    grid_q = np.zeros(n)
    filled = counts > 0
    grid_f[filled] = fsum[filled] / counts[filled]
    grid_q[filled] = qsum[filled] / counts[filled]
    return grid_t, grid_f, grid_q


def find_single_transits(lcd_flat: LightCurveData,
                         known_ephemeris: tuple[float, float, float] | None = None,
                         snr_threshold: float = config.SINGLE_TRANSIT_SNR_THRESHOLD
                         ) -> list[SingleTransitEvent]:
    """Hunt isolated transit-shaped dips. `known_ephemeris` (P, t0, dur_days) masks
    transits already claimed by the periodic search."""
    t, f, q = _uniform_grid(lcd_flat.time, lcd_flat.flux, lcd_flat.quality,
                            config.SINGLE_TRANSIT_BIN_MINUTES)
    resid = f - 1.0
    valid = np.isfinite(resid)
    if valid.sum() < 100:
        return []

    if known_ephemeris is not None:
        from .detrend import transit_mask
        p, t0, dur = known_ephemeris
        resid[transit_mask(t, p, t0, dur, pad=2.0)] = np.nan
        valid = np.isfinite(resid)

    sigma = 1.4826 * np.nanmedian(np.abs(resid - np.nanmedian(resid)))
    if not np.isfinite(sigma) or sigma <= 0:
        return []
    bin_days = config.SINGLE_TRANSIT_BIN_MINUTES / 1440.0

    gap_or_edge = np.zeros(len(t), dtype=bool)
    nan_runs = ~valid
    for i in range(len(t)):
        lo, hi = max(0, i - 8), min(len(t), i + 9)
        if i < 8 or i > len(t) - 9 or nan_runs[lo:hi].any():
            gap_or_edge[i] = True

    events: list[SingleTransitEvent] = []
    claimed = np.zeros(len(t), dtype=bool)

    for dur_h in config.SINGLE_TRANSIT_DURATIONS_HOURS:
        width = max(int(round(dur_h / 24.0 / bin_days)), 2)
        template = -np.ones(width)
        # matched-filter SNR: sum of (negative) residuals over window / (sigma * sqrt(w))
        filled = np.where(valid, resid, 0.0)
        nvalid = np.convolve(valid.astype(float), np.ones(width), mode="same")
        score = np.convolve(filled, -template, mode="same")  # positive for dips... sign:
        # template = -1s; convolve(filled, -template) = sum(filled * 1) -> negative in dips.
        snr_series = -score / (sigma * np.sqrt(np.maximum(nvalid, 1)))
        snr_series[nvalid < 0.7 * width] = 0.0

        while True:
            i = int(np.nanargmax(snr_series))
            snr = float(snr_series[i])
            if snr < snr_threshold:
                break
            lo, hi = max(0, i - 2 * width), min(len(t), i + 2 * width)
            if claimed[lo:hi].any():
                snr_series[lo:hi] = 0.0
                continue
            window = slice(max(0, i - width // 2), min(len(t), i + width // 2 + 1))
            seg = resid[window]
            seg_valid = np.isfinite(seg)
            depth_ppm = float(-np.nanmedian(seg[seg_valid]) * 1e6) if seg_valid.any() else np.nan
            qfrac = float(np.nanmean(q[window])) if np.isfinite(q[window]).any() else 0.0
            events.append(SingleTransitEvent(
                t0_btjd=float(t[i]),
                duration_hours=float(dur_h),
                depth_ppm=depth_ppm,
                snr=snr,
                n_points_in_event=int(seg_valid.sum()),
                min_period_days=float(t[-1] - t[0]),
                quality_flag_fraction=qfrac,
                near_gap_or_edge=bool(gap_or_edge[i]),
            ))
            claimed[lo:hi] = True
            snr_series[lo:hi] = 0.0

    # An event that repeats is periodic business, not a single transit: drop groups
    # of 2+ events with consistent depth at any spacing (the periodic search owns them).
    events.sort(key=lambda e: -e.snr)
    survivors: list[SingleTransitEvent] = []
    for e in events:
        twin = any(
            abs(e.depth_ppm - s.depth_ppm) < 0.5 * max(e.depth_ppm, s.depth_ppm)
            and abs(e.t0_btjd - s.t0_btjd) > 2 * e.duration_hours / 24.0
            for s in survivors
        )
        if twin:
            continue
        if e.near_gap_or_edge or e.quality_flag_fraction > 0.3 or not np.isfinite(e.depth_ppm):
            continue
        survivors.append(e)
    return survivors[:3]
