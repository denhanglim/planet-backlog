"""Calibration gate CLI: known-planet recovery + injection-recovery -> data/calibration.json.

  python -m calibration.run                      # full gate
  python -m calibration.run --skip-injection     # recovery only (fast)
  python -m calibration.run --injections 12      # smaller injection budget
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone

from pipeline import __version__, config
from pipeline.contract import sanitize, write_json

from . import injection, known_recovery

log = logging.getLogger("calibration.run")


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-injection", action="store_true")
    ap.add_argument("--injections", type=int, default=24, help="per host")
    ap.add_argument("--nulls", type=int, default=4, help="null trials per host")
    ap.add_argument("--out", default=config.DATA_DIR / "calibration.json")
    args = ap.parse_args(argv)

    log.info("=== known-planet recovery on %d hosts", len(config.CALIBRATION_HOSTS))
    recovery = known_recovery.run()
    log.info("recovery: %s/%s (%s)", recovery["recovered"],
             recovery["hosts_with_data_and_truth"], recovery["recovery_rate"])

    inj = None
    if not args.skip_injection:
        log.info("=== injection-recovery: %d per host + %d nulls", args.injections, args.nulls)
        inj = injection.run(n_injections_per_host=args.injections, n_null_per_host=args.nulls)
        log.info("completeness %s | reliability %s",
                 inj["overall_completeness"], inj["reliability"])

    payload = sanitize({
        "pipeline_version": __version__,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "detection_threshold_sde": config.DETECTION_SDE_THRESHOLD,
        "known_planet_recovery": recovery,
        "injection_recovery": inj,
        "scope_notes": [
            f"Injection budget: {args.injections} injections + {args.nulls} null trials per host "
            "(hundreds total, not thousands; single-session compute budget).",
            "Search runs on 10-min binned flux; depths near the per-bin noise floor at the "
            "shortest periods are the hardest cells.",
            "Null trials use 1-day block shuffles of the flux: intra-day noise structure "
            "preserved, longer coherent signals destroyed. Known-planet transits AND "
            "secondary-eclipse windows are masked before injection/null trials.",
        ],
    })
    write_json(args.out, payload)
    log.info("wrote %s", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
