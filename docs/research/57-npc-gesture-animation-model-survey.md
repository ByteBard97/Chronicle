# Report 57: NPC gesture/animation model survey — audio-driven body language for Phase 2 embodiment

**Also filed in the sibling `Countenance` repo** (`research/findings-7-chronicle-report-57-idle-states-and-batching.md`,
copied 2026-09-08), which owns this problem domain going forward and has its
own, more thoroughly corroborated `research/SYNTHESIS.md` covering model
selection — treat that as the current model-selection reference over this
doc's §1/§4. This copy stays here as Chronicle's own historical record of
where the embodiment idea came from; not moved or deleted.

**Status:** filed, ahead-of-need. This is Phase 2/3 embodiment research (NPC
voice already commits to TTS + lip sync per reports 41/44; this extends that
to body language), not current Phase 1 build scope. No ADR change. Captured
so it isn't lost before Phase 2 design/prototyping starts.

**Source:** three rounds of owner-run web research against a conversational
AI ("Fable"), pasted into this session verbatim and reorganized here into the
house research-doc format. Citation tags below (`[sourced]`,
`[built from user premise]`, `[from memory]`) are carried over from the
original passes, not re-verified by this session — treat unverified tags
with the same caution the tag implies.

**The underlying goal (owner's framing, refined across the three passes):**
a model that takes **audio (and optionally text)** and outputs **animation
instructions for a given character**, with an auxiliary channel for
character affect (excited/passive/angry/etc.) if available — explicitly
**not** a model that requires a reference animation/style clip as an input
at runtime, since Chronicle needs to drive gesture from live sim state
(mood/temperament/sentiment), not a hand-picked example clip per line.

---

## 1. Candidate models

| Model | Inputs | Outputs | License | Status |
|---|---|---|---|---|
| **ZeroEGGS** | audio + a style example (BVH clip) | gesture BVH | Ubisoft, all-rights-reserved custom License.md | Pretrained weights ship in-repo; **rejected** — see below |
| **EMAGE** | audio only | SMPL-X 55-joint pose + face expression + translation, 30 FPS, 64-frame windows | Apache-2.0 (via the Motius `H-Liu1997/emage_audio` / `ZeyuLing/Motius-EMAGE-BEAT2` release) | Real checkpoint, clean license, face+body in one call; no native style/emotion conditioning |
| **DiffuseStyleGesture+ (DSG+)** | audio (WavLM + acoustic features) + aligned text (FastText) + speaker ID | 75-joint BVH, 30 FPS | MIT (model + runtime, via a Motius HF release that also converts to SMPL-X) | **Primary pick** — closest match to the stated spec |
| **BEAT / CaMN (baseline)** | audio + text + speaker ID + 8-class one-hot emotion (neutral, happiness, anger, sadness, contempt, surprise, fear, disgust) | body + hand gesture | checkpoints provided in the BEAT repo | Where the explicit emotion channel lives; DSG's original variant also accepted this one-hot on BEAT |
| **DiffSHEG** | — | BVH/JSON, has inference + Blender viz scripts | — | No hosted checkpoint found; treat as unavailable unless a release page turns up one |
| **LiveGesture** | — | — | — | No code or weights found at all |

**On the "no reference animation" requirement, resolved:** ZeroEGGS's
"style example" is one fixed clip per emotion, shipped in the repo — at
runtime its actual input reduces to `(audio, emotion_label)`, which *is*
the auxiliary affect channel asked for; the clips only exist to define what
"angry" *means* to the model, not to supply a reference per call. The real
disqualifier for ZeroEGGS is the Ubisoft all-rights-reserved license and its
2022-era pinned PyTorch 1.12/CUDA/Python 3.8 environment (would need MPS
porting or a Windows box), not the input interface. `[sourced]`

**Recommendation:** **DiffuseStyleGesture+** for style-driven body gesture
with the closest input match to spec (audio + text + speaker ID, MIT), with
the original DSG variant's BEAT emotion one-hot as the lever for steering
affect directly from sim state if wanted; **EMAGE** as the Apache-2.0,
audio-only, face+body alternative if emotion is instead routed through
sim-driven expression compositing rather than a model input. Speaker ID is
a free per-NPC style lever either way: BEAT has 30 speakers, so assigning
each Skyrim voice type a speaker ID gives per-NPC gesturing style with zero
additional training. `[sourced]`

## 2. Coherence mechanism

DSG+ runs as rolling 150-frame windows with 30 seed frames carried from its
*own* previous window (not supplied externally) — the first window seeds
from a rest pose, the rest of the chain is self-seeding. This is how it
stays temporally coherent across a long line without external state
management. `[sourced]`

## 3. Difficulty ordering (owner's original question: how hard is this to
build)

