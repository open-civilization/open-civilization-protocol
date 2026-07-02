# Open Civilization Protocol (OCP)

## Searching for Possible Civilizations

> **An open protocol for evolving artificial civilizations.**
>
> We are not recreating human history.
>
> We are searching for all possible civilizations.

## 1. Positioning

OCP is not a game.

OCP is not a metaverse.

OCP is not GameFi.

OCP is an **Artificial Civilization Laboratory**.

Its purpose is to study how civilizations may naturally:

- emerge
- evolve
- compete
- merge
- collapse
- leave legacies

Roles inside the system:

- Developers define laws.
- AI explores laws.
- Players influence history.
- Time validates laws.

## 2. First Principle

There is only one sentence at the center of the project:

> Civilization is not designed. It emerges.

Developers must never directly design:

- countries
- democracy
- dictatorship
- industrial revolution
- China
- Europe

Developers only design world laws.

Everything else must be allowed to arise from interaction, scarcity, adaptation, memory, and time.

## 3. World Architecture

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

Invariant boundaries:

- Players cannot modify `Universe`.
- AI cannot modify `Physics`.
- Civilizations cannot modify `Universe`.

## 4. Universe Constitution

This layer is the deepest contract in the system and should be treated as effectively immutable.

### Law 0: Persistence

The world persists.

Civilizations may die.

Players may leave.

Nations may vanish.

The map remains.

Time continues.

### Law 1: Civilization Can Die, Legacy Persists

Roads, bridges, buildings, knowledge, DNA, and culture must be able to outlive the civilization that produced them.

### Law 2: Time Is Irreversible

History cannot be rewritten.

Only forks are allowed.

### Law 3: Causality

Every event must have a cause.

Forbidden:

- spontaneous technology
- spontaneous wealth
- spontaneous population
- spontaneous resources

### Law 4: Energy Conservation

All usable energy must come from real sources, such as:

- solar
- geothermal
- tidal
- chemical
- biological

Infinite resources are forbidden.

### Law 5: Matter Conservation

Resources deplete.

Forests can be cut down.

Mines can be exhausted.

Animals can go extinct.

### Law 6: Knowledge Cannot Appear from Nothing

Knowledge may only come from:

- observation
- experiment
- learning
- inheritance
- transmission

### Law 7: Bounded Cognition

No individual knows the whole world.

### Law 8: Bounded Computation

Every AI resident has a daily thinking budget.

### Law 9: Information Has Speed

No global broadcast.

No instant communication.

### Law 10: Entropy

Without maintenance, systems decay.

That includes:

- roads
- cities
- knowledge
- states

## 5. Core World Variables

The world is built around six foundational variables.

### 5.1 Energy

This is the first variable.

Examples:

- Individual: BMR, calories, fat, stamina
- Household: food reserves, tools
- Tribe: granaries, livestock, land
- Civilization: capture, storage, transport, conversion, utilization, energy density

Civilization development can be framed as improving:

```text
Capture
    ↓
Store
    ↓
Transport
    ↓
Convert
    ↓
Utilize
```

### 5.2 Information

Civilization is, in part, a system for storing and transmitting information.

Examples:

- language
- writing
- education
- religion
- law
- history

### 5.3 Organization

Organization increases energy efficiency.

Examples:

- household
- village
- state
- company
- alliance
- religion

### 5.4 Activity Radius

The key measure is not tech level.

It is how far a civilization can effectively reach.

Examples:

- walking
- horse travel
- ships
- railways
- internet-like communication systems

As activity radius grows, civilization propagation speed rises sharply.

### 5.5 Adaptability

The most durable civilization is not necessarily the strongest.

It is the one that fits changing conditions best.

### 5.6 Time

A civilization's greatest asset is not wealth.

It is the ability to persist.

## 6. Civilization Laws

This section is intentionally provisional and should evolve through RFCs.

### Law A

Life tends to seek maximum net energy.

### Law B

Knowledge has transmission pressure.

