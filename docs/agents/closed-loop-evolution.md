# Closed-Loop Evolution Architecture

## Status

Draft

## Summary

This document defines how OCP should evolve its world rules through an auditable agent loop rather than through ad hoc manual tuning.

The goal is not to let an agent "author civilization."

The goal is to let agents:

- observe simulation behavior
- detect distortion
- map distortion to candidate scientific theory
- propose minimal rule changes
- validate those changes in sandbox runs
- submit the result for human review

This is the operational path by which OCP becomes more scientifically grounded over time while preserving its protocol-first philosophy.

## Why This Exists

OCP is not trying to script history.

It is trying to search the space of possible civilizations under bounded laws.

That creates a difficult engineering requirement:

- the world must remain open-ended
- the rules must remain falsifiable
- the simulation must keep improving
- improvement must not silently collapse into designer bias

A closed-loop agent system exists to solve that tension.

It makes rule evolution:

- evidence-driven
- theory-linked
- reversible
- reviewable

## First Principle

Agents may improve rules.

Agents may not decide outcomes.

An agent is allowed to change:

- thresholds
- decay rates
- discovery probabilities
- interaction conditions
- diffusion friction
- maintenance costs
- resource formulas

An agent is not allowed to directly create:

- a nation
- a religion
- a language family
- a class system
- a government form
- a technology unlock

If a proposed change hardcodes a civilization result, it violates OCP.

## Closed Loop

```text
Sandbox Run
    ↓
Observer Agent
    ↓
Distortion Report
    ↓
Scientist Agent
    ↓
Rule Hypothesis
    ↓
Refactor Agent
    ↓
Code / RFC Patch
    ↓
Experiment Run
    ↓
Branch / PR
    ↓
Human Review
    ↓
Merge / Reject / Revise
```

## Agent Roles

### 1. Observer Agent

Purpose:

- watch the world as it actually runs
- compute structured metrics
- surface suspicious patterns

Inputs:

- state snapshots
- tick history
- event logs
- population summaries
- knowledge diffusion metrics
- disease and mortality traces
- mobility and crowding data

Outputs:

- anomaly reports
- trend summaries
- regime-shift warnings
- reproducible experiment records

The Observer Agent does not explain the world.

It only says:

- what happened
- how often
- how severe it was
- where it differs from expectation or baseline

### 2. Scientist Agent

Purpose:

- translate anomalies into candidate scientific explanations
- identify which mechanism is missing, too weak, too strong, or wrongly coupled

Inputs:

- Observer reports
- theory library
- historical experiment comparisons
- human research notes

Outputs:

- diagnosis memos
- theory links
- falsifiable hypotheses
- ranked intervention candidates

This agent should think like a research assistant, not like a content designer.

It should answer questions such as:

- Is this a carrying-capacity problem or a diffusion problem?
- Is this unrealistic because the mechanism is absent, or because its weight is wrong?
- Is this a local distortion, or a constitutional-layer problem?

### 3. Refactor Agent

Purpose:

- implement the smallest rule change that tests the current hypothesis

Inputs:

- accepted hypothesis
- target files
- edit constraints
- constitutional guardrails

Outputs:

- code patch
- RFC patch when needed
- experiment notes
- branch
- commit
- PR

This agent should prefer:

- one mechanism change
- one parameter family
- one experiment objective

It must not mix multiple theories into one opaque patch.

## Human Role

The human remains:

- constitutional authority
- scientific arbiter
- merge authority
- product and research direction owner

Agents are collaborators inside the protocol.

They are not sovereign maintainers.

## Distortion Categories

The loop should not treat every bug as the same kind of problem.

OCP needs a stable vocabulary for simulation distortion.

### 1. Conservation Distortion

Examples:

- energy appears from nowhere
- population grows without resource support
- information propagates without carrier cost

Likely response:

- physics or accounting fix

### 2. Pressure Distortion

Examples:

- Malthusian pressure is too weak
- seasonal bottlenecks do not matter
- disease never meaningfully changes behavior

Likely response:

- crowding, mortality, fertility, storage, or scarcity coupling changes

### 3. Diffusion Distortion

Examples:

- language reaches near-universal adoption too quickly
- writing spreads faster than social complexity can support
- knowledge jumps across the map with little contact

Likely response:

