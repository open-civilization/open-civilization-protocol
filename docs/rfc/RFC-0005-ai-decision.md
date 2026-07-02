# RFC-0005 AI Decision

## Status

Draft

## Summary

This RFC defines how AI reasoning is integrated into resident decision-making in OCP.

AI is not the world. AI is not the engine. AI is a resident of the world — a bounded agent that perceives locally, reasons under constraint, and proposes intent. The world decides whether that intent succeeds.

The central architectural decision is a two-tier model: a fast rules-based tier that handles every tick cheaply, and a slow LLM-assisted tier that is invoked only for novel, high-stakes, or culturally generative situations. The target ratio is approximately 95% rules / 5% LLM by tick-action volume.

## Motivation

The temptation in any LLM-integrated simulation is to route every decision through a language model. This fails for three reasons:

- cost: at 1000 residents and multiple ticks per simulated day, even cheap LLM calls produce ruinous API bills
- latency: LLM round-trips dominate tick time and serialize what should be parallel
- behavioral convergence: LLMs trained on human text tend to produce "reasonable human" behavior by default, which defeats the goal of searching for non-human-templated civilizations

OCP needs AI that is powerful enough to produce surprising, adaptive behavior in novel situations, but constrained enough to not collapse the simulation into a slow, expensive echo of human common sense.

## Goals

This RFC defines:

- the two-tier decision architecture (fast tier + slow tier)
- which decisions belong to each tier
- the intent schema
- the observation and context window available to AI
- the LLM invocation budget and allocation policy
- the boundary between AI reasoning and physics resolution
- safeguards against AI omniscience, AI monoculture, and AI cost explosion

## Non-Goals

This RFC does not define:

- the life engine's survival loop mechanics (see RFC-0004)
- the knowledge representation format (see RFC-0006)
- specific LLM model selection or prompt engineering
- civilization-level collective intelligence (see RFC-0007)

## Architectural Position

```text
Universe
    ↓
Physics
    ↓
Life
    ↓
AI Decision    ← this RFC (cross-cutting service to Life)
    ↓
Civilization
    ↓
Player
```

AI Decision is not a layer in the world stack. It is a service that the life engine calls when a resident's situation exceeds the fast tier's competence. The physics engine never calls the AI layer directly. The AI layer never mutates world state directly.

The flow is always:

```text
Life Engine → (optionally) AI Decision → Intent → Physics Resolution → State Update
```

## Normative Language

The key words "MUST", "MUST NOT", "SHOULD", and "MAY" in this document are to be interpreted as binding protocol terms.

## Two-Tier Decision Architecture

### Tier 1: Fast Rules (Every Tick)

The fast tier handles routine survival decisions using deterministic or stochastic rules. No LLM is involved.

Examples:

- eat available food when hungry
- drink available water when thirsty
- flee from perceived immediate danger
- sleep when exhausted
- move toward known food source when reserves are low
- stay near shelter in bad conditions
- continue current activity if no state change triggers re-evaluation

The fast tier SHOULD be implementable as a utility function, behavior tree, or finite state machine per resident.

### Tier 2: Slow AI (Sparse Invocation)

The slow tier is invoked only when the fast tier encounters a situation it cannot resolve with existing rules.

#### Trigger Conditions

The slow tier SHOULD be triggered when:

- a resident encounters a novel entity, object, or situation not previously categorized in memory
- a high-stakes social decision is required (trust a stranger, form or break an alliance, negotiate a non-routine exchange)
- a resident must evaluate whether to migrate to an unknown area
- a resident has an opportunity to create, name, or ritualize something (cultural generativity)
- a resident faces a dilemma where multiple survival-relevant options conflict
- a resident is asked to communicate complex or abstract information

#### Non-Trigger Situations

The slow tier MUST NOT be invoked for:

- routine foraging, eating, drinking, sleeping
- simple movement along known paths
- reflexive danger avoidance
- repetition of previously resolved decisions in unchanged conditions
- any situation the fast tier already handles adequately

### Budget Enforcement

- Each resident MUST have a per-day (or per-N-ticks) LLM invocation budget.
- Budget SHOULD vary by individual cognitive capacity (per RFC-0001 Law 8).
- When budget is exhausted, the resident MUST fall back to fast-tier decisions only for the remainder of the budget period.
- A resident operating on fast-tier-only is not broken — it is simply less reflective, which is a realistic cognitive constraint.

## Intent Schema

All resident decisions, whether from the fast tier or the slow tier, MUST be expressed as structured intents.

### Minimum Intent Fields

```text
intent:
  actor:        resident_id
  action:       enum (move, forage, hunt, fish, drink, rest, build, repair,
                      communicate, share, attack, observe, experiment, ...)
  target:       cell_id | resident_id | object_id | null
  parameters:   action-specific key-value pairs
  energy_offer: maximum energy the resident is willing to spend
  timestamp:    simulation tick
```

### Intent Properties

- Intents MUST NOT include world state modifications. They are proposals, not commands.
- Intents MUST be resolvable by the physics engine without reference to the AI layer.
- The physics engine MAY reject, partially fulfill, or fully fulfill any intent.
- The AI layer MUST NOT receive feedback about whether an intent will succeed before submitting it. Prediction is the resident's problem, not a service the engine provides.

## Observation Window

The AI layer, when invoked, MUST reason from a constrained context — not from global world state.

### Context Available to AI

- the resident's current physiological state (energy, health, hunger, fatigue)
- the resident's memory (bounded, lossy, as defined in RFC-0004)
- the resident's current perception (local cells within perception radius)
- the resident's social bonds and recent interaction history
- the resident's trait vector

### Context Forbidden to AI