Transmission channels may include:

- trade
- war
- migration
- marriage
- education

### Law C

War is not only destruction.

It is also a mechanism of knowledge transfer.

### Law D

Civilization searches for new energy layers.

This is not a technology tree.

It is an energy transition search.

### Law E

Civilization searches for new organizational forms.

This is not a democracy-vs-dictatorship template.

It is an organization search process.

## 7. Life

Life has only three native goals:

```text
Survive
Reproduce
Increase fitness
```

There are no quests.

There is no plot.

## 8. AI

AI is not the world.

AI is only a resident of the world.

AI may only propose intent.

Example:

> Today I want to fish.

The system is responsible for validating whether reality allows that intent to succeed.

AI may not:

- modify physics
- modify universe rules
- access the internet

AI may only perceive and reason over OCP world data, filtered by its own knowledge and constraints.

## 9. Player

The player is not a king.

The player is not a hero.

The player is not a GM.

The player owns a `House` and has limited daily `Influence`.

Players may influence, but not directly control, residents.

Examples of allowed actions:

- sponsor
- invest
- build a school
- arrange introductions or marriages
- build a bridge

Forbidden actions:

- direct NPC mind control

## 10. Story

Stories are not written ahead of time.

Stories are discovered.

The system should automatically detect and summarize events such as:

- love
- war
- invention
- family rise and fall
- dynasties
- entrepreneurship
- religion

From that, the world may generate:

- civilization daily reports
- biographies
- history books

## 11. Token

The token belongs to the platform layer, not the world economy.

It must not directly buy:

- population
- technology
- resources
- war
- weather

It may buy platform rights such as:

- operating rights
- DAO participation
- API access
- AI services
- licenses

## 12. AI Learning

The loop is:

```text
World runs
    ↓
Data is produced
    ↓
AI summarizes patterns
    ↓
Civilization memory forms
    ↓
Residents learn from civilization memory
    ↓
World continues
```

Over time, AI should become more like an OCP resident and less like a generic assistant.

## 13. Open Governance

The protocol should be open.

- GitHub hosts the protocol.
- RFCs structure change.
- Community discusses.
- AI simulates consequences.
- DAO decides.

## 14. Project Phases

### Phase 1

- Universe
- Physics
- Energy
- Life
- 1000 residents
- CLI only

### Phase 2

- agriculture
- trade
- reproduction
- tribes
- maps
- web interface

### Phase 3

- player entry
- house system
- influence system

### Phase 4

- AI stories
- civilization daily reports
- history layer

### Phase 5

- open API
- SDK
- RFC maturity

### Phase 6

- token layer
- DAO
- plugin system

## 15. Phase 1 Technical Direction

Suggested stack:

```text
Rust        world engine
Rust        physics engine
Rust        life engine
Go          API
PostgreSQL  world state
Redis       queue
Python      AI worker
Next.js     web
MapLibre    maps
```

AI balance target:

- rules: 95%
- LLM: 5%

## 16. Repository Structure

```text
open-civilization/
├── README.md
├── VISION.md
├── ROADMAP.md
├── LICENSE
├── docs/
├── rfc/
├── world-engine/
├── physics-engine/
├── life-engine/
├── civilization-engine/
├── ai-engine/
├── story-engine/
├── sdk/
└── api/
```

## 17. Initial RFC Set

- RFC-0000 Project Vision
- RFC-0001 Universe Constitution
- RFC-0002 Energy System
- RFC-0003 World Physics
- RFC-0004 Life Engine
- RFC-0005 AI Decision
- RFC-0006 Knowledge System
- RFC-0007 Civilization Emergence
- RFC-0008 Story Engine
- RFC-0009 Player Protocol
- RFC-0010 Economy Protocol

## 18. North Star

The entire project exists to answer one question:

> If we only give the world a set of fundamental laws, and do not give it any civilization template, what kinds of civilizations will AI evolve?

We do not know the answer.

That is why OCP does not simulate history.

It searches for possible civilizations.
