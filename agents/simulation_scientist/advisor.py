"""LLM-based advisor for the Simulation Scientist Agent.

Takes an audit report (findings from a sandbox run) plus the current tunable
constants in engine.py, asks an LLM to propose exactly one next experiment —
either a single constant adjustment or a small, precisely-scoped code edit —
and parses that proposal into a structured, safely-applicable form.

Reuses the same LLM provider/credentials configured for resident AI decisions
(RFC-0005) via simulation.ocp.ai.load_settings/call_llm, so no separate API
key setup is needed.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

try:
    from simulation.ocp.ai import call_llm, load_settings
except ModuleNotFoundError:
    from ocp.ai import call_llm, load_settings


@dataclass
class Proposal:
    hypothesis: str
    action: str  # "parameter" | "code_edit" | "none"
    rationale: str
    parameter_name: Optional[str] = None
    parameter_value: Optional[str] = None
    file: Optional[str] = None
    old_string: Optional[str] = None
    new_string: Optional[str] = None
    raw_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


NONE_PROPOSAL = Proposal(
    hypothesis="", action="none", rationale="No advisor response available.",
)


def _extract_tunable_excerpt(engine_source: str, max_lines: int = 200) -> str:
    """Pulls the module-level constants block from engine.py — this is the section
    the advisor is expected to reason about for 'parameter' proposals. Falls back to
    the first max_lines of the file if the expected markers aren't found."""
    lines = engine_source.splitlines()
    start_marker = "# ── Configuration ──"
    end_marker = "def climate_zone"
    start_idx = next((i for i, l in enumerate(lines) if start_marker in l), 0)
    end_idx = next((i for i, l in enumerate(lines) if end_marker in l), min(len(lines), start_idx + max_lines))
    return "\n".join(lines[start_idx:end_idx])


def build_prompt(report: dict[str, Any], engine_source: str) -> str:
    tunable_excerpt = _extract_tunable_excerpt(engine_source)
    findings_json = json.dumps(report.get("aggregate", {}), indent=2, ensure_ascii=False)
    run_findings = []
    for run in report.get("runs", []):
        for f in run.get("findings", []):
            run_findings.append({"run": run.get("run_id"), **f})
    per_run_json = json.dumps(run_findings, indent=2, ensure_ascii=False)

    return f"""You are a simulation scientist studying an emergent-civilization sandbox (OCP).
Residents forage, reproduce, age, and die under real physical constraints (climate, calories,
population pressure). All knowledge (food storage, farming, herding, shelter, clothing, fire,
language, writing) emerges only through in-world experience — nothing is scripted to unlock.

Below is an audit report from one or more test runs, followed by the current tunable constants
in the simulation engine.

## Aggregate findings
{findings_json}

## Per-run findings
{per_run_json}

## Current tunable constants (engine.py, Configuration section)
```python
{tunable_excerpt}
```

Propose exactly ONE next experiment to run. Prefer adjusting a single existing constant
("parameter") over changing logic ("code_edit") unless the findings clearly indicate a
structural problem (e.g. a mechanic that can never fire, a double-counted cost, a formula
that doesn't scale with something it should). Do not propose to "wait and see" — always
propose a concrete, testable change.

If action is "code_edit", `old_string` MUST be an exact, minimal, UNIQUE substring of the
named file as currently written (a diff-style anchor), and `new_string` is what it should
become. Do not paraphrase the source; quote it exactly.

Respond with ONLY a JSON object, no other text, in this exact shape:
{{
  "hypothesis": "one sentence: what you think is happening and why",
  "action": "parameter" | "code_edit" | "none",
  "rationale": "one sentence: why this specific change should help",
  "parameter_name": "CONSTANT_NAME or null",
  "parameter_value": "new literal value as a string, or null",
  "file": "engine.py or null",
  "old_string": "exact source excerpt to replace, or null",
  "new_string": "replacement source excerpt, or null"
}}"""


def _parse_json_response(text: str) -> dict[str, Any]:
    text = text.strip()
    # Strip markdown code fences if the model wrapped its JSON anyway
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        # Fall back to the first {...} block found
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)
    return json.loads(text)


