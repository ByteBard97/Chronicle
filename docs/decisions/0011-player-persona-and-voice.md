---
status: proposed
date: 2026-08-30
---

# 0011: Player persona — authored character voice, intent-driven dialogue, and utterances as evidence

## Context

`docs/vision.md`'s conversation tier (tier 3) already commits to two things:
a large local LLM rendering NPC belief state as dialogue, and **ingesting
player statements as new evidence** that writes back into the belief system.
This ADR designs the missing half of that loop: the player's side of the
conversation.

The problem it solves is the oldest unsolved compromise in CRPG dialogue.
Authored option lists (Skyrim's 3–5 fixed choices) can only ever offer what a
writer predicted, and voiced protagonists have historically made it worse —
Fallout 4's paraphrase-wheel is the canonical failure: the player picks
"sarcastic," hears a line that isn't what they meant, and loses ownership of
their own character. Silent protagonists preserve ownership but sacrifice
voice entirely.

Chronicle's architecture enables a third option that wasn't previously
available: the player *authors their character's personality once* (the way
they already author race and appearance), picks an **intent** in each
conversation, and the LLM renders the line in that character's voice —
grounded in what the NPC actually believes about the player (rule 10's
observer-local reputation, `chronicle/social.py`) and what has actually
happened (the event log, layer 1). The generated utterance then enters the
simulation as a claim (`chronicle/claims.py`) — it can be overheard, repeated,
mutated, and traveled with, exactly like any NPC-originated claim. What you
say has consequences because what you say becomes *evidence*.

`chronicle/fixtures/north_star.py` already models the player as a first-class
entity (`the_player`); this ADR extends that from "entity the sim reasons
about" to "entity with an authored expressive identity."

## Decision

### 1. The persona is authored once, as a character-creation step

At character creation (or first Chronicle init on an existing save), the
player defines:

- **Trait profile** — Big Five dimensions plus a small set of D&D-fluent
  stats (intelligence, charisma, composure). These are the player's authoring
  interface, chosen for legibility, not because trait scores are directly
  promptable (they are not — see §2).
- **Mannerisms** — free-text and pick-list behavioral notes: formal vs. blunt,
  what the character never does, how they handle being insulted.
- **Voice** — a TTS voice selected from a provided cast, the same way race is
  selected. Voices are original synthetic voices or properly licensed/
  consented recordings. **Cloning the voices of Skyrim's voice actors — or
  any real person's voice without documented consent — is out of scope for
  anything Chronicle ships or recommends**, both for licensing reasons and
  because the modding community's consent norms around voice cloning are
  settled and we are on the wrong side of them if we ignore it.

The persona is stored per-`save_uuid` (ADR-0004), so it branches with the
timeline like everything else.

### 2. Trait scores compile to a "voice card"; the model never sees raw scores

An LLM cannot reliably render "Agreeableness 0.3" into prose. The authoring
UI's trait sliders therefore **compile into a voice card**: a behavioral
prompt document containing speech patterns, verbal tics, hard constraints
("never apologizes," "answers questions with questions"), and 3–5 exemplar
lines in the character's voice. The compilation is deterministic and
inspectable in the dashboard — the player (and a debugger) can read exactly
what the model will be told about who this character is. Persona edits
recompile the card; the card, not the sliders, is what the conversation tier
consumes.

### 3. Dialogue is intent-driven; options are generated in a single call

In conversation, the player selects from a bounded **intent taxonomy** —
initial set: *greet, inquire, negotiate, persuade, deceive, intimidate,
charm, mock, farewell* — plus free-form input as an advanced path. The
conversation tier then generates 3–5 candidate lines **in one LLM call**
("four ways this voice card expresses intent=negotiate, given this NPC's
belief state about the player"), each tagged with its intended register so
the player can verify the paraphrase before committing. This inverts the
Fallout 4 failure mode: the player confirms the *actual words*, never a
paraphrase of them.

Hard constraints:

- **"Say nothing / walk away" is always an option.** Generated dialogue is an
  offer, never a funnel.
- **A re-roll costs one call** and is always available.
- **Silent protagonist remains a first-class path.** Voice is opt-in;
  subtitles-only must never be a degraded experience.

### 4. Utterances become claims, with credibility as a mechanical stat

A committed player line is ingested as a claim via the same write path any
witness statement uses, stamped with the player as origin. Two mechanical
hooks keep the persona from being cosmetic:

- **Credibility.** Deception attempts (intent=deceive) enter listeners'
  belief stores with confidence scaled by the character's charisma/
  composure stats and the listener's existing disposition toward the player
  (rule 10's observer-local reputation) — a trusted face lies better, a
  known liar's truths land weaker. This uses the existing
  confidence/strength machinery; no new belief mechanics.
- **Speech checks.** Persuade/intimidate resolve against Skyrim's existing
  Speech skill, with the Chronicle-side reputation delta as a modifier —
  the stats touch the game's own systems rather than inventing parallel
  ones.

Consequences are emergent, not scripted: a boast made in Belethor's shop is
a claim like any other — it can be overheard, retold, mutated per the
existing propagation rules, and come back to the player garbled a week
later.

### 5. Serving-shape constraints (from the local-hardware target)

The conversation tier runs against a LAN-hosted local model per ADR-0001's
external-service architecture; target hardware is consumer (~64GB unified
memory, 27B-class instruct model plus a sub-1B-param TTS). This imposes two
design requirements:

- **Shared prompt prefix.** All prompts to the conversation model share an
  identical prefix (world rules, voice-card format, output contract) with
  per-entity state appended as a suffix, so serving-stack prefix caching
  amortizes prefill cost across NPCs and option sets.
- **Bounded generation.** Option sets are one call with a hard token cap;
  NPC replies stream. The intent taxonomy exists partly *for* this — it
  bounds the generation space, which keeps latency predictable in a way
  free-form-only input cannot.

TTS renders the committed line only (never discarded options), pipelined
against the next LLM call so audio render overlaps generation.

## Consequences

- `chronicle/` gains no Skyrim knowledge and no LLM calls — persona storage,
  voice-card compilation, and option generation live in the service layer
  alongside the driver; only *committed utterances* cross into `chronicle/`
  as ordinary claims/events. The one architectural rule (ADR-0001) is
  preserved.
- The claims schema needs one addition: an utterance origin kind (player
  speech) distinct from witness/crime origins, so provenance chains stay
  honest about "the player said this" vs. "this happened." Frame-log schema
  impact is additive only — no encoding break (per the schema-versioning
  rule).
- Save/reload: persona and voice card live under the ADR-0004 branch key and
  the ADR-0005 handshake, inheriting timeline forking for free.
- Testing: voice-card compilation is deterministic and unit-testable;
  "utterance becomes claim, claim propagates" gets a scenario test in
  `scenarios/` (a player boast mutating as it travels is a natural tier-2
  scenario). LLM output quality itself is evaluated via recorded-fixture
  replay, not asserted in CI.

## Open questions (for `open-questions.md`)

- Free-form player input: full support, or gated behind an "advanced" flag?
  It breaks the bounded-generation latency contract (§5).
- How much of the voice card should the *player* be allowed to hand-edit
  vs. keeping compilation one-way from the sliders?
- Does intent=deceive need a player-visible "they didn't buy it" signal, or
  does that stay diegetic (NPC behavior change only)?

## Out of scope for this ADR

NPC-side dialogue rendering (vision tier 3's other half — separate design),
the specific LLM/TTS model choices (an operations decision, revisited as the
open-model landscape moves), and MCM/in-game UI for persona authoring.
