"""Simulation Scientist Agent.

Two modes:
- `audit`: one-shot, in-process batch runs analyzed against a fixed set of Finding
  heuristics (fast, no deployment, good for quick regression checks).
- `autonomous`: deploys to a real running sandbox, runs an experiment, asks an LLM
  advisor for one concrete next parameter/code change, applies it locally, and
  repeats — never commits or pushes, so every change lands as a plain working-tree
  diff for a human to review.
"""

from .audit import analyze_live_experiment, build_report_from_live_runs, run_audit
from .discovery import discover_theory, register_discovered_theory
from .theories import run_theory_lenses

__all__ = [
    "run_audit", "analyze_live_experiment", "build_report_from_live_runs", "run_theory_lenses",
    "discover_theory", "register_discovered_theory",
]
