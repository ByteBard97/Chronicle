---
status: accepted
date: 2026-08-20
---

# 0001: External Python service, not an in-process SKSE plugin

## Context

Chronicle needs to simulate beliefs, rumors, grudges, and reputation across
~1,000 NPCs, including LLM calls at two of its three tiers. Skyrim's engine
constraints (Papyrus's execution model, SKSE plugin threading, no native
Python) make this hard to do entirely in-process.

## Decision

Chronicle runs as an external Python service. Skyrim-side code
(`adapters/skyrim/`) is a thin seam: it forwards game events out over IPC
and accepts state/AI-package injections back in. The simulation itself
never runs inside the game process.

## Rationale

- LLM inference (local or API) is far more tractable as a normal Python
  process than embedded in an SKSE DLL.
- Keeps the simulation engine-agnostic (`chronicle/` has zero Skyrim
  imports) — the substrate choice stays reversible even after this decision.
- Precedent exists: Mantella and CHIM both prove the "external service +
  Papyrus/SKSE bridge" pattern works in practice. See
  `docs/research/` once filed.

## Consequences

- Need an IPC/transport layer (HTTP, as Mantella and CHIM both use, is the
  likely default — confirm against research findings).
- Latency budget between the game and the service becomes a real design
  constraint, especially for the conversation tier.
