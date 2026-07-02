# RFC-0009 Player Protocol

## Status

Draft

## Summary

This RFC defines how human players participate in OCP without collapsing emergence into command-and-control.

The player is not a king. The player is not a god. The player is not a game master. The player owns a House — a persistent presence in the world — and has limited daily Influence that can nudge outcomes but never dictate them.

The player protocol exists to make OCP engaging for humans while preserving the constitutional guarantee that civilization emerges rather than being designed.

## Motivation

A pure research simulation with no human participation is viable but limited in reach. Players bring attention, investment, and unpredictability. But players also bring the instinct to control, optimize, and win — instincts that, if given direct expression, will flatten emergence into strategy-game meta.

The challenge is designing a participation model where players feel meaningful without being sovereign.

## Goals

This RFC defines:

- the House abstraction
- the Influence budget
- allowed player actions
- prohibited player actions
- the boundary between player influence and world causality
- how player participation interacts with AI residents

## Non-Goals

This RFC does not define:

- player UI/UX design
- matchmaking or social features
- monetization details (see RFC-0010)
- specific game modes or scenarios

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
Player          ← this RFC
```

The player sits at the bottom of the world stack. Everything above constrains what the player can do. The player cannot modify Physics, cannot rewrite Universe laws, and cannot directly control Life.

## Normative Language

The key words "MUST", "MUST NOT", "SHOULD", and "MAY" in this document are to be interpreted as binding protocol terms.

## First Principle

The player influences. The player does not control.

A player's actions should feel like being a wealthy patron in a world that does not care about your preferences — not like being an RTS commander whose units obey without question.

## The House

### Definition

A House is a player's persistent presence in the world. It is not a character. It is an institution — a named entity with resources, reputation, and influence that persists across play sessions.

### House Properties

- identity (unique, persistent)
- location (spatial anchor — the House has a home region)
- resource reserves (energy, materials accumulated through world-valid means)
- reputation (how AI residents perceive the House, based on past actions)
- influence budget (daily allocation of intervention capacity)
- history (record of all actions taken)

### House Establishment

- A House MUST be established at a specific location in the world.
- Establishing a House SHOULD require investment (resources, time).
- A House exists within the simulation — it is subject to the same physics, energy, and entropy constraints as everything else.
- A House can be weakened, impoverished, or effectively destroyed by world events.

## Influence Budget

### Definition

Influence is the currency of player action. It represents the limited capacity a House has to affect the world in a given period.

### Properties

- Influence MUST be finite per day (or per N ticks).
- Influence MUST NOT accumulate without bound. Unused influence MAY partially carry over but SHOULD have a cap.
- Influence regeneration SHOULD depend on the House's current state (resource level, reputation, location quality).
- Influence is spent when actions are taken, regardless of whether those actions succeed.

### Design Intent

The influence budget exists to prevent players from micro-managing the world. Even the most engaged player can only nudge a few things per day. The world continues to evolve on its own terms between interventions.

## Allowed Actions

Player actions fall into categories of indirect influence. The common thread is that they change conditions or offer incentives — they do not command.

### Sponsorship

- A player MAY allocate resources to a specific resident or group.
- Sponsored resources are delivered through world-valid means (the House physically transfers food, materials, tools).
- Sponsorship MUST cost energy/resources from the House's reserves.
- The recipient MAY choose how to use sponsored resources. The player cannot dictate usage.

### Investment

- A player MAY fund construction of infrastructure (roads, bridges, shelters, granaries).
- Construction MUST be resolved through physics (material cost, labor, time, location).
- The player specifies what and where. The world determines whether it succeeds and what it costs.
- Invested infrastructure is subject to maintenance and decay like any other structure.

### Introduction

- A player MAY arrange for two residents who would not otherwise meet to encounter each other.
- Introductions MUST respect spatial constraints — the residents must be brought into proximity through movement, not teleportation.
- What happens after the introduction is entirely up to the residents.

### Education

- A player MAY establish or fund teaching relationships.
- Education MUST follow knowledge system rules (RFC-0006): transmission takes time, is lossy, and requires proximity.
- The player can create the conditions for knowledge transfer. The player cannot inject knowledge directly.

### Construction

- A player MAY commission buildings, paths, or other structures.
- All construction MUST comply with physics (material input, location, time, energy cost).
- Built structures belong to the world, not to the player. They may be used, occupied, or damaged by anyone.

### Signaling

- A player MAY place markers, signals, or incentives that residents can perceive.
- Signals MUST be perceivable only by residents within range.
- Signals suggest; they do not compel. A resident MAY ignore a player signal.

## Prohibited Actions

### Direct Control

- A player MUST NOT directly control any resident's actions, movement, or decisions.
- No mind control. No puppet mode. No direct unit commands.

### State Manipulation

- A player MUST NOT directly modify world state (terrain, resources, weather, physics parameters).
- A player MUST NOT create or destroy resources outside of world-valid economic activity.
- A player MUST NOT teleport residents, objects, or information.

### Information Advantage

- A player MUST NOT access information that their House could not legitimately possess (global maps, other players' House state, resident internal states).
- A player's view of the world SHOULD be limited by their House's location, reputation, and communication networks.

### Constitutional Override

- A player MUST NOT bypass any constitutional law.
- No action available to a player may violate energy conservation, causality, bounded cognition, or any other constitutional guarantee.
- There is no admin mode, no cheat code, and no pay-to-bypass.

## Player-Resident Interaction

### Residents Are Not NPCs

AI residents are autonomous agents. They have their own goals, memories, relationships, and survival pressures. A player's House is one influence among many in their world.

### Resident Response to Player Actions

- Residents SHOULD evaluate player actions through the same decision framework they use for all external events.
- Residents MAY accept, reject, or partially comply with player-initiated situations.
- Residents SHOULD develop opinions about the player's House based on past interactions (trust, suspicion, gratitude, resentment).
- A player who consistently provides resources may attract loyal residents. A player whose investments repeatedly fail may lose reputation.

### No Guaranteed Outcomes

- Sponsoring a resident does not guarantee loyalty.
- Building a road does not guarantee usage.
- Introducing two residents does not guarantee cooperation.
- The player proposes conditions. The world and its residents determine outcomes.

## Multi-Player Considerations

### Multiple Houses

- The world MAY support multiple player Houses.
- Houses MUST interact through the same world mechanics as everything else (spatial proximity, resource competition, information limits).
- Houses MUST NOT have special communication channels outside the world's information infrastructure.

### Competition

- Houses MAY compete for influence over regions, residents, or resources.
- Competition MUST be mediated through world mechanics, not through meta-game systems.
- No House has built-in advantages over another (except those earned through in-world investment and reputation).

## Player Entry and Exit

### Entry

- A new player SHOULD be able to establish a House at a location where establishment conditions are met.
- Entry SHOULD NOT disrupt existing simulation state (no land grants carved from occupied territory without world-valid process).

### Exit

- When a player stops participating, the House SHOULD persist as an institution without active direction.
- An abandoned House SHOULD gradually lose influence, resources, and eventually infrastructure through normal entropy.
- The House's historical impact on the world MUST remain.

### Re-Entry

- A returning player SHOULD find their House in whatever state the world has produced during their absence — prosperous, diminished, or gone.

## Constitutional Compliance

This RFC is subordinate to RFC-0001 Universe Constitution.

### Law 3: Causality

- all player actions produce traceable causal chains through world mechanics

### Law 4 & 5: Conservation

- player resource expenditure follows conservation rules; no free resources from player privilege

### Law 7: Bounded Cognition

- player information access is limited to what the House can legitimately perceive

### Law 8: Bounded Computation

- influence budget limits player intervention frequency, analogous to computation limits on AI residents

### Law 9: Information Has Speed

- player communication and awareness are spatially constrained

## Phase 1 Implications

Phase 1 is CLI-only with no player participation. However, the player protocol SHOULD be considered during Phase 1 design to ensure that:

- the simulation architecture supports external influence injection without bypassing the intent-action-resolution cycle
- the event system supports tracking actions by source (engine, AI, player)
- the information model supports perspective-limited views

Player features are implemented in Phase 3.

## Open Questions

- What is the right daily influence budget size (too small = irrelevant, too large = controlling)?
- Should influence regeneration depend on House prosperity, creating a feedback loop?
- How should player actions be priced in influence — flat cost or variable by impact?
- Should players be able to communicate with each other outside the world's information layer?
- How should the system handle players who attempt to grief or exploit the simulation?
- Can a player voluntarily surrender their House to become a pure observer?

## Future Dependencies

The following RFCs interact with this one:

- `RFC-0010 Economy Protocol` (platform rights, potential monetization boundaries)

## Conclusion

The player protocol is OCP's answer to the question: how do humans participate in a world that must remain free to evolve on its own terms?

The answer is: with resources, not commands. With influence, not control. With patience, not optimization.

A player who succeeds in OCP is not one who builds the biggest empire. It is one who nudges conditions in a direction and watches, with genuine uncertainty, what the world makes of it.
