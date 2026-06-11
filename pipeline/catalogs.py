"""Catalog cross-checks: TOI list (ExoFOP), confirmed planets (NASA Exoplanet Archive),
known false positives / EBs (TFOPWG dispositions; Villanova TESS-EB best-effort).

This is dedup defense: a candidate matching any catalog is NEVER presented as a
discovery. Catalogs are downloaded once and cached under data/cache/ with timestamps.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from . import config

log = logging.getLogger(__name__)

TOI_URL = "https://exofop.ipac.caltech.edu/tess/download_toi.php?sort=toi&output=csv"
NASA_TAP = (
    "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query="
    "select+pl_name,tic_id,pl_orbper,pl_rade,pl_trandep,disc_facility,discoverymethod,tran_flag"
    "+from+pscomppars&format=csv"
)
VILLANOVA_EB_URL = "http://tessebs.villanova.edu/api/ebs/?format=json&limit=10000"


def _cached_download(url: str, dest: Path, max_age_days: float = 7.0) -> Path | None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and (time.time() - dest.stat().st_mtime) < max_age_days * 86400:
        return dest
    try:
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return dest
    except Exception as exc:
        log.warning("Catalog download failed (%s): %s", url, exc)
        return dest if dest.exists() else None


class Catalogs:
    """Loaded catalog tables + crossmatch logic."""

    def __init__(self, cache_dir: Path = config.CACHE_DIR):
        self.cache_dir = cache_dir
        self.toi: pd.DataFrame | None = None
        self.confirmed: pd.DataFrame | None = None
        self.ebs: pd.DataFrame | None = None
        self.status: dict = {}

    def load(self) -> "Catalogs":
        p = _cached_download(TOI_URL, self.cache_dir / "toi.csv")
        if p is not None:
            try:
                self.toi = pd.read_csv(p, low_memory=False)
                self.status["toi"] = f"loaded {len(self.toi)} rows"
            except Exception as exc:
                self.status["toi"] = f"parse failed: {exc}"
        else:
            self.status["toi"] = "download failed"

        p = _cached_download(NASA_TAP, self.cache_dir / "confirmed.csv")
        if p is not None:
            try:
                self.confirmed = pd.read_csv(p, low_memory=False)
                self.confirmed["tic_int"] = (
                    self.confirmed["tic_id"].astype(str).str.extract(r"(\d+)").astype(float)
                )
                self.status["confirmed"] = f"loaded {len(self.confirmed)} rows"
            except Exception as exc:
                self.status["confirmed"] = f"parse failed: {exc}"
        else:
            self.status["confirmed"] = "download failed"

        p = _cached_download(VILLANOVA_EB_URL, self.cache_dir / "tess_ebs.json")
        self.ebs = None
        if p is not None:
            try:
                raw = json.loads(p.read_text())
                rows = raw.get("results", raw) if isinstance(raw, dict) else raw
                self.ebs = pd.DataFrame(rows)
                self.status["ebs"] = f"loaded {len(self.ebs)} rows"
            except Exception as exc:
                self.status["ebs"] = f"parse failed: {exc} (best-effort source)"
        else:
            self.status["ebs"] = "unavailable (best-effort source; TFOPWG FP dispositions still active)"
        return self

    # ---------------------------------------------------------------- crossmatch

    def known_tics(self) -> set[int]:
        """All TIC IDs present in any catalog (used to exclude from the blind batch)."""
        tics: set[int] = set()
        if self.toi is not None and "TIC ID" in self.toi.columns:
            tics |= set(self.toi["TIC ID"].dropna().astype(int))
        if self.confirmed is not None:
            tics |= set(self.confirmed["tic_int"].dropna().astype(int))
        if self.ebs is not None:
            for col in ("tic_id", "tess_id", "TIC"):
                if col in self.ebs.columns:
                    tics |= set(pd.to_numeric(self.ebs[col], errors="coerce").dropna().astype(int))
                    break
        return tics

    def crossmatch(self, tic_id: int, period_days: float | None) -> dict:
        """Match a candidate by TIC ID and (when available) period/harmonics."""
        out: dict = {"toi": None, "confirmed": None, "eb": None, "verdict": "novel",
                     "catalog_status": self.status}

        def _period_match(p_known) -> bool:
            if period_days is None or p_known is None or not np.isfinite(p_known) or p_known <= 0:
                return False
            return any(
                abs(period_days - p_known * r) / (p_known * r) < config.PERIOD_MATCH_TOLERANCE
                for r in config.HARMONIC_RATIOS
            )

        if self.toi is not None and "TIC ID" in self.toi.columns:
            rows = self.toi[self.toi["TIC ID"] == tic_id]
            if len(rows):
                r = rows.iloc[0]
                p_toi = r.get("Period (days)")
                disp = str(r.get("TFOPWG Disposition", "") or "")
                out["toi"] = {
                    "toi": str(r.get("TOI")),
                    "period_days": float(p_toi) if pd.notna(p_toi) else None,
                    "tfopwg_disposition": disp,
                    "period_match": _period_match(p_toi if pd.notna(p_toi) else None),
                }
                out["verdict"] = "known-fp" if disp in ("FP", "FA") else "known-toi"

        if self.confirmed is not None:
            rows = self.confirmed[self.confirmed["tic_int"] == tic_id]
            if len(rows):
                best = None
                for _, r in rows.iterrows():
                    rec = {
                        "pl_name": r["pl_name"],
                        "period_days": float(r["pl_orbper"]) if pd.notna(r["pl_orbper"]) else None,
                        "radius_rearth": float(r["pl_rade"]) if pd.notna(r["pl_rade"]) else None,
                        "period_match": _period_match(r["pl_orbper"] if pd.notna(r["pl_orbper"]) else None),
                    }
                    if best is None or (rec["period_match"] and not best["period_match"]):
                        best = rec
                out["confirmed"] = best
                out["verdict"] = "known-planet"

        if self.ebs is not None and len(self.ebs):
            col = next((c for c in ("tic_id", "tess_id", "TIC") if c in self.ebs.columns), None)
            if col:
                rows = self.ebs[pd.to_numeric(self.ebs[col], errors="coerce") == tic_id]
                if len(rows):
                    out["eb"] = {"matched": True, "source": "Villanova TESS-EB"}
                    if out["verdict"] == "novel":
                        out["verdict"] = "known-eb"

        return out
