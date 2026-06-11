"""Ingest: pull TESS light curves and target pixel files from MAST via lightkurve.

All downloads are cached by lightkurve (~/.lightkurve/cache). Functions return
plain numpy arrays plus a metadata dict so downstream stages stay framework-free.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field

import numpy as np

log = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=UserWarning, module="lightkurve")


@dataclass
class LightCurveData:
    """One sector of one star, SPOC 2-min PDCSAP photometry."""

    tic_id: int
    sector: int
    time: np.ndarray          # BTJD days, NaN-free
    flux: np.ndarray          # normalized PDCSAP flux
    flux_err: np.ndarray
    quality: np.ndarray       # SPOC quality bitmask, aligned with time
    meta: dict = field(default_factory=dict)

    @property
    def baseline_days(self) -> float:
        return float(self.time[-1] - self.time[0])


def fetch_lightcurve(target: str | int, sector: int | None = None) -> LightCurveData | None:
    """Download one SPOC 2-min light curve. `target` is a name ("WASP-18") or TIC int.

    Returns None (and logs why) if nothing is available — never fabricates.
    """
    import lightkurve as lk

    query = f"TIC {target}" if isinstance(target, int) else target
    try:
        sr = lk.search_lightcurve(query, mission="TESS", author="SPOC", exptime=120)
    except Exception as exc:
        log.warning("MAST search failed for %s: %s", query, exc)
        return None
    if len(sr) == 0:
        log.info("No SPOC 2-min data for %s", query)
        return None
    if sector is not None:
        mask = [int(m) == sector for m in sr.table["sequence_number"]]
        if not any(mask):
            log.info("No SPOC 2-min data for %s in sector %s", query, sector)
            return None
        sr = sr[mask]
    try:
        lc = sr[0].download()
    except Exception as exc:
        log.warning("Download failed for %s: %s", query, exc)
        return None
    return _to_data(lc)


def fetch_all_sectors(target: str | int, max_sectors: int = 3) -> list[LightCurveData]:
    """Download up to `max_sectors` SPOC 2-min sectors for a target (earliest first)."""
    import lightkurve as lk

    query = f"TIC {target}" if isinstance(target, int) else target
    try:
        sr = lk.search_lightcurve(query, mission="TESS", author="SPOC", exptime=120)
    except Exception as exc:
        log.warning("MAST search failed for %s: %s", query, exc)
        return []
    out: list[LightCurveData] = []
    for row in sr[:max_sectors]:
        try:
            out.append(_to_data(row.download()))
        except Exception as exc:
            log.warning("Download failed for %s row: %s", query, exc)
    return [d for d in out if d is not None]


def _to_data(lc) -> LightCurveData:
    """Normalize a lightkurve LightCurve to plain arrays. Keeps quality flags aligned."""
    lc = lc.normalize()
    time = np.asarray(lc.time.value, dtype=float)
    flux = np.asarray(lc.flux.value, dtype=float)
    err = np.asarray(lc.flux_err.value, dtype=float)
    quality = np.asarray(lc.quality.value if hasattr(lc.quality, "value") else lc.quality, dtype=int)

    good = np.isfinite(time) & np.isfinite(flux)
    return LightCurveData(
        tic_id=int(lc.meta.get("TICID", 0)),
        sector=int(lc.meta.get("SECTOR", -1)),
        time=time[good],
        flux=flux[good],
        flux_err=np.where(np.isfinite(err[good]), err[good], np.nanmedian(err)),
        quality=quality[good],
        meta={
            "object": lc.meta.get("OBJECT"),
            "ra": float(lc.meta.get("RA_OBJ", np.nan)),
            "dec": float(lc.meta.get("DEC_OBJ", np.nan)),
            "tmag": float(lc.meta.get("TESSMAG", np.nan)),
            "teff": _safe_float(lc.meta.get("TEFF")),
            "radius": _safe_float(lc.meta.get("RADIUS")),
            "data_product": "TESS SPOC 2-min PDCSAP",
            "filename": str(lc.meta.get("FILENAME", "")),
        },
    )


def _safe_float(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def fetch_tpf(tic_id: int, sector: int):
    """Download the SPOC target pixel file for centroid analysis. None on failure."""
    import lightkurve as lk

    try:
        sr = lk.search_targetpixelfile(
            f"TIC {tic_id}", mission="TESS", author="SPOC", exptime=120, sector=sector
        )
        if len(sr) == 0:
            return None
        return sr[0].download()
    except Exception as exc:
        log.warning("TPF download failed for TIC %s sector %s: %s", tic_id, sector, exc)
        return None


def list_sector_targets(sector: int, n: int, seed: int, exclude_tics: set[int]) -> list[int]:
    """Sample n TIC IDs with SPOC 2-min light curves in a sector, excluding known objects.

    This is the honest 'backlog' batch: targets the curated pipelines already observed
    but that are not in the TOI / confirmed-planet catalogs.
    """
    from astroquery.mast import Observations

    obs = Observations.query_criteria(
        obs_collection="TESS",
        dataproduct_type="timeseries",
        provenance_name="SPOC",
        sequence_number=sector,
    )
    tics: set[int] = set()
    for name in obs["target_name"]:
        try:
            tics.add(int(name))
        except (TypeError, ValueError):
            continue
    pool = sorted(tics - set(exclude_tics))
    rng = np.random.default_rng(seed)
    if len(pool) <= n:
        return pool
    return sorted(rng.choice(pool, size=n, replace=False).tolist())