- other residents' internal states (energy, intent, memory)
- cells beyond perception radius
- global world statistics (total population, average energy, resource maps)
- future environmental changes
- the physics engine's resolution rules or probability tables
- any real-world internet or training data not mediated through OCP world context

### Prompt Construction

When the slow tier is invoked, the prompt to the LLM SHOULD be constructed from the observation window above and nothing else.

The prompt MUST NOT include:

- system instructions that leak world rules the resident could not know
- historical context the resident has not personally experienced or been told
- hints about what the "correct" or "interesting" decision would be

The AI is a resident, not a narrator.

## Personality and Behavioral Diversity

### Anti-Monoculture Requirement

If all residents use the same LLM with the same prompt structure, they will tend to converge on similar behaviors. This defeats emergence.

To counteract monoculture:

- The slow tier SHOULD inject the resident's trait vector into the prompt as behavioral biases (e.g., risk-tolerant vs. cautious, social vs. solitary, curious vs. conservative).
- Residents with different life histories SHOULD produce different AI outputs even in identical situations, because their memories and social bonds differ.
- The engine MAY add controlled noise or temperature variation to LLM sampling to increase behavioral diversity.
- Residents MUST NOT share a collective reasoning process. Each AI invocation is individual.

## Decision Quality and Cognitive Budget

### Relationship Between Budget and Quality

- Residents with higher cognitive budgets MAY receive longer context windows, more reasoning steps, or more sophisticated prompt construction.
- Residents with lower cognitive budgets SHOULD receive shorter context, simpler prompts, or faster (cheaper) model tiers.
- This creates a natural spectrum from "instinctive" to "reflective" behavior within the population.

### Cognitive Development

- A resident's effective cognitive budget MAY increase with age, experience, or tool access.
- A resident's effective cognitive budget MAY decrease with injury, starvation, or extreme fatigue.
- This allows the simulation to model the difference between a desperate, exhausted forager making snap decisions and a well-fed, experienced elder deliberating carefully.

## Learning and Behavioral Adaptation

### Within-Lifetime Learning

- Residents SHOULD be able to update their fast-tier behavior based on outcomes.
- If a resident discovers that a particular location reliably provides food, the fast tier SHOULD learn to prefer that location without requiring an LLM call.
- If a resident suffers repeated negative outcomes from a behavior, the fast tier SHOULD reduce its weight.

### Cross-Generation Learning

- Learned behavioral patterns MAY be transmitted to offspring or nearby residents through imitation or communication (subject to RFC-0006 Knowledge System constraints).
- Transmitted knowledge MUST include fidelity loss as specified in RFC-0001 Law 6.

## Safeguards

### Against Omniscience

- The observation window is the only input to AI reasoning. No exceptions.
- Audit: it SHOULD be possible to inspect any AI decision and verify that the input context contained only information the resident could legitimately possess.

### Against Cost Explosion

- Hard per-resident, per-tick LLM budget caps.
- The fast tier MUST be the default path. The slow tier is the exception.
- Batch processing: when multiple residents trigger the slow tier in the same tick, calls MAY be batched for throughput but MUST remain individually contextualized.

### Against Behavioral Convergence

- Trait-based prompt variation.
- Memory-based context variation.
- Temperature/sampling variation.
- No shared reasoning or collective prompt.

### Against World-Knowledge Leakage

- The LLM's training data contains human history, science, and culture. A resident must not benefit from this knowledge unless it has been independently discovered within the simulation.
- Prompt construction MUST actively frame the resident as an OCP world inhabitant with only OCP world knowledge.
- If a resident "invents" something suspiciously similar to a real-world technology without a plausible in-world causal chain, the engine SHOULD flag this for review.

## Constitutional Compliance

This RFC is subordinate to RFC-0001 Universe Constitution.

### Law 6: Knowledge Cannot Appear from Nothing

- AI reasoning inputs are restricted to legitimately acquired knowledge

### Law 7: Bounded Cognition

- observation window enforces local, partial, delayed perception

### Law 8: Bounded Computation

- LLM budget caps enforce finite thinking resources
- budget heterogeneity reflects individual differences

### Law 9: Information Has Speed

- AI context excludes distant or instantaneous global information

## Phase 1 Implementation Guidance

A good Phase 1 AI decision system would include:

- utility-function-based fast tier covering basic survival actions
- LLM slow tier triggered by novelty, social stakes, or cultural opportunity
- hard budget of 1–3 LLM calls per resident per simulated day
- observation window constructed from resident perception + memory only
- trait vector injected into slow-tier prompts for behavioral diversity
- intent schema submitted to physics for resolution
- logging of all AI invocations for audit and research analysis

Start with 50 residents to calibrate the trigger conditions and budget allocation before scaling to 1000.

## Open Questions

- What is the optimal trigger threshold for slow-tier invocation (too sensitive = cost explosion, too conservative = missed emergence)?
- Should the fast tier use a shared utility function with per-resident parameter variation, or fully independent behavior specifications?
- How should "novelty" be detected — by the resident's memory state, by a hash of the situation, or by a lightweight classifier?
- What is the minimum LLM capability required (can a small/local model handle slow-tier duties, or is a frontier model necessary)?
- Should residents be able to "delegate" cognitive budget to another resident (a primitive form of institutional reasoning)?

## Future Dependencies

The following RFCs depend on or interact with this one:

- `RFC-0006 Knowledge System`
- `RFC-0007 Civilization Emergence`
- `RFC-0008 Story Engine`

## Conclusion

AI in OCP is not the engine that runs the world. It is the spark that makes residents occasionally surprising.

The two-tier architecture protects the project from the two traps that kill LLM-integrated simulations: cost explosion and behavioral monoculture. Rules handle the ordinary. LLM handles the extraordinary. Physics validates both.

If this boundary holds, 1000 residents can run affordably, behave diversely, and occasionally do something no one designed them to do.
