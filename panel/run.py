"""Panel CLI: run six skeptics + judge on every candidate in data/candidates.json,
attach machine-consumable verdicts, enforce the mechanical survival rule, write back.

  python -m panel.run                       # all candidates missing a panel block
  python -m panel.run --id PB-...-P1        # one candidate
  python -m panel.run --force               # re-run even if panel block exists
  python -m panel.run --model sonnet
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from pipeline import config
from pipeline.contract import write_json

from . import PANEL_VERSION
from .driver import AgentCallError, call_agent
from .prompts import judge_prompt, skeptic_prompt
from .schemas import JUDGE_SCHEMA, SKEPTIC_NAMES, SKEPTIC_VERDICT_SCHEMA

log = logging.getLogger("panel.run")


def mechanical_status(skeptics: list[dict]) -> str:
    """Code-enforced survival rule — the judge cannot override a fatal kill."""
    ok = [s for s in skeptics if "error" not in s]
    if any(s["verdict"] == "killed" and s["lethality"] == "fatal" for s in ok):
        return "killed"
    if len(ok) < len(skeptics):
        return "flagged-for-review"          # a skeptic failed to run: incomplete vetting
    if any(s["lethality"] == "serious-concern" for s in ok):
        return "flagged-for-review"
    if any(s["verdict"] == "inconclusive" for s in ok):
        return "flagged-for-review"
    return "survived"


def run_panel_on(cand: dict, model: str) -> dict:
    """Six skeptics in parallel, then the judge. Returns the panel block."""

    def one(name: str) -> dict:
        try:
            v = call_agent(skeptic_prompt(name, cand, SKEPTIC_VERDICT_SCHEMA),
                           SKEPTIC_VERDICT_SCHEMA, model=model)
            v["skeptic"] = name  # enforce; schema allows any enum member
            return v
        except AgentCallError as exc:
            log.error("%s skeptic failed on %s: %s", name, cand["id"], exc)
            return {"skeptic": name, "error": str(exc)}

    with ThreadPoolExecutor(max_workers=6) as pool:
        skeptics = list(pool.map(one, SKEPTIC_NAMES))

    tally = {
        "killed": sum(1 for s in skeptics if s.get("verdict") == "killed"),
        "failed_to_kill": sum(1 for s in skeptics if s.get("verdict") == "failed_to_kill"),
        "inconclusive": sum(1 for s in skeptics if s.get("verdict") == "inconclusive"),
        "errors": sum(1 for s in skeptics if "error" in s),
    }
    status = mechanical_status(skeptics)

    judge = None
    try:
        judge = call_agent(judge_prompt(cand, skeptics, tally, JUDGE_SCHEMA),
                           JUDGE_SCHEMA, model=model)
    except AgentCallError as exc:
        log.error("judge failed on %s: %s", cand["id"], exc)
        judge = {"error": str(exc)}

    judge_decision = (judge or {}).get("decision")
    decision_map = {"survives": "survived", "killed": "killed",
                    "needs-human-review": "flagged-for-review"}
    if judge_decision and decision_map.get(judge_decision) != status:
        final = "flagged-for-review" if status == "survived" else status
        conflict = True
    else:
        final = status
        conflict = False

    return {
        "panel_version": PANEL_VERSION,
        "model": model,
        "ran_utc": datetime.now(timezone.utc).isoformat(),
        "skeptics": skeptics,
        "tally": tally,
        "mechanical_status": status,
        "judge": judge,
        "judge_agrees_with_mechanical_rule": not conflict,
        "status": final,
    }


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidates", type=Path, default=config.DATA_DIR / "candidates.json")
    ap.add_argument("--id", action="append", default=[])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--model", default="sonnet")
    args = ap.parse_args(argv)

    cands = json.loads(args.candidates.read_text())
    todo = [c for c in cands
            if (not args.id or c["id"] in args.id)
            and (args.force or not c.get("panel"))]
    log.info("panel queue: %d of %d candidates", len(todo), len(cands))

    for i, cand in enumerate(todo, 1):
        log.info("[%d/%d] tribunal for %s (%s)", i, len(todo), cand["id"], cand["class"])
        cand["panel"] = run_panel_on(cand, args.model)
        log.info("    -> %s (judge: %s)", cand["panel"]["status"],
                 (cand["panel"].get("judge") or {}).get("decision"))
        write_json(args.candidates, cands)   # checkpoint after every candidate

    survivors = sum(1 for c in cands if (c.get("panel") or {}).get("status") == "survived")
    log.info("done. survivors: %d / %d", survivors, len(cands))

    meta_path = args.candidates.parent / "run-meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        meta.setdefault("counts", {})["panel_survivors"] = survivors
        write_json(meta_path, meta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
