"""Vetting diagnostics — the computed evidence the AI panel reasons over.

Every function returns plain dicts of floats/bools plus a `computed` flag; when a
diagnostic cannot be computed (no TPF, network failure) it reports computed=False
with a reason instead of a fabricated value.
"""

from __future__ import annotations

import logging

import numpy as np
from scipy.optimize import least_squares

from . import config
from .detrend import transit_mask
from .ingest import LightCurveData

log = logging.getLogger(__name__)


# ---------------------------------------------------------------- folding helpers

def fold_phase(time: np.ndarray, period: float, t0: float) -> np.ndarray:
    """Phase in [-0.5, 0.5) with the transit at 0."""
    return ((time - t0 + 0.5 * period) % period) / period - 0.5


def folded_series(lcd: LightCurveData, period: float, t0: float,
                  max_points: int = 2000, n_bins: int = 200) -> dict:
    """Folded light curve for the dossier plot: thinned raw points + binned curve."""
    phase = fold_phase(lcd.time, period, t0)
    order = np.argsort(phase)
    phase, flux = phase[order], lcd.flux[order]

    if len(phase) > max_points:
        keep = np.linspace(0, len(phase) - 1, max_points).astype(int)
        raw_p, raw_f = phase[keep], flux[keep]
    else:
        raw_p, raw_f = phase, flux

    edges = np.linspace(-0.5, 0.5, n_bins + 1)
    idx = np.digitize(phase, edges) - 1
    idx = np.clip(idx, 0, n_bins - 1)
    counts = np.bincount(idx, minlength=n_bins)
    sums = np.bincount(idx, weights=flux, minlength=n_bins)
    filled = counts > 0
    centers = 0.5 * (edges[:-1] + edges[1:])

    return {
        "phase": raw_p.round(5).tolist(),
        "flux": raw_f.round(6).tolist(),
        "binned_phase": centers[filled].round(5).tolist(),
        "binned_flux": (sums[filled] / counts[filled]).round(6).tolist(),
    }


def _in_transit(phase: np.ndarray, dur_phase: float, frac: float = 0.5) -> np.ndarray:
    return np.abs(phase) < (frac * dur_phase)


def _depth_ppm(flux_in: np.ndarray, flux_out: np.ndarray) -> tuple[float, float]:
    """(depth_ppm, err_ppm) from in/out medians; err via out-of-transit scatter."""
    if len(flux_in) < 3:
        return np.nan, np.nan
    depth = (np.median(flux_out) - np.median(flux_in)) * 1e6
    err = 1.4826 * np.median(np.abs(flux_out - np.median(flux_out))) * 1e6 / np.sqrt(len(flux_in))
    return float(depth), float(err)


# ---------------------------------------------------------------- core diagnostics

def measure_depth(lcd: LightCurveData, period: float, t0: float, duration_days: float) -> dict:
    """Re-measure depth on full 2-min cadence (search ran on binned flux)."""
    phase = fold_phase(lcd.time, period, t0)
    dur_phase = duration_days / period
    in_t = _in_transit(phase, dur_phase)
    out = np.abs(phase) > 1.5 * dur_phase
    depth, err = _depth_ppm(lcd.flux[in_t], lcd.flux[out])
    return {
        "depth_ppm": depth,
        "depth_err_ppm": err,
        "n_in_transit": int(in_t.sum()),
        "computed": bool(np.isfinite(depth)),
    }


def odd_even(lcd: LightCurveData, period: float, t0: float, duration_days: float) -> dict:
    """Depth of odd vs even epochs. A mismatch is the classic eclipsing-binary tell
    (the 'transit' is alternating primary/secondary eclipses at half the true period)."""
    epoch = np.round((lcd.time - t0) / period).astype(int)
    phase = fold_phase(lcd.time, period, t0)
    dur_phase = duration_days / period
    in_t = _in_transit(phase, dur_phase)
    out = np.abs(phase) > 1.5 * dur_phase

    odd_in = in_t & (epoch % 2 != 0)
    even_in = in_t & (epoch % 2 == 0)
    d_odd, e_odd = _depth_ppm(lcd.flux[odd_in], lcd.flux[out])
    d_even, e_even = _depth_ppm(lcd.flux[even_in], lcd.flux[out])

    if not (np.isfinite(d_odd) and np.isfinite(d_even)):
        return {"computed": False, "reason": "too few in-transit points in odd or even epochs"}

    err = float(np.hypot(e_odd, e_even))
    sigma = abs(d_odd - d_even) / err if err > 0 else np.nan
    return {
        "depth_odd_ppm": d_odd,
        "depth_even_ppm": d_even,
        "difference_sigma": float(sigma),
        "n_odd": int(odd_in.sum()),
        "n_even": int(even_in.sum()),
        "computed": True,
    }