Ordered by dependency, honestly:

1. **The social sim + SKSE bridge is the core and is months of work on its
   own** — everything else sits on top of it.
2. **LLM dialogue + TTS + lip sync is a solved pipeline** — assemblable from
   Mantella's code, AudioUtil, and Rhubarb in weeks (this is the part
   reports 41/44 already scoped for Chronicle).
3. **Neural body language is the piece with no Skyrim precedent.** Running
   the model itself is the easy part; retargeting BEAT's 75-joint or
   SMPL-X output onto the XPMSE skeleton and writing a bone-override plugin
   with collision clamping (§4 below) is real engineering, "probably
   comparable to the sim itself."

**Recommendation:** build the gesture layer last, ship everything else
first with the existing OAR clip-library approach covering emotional body
language in the interim. `[built from user premise] [from memory]`

## 4. Size, GPU, and real-time feasibility

No published parameter count or VRAM figure was found for either DSG+'s or
EMAGE's checkpoint — what actually determines runtime cost is the sampling
architecture, not raw size:

- **DSG+** runs the official 1,000-step diffusion sampler over 150-frame
  windows — many seconds per five-second line on a GPU, **not interactive
  as shipped**.
- **EMAGE** is a masked-transformer over four VQ-VAE decoders, no diffusion
  loop — one forward pass per 64-frame window, should be near real-time on
  any modern GPU.

Both models are far smaller than the LLM tier Chronicle is already
targeting; the Mac mini or a mid-range NVIDIA card on the Skyrim PC holds
either. Environment friction (pinned PyTorch versions, WavLM feature
extraction, Python 3.8 for the older repos) is flagged as costing more time
than the actual compute. `[sourced]`

## 5. Pre-generation and offline batching

**Ahead-of-time generation falls out of the pipeline naturally**: LLM
writes the line → TTS renders it → the gesture model consumes the rendered
audio → playback starts only once all three finish. Gesture inference is
one more pipeline stage before the NPC's mouth opens, not a separate
concern. Two latency mitigations:

- **Windowed overlap**: gesture the first sentence while TTS renders the
  second (both models are windowed).
- **Speculative pre-render**: the sim already knows which NPCs are in
  perception range and roughly what they'll say on greeting, so it can
  pregenerate greeting line + audio + gesture for the nearest few NPCs
  while the player walks over, discarding what's unused.

**Fully offline for anything non-LLM-generated**: every vanilla Skyrim line
already has audio. Batch the entire vanilla voice set through EMAGE once,
save per-line gesture clips, ship as an OAR animation set keyed by voice
line — vanilla dialogue gets body language with **zero runtime inference**,
and only novel LLM-authored lines need live generation. The same batch run
doubles as a mining source for idle-clip content (§6). `[built from user
premise] [from memory]`

## 6. Idle states (listening / waiting-to-speak / thinking)

These models are speech-driven and go slack when nobody's talking, which is
a real gap — the fix is a small state machine, not another model call, since
"learning-to-listen" academic models exist but aren't the practical route
here:

- **Listening**: head tracking on the speaker, small nods/brow motion from
  the face channel, occasional weight shift.
