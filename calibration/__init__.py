"""Calibration gate: the system earns the right to present candidates here.

1. known_recovery — re-find confirmed planets in real TESS data; report recovery rate.
2. injection — inject synthetic transits into real light curves (known planets masked),
   run the search blind, measure completeness and reliability.

Nothing in data/candidates.json is presented as novel until this gate has run.
"""
