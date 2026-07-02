# Open Civilization Protocol (OCP)

> **Rule #0: The engine must never assume human civilization is the only correct outcome.**
>
> **世界引擎绝不能假设人类历史的发展路径是唯一正确答案。**

> **An open protocol for evolving artificial civilizations.**
>
> We are not recreating human history.
>
> We are searching for all possible civilizations.

OCP is not a game.

OCP is not a metaverse.

OCP is not GameFi.

OCP is an **Artificial Civilization Laboratory**.

The first phase of this project is not about shipping business features. It is about defining a durable protocol surface for an artificial world that can evolve for years without forcing repeated rewrites.

## North Star

> If we only give a world a set of fundamental laws, and no predefined civilization templates, what kinds of civilizations will AI evolve?

We do not know the answer.

That is why OCP is not a history simulator.

It is a search system for possible civilizations.

## First Principles

There is only one first principle:

> Civilization is not designed. Civilization emerges.

Developers should never directly design:

- nations
- democracies
- dictatorships
- industrial revolutions
- historical analogs

Developers should only design:

- world laws
- constraints
- protocols
- simulation surfaces

Everything else should be allowed to emerge.

## World Stack

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

Control boundaries:

- Players cannot modify `Universe`.
- AI residents cannot modify `Physics`.
- Civilizations cannot rewrite `Universe`.

## Core Documents

- [VISION.md](/Users/robin/Documents/Playground/open-civilization/VISION.md): project charter and philosophy
- [ROADMAP.md](/Users/robin/Documents/Playground/open-civilization/ROADMAP.md): staged execution plan
- [docs/rfc/README.md](/Users/robin/Documents/Playground/open-civilization/docs/rfc/README.md): RFC process and index

## Repository Layout

```text
open-civilization/
├── README.md
├── VISION.md
├── ROADMAP.md
├── LICENSE
├── docs/
│   └── rfc/
├── world-engine/
├── physics-engine/
├── life-engine/
├── civilization-engine/
├── ai-engine/
├── story-engine/
├── sdk/
├── api/
└── examples/
```

## Phase 1 Scope

Phase 1 should stay intentionally narrow:

- `Universe`
- `Physics`
- `Energy`
- `Life`
- about 1000 residents
- command-line execution

The goal is to prove the constitutional layer and simulation protocol, not to prematurely optimize for product UX.

## Design Bias

OCP should prefer:

- persistence over spectacle
- causality over convenience
- emergence over scripting
- protocols over hardcoded content
- simulation integrity over short-term monetization

## Status

This repository currently defines the founding vision, roadmap, and RFC surface for OCP v0.1.
