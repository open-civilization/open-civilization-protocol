"""Autonomous theory discovery.

When an anomaly in the simulation doesn't match any lens already registered
in theories.py, this module asks the LLM to identify the single most
authoritative real-world theory for that specific domain — economics,
political science, philosophy, physics, sociology, biology, anthropology,
or anything else — and formalizes it into a new, executable theory lens
plus a citation write-up, growing the agent's own theoretical toolkit over
time rather than being bounded by a fixed list of domains chosen in advance.

The discovered lens is validated in two stages before being accepted:
1. static — the proposed function must parse as valid Python, define the
   claimed function name, and contain no imports/exec/eval/filesystem/process
   access (it should be pure data analysis, nothing else)
2. dynamic — the function is actually executed, in a restricted namespace,
   against real run data, and must return None or a TheoryFinding without
   raising

Only a lens that survives both checks gets appended to theories.py.
"""

from __future__ import annotations

import ast
import builtins as _builtins_module
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any, Optional

try:
    from simulation.ocp.ai import call_llm, load_settings
except ModuleNotFoundError:
    from ocp.ai import call_llm, load_settings

from .theories import LENSES, TheoryFinding

SEED_MARKER = "# AUTO-DISCOVERED LENSES REGISTERED BELOW THIS LINE — appended by discovery.py"

_ALLOWED_BUILTIN_NAMES = (
    "len", "range", "min", "max", "sum", "abs", "round", "sorted", "enumerate",
    "zip", "list", "dict", "set", "tuple", "float", "int", "str", "bool",
    "isinstance", "Exception", "getattr", "map", "filter", "any", "all",
)

DATA_SCHEMA_DESCRIPTION = """
Available data for a `compare(history, state)` function:

`history`: list of per-tick metrics dicts (most recent last), each with keys including:
  tick, season, year, pop, avg_energy, avg_health, births, deaths, total_births,
  total_deaths, avg_age, max_gen, gini, cluster, pressure, carrying_cap,
  knowledge_holders, avg_storage_skill, knowledge_ratio, farmer_holders,
  avg_farm_skill, herder_holders, avg_herd_skill, cultivated_cells,
  language_holders, writing_holders, shelter_holders, clothing_holders,
  fire_holders, avg_immunity

`state`: final snapshot dict with keys:
  gw, gh (grid width/height), terrain (list[str], one per cell, row-major),
  biomass (list[float], one per cell), leftover (list[float], one per cell),
  cultivation (list[float], one per cell), residents (list of per-resident
  dicts: id, name, x, y, age, energy, health, gen, parent_id (int or null —
  the id of the resident this one was born to, or null for the founding
  generation; two residents sharing a parent_id are siblings), str, spd,
  per, end, soc, risk, bonds (int count), children, skills (dict
  str->float), knowledge (dict str->float level)), metrics (same shape as
  a history row).

Note: individual bond targets/qualities and raid event details (who raided
whom) are NOT exposed — only the aggregate bond count per resident. A lens
needing that level of detail should treat it as a documented limitation in
the gap rather than assuming the field is available.
"""


@dataclass
class TheoryDiscovery:
    theory_name: str
    citation: str
    domain: str
    prediction: str
    function_name: str
    function_code: str
    writeup_markdown: str
    raw_response: str = ""


