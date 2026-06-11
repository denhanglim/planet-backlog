"""LLM driver: headless `claude -p` calls with schema validation and retry.

Why the Claude Code CLI: the repo stays runnable on any machine with `claude` installed
and authenticated — no API key management. Each call is stateless; agents cannot browse,
so the only evidence they can use is the digest in the prompt.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess

import jsonschema

log = logging.getLogger("panel.driver")

DEFAULT_MODEL = "sonnet"
CALL_TIMEOUT_S = 300


class AgentCallError(RuntimeError):
    pass


def call_agent(prompt: str, schema: dict, model: str = DEFAULT_MODEL,
               max_retries: int = 2) -> dict:
    """One structured LLM call. Returns the schema-validated dict or raises."""
    attempt_prompt = prompt
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        raw = _invoke_claude(attempt_prompt, model)
        try:
            obj = _extract_json(raw)
            jsonschema.validate(obj, schema)
            return obj
        except (ValueError, jsonschema.ValidationError) as exc:
            last_err = exc
            log.warning("attempt %d invalid output: %s", attempt, exc)
            attempt_prompt = (
                f"{prompt}\n\nYOUR PREVIOUS OUTPUT WAS INVALID: {exc}\n"
                "Output ONLY the corrected JSON object."
            )
    raise AgentCallError(f"agent output never validated: {last_err}")


def _invoke_claude(prompt: str, model: str) -> str:
    # --strict-mcp-config with an empty config stops the CLI from booting the
    # user's MCP servers: the panel needs no tools, and each server boot costs
    # tens of seconds and leaks child processes across 80+ calls.
    cmd = [
        "claude", "-p", "--output-format", "json", "--model", model,
        "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
        "--disallowed-tools", "*",
    ]
    try:
        proc = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, timeout=CALL_TIMEOUT_S,
        )
    except FileNotFoundError as exc:
        raise AgentCallError("`claude` CLI not found — install Claude Code") from exc
    except subprocess.TimeoutExpired as exc:
        raise AgentCallError(f"claude call timed out after {CALL_TIMEOUT_S}s") from exc
    if proc.returncode != 0:
        raise AgentCallError(f"claude exited {proc.returncode}: {proc.stderr[:500]}")
    try:
        envelope = json.loads(proc.stdout)
        return envelope.get("result", proc.stdout)
    except json.JSONDecodeError:
        return proc.stdout


def _extract_json(text: str) -> dict:
    """Parse a JSON object out of agent text (tolerates code fences / preamble)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object in agent output")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("unbalanced JSON in agent output")
