# Conversation-tier design notes — 2026-08-30 session

**Status:** design input, not decided. Extends ADR-0011 (player persona) and the
vision's tier 3. Nothing here is implemented. Where this contradicts ADR-0011,
the contradiction is flagged explicitly — this document proposes amendments, it
does not silently override an accepted ADR.

**Source:** hardware/model research synthesis session (owner + assistant),
building on the six research reports in `docs/research/` and the Prompt 7
synthesis. Hardware decision context: serving box is a Mac mini M5 Pro 64GB
(307 GB/s), on order; gamemaster layer deferred to a hosted frontier model
(Claude/Kimi) behind the validator, so the mini serves the voice layer only.

---

## 1. Decision: no player STT, ever, in the core design

The player's expressive channel is the persona system (voice card + intent +
generated line), not their microphone. Audio is **output-only**: one TTS engine
serving two speaker classes — NPC voices and the player-character's authored
voice.

Consequences:

- No STT model, no audio-input LLM, no paralinguistics side-channel. Drop these
  from any model-selection matrix.
- Every player utterance is **engine-mediated**: the claim entering the rumor
  system is always a string the system generated and the player committed —
  canonical text, known register, closed vocabulary. No freeform-input
  moderation problem.
- ADR-0011's free-form "advanced path" open question is therefore bigger than a
  latency footnote: shipping it would be the only escape from engine mediation
  (open vs. closed claims vocabulary). Recommend deciding it as its own
  question, not bundling it.

## 2. Amendment to ADR-0011 §3: engine-authored option menus, LLM as renderer

ADR-0011 currently has the LLM generate 3–5 candidate *lines* per intent in one
call. This session's proposal narrows the LLM's role further:

**The option menu is a deterministic Chronicle query, with no LLM in the loop.**
"What can the PC say to this NPC right now" is a rule-based function over:

- active grudges/claims involving the target NPC
- rumors the NPC is believed to have heard
- the player's recent quest completions and notable events
- observer-local reputation (rule 10) toward the player
- location context

The query returns 5–10 **parameterized intents** — not bare verbs but grounded
tuples: `(confront, rumor_id=X)`, `(boast, quest_id=Y)`,
`(inquire, topic=missing_person)`. The bare-intent taxonomy from ADR-0011
(greet, negotiate, deceive, intimidate, ...) becomes the *type* of these
tuples, with grounding refs as arguments.

Why this split wins:

- **Testable**: menu construction is pure engine code — unit tests and scenario
  tests like everything else, microsecond-fast, no inference cost.
- **Explainable**: the dashboard can trace exactly why an option appeared
  (which belief/claim/quest put it there). An LLM-generated menu can never
  give that provenance.
- **Clean claims loop**: the committed claim records its grounding refs *from
  the menu selection*, not from parsing LLM output. Provenance stays
  engine-authored end to end. This is the strongest form of "the model never
  decides anything, it verbalizes": the model no longer even decides what the
  player is talking about.

**Flow:** player targets NPC → engine computes menu (instant, before the
dialogue camera engages) → player taps an option → **one LLM call renders one
line** (~30 tokens) in the voice card's register, grounded in the parameterized
intent + NPC belief context → TTS → audio streams into the game → committed
line enters `chronicle/` as a claim carrying the menu-supplied grounding refs.

Note the change from ADR-0011 §3: one line per tap, not a 3–5-candidate set.
The confirm-the-words contract this affects is discussed in §6.

## 3. TTS annotation schema: Chronicle owns the vocabulary

The rendered line includes delivery annotations for the TTS model. Design rule:
**the annotation vocabulary belongs to Chronicle, not to any TTS model.**
Inline-tag support is wildly model-specific (CosyVoice-class models take inline
`[laughter]`/`[breath]` tags; Chatterbox exposes intensity as a parameter, not
tags; Kokoro supports essentially none). Therefore:

- Define a small **closed Chronicle annotation set** (proposal: emphasis,
  pause, laugh, and a tone enum — angry/wry/hushed/etc.). The LLM emits only
  this schema.
- A per-TTS **adapter** in the audio layer translates Chronicle annotations to
  each model's native mechanism (inline tags, API parameters, or dropping
  what the model can't express). Same adapter-seam pattern as the rest of the
  architecture; swapping TTS models never touches prompts.
- **Validation is post-hoc, not grammar-constrained**: regex-check that every
  bracket in the output is in the closed set; one re-roll on failure. Do not
  wrap the spoken line in a constrained-decoding grammar — this is the
  structured-output report's "constrain only the metadata envelope, never the
  prose" rule; the annotations live inside the prose.
- The voice card may carry per-character annotation *tendencies* (a composed
  character rarely `[shout]`s; a nervous one breathes) so delivery style is
  part of the authored persona.

## 4. Prompt/KV-cache architecture (serving-side, affects prompt rendering)

KV cache is only valid as an exact-token *prefix*; no splicing. Prompt segments
must therefore be ordered by update frequency, most stable first:

1. **Global**: world rules, generalized NPC instruction block, output contract,
   annotation schema, (player voice card — global-stable per save)
2. **Location**: cell-local ground truth (e.g. Whiterun state) — shared by
   every NPC in the cell
3. **NPC rider**: this NPC's beliefs, disposition, memories — observer-local
   material lives here *even when the underlying event is public*, because
   each NPC's version differs
4. **Turns**

