"""Single-transit hunter: find one isolated dip, ignore noise and repeated events."""

import numpy as np

from pipeline.ingest import LightCurveData
from pipeline.singletransit import find_single_transits
from tests.conftest import synthetic_lcd


def _with_single_dip(depth_ppm=4000, t0=1331.0, dur_days=8 / 24, seed=10):
    lcd = synthetic_lcd(seed=seed)
    flux = lcd.flux.copy()
    in_t = np.abs(lcd.time - t0) < dur_days / 2
    flux[in_t] *= 1 - depth_ppm / 1e6
    return LightCurveData(lcd.tic_id, lcd.sector, lcd.time, flux, lcd.flux_err,
                          lcd.quality, lcd.meta)


def test_finds_single_transit():
    lcd = _with_single_dip()
    events = find_single_transits(lcd)
    assert len(events) >= 1
    best = events[0]
    assert abs(best.t0_btjd - 1331.0) < 0.3
    assert best.snr >= 8
    assert 2000 < best.depth_ppm < 8000


def test_quiet_curve_yields_nothing():
    events = find_single_transits(synthetic_lcd(seed=11))
    assert events == []


def test_event_near_gap_is_rejected():
    # place the dip right at the downlink gap edge (mid-sector gap at ~1338)
    lcd = _with_single_dip(t0=1338.6, seed=12)
    events = find_single_transits(lcd)
    assert all(abs(e.t0_btjd - 1338.6) > 0.3 for e in events)
