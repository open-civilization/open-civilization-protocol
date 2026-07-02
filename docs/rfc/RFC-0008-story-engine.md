# RFC-0008 Story Engine

## Status

Draft

## Summary

This RFC defines how OCP extracts, summarizes, and presents narrative from simulation data.

Stories in OCP are not written ahead of time. They are discovered. The story engine is a read-only observer that watches the simulation and identifies events, patterns, and trajectories worth remembering — then presents them in human-readable form.

The story engine MUST NOT influence simulation outcomes. It is a lens, not a hand.

## Motivation

A simulation that produces rich emergent behavior but no readable output is a research tool that only its operator can appreciate. OCP aspires to be legible — not just to its developers, but to observers, players, and eventually a community.

But legibility is dangerous. The moment a narrative system gains the power to influence simulation outcomes (even subtly, through event prioritization or reward signals), OCP stops being a search system and becomes a story generator that optimizes for drama rather than truth.

The story engine must serve comprehension without compromising causality.

## Goals

This RFC defines:

- the story engine's role as a read-only observer
- event detection and significance assessment
- narrative extraction at multiple scales (individual, group, civilization)
- output formats (reports, biographies, histories)
- the strict boundary between observation and intervention
- how narrative compression handles causal fidelity

## Non-Goals

This RFC does not define:

- simulation mechanics (those belong to Physics, Life, and Civilization RFCs)
- player-facing UI design
- real-time rendering or visualization
- marketing or content strategy

## Architectural Position

```text
Universe
    ↓
Physics
    ↓
Life
    ↓
Civilization
    ↓
Player
    ↓
Story Engine    ← read-only observer, outside the causal stack
```

The story engine sits outside the causal world stack. It reads simulation state and event logs. It writes narrative artifacts. It never writes back to the simulation.

## Normative Language

The key words "MUST", "MUST NOT", "SHOULD", and "MAY" in this document are to be interpreted as binding protocol terms.

## First Principle

Stories are discovered, not written.

The story engine is an archaeologist, not an author. It sifts through what happened and finds the patterns that matter. It does not decide what should happen next.

## Read-Only Constraint

### Hard Rule

The story engine MUST NOT:

- modify any simulation state
- influence any resident's decision
- adjust any physics parameter
- prioritize events for the simulation to produce
- send reward signals or feedback to AI residents
- create residents, resources, or events
- alter the probability of any outcome

### Rationale

Any feedback path from narrative to simulation creates an optimization target. Once the simulation "knows" what makes a good story, it will produce stories instead of honest emergence. This is the narrative corruption failure mode, and it must be prevented architecturally, not just by policy.

## Event Detection

The story engine SHOULD detect significant events from the simulation event stream.

### Event Categories

- **survival events**: deaths, near-deaths, famines, migrations
- **social events**: first contact between groups, alliance formation, betrayal, conflict
- **knowledge events**: discovery, invention, knowledge transmission, knowledge loss
- **construction events**: first structures, infrastructure, settlement founding
- **organizational events**: group formation, group dissolution, leadership emergence
- **demographic events**: population milestones, extinction, expansion
- **environmental events**: resource exhaustion, seasonal crises, natural disasters

### Significance Assessment

Not every event is worth reporting. The story engine SHOULD assess significance based on:

