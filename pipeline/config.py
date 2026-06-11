"""Run configuration: target lists, search parameters, paths.

Calibration targets are referenced by NAME only — TIC IDs, ephemerides and stellar
parameters are resolved from MAST / the NASA Exoplanet Archive at runtime so that no
hand-typed identifier or period can silently corrupt a result (principle: no invented
numbers, not even by the build author).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"

# --- Calibration set: hosts of confirmed transiting planets with TESS 2-min SPOC data.
# Names resolve via MAST; ground-truth ephemerides come from the NASA Exoplanet Archive.
CALIBRATION_HOSTS = [
    "WASP-18",    # hot Jupiter, very deep, P ~ 0.94 d
    "WASP-121",   # hot Jupiter, P ~ 1.27 d
    "WASP-126",   # hot Jupiter, P ~ 3.29 d
    "WASP-100",   # hot Jupiter, P ~ 2.85 d
    "WASP-62",    # hot Jupiter, P ~ 4.41 d
    "pi Men",     # super-Earth pi Men c, shallow ~300 ppm, P ~ 6.27 d
    "LHS 3844",   # ultra-short-period rocky planet, P ~ 0.46 d
    "HD 219666",  # hot Neptune, P ~ 6.04 d
]

# --- Blind search batch: drawn at runtime from SPOC 2-min targets of this sector,
# excluding anything already in the TOI / confirmed-planet catalogs (those would not
# be "backlog"). Sector 1 chosen: well-studied, so catalog cross-checks are strongest.
BLIND_SECTOR = 1
BLIND_BATCH_SIZE = 40
BLIND_SAMPLE_SEED = 42

# --- Detrending
FLATTEN_WINDOW_DAYS = 0.75       # Savitzky-Golay window; long vs transit durations (hours)
OUTLIER_SIGMA_UPPER = 5.0        # clip flares; never clip the lower side (transits live there)

# --- Period search
PERIOD_MIN_DAYS = 0.5
PERIOD_MAX_DAYS = 15.0           # one TESS sector ~27 d -> 2 transits up to ~13 d
SEARCH_BIN_MINUTES = 10.0        # bin for the TLS/BLS search; diagnostics use full cadence
DETECTION_SDE_THRESHOLD = 9.0    # TLS SDE detection threshold (standard in the literature)
DETECTION_SNR_THRESHOLD = 7.0

# --- Single-transit hunter
SINGLE_TRANSIT_BIN_MINUTES = 30.0
SINGLE_TRANSIT_SNR_THRESHOLD = 8.0
SINGLE_TRANSIT_DURATIONS_HOURS = [2.0, 4.0, 8.0, 16.0]

# --- Diagnostics
SECONDARY_SEARCH_WINDOW_PHASE = 0.04   # half-width of window around phase 0.5
NEIGHBOR_SEARCH_RADIUS_ARCSEC = 63.0   # 3 TESS pixels
TESS_PIXEL_ARCSEC = 21.0

# --- Catalog crossmatch
PERIOD_MATCH_TOLERANCE = 0.02          # relative
HARMONIC_RATIOS = [0.5, 1.0, 2.0, 3.0, 1.0 / 3.0]