- **Waiting-to-speak**: a brief lean/inhale cue when the sim decides the
  NPC has something to say — doubles as a turn-taking signal to the player.
- **Thinking**: gaze drift during LLM/TTS latency — "an NPC who visibly
  considers before answering makes the pipeline's latency read as character
  rather than lag" — this is the state that matters most for hiding the
  actual wait.

Each state gets a handful of short OAR clips selected by mood, blended
under head-tracking/expression, cross-fading into the neural gesture stream
once the line begins. `[built from user premise]`

## 7. Clipping mitigation (walls, objects, furniture)

The generative models produce motion in free space and don't solve this —
three layers do, stacked:

1. **Scope the neural output to upper body only** (spine, clavicles, arms,
   hands, head); leave pelvis/legs on Havok. An NPC never walks into a wall
   *because of a gesture* — only gestures into one, which is the narrower
   problem layers 2-3 solve.
2. **Per-frame reach check in the SKSE plugin before applying**: raycast
   from shoulder to wrist target against the collision world
   (`RE::bhkWorld` exposes this; the Precision and Universal Kinematics
   community plugins already do exactly this kind of check). On a hit
   inside the reach, scale the arm rotation toward rest pose by the
   penetration fraction.
3. **Context-gated envelopes**: the sim already knows an NPC is behind a
   bar, seated, or in a doorway, and can send a "gesture envelope" (max arm
   extension, allowed sides) the plugin clamps against *before* the
   raycast. The seated case is flagged as the one that matters most in
   practice — tavern/throne conversations are common in Skyrim, and BEAT2's
   underlying mocap is standing-only, so an unclamped output would put
   arms through a table or into a chair back.

`[built from user premise] [from memory]`

---

## Findings

- The stated requirement (audio/text in, no reference-animation input,
  optional affect channel) is satisfiable today with released, runnable
  weights — this isn't a research-stage bet, it's an integration project.
  DSG+ (MIT) is the closest single match; EMAGE (Apache-2.0) is the
  cleanest-licensed fallback if emotion routes through expression
  compositing instead of a model input.
- ZeroEGGS's "requires a reference clip" framing was a misreading, not a
  disqualifier — the actual disqualifiers are licensing and a stale
  environment. Worth remembering if ZeroEGGS resurfaces later as
  seemingly-attractive (19 named emotional styles is a lot of authored
  variety) — it can come back into consideration if the license terms
  are re-read and accepted, or a newer ZeroEGGS-style model ships under a
  cleaner license.
- The actual hard engineering problem isn't model selection, it's
  retargeting + collision-safe application onto the XPMSE skeleton inside
  Skyrim's own physics/animation stack (§3, §7) — this is genuinely
  comparable in scope to the sim itself and has no Skyrim precedent to
  build on, unlike the LLM/TTS/lip-sync pipeline.
- None of this blocks or is blocked by current Phase 1 work. It's a
  Phase 2/3 embodiment layer under "NPC voice," not yet named as its own
  sub-bet in `docs/vision-v3.0.md` — worth a line there once Phase 2
  design actually starts, not now.

## Open questions for a future Phase 2 design pass

- Fixed emotion taxonomy (BEAT's 8-class) vs. a richer/continuous affect
  channel, and how it maps onto Chronicle's own `temperament`/`mood`
  fields (design doc §2 X3) and the dual-wheel tenor idea (conversation-
  tier-design-notes §8) if that ships.
- Whether to build the retargeting/collision-clamping plugin in-house or
  find/adapt an existing community solution (Precision, Universal
  Kinematics) rather than writing raycast clamping from scratch.
- Whether EMAGE's single-speaker training (no native style conditioning)
  is a real limitation once actually tried, or fully absorbed by the
  per-NPC speaker-ID lever plus expression compositing.
- A concrete GPU/latency benchmark on real target hardware (the M5 Pro
  mini, or the Skyrim PC's own GPU) — nothing above is a measured number,
  all of it is architectural inference from how each model samples.
