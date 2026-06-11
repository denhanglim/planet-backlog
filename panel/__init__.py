"""Adversarial AI vetting panel.

Six skeptic agents each try to KILL a candidate from one angle, reasoning ONLY over
diagnostics computed by the deterministic pipeline. A judge synthesizes the verdicts.
The final survival status is enforced by a mechanical rule in code (any fatal kill ->
killed); the judge's own decision is recorded and any disagreement flags the candidate
for human review. The LLM never produces a number that wasn't computed upstream.
"""

PANEL_VERSION = "1.0.0"
