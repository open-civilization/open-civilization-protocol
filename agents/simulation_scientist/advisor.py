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


def build_prompt(report: dict[str, Any], engine_source: str) -> str:
    findings_json = json.dumps(report.get("aggregate", {}), indent=2, ensure_ascii=False)
    run_findings = []
    theory_findings = []
    for run in report.get("runs", []):
        for f in run.get("findings", []):
            run_findings.append({"run": run.get("run_id"), **f})
        for tf in run.get("theory_findings", []):
            theory_findings.append({"run": run.get("run_id"), **tf})
    per_run_json = json.dumps(run_findings, indent=2, ensure_ascii=False)
    theory_json = json.dumps(theory_findings, indent=2, ensure_ascii=False)

    return f"""You are a simulation scientist studying an emergent-civilization sandbox (OCP).
Residents forage, reproduce, age, and die under real physical constraints (climate, calories,
population pressure). All knowledge (food storage, farming, herding, shelter, clothing, fire,
language, writing) emerges only through in-world experience — nothing is scripted to unlock.

Below is an audit report: ad hoc heuristic findings, then "theory-lens" findings that compare
observed behavior against named, citable real-world theories (Malthusian population dynamics,
information theory, kin selection / inclusive fitness, collective action / tragedy of the
commons, exchange economics) — these are the more important signal, since they tell you WHICH
established theory the simulation is failing to reproduce and WHY, in terms of what the model
does or doesn't represent. Ad hoc findings tell you something is off; theory findings tell you
what real-world mechanism is missing or misapplied. Finally, the full current engine source.

## Ad hoc heuristic findings (aggregate)
{findings_json}

## Ad hoc heuristic findings (per run)
{per_run_json}

## Theory-lens findings (compare simulation to named real-world theory)
{theory_json}

## Full current engine source (engine.py)
```python
{engine_source}
```

Propose exactly ONE next experiment to run. A theory-lens finding with a clear structural gap
(e.g. "the model has no representation of X at the decision point where X should matter") is a
strong signal to propose a "code_edit" that adds the missing mechanism, grounded in the cited
theory — do not default to a parameter tweak just because it's simpler, if the finding says a
mechanism is absent rather than miscalibrated. Prefer "parameter" only when the mechanism
already exists and the finding is about its magnitude/threshold, not its existence. Do not
propose to "wait and see" — always propose a concrete, testable change.

If action is "code_edit", `old_string` MUST be an exact, minimal, UNIQUE substring of the
named file as currently written (a diff-style anchor), and `new_string` is what it should
become. Do not paraphrase the source; quote it exactly. Keep the edit as small as it can be
while still being a real, working mechanism — do not propose multi-function refactors in one
step; iterate.

CONSTITUTIONAL CONSTRAINT — this project's one non-negotiable rule (RFC-0001 Law 6, RFC-0007
"Detection vs Design"): every change you propose must be a change to a RULE — a probability,
formula, threshold, discovery gate, or decision-logic condition that GOVERNS how outcomes can
emerge — never a change that directly CREATES a specific outcome, grants a resident knowledge/
skill/state outside an existing probabilistic discovery path, or hardcodes a new fixed "fact"
into the simulation. Concretely:
  - ALLOWED: adjusting a discovery_chance value; changing what condition gates a discovery;
    adding a new gating condition (e.g. a relatedness check) to an existing probabilistic
    mechanism; changing how an existing effect scales; adding a new decay/erosion term.
  - NOT ALLOWED: directly setting `r.known_knowledge[...] = {{...}}` or `r.skills[...] = ...`
    outside of a probability roll or other existing acquisition pathway; inventing a new
    named technology/knowledge/civilization feature and simply granting it to residents;
    hardcoding specific values that represent invented in-world "content" rather than a
    tunable rule. If you cannot express your idea as a rule change, propose "none" instead
    and explain why in `rationale`.

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
    raw = call_llm(provider, api_key, model, prompt, max_tokens=1200, timeout=60)
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


_DIRECT_GRANT_PATTERN = re.compile(r"\b(?:known_knowledge|skills)\s*\[[^\]]*\]\s*=")


def check_constitutional_compliance(new_string: str) -> tuple[bool, str]:
    """Static guardrail for RFC-0001 Law 6 / RFC-0007 "Detection vs Design": a proposed
    edit may change the RULES that govern how outcomes can emerge (a discovery chance, a
    gating condition, a formula, a decision threshold), but must never directly grant a
    resident knowledge/skill/state outside an existing probabilistic acquisition pathway,
    or hardcode a new fixed "fact" into the simulation. Every legitimate knowledge grant in
    this codebase is written as a direct known_knowledge/skills assignment guarded by a
    `random.random()` roll (see engine.py's food_storage/shelter/clothing/fire/language/
    writing/domestication discovery blocks) — an edit that assigns to either without any
    randomness present anywhere in the same edit is very likely injecting content rather
    than changing a rule, and is rejected."""
    if _DIRECT_GRANT_PATTERN.search(new_string) and "random.random()" not in new_string:
        return False, (
            "Rejected: new_string directly assigns to known_knowledge[...] or skills[...] "
            "without any random.random() gate present in the same edit. Per this project's "
            "constitutional constraint (RFC-0001 Law 6), knowledge/skill grants must remain "
            "probabilistic and tied to an existing acquisition pathway — propose the "
            "surrounding gate/condition as part of the same edit, or express this as a rule "
            "change (a chance, threshold, or formula) instead of a direct grant."
        )
    return True, "OK"


def apply_code_edit(file_path: Path, old_string: str, new_string: str) -> ApplyResult:
    """Same contract as the interactive Edit tool: old_string must appear exactly once."""
    compliant, compliance_message = check_constitutional_compliance(new_string)
    if not compliant:
        return ApplyResult(applied=False, message=compliance_message)

    source = file_path.read_text(encoding="utf-8")
    count = source.count(old_string)
    if count == 0:
        return ApplyResult(applied=False, message="old_string not found in file — proposal may be stale.")
    if count > 1:
        return ApplyResult(applied=False, message=f"old_string is ambiguous ({count} occurrences) — refusing to apply.")
    new_source = source.replace(old_string, new_string, 1)
    file_path.write_text(new_source, encoding="utf-8")

    # Post-write verification: re-read from disk and confirm the change actually landed.
    # This exists because a silent mismatch here (claiming success without the file
    # actually reflecting it) is worse than a loud failure — a human reviewing the loop
    # report needs "applied: True" to be trustworthy, not just "the write call didn't
    # raise."
    written = file_path.read_text(encoding="utf-8")
    if new_string not in written:
        return ApplyResult(applied=False, message="Write completed but new_string is not present on re-read — treating as failed.")
    return ApplyResult(applied=True, message="Code edit applied and verified on disk.")


def apply_proposal(proposal: Proposal, engine_path: Path) -> ApplyResult:
    if proposal.action == "parameter":
        if not proposal.parameter_name or proposal.parameter_value is None:
            return ApplyResult(applied=False, message="Parameter proposal missing name or value.")
        return apply_parameter_change(engine_path, proposal.parameter_name, proposal.parameter_value)
    if proposal.action == "code_edit":
        if not proposal.old_string or proposal.new_string is None:
            return ApplyResult(applied=False, message="Code-edit proposal missing old_string/new_string.")
        # Only engine.py is currently a valid target — the advisor is only ever shown
        # engine.py's source, so any other file name in the proposal is untrustworthy.
        if proposal.file and not proposal.file.endswith("engine.py"):
            return ApplyResult(applied=False, message=f"Refusing to edit '{proposal.file}' — only engine.py is a supported code_edit target.")
        return apply_code_edit(engine_path, proposal.old_string, proposal.new_string)
    return ApplyResult(applied=False, message="Proposal action is 'none' — nothing to apply.")