def get_advice(
    report: dict[str, Any],
    engine_path: Path,
    settings: Optional[dict[str, Any]] = None,
) -> Proposal:
    settings = settings or load_settings()
    provider = settings.get("provider", "anthropic")
    prov_conf = settings.get("providers", {}).get(provider, {})
    api_key = prov_conf.get("api_key", "")
    model = prov_conf.get("model", "")
    if not api_key:
        return Proposal(
            hypothesis="",
            action="none",
            rationale="No LLM API key configured in settings.json — set one under the AI "
                      "settings used for resident decisions, or pass --provider/--api-key.",
        )

    engine_source = engine_path.read_text(encoding="utf-8")
    prompt = build_prompt(report, engine_source)
    raw = call_llm(provider, api_key, model, prompt, max_tokens=600)
    if not raw:
        return Proposal(hypothesis="", action="none", rationale="LLM call failed or returned nothing.")

    try:
        parsed = _parse_json_response(raw)
    except (json.JSONDecodeError, AttributeError):
        return Proposal(
            hypothesis="", action="none",
            rationale="Could not parse a JSON proposal from the LLM response.",
            raw_response=raw,
        )

    return Proposal(
        hypothesis=str(parsed.get("hypothesis", "")),
        action=str(parsed.get("action", "none")),
        rationale=str(parsed.get("rationale", "")),
        parameter_name=parsed.get("parameter_name") or None,
        parameter_value=parsed.get("parameter_value") or None,
        file=parsed.get("file") or None,
        old_string=parsed.get("old_string") or None,
        new_string=parsed.get("new_string") or None,
        raw_response=raw,
    )


@dataclass
class ApplyResult:
    applied: bool
    message: str


def apply_parameter_change(engine_path: Path, name: str, new_value: str) -> ApplyResult:
    """Regex-based single-constant replacement: `NAME = <old literal>` -> `NAME = <new_value>`.
    Only touches the first top-level assignment matching `name` and refuses if it's not
    found exactly once, to avoid silently editing the wrong thing."""
    source = engine_path.read_text(encoding="utf-8")
    pattern = re.compile(rf"^({re.escape(name)}\s*=\s*)([^\n#]+?)(\s*(?:#.*)?)$", re.MULTILINE)
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        return ApplyResult(
            applied=False,
            message=f"Expected exactly one top-level assignment to {name}, found {len(matches)}.",
        )
    m = matches[0]
    trailing = m.group(3)
    # Preserve a single space before any trailing comment for readability
    if trailing.strip().startswith("#") and not trailing.startswith("  "):
        trailing = "  " + trailing.lstrip()
    new_source = source[: m.start()] + f"{m.group(1)}{new_value}{trailing}" + source[m.end():]
    engine_path.write_text(new_source, encoding="utf-8")
    return ApplyResult(applied=True, message=f"{name} changed to {new_value}")


def apply_code_edit(file_path: Path, old_string: str, new_string: str) -> ApplyResult:
    """Same contract as the interactive Edit tool: old_string must appear exactly once."""
    source = file_path.read_text(encoding="utf-8")
    count = source.count(old_string)
    if count == 0:
        return ApplyResult(applied=False, message="old_string not found in file — proposal may be stale.")
    if count > 1:
        return ApplyResult(applied=False, message=f"old_string is ambiguous ({count} occurrences) — refusing to apply.")
    new_source = source.replace(old_string, new_string, 1)
    file_path.write_text(new_source, encoding="utf-8")
    return ApplyResult(applied=True, message="Code edit applied.")


def apply_proposal(proposal: Proposal, engine_path: Path) -> ApplyResult:
    if proposal.action == "parameter":
        if not proposal.parameter_name or proposal.parameter_value is None:
            return ApplyResult(applied=False, message="Parameter proposal missing name or value.")
        return apply_parameter_change(engine_path, proposal.parameter_name, proposal.parameter_value)
    if proposal.action == "code_edit":
        if not proposal.old_string or proposal.new_string is None:
            return ApplyResult(applied=False, message="Code-edit proposal missing old_string/new_string.")
        target = engine_path if (proposal.file or "engine.py").endswith("engine.py") else engine_path
        return apply_code_edit(target, proposal.old_string, proposal.new_string)
    return ApplyResult(applied=False, message="Proposal action is 'none' — nothing to apply.")
