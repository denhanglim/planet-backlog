"""Definition-of-done test: the pipeline must recover a known planet in real TESS data.

Marked `network`: downloads (or reads the lightkurve cache of) pi Men sector 1 SPOC
data from MAST and re-detects pi Men c. Run with: pytest -m network
"""

import pytest

from pipeline import config
from pipeline.detrend import detrend
from pipeline.ingest import fetch_lightcurve
from pipeline.search import periods_agree, run_tls, stellar_params

PI_MEN_C_PUBLISHED_PERIOD_DAYS = 6.2679  # NASA Exoplanet Archive (pscomppars)


@pytest.mark.network
def test_pipeline_recovers_pi_men_c():
    lcd = fetch_lightcurve("pi Men", sector=1)
    assert lcd is not None, "MAST download failed — cannot verify recovery"
    assert lcd.tic_id == 261136679

    flat = detrend(lcd)
    det = run_tls(flat, star=stellar_params(lcd.tic_id))

    assert det is not None, "TLS search failed"
    assert det.sde is not None and det.sde >= config.DETECTION_SDE_THRESHOLD, (
        f"pi Men c not detected above threshold (SDE={det.sde})"
    )
    assert periods_agree(det.period_days, PI_MEN_C_PUBLISHED_PERIOD_DAYS), (
        f"recovered period {det.period_days} does not match published "
        f"{PI_MEN_C_PUBLISHED_PERIOD_DAYS}"
    )
    # pi Men c is ~300 ppm; recovered depth must be the right order of magnitude
    assert 100 < det.depth_ppm < 600
