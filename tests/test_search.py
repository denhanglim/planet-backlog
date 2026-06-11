"""The search must find what was injected, and stay quiet on pure noise."""

import numpy as np

from pipeline import config
from pipeline.search import run_tls, run_bls, periods_agree
from tests.conftest import synthetic_lcd, inject

SOLAR = {"limb_darkening": [0.4804, 0.1867], "mass_msun": 1.0, "radius_rsun": 1.0,
         "source": "test"}


def test_tls_recovers_injected_transit():
    lcd = inject(synthetic_lcd(n_days=16, seed=1), period=3.456, t0=1326.2, depth_ppm=5000,
                 duration_days=0.12)
    det = run_tls(lcd, star=SOLAR)
    assert det is not None
    assert det.sde >= config.DETECTION_SDE_THRESHOLD
    assert periods_agree(det.period_days, 3.456)
    assert 3000 < det.depth_ppm < 8000


def test_bls_agrees_with_tls_on_injection():
    lcd = inject(synthetic_lcd(n_days=16, seed=2), period=2.2, t0=1325.5, depth_ppm=8000,
                 duration_days=0.1)
    bls = run_bls(lcd)
    assert bls is not None
    assert periods_agree(bls.period_days, 2.2)


def test_no_detection_on_pure_noise():
    det = run_tls(synthetic_lcd(n_days=16, seed=3), star=SOLAR)
    # TLS always returns its best peak; it must simply be sub-threshold
    assert det is None or det.sde < config.DETECTION_SDE_THRESHOLD


def test_periods_agree_harmonics():
    assert periods_agree(2.0, 2.0)
    assert periods_agree(1.0, 2.0)   # half
    assert periods_agree(4.0, 2.0)   # double
    assert not periods_agree(2.7, 2.0)