def build_discovery_prompt(report: dict[str, Any], existing_theories: list[str]) -> str:
    findings_json = json.dumps(report.get("aggregate", {}), indent=2, ensure_ascii=False)
    run_findings: list[dict[str, Any]] = []
    theory_findings: list[dict[str, Any]] = []
    for run in report.get("runs", []):
        run_findings.extend({"run": run.get("run_id"), **f} for f in run.get("findings", []))
        theory_findings.extend({"run": run.get("run_id"), **tf} for tf in run.get("theory_findings", []))

    existing = "\n".join(f"- {name}" for name in existing_theories) or "(none yet)"

    return f"""You are a simulation scientist studying an emergent-civilization sandbox (OCP) —
residents forage, reproduce, form bonds, discover technology, and die under real physical
constraints. You already have a toolkit of "theory lenses": each encodes a citable,
real-world academic theory as a quantified prediction, checked against actual run data.

Theories already in the toolkit (do not propose one of these again):
{existing}

## Ad hoc heuristic findings (aggregate)
{findings_json}

## Ad hoc heuristic findings (per run)
{json.dumps(run_findings, indent=2, ensure_ascii=False)}

## Existing theory-lens findings from this run
{json.dumps(theory_findings, indent=2, ensure_ascii=False)}

Your task: identify ONE aspect of the observed behavior above that is NOT already explained
by an existing lens and is NOT just a restatement of an ad hoc finding — something that calls
for a genuinely different theoretical lens. You are not restricted to economics or biology —
draw from political science, sociology, philosophy, physics, anthropology, or any field where
a real, named theory applies. Identify the single most authoritative real-world theory, model,
or law for that specific phenomenon: a real person, a real paper or book, a real year. If
nothing in the data calls for a new lens beyond what's already covered, set "domain" to "none".

{DATA_SCHEMA_DESCRIPTION}

Write a Python function implementing the comparison, matching this exact contract:
    def compare(history, state):
        # return None if the theory's prediction currently holds (no gap worth reporting)
        # return a TheoryFinding(...) if there is a quantified, evidenced gap
It must be complete, syntactically valid, and self-contained. `TheoryFinding`, `mean`,
`median`, and `pstdev` are already available in scope — do not write any import statements,
and do not reference anything not described in the data schema above. This function is
pure read-only analysis: it must never mutate `history` or `state`, and must not be a
disguised way of injecting new simulated "facts" — it only measures and reports a gap
between theory and observation, it never creates the thing being measured.

Respond with ONLY a JSON object, no other text, in this exact shape:
{{
  "domain": "e.g. 'monetary economics' or 'none'",
  "theory_name": "exact theory/law name",
  "citation": "real person, real work, real year",
  "prediction": "one sentence: what the theory predicts, in terms of this simulation",
  "function_name": "a valid Python identifier starting with _, e.g. '_gresham_law_compare'",
  "function_code": "the complete Python function source as a string, starting with 'def '",
  "writeup_markdown": "2-4 paragraphs in markdown: what the theory says, why it applies here, what a confirming vs. disconfirming observation would look like"
}}"""


def _parse_response(text: str) -> dict[str, Any]:
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)
    return json.loads(text)


def _validate_function_code(function_code: str, function_name: str) -> tuple[bool, str]:
    """Static check: valid syntax, defines the claimed function, and contains no
    import/exec/eval/filesystem/process access — a discovered lens must be pure
    data analysis over the arguments it's given, nothing else."""
    try:
        tree = ast.parse(function_code)
    except SyntaxError as exc:
        return False, f"Proposed function has a syntax error: {exc}"
    func_defs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    if not any(f.name == function_name for f in func_defs):
        return False, f"Proposed code does not define a function named {function_name}."
    banned = ("import ", "open(", "exec(", "eval(", "__import__", "subprocess", "os.", "sys.", "globals(", "locals(")
    if any(tok in function_code for tok in banned):
        return False, "Proposed code contains a disallowed construct (import/exec/eval/filesystem/process access)."
    return True, "OK"


def _test_run_function(
    function_code: str, function_name: str, history: list[dict[str, Any]], state: dict[str, Any]
) -> tuple[bool, str]:
    """Dynamic check: executes the candidate in a restricted namespace against real run
    data, confirming it runs without raising and returns None or a TheoryFinding."""
    safe_builtins = {name: getattr(_builtins_module, name) for name in _ALLOWED_BUILTIN_NAMES
                     if hasattr(_builtins_module, name)}
    namespace: dict[str, Any] = {
        "__builtins__": safe_builtins,
        "mean": mean, "median": median, "pstdev": pstdev,
        "TheoryFinding": TheoryFinding,
        "Optional": Optional,
        "Any": Any,
    }
    try:
        exec(function_code, namespace)  # noqa: S102 - syntax pre-validated, restricted builtins
        fn = namespace[function_name]
        result = fn(history, state)
        if result is not None and not isinstance(result, TheoryFinding):
            return False, f"Function returned {type(result).__name__}, expected None or TheoryFinding."
        return True, "OK" if result is None else f"OK — produced a finding (severity={result.severity})"
    except Exception as exc:  # noqa: BLE001 - any runtime failure invalidates the candidate
        return False, f"Function raised during test execution: {exc!r}"


