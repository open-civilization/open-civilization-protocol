# Simulation Scientist Agent

## Purpose

The Simulation Scientist Agent is a protocol research agent for OCP.

It does not act as a world designer, sovereign controller, or direct constitutional authority.

Its role is to:

- observe simulation behavior
- detect anomalies or implausible dynamics
- map observed problems to candidate scientific theories
- propose rule or parameter changes
- prepare isolated branches and pull requests for human review

The final authority remains with the human maintainer.

## Why This Agent Exists

OCP aims to build an artificial civilization laboratory rather than a scripted game.

That creates a hard requirement:

- rules must be improved from evidence
- evidence must come from world behavior
- theory should inform revision
- revisions should remain auditable and reversible

The maintainer should not need deep expertise in every relevant field before progress can continue.

This agent exists to narrow that gap responsibly.

## Core Principle

The agent may recommend changes.

The agent may not declare truth.

Its purpose is to produce:

- observations
- hypotheses
- rule proposals
- experiment plans
- pull requests

It must not silently rewrite the world model.

## Agent Class

This is best understood as a `Simulation Scientist Agent`.

It combines three functions:

- observer
- research assistant
- change drafter

It is not a freeform autonomous civilization author.

## Responsibilities

The agent SHOULD be able to:

- inspect simulation metrics, logs, and event traces
- detect unstable, unrealistic, or suspicious dynamics
- compare outcomes across parameter sets or branches
- connect anomalies to candidate theory domains
- draft RFC notes, code changes, or parameter changes
- create a branch
- commit proposed changes
- prepare a pull request for human review

## Non-Responsibilities

The agent MUST NOT:

- modify `main` directly
- bypass pull request review
- amend the universe constitution without explicit human direction
- assume human history is the correct target outcome
- optimize only for “looks realistic to modern humans”
- inject knowledge into the simulation as a hidden shortcut
- hide failed experiments

## Human Governance Model

The intended workflow is:

1. simulation runs produce data
2. the agent detects anomalies
3. the agent proposes candidate explanations
4. the agent drafts a rule or parameter change
5. the agent opens a branch and PR
6. the human reviews, validates, rejects, or revises

The human remains:

- constitutional authority
- scientific arbiter
- merge authority

## Recommended Architecture

The first implementation SHOULD be split into three layers.

### 1. Observer Layer

Purpose:

- collect outputs from simulation runs
- compute structured metrics
- detect anomalies

Inputs:

- event logs
- resident-level state snapshots
- population summaries
- knowledge diffusion metrics
- disease and mortality traces
- geographic distribution data

Outputs:

- anomaly reports
- trend summaries
- baseline versus experiment comparisons

### 2. Theory Layer

Purpose:

- interpret anomaly reports
- map them to relevant theory families
- generate candidate explanations

Examples:

- disease spread models
- Malthusian pressure
- carrying capacity
- evolutionary selection
- information theory
- diffusion dynamics
- coordination failure
- entropy and decay

Outputs:

- hypothesis memos
- “why this may be happening” notes
- candidate rule-change rationale

### 3. Change Layer

Purpose:

- translate accepted hypotheses into repo changes

Actions:

- update parameter values
- adjust mechanics
- add diagnostics
- update RFC notes
- create branch
- commit
- open PR

Outputs:

- code patch
- RFC patch
- experiment notes
- pull request description

## LLM Usage Policy

The Simulation Scientist Agent SHOULD use LLM assistance, but LLM must not be the foundation of the system.

Recommended balance:

- 80% deterministic tooling
- 20% LLM-assisted interpretation and drafting

### LLM Should Be Used For

- translating anomalies into research questions
- summarizing candidate scientific explanations
- drafting RFC notes
- drafting pull request descriptions
- generating human-readable experiment summaries

### LLM Should Not Be Used For

- deciding whether a simulation fact is numerically true
- inventing unverified scientific claims without evidence
- directly changing constitutional rules without review
- silently modifying simulation outputs
- serving as the only anomaly detector

## Modes

The agent SHOULD support at least two modes.

### Mode A: Audit Mode

Purpose:

- observe and report only

Behavior:

- no model call required
- no repo mutation
- no branch creation
- emits anomaly and trend reports

This should be the default stable mode.

### Mode B: Research Mode

Purpose:

- investigate a chosen anomaly domain and propose changes

Behavior:

- may call LLM
- may generate theory notes
- may write code or RFC changes
- may create a branch and PR
- must remain auditable

## Target Domains

The first useful domains for this agent are:

- disease propagation
- starvation and seasonal mortality
- carrying capacity and Malthusian traps
- migration pressure
- knowledge transmission loss
- language and writing emergence
- selection pressure
- environmental adaptation
- surplus and organizational scaling
- collapse and post-collapse recovery

## Scientific Guardrails

The agent must behave like a research assistant, not like a mythology generator.

Every proposed change SHOULD include:

- observed symptom
- evidence from runs
- candidate theory basis
- proposed rule change
- expected impact
- possible side effects
- rollback path

If those fields are absent, the change proposal is incomplete.

## Constitutional Guardrails

This agent is subordinate to the OCP constitution.

It MUST NOT propose changes that violate:

- causality
- energy conservation
- matter conservation
- bounded cognition
- bounded computation
- information propagation limits
- entropy

If a proposal appears to “solve” a problem by bypassing one of these laws, the proposal should be rejected or flagged.

## Git Workflow

The recommended Git workflow is:

1. create a topic branch
2. store experiment notes
3. modify code and/or RFCs
4. run targeted validation
5. commit changes
6. push branch
7. open PR with evidence summary

Suggested branch naming:

- `codex/agent-disease-audit-*`
- `codex/agent-malthus-*`
- `codex/agent-language-*`

## Pull Request Template Expectations

Every PR from this agent SHOULD contain:

- problem statement
- evidence summary
- theory basis
- exact rule or code changes
- expected simulation impact
- risks and unknowns
- validation steps run

## Minimum Viable Version

The first version of this agent should be deliberately narrow.

Recommended MVP:

- focus on one domain only
- read simulation metrics from one run format
- produce one anomaly report
- propose one parameter or rule patch
- create one branch
- create one PR draft

A good first target domain is:

- disease propagation

or

- language and writing emergence

## Example Loop

Example workflow:

1. run 50 simulations with current rules
2. detect that writing causes near-perfect transmission of all knowledge
3. map anomaly to information theory and explicit external-memory modeling
4. propose separating symbolic record from generic tacit skill transfer
5. write RFC note and engine patch
6. open PR for review

This is the intended style of operation: evidence first, theory second, code third.

## Recommended Repository Placement

A likely long-term layout could be:

```text
docs/agents/
  simulation-scientist-agent.md

agents/
  observer/
  theory/
  change/

experiments/
  disease/
  language/
  malthus/
```

This document defines the policy layer first. The implementation can follow later.

## Success Criteria

This agent is successful if it helps the maintainer:

- find real problems earlier
- ground changes in evidence
- connect mechanics to theory
- evolve rules through reviewable PRs
- preserve the integrity of emergence

It is unsuccessful if it becomes:

- a hidden world author
- a black-box theory oracle
- an auto-merge rule mutator
- a shortcut mechanism for “making the simulation look smart”

## Conclusion

OCP should eventually have agents that help improve the world.

But those agents must serve the protocol, not replace it.

The Simulation Scientist Agent is a safe and powerful pattern because it keeps:

- observation
- theory
- change
- human judgment

in the same loop, without giving any single model unchecked authority.