- rarity (how unusual is this event relative to baseline?)
- impact (how many residents or how much state is affected?)
- novelty (has this type of event occurred before in this lineage?)
- persistence (does this event's consequence last beyond a few ticks?)
- human interest (does this event involve recognizable drama: struggle, loss, achievement, surprise?)

Significance assessment is a heuristic, not a constitutional law. It MAY use LLM assistance for nuanced judgment.

## Narrative Scales

The story engine SHOULD produce narrative at multiple temporal and social scales.

### Tick Reports (Micro)

- brief summaries of notable events in the current tick or day
- useful for live monitoring during development
- format: short structured entries

### Biographies (Individual)

- life summaries of individual residents
- key events: birth, migrations, relationships, achievements, knowledge acquired, death
- especially valuable for residents whose lives were unusual or influential
- format: short narrative paragraphs

### Group Histories (Meso)

- formation, growth, conflicts, achievements, and decline of detected groups
- trade relationships, territorial changes, cultural developments
- format: chronicle-style entries

### Civilization Reports (Macro)

- periodic summaries of the state of civilization emergence
- surplus trends, population dynamics, knowledge distribution, activity radius changes
- comparison across groups or regions
- format: analytical reports with key metrics

### Epoch Summaries (Long-term)

- summaries covering long simulation periods
- major transitions, collapses, recoveries, and unprecedented events
- the closest thing to a "history book" the engine produces
- format: narrative essays

## Causal Fidelity

### The Compression Problem

Narrative necessarily compresses events. A biography cannot include every tick. The danger is that compression introduces false causality — implying that event A caused event B when they were actually coincidental, or omitting the real cause because it was mundane.

### Requirements

- Narrative summaries SHOULD preserve causal relationships from the simulation event log.
- Narrative MUST NOT invent causal links that do not exist in the simulation data.
- Narrative MAY omit events for brevity but SHOULD NOT omit events that are causal prerequisites of reported outcomes.
- When the story engine uses LLM to generate readable prose, the LLM MUST be constrained to work from verified event data, not from its own world knowledge or narrative instincts.

### Auditability

- Every narrative claim SHOULD be traceable to specific simulation events.
- The story engine SHOULD maintain references from narrative artifacts back to source events, enabling verification.

## LLM Usage in Story Engine

The story engine is one of the places where LLM usage is natural and relatively safe (because it is read-only).

### Permitted Uses

- converting structured event data into readable prose
- assessing event significance
- identifying narrative patterns across events
- generating summaries at various scales
- translating simulation data into multiple human languages

### Prohibited Uses

- generating events that did not occur
- filling narrative gaps with plausible but unverified speculation
- creating dialogue that residents did not actually produce
- adding emotional or dramatic interpretation that contradicts the simulation record

### Prompt Discipline

When using LLM for narrative generation, prompts SHOULD:

- provide the raw event data as the primary input
- explicitly instruct the model to report only what happened
- prohibit fabrication or dramatic embellishment beyond what the data supports
- include causal chain data where available

## Output Artifacts

### Artifact Types

- daily/tick reports (structured, automated)
- notable event alerts (real-time during simulation)
- resident biographies (generated on death or on demand)
- group chronicles (periodic or on dissolution)
- civilization status reports (periodic)
- epoch histories (on milestone or on demand)

### Artifact Storage

- Story artifacts MUST be stored separately from simulation state.
- Story artifacts SHOULD reference simulation events by ID for traceability.
- Story artifacts MAY be versioned if regenerated with improved narrative techniques.

## Observation Metrics Integration

The story engine SHOULD incorporate metrics from RFC-0007 (Civilization Emergence) into its reports:

- surplus distribution changes
- cooperation pattern shifts
- knowledge accumulation or loss trends
- activity radius expansion or contraction
- population dynamics

Metrics provide the quantitative backbone that narrative wraps in qualitative context.

## Constitutional Compliance

This RFC is subordinate to RFC-0001 Universe Constitution.

### Law 2: Time Is Irreversible

- narrative MUST NOT retroactively alter the historical record
- narrative is a view of history, not a rewrite of it

### Law 3: Causality

- narrative MUST preserve causal chains from simulation data
- narrative MUST NOT invent causality

### General

- the story engine's read-only constraint protects all constitutional laws by ensuring narrative has zero causal influence on the simulation

## Phase 1 Implementation Guidance

A good Phase 1 story engine would include:

- event detection on the simulation event stream (filter for deaths, first contacts, migrations, discoveries)
- simple significance scoring (rarity + impact)
- automated tick summaries (structured, not prose)
- resident biography generation on death (using LLM to produce a few paragraphs from event log)
- basic metrics dashboard (surplus, population, clustering)
- strict read-only access to simulation state (no write path exists)

Full group chronicles, epoch histories, and multilingual output MAY be deferred to Phase 4.

## Open Questions

- How much LLM cost should be allocated to story generation vs. resident AI decisions?
- Should story artifacts be generated in real-time during simulation or in batch after simulation runs?
- How should the story engine handle events that are statistically significant but narratively boring (gradual surplus growth)?
- Should players be able to request custom narrative views (e.g., "tell me the history of this region")?
- How should the engine handle narrative about events that were caused by bugs or constitutional violations — report them as anomalies or suppress them?

## Future Dependencies

The following RFCs interact with this one:

- `RFC-0009 Player Protocol` (players consume story output)
- `RFC-0010 Economy Protocol` (story access may be a platform service)

## Conclusion

The story engine is OCP's window into its own output. Without it, the simulation is a black box that only its operators can interpret. With it, the search for possible civilizations becomes legible to anyone who cares to watch.

But the window must never become a door. The moment narrative influences simulation, OCP stops searching and starts performing.