def discover_theory(
    report: dict[str, Any],
    history: list[dict[str, Any]],
    state: dict[str, Any],
    settings: Optional[dict[str, Any]] = None,
) -> tuple[Optional[TheoryDiscovery], str]:
    """Returns (discovery_or_None, message). A None discovery with a non-error message
    means the LLM legitimately found nothing new to add this round, not a failure."""
    existing_names = [lens.name for lens in LENSES]
    settings = settings or load_settings()
    provider = settings.get("provider", "anthropic")
    prov_conf = settings.get("providers", {}).get(provider, {})
    api_key = prov_conf.get("api_key", "")
    model = prov_conf.get("model", "")
    if not api_key:
        return None, "No LLM API key configured — cannot run theory discovery."

    prompt = build_discovery_prompt(report, existing_names)
    raw = call_llm(provider, api_key, model, prompt, max_tokens=3500, timeout=90)
    if not raw:
        return None, "LLM call failed or returned nothing."

    try:
        parsed = _parse_response(raw)
    except (json.JSONDecodeError, AttributeError):
        return None, "Could not parse a JSON proposal from the LLM response."

    if str(parsed.get("domain", "none")).strip().lower() == "none":
        return None, "LLM reported no new theory domain was needed this round."

    function_code = str(parsed.get("function_code", ""))
    function_name = str(parsed.get("function_name", ""))
    if not function_code or not function_name:
        return None, "Proposal missing function_code or function_name."

    ok, message = _validate_function_code(function_code, function_name)
    if not ok:
        return None, f"Static validation failed: {message}"

    ok, message = _test_run_function(function_code, function_name, history, state)
    if not ok:
        return None, f"Dynamic validation failed: {message}"

    return TheoryDiscovery(
        theory_name=str(parsed.get("theory_name", "")),
        citation=str(parsed.get("citation", "")),
        domain=str(parsed.get("domain", "")),
        prediction=str(parsed.get("prediction", "")),
        function_name=function_name,
        function_code=function_code,
        writeup_markdown=str(parsed.get("writeup_markdown", "")),
        raw_response=raw,
    ), f"Discovered and validated: {parsed.get('theory_name', '')} ({message})"


@dataclass
class RegisterResult:
    registered: bool
    message: str
    doc_path: Optional[Path] = None


def register_discovered_theory(
    discovery: TheoryDiscovery, theories_path: Path, docs_dir: Path
) -> RegisterResult:
    """Appends the new lens function + registration to theories.py (just above the
    seed-lenses-end marker) and writes a citation write-up under theories_docs/. Never
    reorders or touches the existing seed lenses."""
    source = theories_path.read_text(encoding="utf-8")
    if SEED_MARKER not in source:
        return RegisterResult(False, "Could not find the insertion marker in theories.py — refusing to guess.")
    if discovery.function_name in source:
        return RegisterResult(False, f"A function named {discovery.function_name} already exists — refusing to shadow it.")
    if "LENSES: list[TheoryLens]" not in source:
        return RegisterResult(False, "Could not find the LENSES list declaration in theories.py.")

    lens_registration = (
        f'    TheoryLens("{discovery.theory_name}", "{discovery.citation}",\n'
        f'               "{discovery.prediction}",\n'
        f'               {discovery.function_name}),\n'
    )

    lenses_start = source.index("LENSES: list[TheoryLens]")
    new_source = source[:lenses_start] + discovery.function_code.strip() + "\n\n\n" + source[lenses_start:]
    marker_idx = new_source.index(SEED_MARKER)
    new_source = new_source[:marker_idx] + lens_registration + new_source[marker_idx:]

    # Re-validate the FULL resulting module compiles before committing to disk.
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        return RegisterResult(False, f"Resulting theories.py would not parse: {exc}")

    theories_path.write_text(new_source, encoding="utf-8")

    docs_dir.mkdir(parents=True, exist_ok=True)
    existing_docs = sorted(docs_dir.glob("TL-*.md"))
    next_num = len(existing_docs) + 1
    slug = re.sub(r"[^a-z0-9]+", "-", discovery.theory_name.lower()).strip("-")[:50] or "theory"
    doc_path = docs_dir / f"TL-{next_num:04d}-{slug}.md"
    doc_path.write_text(
        f"# TL-{next_num:04d}: {discovery.theory_name}\n\n"
        f"**Citation:** {discovery.citation}\n\n"
        f"**Domain:** {discovery.domain}\n\n"
        f"**Prediction:** {discovery.prediction}\n\n"
        f"**Discovered:** {datetime.now(timezone.utc).isoformat()}\n\n"
        f"## Write-up\n\n{discovery.writeup_markdown}\n\n"
        f"## Implementation\n\n```python\n{discovery.function_code}\n```\n",
        encoding="utf-8",
    )
    return RegisterResult(True, f"Registered {discovery.theory_name} as {discovery.function_name}.", doc_path)
