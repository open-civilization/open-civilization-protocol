# RFC-0010 Economy Protocol

## Status

Draft

## Summary

This RFC defines the boundary between OCP's platform economy and the simulated world economy.

There are two economies in OCP. They must never be confused:

1. **World economy**: the in-simulation flow of energy, resources, labor, and knowledge among residents and groups. This is governed by physics, energy conservation, and causality. It is real within the simulation.

2. **Platform economy**: the external economic layer through which human participants, developers, and the DAO interact with OCP as a service. This includes tokens, API access, operational rights, and governance participation.

The platform economy MUST NOT corrupt the world economy. No amount of external spending may create in-world resources, bypass physics, or purchase simulation outcomes.

## Motivation

Every simulation project that introduces monetization faces the same failure mode: economic incentives begin to distort the simulation itself. Pay-to-win, resource injection, premium advantages, and sponsored outcomes gradually erode the integrity of the world until the simulation is optimizing for revenue rather than emergence.

OCP's constitutional layer (RFC-0001) was designed to resist exactly this pressure. This RFC makes that resistance explicit at the economic level.

## Goals

This RFC defines:

- the strict separation between platform economy and world economy
- what the platform token may and may not purchase
- anti-corruption constraints
- how platform economics interacts with governance
- the boundary between legitimate platform services and world-integrity violations

## Non-Goals

This RFC does not define:

- token price or monetary policy
- specific DAO governance mechanics
- marketing or growth strategy
- detailed API pricing
- investment or fundraising structure

## Architectural Position

The platform economy exists outside the world stack entirely.

```text
┌─────────────────────────────┐
│      Platform Economy       │  ← tokens, rights, services, governance
│      (this RFC)             │
├─────────────────────────────┤
│      World Stack            │
│  Universe → Physics → Life  │  ← governed by RFC-0001 through RFC-0009
│  → Civilization → Player   │
└─────────────────────────────┘
```

The platform economy wraps around the world stack but never penetrates it. It provides access to the simulation, not influence over it.

## Normative Language

The key words "MUST", "MUST NOT", "SHOULD", and "MAY" in this document are to be interpreted as binding protocol terms.

## First Principle

Money buys access. Money does not buy reality.

The platform economy provides rights to participate, observe, compute, and govern. It MUST NOT provide rights to alter simulation physics, inject resources, or purchase outcomes.

## World Economy

The world economy is fully internal to the simulation.

### Properties

- Energy and resources flow according to physics and conservation laws.
- Trade, exchange, and economic activity among residents emerge through life-layer interactions.
- Value in the world economy is determined by scarcity, labor, and situational need — not by external pricing.
- No world-economy variable is denominated in platform tokens.

### Restrictions

- The world economy MUST NOT reference, contain, or be influenced by the platform token.
- World-economy resource quantities MUST NOT be adjustable by token expenditure.
- World-economy trade prices MUST NOT be set by external market forces.
- No resident, group, or civilization may possess platform tokens or interact with the platform economy directly.

## Platform Economy

The platform economy governs external human interaction with OCP as a system.

### Platform Token

The platform token is a governance and access instrument, not an in-world currency.

### What the Token May Purchase

- **Operational rights**: the right to run a House (player participation), subject to all player protocol constraints (RFC-0009)
- **API access**: the right to query simulation data, event streams, story artifacts
- **Compute allocation**: the right to run simulation instances, fork experiments, or request analysis
- **DAO participation**: voting rights on protocol governance decisions
- **AI services**: access to LLM-powered analysis, story generation, or research tools operating on simulation data
- **Observation rights**: access to detailed metrics, dashboards, and research data

### What the Token Must Not Purchase

- **Population**: tokens MUST NOT create, spawn, or summon residents
- **Technology**: tokens MUST NOT unlock, accelerate, or inject knowledge
- **Resources**: tokens MUST NOT create energy, food, materials, or any world resource
- **Military advantage**: tokens MUST NOT grant combat bonuses, troop spawning, or strategic information
- **Weather or environment**: tokens MUST NOT alter terrain, climate, seasons, or natural processes
- **Resident behavior**: tokens MUST NOT directly influence, bribe, or control AI resident decisions
- **Historical revision**: tokens MUST NOT alter, delete, or suppress historical records
- **Constitutional exemption**: tokens MUST NOT purchase exceptions to any constitutional law

