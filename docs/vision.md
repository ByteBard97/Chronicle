# Vision

## The reactive-world goal

Skyrim's world is static except where scripted. NPCs don't know things
unless a quest told them to; they don't gossip, hold grudges, or update
their opinion of the player based on anything but scripted faction/crime
flags. Chronicle exists to make the world *aware of itself*: give NPCs
beliefs with provenance, let those beliefs propagate and mutate as rumors,
let grudges and obligations accumulate from lived events, and feed all of
that back into the game as behavior — schedules, dialogue, reputation — that
the player can perceive and shape.

The goal is not "smarter individual NPCs." It's a world that remembers,
talks about itself, and visibly changes in response to what happens in it.

## North star: the Jarl of Whiterun assassination

If the player (or anything else) kills Jarl Balgruuf, that single event
should cascade:

- **Succession contest** — the court (Proventus Avenicci, Irileth, other
  claimants) reacts distinctly based on their existing relationship to the
  Jarl and to each other; a successor emerges through in-world social
  dynamics, not a scripted flag flip.
- **Economic ripple** — merchants and guards tied to the Jarl's patronage
  are affected; trade and prices in Whiterun shift plausibly.
- **Rumor propagation with mutation** — witnesses tell others, who tell
  others; the story mutates in transit (who did it, why, how) in a way
  that's traceable back through evidence chains to what actually happened.
- **Infrastructure consequences** — guard patrols, faction alignments, and
  quest availability shift as a *consequence* of the social simulation
  state, not as a hand-authored quest branch.

This scenario is the acceptance test for the whole architecture. If
Chronicle can't produce a plausible, legible version of this cascade
headless (see `scenarios/`), the design isn't done.

## Three-tier belief architecture

1. **Math tier** (all ~1,000 named NPCs) — deterministic propagation, decay,
   and encounter rolls sampled from NPC schedules. Cheap, runs every tick.
2. **Local-LLM tier** (~30 high-centrality "gossip hub" NPCs) — semantic
   rumor mutation and motivated reasoning, using a small local model.
3. **Conversation tier** (NPCs talking to the player) — a large LLM renders
   belief state as dialogue and ingests player statements as new evidence,
   writing back into the belief system.

See `docs/architecture.md` for how these tiers interface and how the
Skyrim-specific injection/hydration seams work.

## Tooling as a first-class artifact

The debug dashboard (map + rumor overlay, social graph inspector, causality
timeline, injection console — see `dashboard/README.md`) is not a
nice-to-have. A social simulation you can't inspect is a social simulation
you can't debug, tune, or trust. It ships alongside the sim, not after it.
