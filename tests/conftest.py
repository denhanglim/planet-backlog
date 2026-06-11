import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.ingest import LightCurveData  # noqa: E402


def synthetic_lcd(n_days: float = 27.0, cadence_min: float = 2.0, noise_ppm: float = 200.0,
                  seed: int = 0) -> LightCurveData:
    """White-noise light curve, TESS-like cadence, with a mid-sector downlink gap."""
    rng = np.random.default_rng(seed)
    t = np.arange(0, n_days, cadence_min / 1440.0) + 1325.0  # BTJD-ish epoch
    gap = (t > 1325.0 + n_days / 2 - 0.5) & (t < 1325.0 + n_days / 2 + 0.5)
    t = t[~gap]
    f = 1.0 + rng.normal(0, noise_ppm / 1e6, len(t))
    return LightCurveData(
        tic_id=999000111, sector=99, time=t, flux=f,
        flux_err=np.full(len(t), noise_ppm / 1e6),
        quality=np.zeros(len(t), dtype=int),
        meta={"object": "SYNTHETIC", "ra": 10.0, "dec": -45.0, "tmag": 9.0,
              "data_product": "synthetic"},
    )


@pytest.fixture
def quiet_lcd() -> LightCurveData:
    return synthetic_lcd()


def inject(lcd: LightCurveData, period: float, t0: float, depth_ppm: float,
           duration_days: float) -> LightCurveData:
    from calibration.injection import inject_transit

    return LightCurveData(
        tic_id=lcd.tic_id, sector=lcd.sector, time=lcd.time,
        flux=inject_transit(lcd.time, lcd.flux, period, t0, depth_ppm / 1e6, duration_days),
        flux_err=lcd.flux_err, quality=lcd.quality, meta=lcd.meta,
    )