Rules for the renderer:

- **Segment assignment follows update frequency, not truth scope.** A fact
  that is location-true but changes per-conversation belongs in the rider;
  putting it in segment 2 invalidates every NPC's cache in the cell on each
  update. Segment 2 = ground truth about the place; segment 3 = what this NPC
  believes about it.
- **Rendering must be canonical**: sorted keys, stable ordering, no
  timestamps/clocks above the rider. Cache identity is token identity — any
  nondeterministic serialization silently zeroes the hit rate.
- Batch world-state edits rather than trickling them (each edit invalidates
  everything downstream of its segment).
- Serving stacks discover the hierarchy automatically (vLLM block-hash prefix
  caching, SGLang radix tree); llama.cpp/MLX need explicit per-location warm
  cache files. Cell entry should trigger a background prefill of segments 1–2
  for the cell (loading screens hide this), so any NPC's first line pays only
  its rider.
- The option-render call and the subsequent NPC-reply call share segments 1–3;
  the second call is a near-total cache hit.

## 5. Model-choice consequences (voice layer, 64GB box)

- **MoE is effectively mandatory** for anything on the latency path at
  307 GB/s: dense-27B decode (~19 tok/s at Q4) is fine for a 30-token line but
  has no headroom; MoE (Qwen3.6-35B-A3B / Gemma 4 26B-A4B class, ~100+ tok/s)
  keeps every path comfortable. The single-line-per-tap design (§2) relaxed
  the original option-set pressure, but MoE remains the default choice.
- Sub-1B TTS resident alongside; with no GM and no STT resident, 64GB leaves
  large headroom — spend it on prefix-cache residency (warm caches per cell),
  not on a bigger dense model.
- Latency budget with warm caches: tap → LLM streams text → TTS synthesizes
  per sentence-fragment as text arrives → audio streams to game; NPC-reply
  call fires on commit, overlapping playback. Target: tap-to-first-spoken-word
  ~1–1.5 s. Speculative pre-render of the top 2–3 menu options (greet + the
  engine's contextually hottest) during the player's approach makes the common
  path near-instant.
- Gamemaster: hosted (Claude/Kimi) behind the same validator-against-ledger
  design for now; GM endpoint must be a configurable OpenAI-compatible URL,
  never a hardcoded provider (players' dialogue flows through it). A future
  local 120B GM is a hardware add (second box), not a mini replacement.

## 6. Open questions raised by this session (for `open-questions.md`)

1. **Confirm-vs-autoplay.** Speaking the rendered line immediately deletes
   ADR-0011's confirm-the-actual-words step — the ADR's named fix for the
   Fallout 4 paraphrase-wheel failure. The parameterized intent is far more
   precise than a four-way wheel and the voice is the player's authored
   character, so the failure is softened — but utterances are *claims with
   consequences* here, so "that's not what I meant" costs more than in
   Fallout: the line propagates. Candidate middle grounds: (a) subtitle
   preview with a short cancel window before audio commits; (b) auto-speak as
   a setting, confirm-first default — which doubles as a natural experiment on
   whether confirmation matters in play. Needs a decision before the render
   path is built.
2. **Menu staleness across the render hop.** Between menu construction and the
   render call, state can tick (rumor decays, target NPC dies mid-approach).
   The render path must revalidate the option's grounding refs against current
   state and rebuild the menu on failure, rather than voicing a line about a
   dead man's opinion. Where does this revalidation live — service layer
   (likely, per the ADR-0001 rule) or engine query?
3. **Menu ranking.** With 5–10 slots and potentially more eligible
   parameterized intents, the engine needs a ranking rule (recency? claim
   strength? disposition relevance?). Deterministic, testable, and probably
   its own small design note.
4. **Annotation set contents.** The closed set in §3 is a proposal; freeze v1
   before the first TTS adapter is written.
5. **Streaming audio delivery into Skyrim.** File-handoff (fuz/wav via voice
   path) vs. ChronicleBridge playing from a memory ring buffer filled over
   HTTP (`POST /audio-chunk` → play-on-threshold). The bridge already owns
   HTTP + threads, so the buffer path fits the architecture, but **lip sync
   is the early constraint to check**: Skyrim lip files are pregenerated per
   audio file, so streaming means either generating lip data on the mini
   alongside audio (FaceFX-compatible tooling exists in the modding
   ecosystem) or accepting no player-character lip movement (possibly
   invisible in first person). Needs a spike in the issue-4 style.
6. **Free-form advanced path** (carried from ADR-0011, upgraded in weight per
   §1): it is now the only escape from engine mediation. Decide deliberately.

## 7. What this document does NOT change

- The one architectural rule: `chronicle/` gains no LLM calls, no Skyrim
  knowledge. Menu *query* logic is engine-side (pure state function); option
  rendering, annotation adaptation, TTS, and audio delivery live in the
  service layer. Committed utterances cross into the engine as ordinary
  claims.
- ADR-0011 §1 (persona authoring, voice-card compilation), §4 (utterances as
  claims, credibility mechanics, speech checks), §5's shared-prefix
  requirement (this doc's §4 is its concrete design), and the no-voice-cloning
  hard line — all unchanged.
- Determinism (ADR-0009): menu construction uses keyed rolls if it needs
  randomness at all; LLM/TTS nondeterminism stays outside the engine boundary
  and is evaluated by recorded-fixture replay, per existing practice.