def secondary_eclipse(lcd: LightCurveData, period: float, t0: float, duration_days: float) -> dict:
    """Search for a dip at phase 0.5. A significant secondary at planetary depth means
    an eclipsing binary (planetary occultations are far below TESS noise here).
    Significance is bootstrapped against random non-transit phases."""
    phase = fold_phase(lcd.time, period, t0)  # transit at 0
    dur_phase = duration_days / period
    w = max(config.SECONDARY_SEARCH_WINDOW_PHASE, dur_phase)

    # shift so secondary sits at phase 0 of a re-fold
    sec = np.abs(np.abs(phase) - 0.5) < w / 2
    out = (np.abs(phase) > 1.5 * dur_phase) & (np.abs(np.abs(phase) - 0.5) > w)
    d_sec, e_sec = _depth_ppm(lcd.flux[sec], lcd.flux[out])
    if not np.isfinite(d_sec):
        return {"computed": False, "reason": "no coverage at phase 0.5"}

    # bootstrap: depth measured in 200 random windows away from primary & secondary
    rng = np.random.default_rng(0)
    null_depths = []
    for _ in range(200):
        c = rng.uniform(-0.5, 0.5)
        if abs(c) < 2 * dur_phase or abs(abs(c) - 0.5) < w:
            continue
        win = np.abs(phase - c) < w / 2
        if win.sum() < 5:
            continue
        d, _ = _depth_ppm(lcd.flux[win], lcd.flux[out])
        if np.isfinite(d):
            null_depths.append(d)
    null = np.array(null_depths)
    if len(null) < 20:
        sigma = d_sec / e_sec if e_sec > 0 else np.nan
        method = "analytic"
    else:
        spread = 1.4826 * np.median(np.abs(null - np.median(null)))
        sigma = (d_sec - np.median(null)) / spread if spread > 0 else np.nan
        method = "bootstrap-200-windows"

    return {
        "depth_ppm": d_sec,
        "significance_sigma": float(sigma),
        "n_points": int(sec.sum()),
        "method": method,
        "computed": True,
    }


def transit_shape(lcd: LightCurveData, period: float, t0: float, duration_days: float) -> dict:
    """Trapezoid fit to the folded transit. shape = flat-bottom / total duration:
    ~0 -> V-shaped (grazing EB-like), -> 1 boxy. Also returns fitted depth/duration."""
    phase = fold_phase(lcd.time, period, t0)
    dur_phase = duration_days / period
    near = np.abs(phase) < 3 * dur_phase
    if near.sum() < 30:
        return {"computed": False, "reason": "too few points near transit"}
    x, y = phase[near], lcd.flux[near]

    def model(params, xx):
        depth, t_total, t_flat, x0 = params
        half_t, half_f = t_total / 2, t_flat / 2
        m = np.ones_like(xx)
        dx = np.abs(xx - x0)
        ingress = (dx >= half_f) & (dx < half_t)
        m[dx < half_f] = 1 - depth
        with np.errstate(divide="ignore", invalid="ignore"):
            slope = (dx[ingress] - half_f) / max(half_t - half_f, 1e-8)
        m[ingress] = 1 - depth * (1 - slope)
        return m

    depth0 = max(1 - np.min(y), 1e-5)
    p0 = [depth0, dur_phase, 0.5 * dur_phase, 0.0]
    bounds = ([1e-7, 0.2 * dur_phase, 0.0, -0.5 * dur_phase],
              [0.5, 6 * dur_phase, 6 * dur_phase, 0.5 * dur_phase])
    try:
        fit = least_squares(
            lambda p: model(p, x) - y, p0, bounds=bounds, loss="soft_l1", max_nfev=2000
        )
        depth, t_total, t_flat, _ = fit.x
        t_flat = min(t_flat, t_total)
        return {
            "shape_param": float(t_flat / t_total),
            "fitted_depth_ppm": float(depth * 1e6),
            "fitted_duration_hours": float(t_total * period * 24),
            "v_shaped": bool(t_flat / t_total < 0.15),
            "computed": True,
        }
    except Exception as exc:
        return {"computed": False, "reason": f"trapezoid fit failed: {exc}"}


