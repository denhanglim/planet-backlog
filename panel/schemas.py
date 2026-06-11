"""JSON schemas for machine-consumable panel verdicts. Every agent output is
validated against these; invalid output is retried, then recorded as a failure."""

SKEPTIC_NAMES = ["binary", "blend", "instrument", "stellar", "alias", "catalog"]

SKEPTIC_VERDICT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["skeptic", "verdict", "lethality", "reasoning", "evidence_cited",
                 "what_would_change_my_mind"],
    "properties": {
        "skeptic": {"type": "string", "enum": SKEPTIC_NAMES},
        "verdict": {"type": "string", "enum": ["killed", "failed_to_kill", "inconclusive"]},
        "lethality": {
            "type": "string",
            "enum": ["fatal", "serious-concern", "minor-concern", "none"],
            "description": "fatal only when the cited computed evidence is decisive",
        },
        "reasoning": {"type": "string", "minLength": 40, "maxLength": 1600},
        "evidence_cited": {
            "type": "array", "minItems": 1, "maxItems": 12,
            "items": {"type": "string"},
            "description": "names of diagnostic fields actually weighed (e.g. 'odd_even.difference_sigma')",
        },
        "what_would_change_my_mind": {"type": "string", "minLength": 10, "maxLength": 600},
    },
}

JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["decision", "confidence", "summary_plain_english", "why_it_might_be_real",
                 "why_we_are_cautious", "recommended_followup"],
    "properties": {
        "decision": {"type": "string", "enum": ["survives", "killed", "needs-human-review"]},
        "confidence": {
            "type": "string", "enum": ["high", "medium", "low"],
            "description": "qualitative judgment of the panel's overall read — NOT a measured quantity",
        },
        "summary_plain_english": {"type": "string", "minLength": 60, "maxLength": 1200},
        "why_it_might_be_real": {"type": "string", "minLength": 20, "maxLength": 800},
        "why_we_are_cautious": {"type": "string", "minLength": 20, "maxLength": 800},
        "recommended_followup": {"type": "string", "minLength": 20, "maxLength": 600},
    },
}
