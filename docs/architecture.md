# Architecture

## Event-sourced core

`chronicle/events.py` defines an append-only `EventLog`. Every fact that
enters the system — an NPC death, a witnessed crime, a rumor heard — is an
immutable `Event`. All derived state (belief facets, rumor content,
grudge/obligation ledgers, reputation scores) is computed by folding over
the log, never mutated in place. This gives us, for free:

- **Replayability** — rerun the log to reproduce any world state exactly.
- **Debuggability** — the dashboard's causality timeline is just "show me
  the events that produced this belief."
- **Headless testability** — scenarios seed the log and assert on derived
  state; no running game required (see `scenarios/`).

`chronicle/` must stay engine-agnostic: no Skyrim-specific types or imports.
Everything that knows about Skyrim lives in `adapters/skyrim/`.

## The three tiers

See `docs/vision.md` for the *why*. Architecturally:

- **Math tier** — runs every tick over all ~1,000 NPCs. Deterministic
  propagation (who hears what, from whom, via encounter rolls sampled from
  NPC schedules), decay, and opinion/reputation drift. No LLM calls.
- **Local-LLM tier** — a small local model runs semantic mutation only for
  ~30 high-centrality "gossip hub" NPCs, on a much lower cadence than the
  math tier. Produces new/mutated rumor content and belief updates that get
  folded back into the event log as ordinary events, so tier 1 stays the
  only thing that has to run every tick.
- **Conversation tier** — a large LLM handles player-facing dialogue. It
  reads rendered belief state as context and writes back structured
  evidence (what the player told this NPC, what the NPC just revealed) as
  new events. This is the seam that has to interoperate with Mantella/CHIM
  — see below.

Tier interface is event-in, event-out at every boundary: no tier holds
authoritative state itself. The event log is the only source of truth.

## Injection seam (Mantella/CHIM)

Chronicle doesn't render its own dialogue. Belief/rumor/relationship state
gets serialized into prompt context that Mantella- or CHIM-style dialogue
mods consume, and player statements captured by those mods get turned back
into Chronicle events. This seam is intentionally thin and lives in
`adapters/skyrim/` — see `docs/decisions/0003-substrate-choice.md` for the
open question of exactly which mod's extension points we integrate against.

## Hydration-override seam

When a Skyrim cell loads, vanilla NPC AI packages/schedules take over by
default. The hydration seam is where Chronicle overrides that: on cell
attach, it checks whether any NPC in the cell has Chronicle-driven state
(a grudge that should change their patrol, a rumor that should send them
somewhere) and injects a runtime AI package override before vanilla
schedule logic runs. Also lives in `adapters/skyrim/`.
