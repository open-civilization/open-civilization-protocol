# RFC-0001 Universe Constitution

## Status

Draft

## Summary

This RFC defines the constitutional layer of OCP.

The constitution is the deepest protocol contract in the system. It exists to protect emergence from being corrupted by implementation shortcuts, authorial bias, or product pressure.

If later engines, AI policies, or player systems conflict with the constitution, the constitution wins.

## Motivation

Without a constitutional layer, artificial civilization projects tend to drift toward one or more failure modes:

- hidden human-history assumptions
- direct state mutation by privileged systems
- resource creation without causal origin
- omniscient AI behavior
- story-first overrides of simulation reality
- product decisions that quietly weaken the world model

OCP cannot become a search system for possible civilizations unless its deepest laws are explicit, testable, and resistant to accidental erosion.

## Goals

This RFC defines:

- which laws sit at the `Universe` layer
- who is constrained by those laws
- which guarantees are mandatory in every implementation
- how constitutional violations should be detected and surfaced

## Non-Goals

This RFC does not define:

- detailed physical formulas
- the full world state schema
- resident decision logic
- player UI or product rules
- economy balancing

Those belong in later RFCs and must remain subordinate to this one.

## Architectural Position

The OCP world stack is:

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
```

The constitution governs the `Universe` layer.

Everything below it must comply with it:

- `Physics` cannot violate constitutional conservation or causality
- `Life` cannot bypass bounded cognition or bounded computation
- `Civilization` cannot create world facts from narrative convenience
- `Player` cannot act as a sovereign controller over reality

## Normative Language

The key words "MUST", "MUST NOT", "SHOULD", and "MAY" in this document are to be interpreted as binding protocol terms.

## Constitutional Scope

The universe constitution is intended to be:

- stable across implementations
- versioned only under extraordinary governance
- stricter than ordinary engine configuration
- enforceable by runtime validation where possible

This means not every engine parameter is constitutional.

For example:

- map size is not constitutional
- tick duration is not constitutional
- whether information has propagation delay is constitutional
- whether history can be rewritten is constitutional

## Constitutional Subjects

The following subjects are bound by this RFC:

- world engine
- physics engine
- life engine
- civilization engine
- AI worker
- story engine
- player protocol
- administrative tooling

No subsystem receives a hidden exemption.

There is no debug path, monetization path, or narrative path that may bypass constitutional laws.

## Law 0: Persistence

### Statement

The world MUST persist beyond the lifespan of any civilization, polity, player, or resident.

### Meaning

Civilizations may collapse.

Players may leave.

States may disappear.

The world timeline continues.

### Requirements

- The simulation MUST model world continuity as a default invariant.
- Local extinction MUST NOT imply world deletion.
- A civilization record MAY terminate, but its former existence MUST remain historically representable.
- Legacy artifacts MAY continue to affect later states after their creators disappear.

### Forbidden Shortcuts

- resetting the world because a major civilization died
- deleting history because no active player remains
- treating a scenario session as if it were the whole universe

## Law 1: Civilization Can Die, Legacy Persists

### Statement

Civilization entities MAY perish, but their artifacts and consequences MUST be allowed to outlive them.

### Meaning

Roads, bridges, buildings, knowledge, genes, customs, and institutions can become inherited world structure.

### Requirements

- Material artifacts SHOULD remain in the world until destroyed, decayed, or transformed.
- Knowledge MAY survive through records, teaching, imitation, or inheritance.
- Cultural or organizational patterns MAY continue after the originating group dissolves.
- Later agents MUST be able to interact with inherited traces.

### Protocol Implication

The world model MUST distinguish between:

- a civilization entity ending
- the legacy graph of effects it leaves behind

## Law 2: Time Is Irreversible

### Statement

Time MUST be one-way within a world lineage.

History MUST NOT be rewritten in place.

Forking is permitted. Editing the past of an existing lineage is not.

### Requirements

- Every committed world event MUST occupy an ordered position in history.
- Once committed, historical facts MUST NOT be mutated retroactively in the same lineage.
- Counterfactual experiments MAY be run only as explicit forks.
- Forked worlds MUST carry lineage metadata identifying their source point.

### Forbidden Shortcuts

- "fixing" simulation errors by editing past outcomes in place
- backfilling outcomes without preserving temporal order
- silently replacing a historical event with a corrected version

## Law 3: Causality

### Statement

Every material world event MUST have a representable cause chain.

### Meaning

Nothing important appears from nowhere:

- no spontaneous technology
- no spontaneous wealth
- no spontaneous population
- no spontaneous resources

### Requirements

- State transitions MUST be attributable to one or more prior conditions, actions, or processes.
- Engine-produced events MUST preserve provenance metadata sufficient for replay or audit.
- High-level summaries MAY compress events, but raw causal traces MUST remain available at engine level.

### Minimum Provenance Expectations

At minimum, a committed event SHOULD be traceable to:

- actor or process origin
- input state
- resolution rule
- output state
- simulation time

## Law 4: Energy Conservation

### Statement

Usable energy MUST come from modeled sources and transformations.

Infinite energy is forbidden.

### Accepted Source Categories

Examples include:

- solar
- geothermal
- tidal
- chemical
- biological

This list is illustrative, not exhaustive. Future energy categories remain subject to the same conservation rule.

### Requirements

- Energy capture, storage, transfer, conversion, and loss MUST be modelable.
- Systems MUST NOT grant free energy because of rank, narrative value, or monetization.
- Efficiency gains MAY improve utilization but MUST NOT imply creation from nothing.

### Protocol Implication

Any subsystem that claims to create output without an upstream energy source is constitutionally invalid.

## Law 5: Matter Conservation

### Statement

Material resources MUST deplete, move, transform, or recycle. They MUST NOT appear from nothing.

### Meaning

Forests can be cut down.

Mines can be exhausted.

Animals can go extinct.

### Requirements

- Resource extraction MUST reduce some accessible stock, quality, or abundance measure.
- Material transformation MUST preserve traceable origin, even if abstracted.
- Renewable systems MAY replenish, but replenishment MUST occur through modeled processes over time.

## Law 6: Knowledge Cannot Appear from Nothing

### Statement

Knowledge MUST arise from acquisition pathways, not arbitrary injection.

### Accepted Pathways

- observation
- experiment
- learning
- inheritance
- transmission

### Requirements

- Residents MUST NOT receive omniscient world truth by default.
- Civilization-level knowledge MUST be accumulated through individual or institutional processes.
- Story systems MUST NOT invent discoveries that the simulation did not earn.
- LLM assistance, if used, MUST operate inside a knowledge boundary defined by world data and agent perspective.

### Transmission Fidelity

- At least one low-cost transmission pathway (such as oral tradition or imitation) MUST be available before formal record-keeping exists.
- Transmission MAY be imperfect. Distortion, forgetting, and reinterpretation during transmission MUST be treated as a legitimate source of novelty, not merely as an error to be eliminated.
- Transmission fidelity SHOULD be net-positive across generations on average; if every generation loses more than it retains, accumulated knowledge cannot outlast individual lifespans and civilization-level memory becomes impossible.

## Law 7: Bounded Cognition

### Statement

No individual agent may know the whole world.

### Requirements

- Resident observations MUST be local, delayed, partial, or otherwise constrained.
- An agent's usable knowledge MUST be separable from objective world state.
- Decision systems MUST reason from perspective-limited context rather than omniscient truth.

### Protocol Implication

There MUST be a distinction between:

- world state
- agent belief state

If the system collapses those two concepts into one, it violates the constitution.

## Law 8: Bounded Computation

### Statement

Every AI resident MUST operate under finite thinking budget.

### Meaning

No resident may perform unbounded planning, inference, or search every tick.

### Requirements

- The engine MUST define or enforce computational ceilings at the resident level.
- Decision quality MAY vary with budget, context, or urgency.
- Privileged "perfect play" resident reasoning is forbidden as a baseline mechanism.
- Computational ceilings MUST NOT be a single uniform constant applied identically to every resident. Budgets SHOULD vary by individual attributes such as age, health, experience, tools, or role.

### Heterogeneity Rationale

Uniform budgets flatten out the differences that comparative advantage depends on. If every resident faces the same effective ceiling, there is no basis for specialization, delegation, or exchange to emerge. Variation in bounded computation is one of the conditions that makes division of labor possible rather than merely permitted.

### Notes

This law protects both realism and system scalability.

It prevents the world from becoming a hidden global optimizer disguised as local life.

## Law 9: Information Has Speed

### Statement

Information propagation MUST take time and route through channels.

There is no global broadcast by default.

There is no instant communication by default.

### Requirements

- Information transfer MUST depend on carrier, medium, or institution.
- Distant knowledge SHOULD propagate with delay, distortion risk, or transmission cost.
- Coordination at scale MUST be constrained by communication infrastructure.

### Protocol Implication

Activity radius and communication capability become real civilization variables rather than cosmetic lore.

## Law 10: Entropy

### Statement

Without maintenance, structures degrade.

### Meaning

Roads decay.

Cities decay.

Knowledge is lost.

States weaken.

### Requirements

- Durable systems MUST still incur maintenance burden.
- Neglected infrastructure SHOULD lose quality or utility over time.
- Institutions MAY decay through coordination failure, memory loss, or resource depletion.
- Preservation SHOULD require ongoing energy, organization, or ritualized transmission.

## Cross-Law Invariants

The laws above are not independent slogans. They form a joint constraint set.

The following composite invariants SHOULD hold:

- persistence plus irreversibility implies durable historical record
- causality plus conservation implies auditable state transitions
- bounded cognition plus information speed implies local perspective
- entropy plus persistence implies archaeology, ruins, and forgotten knowledge
- legacy persistence plus knowledge conservation implies recoverable inheritance

## Enforcement Model

The constitution should not exist only as prose.

Implementations SHOULD enforce it using at least some of the following:

- schema constraints
- invariant checks
- event provenance requirements
- simulation audits
- replay validation
- fork lineage metadata
- engine test suites

## Constitutional Violations

A constitutional violation occurs when a subsystem produces a state transition that contradicts one or more laws in this RFC.

Examples:

- an AI resident acts using knowledge it could not have acquired
- a city consumes energy without a modeled source
- an event appears with no causal predecessor
- a timeline record is rewritten in place

### Required Handling

- Violations MUST be detectable in development environments.
- Violations SHOULD be logged with rule identifiers.
- Violations SHOULD fail tests when reproducible.
- Production handling MAY differ by severity, but silent acceptance is strongly discouraged.

## Governance Guidance

This RFC should be treated as a high-bar document.

Ordinary balance tuning does not justify editing constitutional law.

A constitutional amendment should require stronger governance than a normal feature RFC, because changing these laws changes what kind of project OCP is.

## Open Questions

- Which constitutional checks can be made hard runtime invariants in Phase 1?
- Which checks must begin as offline audits before becoming online enforcement?
- Should constitutional law IDs be surfaced directly in engine event logs?

## Future Dependencies

The following RFCs depend directly on this document:

- `RFC-0002 Energy System`
- `RFC-0003 World Physics`
- `RFC-0004 Life Engine`
- `RFC-0005 AI Decision`
- `RFC-0006 Knowledge System`
- `RFC-0007 Civilization Emergence`
- `RFC-0008 Story Engine`
- `RFC-0009 Player Protocol`
- `RFC-0010 Economy Protocol`

## Conclusion

The universe constitution is what keeps OCP from collapsing into a themed sandbox with hidden author control.

If this layer remains strong, the project can search honestly.

If this layer becomes negotiable, emergence becomes branding rather than architecture.
