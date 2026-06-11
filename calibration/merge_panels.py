"""Re-attach panel verdicts to a regenerated candidates.json.

After a pipeline re-run, candidate dossiers are rebuilt without their panel blocks.
This merges panel verdicts back from a backup — but ONLY for candidates whose
detection is unchanged (same id, period within 0.1%): a verdict must never be
attached to evidence it did not see.

  python -m calibration.merge_panels data/cache/candidates.pre-rerun.json data/candidates.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def merge(backup_path: Path, current_path: Path) -> int:
    backup = {c["id"]: c for c in json.loads(backup_path.read_text())}
    current = json.loads(current_path.read_text())
    attached = 0
    for c in current:
        old = backup.get(c["id"])
        if not old or not old.get("panel"):
            continue
        p_new = c["detection"].get("period_days")
        p_old = old["detection"].get("period_days")
        same = (
            p_new is None and p_old is None
        ) or (
            p_new is not None and p_old is not None
            and abs(p_new - p_old) / p_old < 0.001
        )
        if same:
            c["panel"] = old["panel"]
            attached += 1
    current_path.write_text(json.dumps(current, indent=1))
    print(f"re-attached {attached} panel blocks of {len(current)} candidates")
    return 0


if __name__ == "__main__":
    sys.exit(merge(Path(sys.argv[1]), Path(sys.argv[2])))