def centroid_shift(tic_id: int, sector: int, period: float, t0: float,
                   duration_days: float) -> dict:
    """In-transit vs out-of-transit flux-weighted centroid from the target pixel file.
    A significant shift means the dip comes from a nearby blended source, not the target."""
    from .ingest import fetch_tpf

    tpf = fetch_tpf(tic_id, sector)
    if tpf is None:
        return {"computed": False, "reason": "TPF unavailable"}
    try:
        time = np.asarray(tpf.time.value, dtype=float)
        col, row = tpf.estimate_centroids(aperture_mask="pipeline")
        col = np.asarray(col.value, dtype=float)
        row = np.asarray(row.value, dtype=float)
        ok = np.isfinite(col) & np.isfinite(row)
        time, col, row = time[ok], col[ok], row[ok]

        in_t = transit_mask(time, period, t0, duration_days, pad=1.0)
        out = ~transit_mask(time, period, t0, duration_days, pad=3.0)
        if in_t.sum() < 10 or out.sum() < 100:
            return {"computed": False, "reason": "too few cadences for centroid comparison"}

        dc = np.median(col[in_t]) - np.median(col[out])
        dr = np.median(row[in_t]) - np.median(row[out])
        # null distribution: same-size random cadence groups out of transit
        rng = np.random.default_rng(1)
        n = int(in_t.sum())
        out_idx = np.where(out)[0]
        nulls = []
        for _ in range(200):
            pick = rng.choice(out_idx, size=n, replace=False)
            nulls.append(np.hypot(np.median(col[pick]) - np.median(col[out]),
                                  np.median(row[pick]) - np.median(row[out])))
        nulls = np.array(nulls)
        shift_pix = float(np.hypot(dc, dr))
        spread = 1.4826 * np.median(np.abs(nulls - np.median(nulls)))
        sigma = (shift_pix - np.median(nulls)) / spread if spread > 0 else np.nan
        return {
            "shift_pixels": shift_pix,
            "shift_arcsec": shift_pix * config.TESS_PIXEL_ARCSEC,
            "significance_sigma": float(sigma),
            "n_in_transit_cadences": n,
            "computed": True,
        }
    except Exception as exc:
        return {"computed": False, "reason": f"centroid analysis failed: {exc}"}


def gaia_neighbors(ra: float, dec: float, target_tmag: float) -> dict:
    """Nearby TIC sources inside ~3 TESS pixels: blend candidates. Reports each
    neighbor's separation, Tmag, and flux ratio vs the target."""
    from astroquery.mast import Catalogs
    from astropy.coordinates import SkyCoord
    import astropy.units as u

    if not (np.isfinite(ra) and np.isfinite(dec)):
        return {"computed": False, "reason": "no target coordinates"}
    try:
        coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg)
        tab = Catalogs.query_region(
            coord, radius=config.NEIGHBOR_SEARCH_RADIUS_ARCSEC * u.arcsec, catalog="TIC"
        )
    except Exception as exc:
        return {"computed": False, "reason": f"TIC cone search failed: {exc}"}

    neighbors = []
    total_neighbor_flux = 0.0
    for r in tab:
        sep = float(r["dstArcSec"])
        tmag = float(r["Tmag"]) if np.isfinite(r["Tmag"]) else None
        if sep < 1.0:   # the target itself
            continue
        if tmag is None:
            continue
        flux_ratio = 10 ** (-0.4 * (tmag - target_tmag)) if np.isfinite(target_tmag) else None
        if flux_ratio is not None:
            total_neighbor_flux += flux_ratio
        neighbors.append({
            "tic_id": int(r["ID"]),
            "sep_arcsec": round(sep, 2),
            "tmag": round(tmag, 2),
            "flux_ratio_vs_target": round(flux_ratio, 5) if flux_ratio is not None else None,
        })
    neighbors.sort(key=lambda x: x["sep_arcsec"])
    return {
        "n_neighbors": len(neighbors),
        "neighbors": neighbors[:10],
        "total_neighbor_flux_fraction": round(float(total_neighbor_flux), 5),
        "search_radius_arcsec": config.NEIGHBOR_SEARCH_RADIUS_ARCSEC,
        "computed": True,
    }