### The Bright Line

If a platform action would create a causal effect inside the simulation that is not mediated through a constitutionally valid channel (physics, life, player protocol), it is a corruption and is prohibited.

The only legitimate path from platform economy to world economy is through the player protocol (RFC-0009), which is itself bounded by influence budgets, spatial constraints, and constitutional compliance.

## Anti-Corruption Constraints

### Structural Protections

- The platform token MUST NOT appear in the world state database.
- No simulation engine component SHOULD have read access to token balances or platform-economy state.
- Player influence budgets MUST NOT scale with token holdings beyond a defined cap.
- The API SHOULD enforce read-only access to simulation state for all token-authenticated requests (write access only through player protocol).

### Escalation Prevention

- If influence budget were proportional to token expenditure without limit, wealthy players would dominate the simulation. This MUST be prevented by capping per-House influence regardless of token holdings.
- Premium tiers MAY exist for observation depth (more data, more history, better analysis) but MUST NOT exist for intervention power.

### Audit Trail

- All platform-to-world interactions (player actions) MUST be logged with both platform identity and world effect.
- Audit logs SHOULD be available for governance review.
- Any pattern of platform actions that appears to circumvent anti-corruption constraints SHOULD be flaggable for review.

## Governance Interface

### DAO Scope

The DAO governs the platform and the protocol — not the world.

DAO decisions MAY include:

- protocol version upgrades
- RFC amendment proposals
- fee structure changes
- new platform service approval
- engine parameter adjustments (map size, tick rate, resident cap)
- research priority allocation

DAO decisions MUST NOT include:

- direct world state modifications
- resource grants to specific Houses or regions
- forced outcomes in ongoing simulations
- constitutional law suspension for commercial purposes
- selective enforcement of rules based on token holdings

### Constitutional Amendment

Changes to RFC-0001 (Universe Constitution) SHOULD require a higher governance threshold than ordinary protocol changes. This protects the deepest laws from being eroded by routine governance pressure.

## Revenue Model Guidance

This section is advisory, not normative. It suggests revenue approaches that are compatible with the anti-corruption framework.

### Compatible Revenue Sources

- subscription access to observation and analysis tools
- compute fees for running simulation instances or forks
- API access tiers based on data depth and query volume
- premium story and narrative services
- research partnership access
- educational and institutional licenses

### Incompatible Revenue Sources

- pay-to-win mechanics
- resource packs or loot boxes
- premium residents with enhanced capabilities
- VIP influence multipliers
- sponsored in-world events or outcomes
- advertising placed within the simulation world

## Phase 1 Implications

Phase 1 has no platform economy. However, Phase 1 design SHOULD ensure that:

- world state and simulation logic contain no hooks for external economic input
- the engine architecture enforces a clean boundary between simulation state and external API state
- event logging supports future audit requirements

Platform economy implementation begins in Phase 6.

## Open Questions

- Should influence budget have any relationship to token holdings, or be completely flat across all players?
- How should the DAO handle proposals that are technically legal but clearly intended to gain unfair world advantage?
- Should simulation forks (what-if experiments) be treated as a premium service or a public good?
- How should the platform handle secondary markets for House ownership or transfer?
- What anti-corruption constraints should be constitutional (hard to change) vs. governance-adjustable?

## Future Dependencies

This RFC is the terminal document in the current RFC set. It depends on all prior RFCs and introduces no new downstream dependencies.

## Conclusion

The economy protocol is the last line of defense between OCP's scientific integrity and the pressures that destroy every simulation that becomes popular enough to monetize.

If this line holds, OCP can sustain itself economically while remaining an honest search system. If this line fails — if tokens can buy world outcomes — then OCP becomes a pay-to-win game wearing a research lab coat.

The rule is simple: money buys access. Money does not buy reality.