- transmission friction
- teaching cost
- memory loss
- network or distance constraints

### 4. Organization Distortion

Examples:

- large stable groups appear without coordination cost
- cooperation is free
- trust scales unrealistically
- institutions never decay

Likely response:

- maintenance cost
- governance radius
- conflict and free-rider mechanics

### 5. Adaptation Distortion

Examples:

- harsh climates are colonized too early
- weak traits face no selective pressure
- disease does not shape trait distribution

Likely response:

- fitness consequences
- inheritance drift
- ecological gating

### 6. Narrative Distortion

Examples:

- stories are repetitive because behavior space is narrow
- all agents make similar social choices
- interesting events occur but are not legible

Likely response:

- decision diversity
- meso-level logging
- event interpretation

## Theory Workflow

The theory layer should work in this order:

1. Detect the observed distortion.
2. Classify its distortion family.
3. Search theory library for matching mechanisms.
4. Propose the smallest missing or misweighted mechanism.
5. Design one testable intervention.
6. Compare post-change behavior against baseline.

The point is not to prove a theory true.

The point is to use theory as a disciplined source of hypotheses.

## Rule Change Policy

Every autonomous change proposal should satisfy all of the following:

- it changes a rule, not an outcome
- it is minimal enough to isolate causality
- it is reversible in git
- it is explainable in one paragraph
- it can be tested against a baseline run

Good examples:

- increase knowledge decay when no teaching chain exists
- require repeated social contact before writing transmission can succeed
- scale epidemic severity with local crowding and nutrition status
- make storage maintenance consume labor and materials

Bad examples:

- grant literacy after population exceeds a threshold
- unlock farming at tick 500
- create tribes directly when nearby population density is high
- inject a new civilization feature because it "should exist by now"

## Experimental Discipline

The closed loop should behave more like a lab than like a game live-ops console.

Each experiment should record:

- hypothesis
- targeted distortion
- changed files
- changed rules
- run length
- seed set
- baseline result
- intervention result
- interpretation
- next question

Where possible, comparisons should be multi-run rather than single-seed.

Single runs are acceptable for smoke tests, but not for concluding that a theory worked.

## LLM Policy

LLMs are useful in this loop, but they must remain bounded.

Recommended role split:

- deterministic tooling for measurement and regression detection
- theory retrieval and comparison for structured reasoning
- LLM assistance for explanation, hypothesis drafting, and edit planning

LLMs should not be the sole source of:

- anomaly detection
- numerical truth
- constitutional interpretation
- code mutation authority

In practice, this means:

- Observer Agent should be mostly deterministic
- Scientist Agent may use LLMs heavily, but with evidence attached
- Refactor Agent should write small, checkable edits with syntax and policy gates

## Governance Boundary

The closed loop must respect three layers of change authority.

### Layer A: Constitution

Examples:

- persistence
- causality
- conservation
- bounded knowledge
- bounded cognition

These should not be changed autonomously.

### Layer B: Protocol Rules

Examples:

- disease spread formula
- teaching fidelity
- maintenance decay
- migration triggers
- crowding penalties

These may be changed through the closed loop.

### Layer C: Implementation Details

Examples:

- logging
- metrics
- thresholds used only for detection
- report formatting

These may be changed more freely.

## Recommended Near-Term Roadmap

For the current OCP phase, the loop should focus on a narrow set of scientifically important distortion families:

1. knowledge saturation
2. language and writing emergence
3. disease realism
4. Malthusian pressure calibration
5. kinship, trust, and social-bond formation
6. maintenance and entropy of infrastructure and institutions

This is enough to materially improve realism without prematurely building a full civilization stack.

## Success Criteria

This loop is successful if, over time:

- fewer world behaviors look like obvious simulation artifacts
- more dynamics can be explained through explicit mechanisms
- rule changes become smaller and more theory-grounded
- civilization-level structure emerges from lower layers more often
- the maintainer can review and steer progress without needing expert knowledge in every field

It is not necessary for the world to become a perfect copy of human history.

It is necessary for the world to become:

- more constrained
- more legible
- more falsifiable
- more capable of genuine emergence

## Final Principle

OCP should evolve like science evolves:

- observe reality
- explain carefully
- change one rule at a time
- keep the record
- never confuse a useful model with the truth
