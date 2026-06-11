"""Diagnostics must flag the failure modes they exist to catch."""

import numpy as np

from pipeline.diagnostics import odd_even, secondary_eclipse, transit_shape, fold_phase
from pipeline.ingest import LightCurveData
from tests.conftest import synthetic_lcd, inject


def _alternating_eb(seed=4):
    """EB disguised at half its true period: odd/even 'transits' differ in depth."""
    lcd = synthetic_lcd(seed=seed)
    period, t0 = 2.0, 1325.5
    epoch = np.round((lcd.time - t0) / period).astype(int)
    phase = ((lcd.time - t0 + 0.5 * period) % period) / period - 0.5
    in_t = np.abs(phase) < 0.02
    flux = lcd.flux.copy()
    flux[in_t & (epoch % 2 == 0)] *= 1 - 0.010   # 10000 ppm primary
    flux[in_t & (epoch % 2 != 0)] *= 1 - 0.004   # 4000 ppm secondary
    return LightCurveData(lcd.tic_id, lcd.sector, lcd.time, flux, lcd.flux_err,
                          lcd.quality, lcd.meta), period, t0


def test_odd_even_flags_alternating_depths():
    lcd, period, t0 = _alternating_eb()
    res = odd_even(lcd, period, t0, duration_days=0.08)
    assert res["computed"]
    assert res["difference_sigma"] > 5


def test_odd_even_clean_for_planet():
    lcd = inject(synthetic_lcd(seed=5), period=3.0, t0=1326.0, depth_ppm=6000,
                 duration_days=0.1)
    res = odd_even(lcd, 3.0, 1326.0, 0.1)
    assert res["computed"]
    assert res["difference_sigma"] < 3


def test_secondary_eclipse_detected():
    lcd = synthetic_lcd(seed=6)
    period, t0 = 3.0, 1326.0
    phase = fold_phase(lcd.time, period, t0)
    flux = lcd.flux.copy()
    flux[np.abs(phase) < 0.015] *= 1 - 0.008                  # primary
    flux[np.abs(np.abs(phase) - 0.5) < 0.015] *= 1 - 0.003    # secondary at phase 0.5
    lcd2 = LightCurveData(lcd.tic_id, lcd.sector, lcd.time, flux, lcd.flux_err,
                          lcd.quality, lcd.meta)
    res = secondary_eclipse(lcd2, period, t0, duration_days=0.09)
    assert res["computed"]
    assert res["depth_ppm"] > 1500
    assert res["significance_sigma"] > 4


def test_no_secondary_for_planet():
    lcd = inject(synthetic_lcd(seed=7), period=3.0, t0=1326.0, depth_ppm=6000,
                 duration_days=0.1)
    res = secondary_eclipse(lcd, 3.0, 1326.0, 0.1)
    assert res["computed"]
    assert res["significance_sigma"] < 4


def test_shape_u_vs_v():
    # boxy (flat-bottomed) transit
    lcd_u = inject(synthetic_lcd(seed=8), period=3.0, t0=1326.0, depth_ppm=10000,
                   duration_days=0.15)
    res_u = transit_shape(lcd_u, 3.0, 1326.0, 0.15)
    assert res_u["computed"]
    assert res_u["shape_param"] > 0.3

    # V-shaped dip: pure triangle
    lcd = synthetic_lcd(seed=9)
    phase = fold_phase(lcd.time, 3.0, 1326.0)
    dur_phase = 0.15 / 3.0
    tri = np.clip(1 - np.abs(phase) / (dur_phase / 2), 0, 1)
    flux = lcd.flux * (1 - 0.01 * tri)
    lcd_v = LightCurveData(lcd.tic_id, lcd.sector, lcd.time, flux, lcd.flux_err,
                           lcd.quality, lcd.meta)
    res_v = transit_shape(lcd_v, 3.0, 1326.0, 0.15)
    assert res_v["computed"]
    assert res_v["shape_param"] < res_u["shape_param"]
    assert res_v["v_shaped"]