def systematics_flags(lcd: LightCurveData, period: float, t0: float,
                      duration_days: float) -> dict:
    """Overlap of transit windows with SPOC quality flags, momentum dumps (bit 5,
    value 32), data gaps, and sector edges."""
    in_t = transit_mask(lcd.time, period, t0, duration_days, pad=1.0)
    n_in = int(in_t.sum())
    if n_in == 0:
        return {"computed": False, "reason": "no in-transit cadences"}

    q = lcd.quality
    frac_flagged = float((q[in_t] != 0).mean())
    frac_momentum = float(((q[in_t] & 32) != 0).mean())

    # transit centers
    n_min = int(np.ceil((lcd.time[0] - t0) / period))
    n_max = int(np.floor((lcd.time[-1] - t0) / period))
    centers = [t0 + n * period for n in range(n_min, n_max + 1)]
    centers = [c for c in centers if lcd.time[0] <= c <= lcd.time[-1]]

    gaps = np.where(np.diff(lcd.time) > 0.2)[0]
    gap_edges = []
    for g in gaps:
        gap_edges += [lcd.time[g], lcd.time[g + 1]]
    gap_edges += [lcd.time[0], lcd.time[-1]]

    near_edge = sum(
        1 for c in centers if any(abs(c - e) < max(duration_days, 0.25) for e in gap_edges)
    )
    return {
        "frac_in_transit_quality_flagged": round(frac_flagged, 4),
        "frac_in_transit_momentum_dump": round(frac_momentum, 4),
        "n_transits_in_data": len(centers),
        "n_transits_near_gap_or_edge": int(near_edge),
        "computed": True,
    }


def rotation_check(rotation: dict, period: float) -> dict:
    """Compare candidate period to the stellar rotation period and its harmonics."""
    if not rotation.get("computed") or not rotation.get("period_days"):
        return {"computed": False, "reason": "no rotation estimate"}
    p_rot = rotation["period_days"]
    matches = []
    for ratio in config.HARMONIC_RATIOS:
        target = p_rot * ratio
        if target > 0 and abs(period - target) / target < 0.03:
            matches.append(ratio)
    return {
        "rotation_period_days": round(p_rot, 4),
        "rotation_power": round(rotation.get("power") or 0.0, 4),
        "period_matches_rotation_harmonic": bool(matches),
        "matched_ratios": matches,
        "computed": True,
    }


# ---------------------------------------------------------------- driver

def run_all(lcd_flat: LightCurveData, rotation: dict, period: float, t0: float,
            duration_days: float, ra: float, dec: float, tmag: float,
            with_centroid: bool = True) -> dict:
    """Compute the full diagnostic block for one candidate."""
    diag = {
        "depth": measure_depth(lcd_flat, period, t0, duration_days),
        "odd_even": odd_even(lcd_flat, period, t0, duration_days),
        "secondary": secondary_eclipse(lcd_flat, period, t0, duration_days),
        "shape": transit_shape(lcd_flat, period, t0, duration_days),
        "neighbors": gaia_neighbors(ra, dec, tmag),
        "systematics": systematics_flags(lcd_flat, period, t0, duration_days),
        "rotation": rotation_check(rotation, period),
    }
    if with_centroid:
        diag["centroid"] = centroid_shift(lcd_flat.tic_id, lcd_flat.sector, period, t0, duration_days)
    else:
        diag["centroid"] = {"computed": False, "reason": "skipped (below vetting threshold)"}
    return diag
