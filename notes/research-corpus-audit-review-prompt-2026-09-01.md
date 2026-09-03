<!--
INSTRUCTIONS FOR GEOFF (delete or leave, Kimi ignores the HTML comment):

1. Copy everything below the "=====" divider as your first message to Kimi.
2. This needs real web/GitHub verification enabled, same as the sync-handshake review — Kimi's
   MCP tools were unreliable for me this session (every call after the first timed out), but the
   same task run manually through the Kimi web/chat UI produced the best review of the whole
   session. Worth trying the direct approach again here rather than the MCP path.
3. Bring the reply back and we'll fold it into whatever comes next for the project.
-->

=====

You are auditing a research corpus for internal consistency, not writing new research. You have
no other context beyond what's in this message — treat it as complete.

## Background

"Chronicle" is a Skyrim mod: a Python event-sourced social-simulation core plus an SKSE C++
plugin bridging game events to/from it. Over roughly the last 48 hours, the project ran a large
batch of external deep-research passes (via you, Claude, and Gemini, in various combinations)
covering the design of a not-yet-built "conversation tier" — the layer that would let NPCs
produce LLM-rendered dialogue grounded in the simulation's actual state, plus supporting
infrastructure (TTS, lip-sync). The reports are numbered and live in `docs/research/34.md`
through `docs/research/48.md` in the repo (topics below); the architectural decision they all
sit under is `docs/decisions/0011-player-persona-and-voice.md` ("the engine decides what happens;
the LLM only renders it into words").

**Topics, briefly, so you know what's in scope:**
- 34: LLM NPC voice / gamemaster-model survey
- 35: LLM structured-output and long-context behavior
- 36: Reddit community survey of LLM-NPC mods
- 37: AI-NPC mod source study
- 38: llama.cpp/MLX KV-cache prefix-reuse mechanics — found that Qwen3.6-35B-A3B's hybrid
  Gated-DeltaNet architecture breaks prefix caching entirely, which is what triggered the whole
  model-selection sub-thread below
- 39: free-text intent grounding for dialogue — recommends free-text only as an LLM-drafted,
  player-confirmed suggestion layer, never direct-to-claim, citing forced-choice-abstention
  literature (a ~48.5% ceiling on players picking "none of these") and Façade's ~30% NLU failure
  rate
- 40: TTS on Apple Silicon (Chatterbox-Turbo, Qwen3-TTS, both with MLX ports)
- 41: Skyrim lip-sync feasibility, pass 1 (Gemini) — recommends native `.lip` file generation via
  `Nukem9/FaceFXWrapper`, matching Mantella's shipped pipeline
- 42/43: prior-art survey (Comme il Faut/Prom Week, Versu, CICERO, DeepMind Concordia) — 43 is the
  rigorous second pass, cites CICERO's real supplementary material (24% of candidate utterances
  filtered for intent mismatch) and surfaces Slice of Life (ACM FDG 2025) as near-identical prior
  art to Chronicle's own architecture
- 44: Skyrim lip-sync, pass 2 (you, Kimi) — **disagrees with 41**, recommends procedural mouth
  animation via Mfg Fix NG as primary instead, auditing Mantella's actual source and finding
  native `.lip` generation practically Windows-only-workflow-dependent
- 45/46/47: three independent passes on "which LLM should Chronicle actually run," triggered by
  38's finding — 45 (Gemini) picked Qwen2.5-32B-Instruct, 46 (Claude) picked
  Qwen3-30B-A3B-Instruct-2507, 47 (you, Kimi, the deciding third pass) picked **GLM-4.7-Flash**
  as primary with Qwen3-30B-A3B-Instruct-2507 as fallback, screening ~12 candidates neither other
  pass considered
- 48: a primary-source read (not a dispatched report) of the actual CIF-CK/"Prom Week meets
  Skyrim" academic papers, validating Chronicle's "expected randomness" design doctrine against
  real player survey data

**A newer, separate line of work** (this week) designed and built the save/reload sync-handshake
feature (`docs/design/chronicle-bridge-sync-handshake-out.md`, `docs/decisions/0004-timeline-branching.md`,
`docs/decisions/0005-sync-handshake.md`) — this is a different subsystem (state continuity across
save/reload) with no direct dependency on the conversation-tier research, but it shares the same
codebase and the same author, and both feed into what the project should build next.

## Two things already resolved, so you don't waste time on them

- **Hardware**: report 47 assumes a 64GB Mac. The owner has confirmed a 64GB M5 Pro Mac mini is
  actually on order, arriving end of month — the assumption is correct for the real target, just
  not in-hand yet. Not a contradiction. Don't re-litigate it.
- **Lip-sync 41 vs. 44**: already resolved in the project's own planning — 44's procedural Mfg
  Fix NG pick (the more thoroughly source-audited of the two passes) is adopted as the default,
  with 41's native `.lip` generation kept as a Windows-only fallback. Don't re-litigate it either.

## Your task

Read the actual files at the paths named above (`docs/research/34.md` through `48.md`,
`docs/decisions/0011-player-persona-and-voice.md`) if you have filesystem access; if not, work
from the summaries above plus whatever you can independently verify online, and say plainly which
claims you couldn't check against the primary source.

Three specific, currently-unexamined contradictions to resolve, plus an open door for anything
else you find:

1. **The model that got picked was never run through the project's own roleplay-benchmark
   methodology — this is the sharpest gap found so far, resolve it first.** Report 34 is a
   rigorous, dedicated NPC-roleplay-capability survey: it cites a real community RP benchmark
   (rp-benchmark, actual multi-turn coherence testing across ~20 turns, not single-message
   scores) and ranks models into an explicit S/A/B/C tier ladder (Gemma 4 31B dense and
   Qwen3.6-27B as the top local picks, with detailed per-family failure modes). **Report 34 never
   evaluates GLM-4.7-Flash at all.** Its only GLM coverage is the GLM-5.1/5.2 family — a
   completely different, much larger model (744B-A40B, ~400GB+ at Q4, explicitly called
   "hosted-only, too big" in that report) — not the 30B/3B-active GLM-4.7-Flash that report 47
   later picked as Chronicle's primary conversation-tier model one day later. Report 47's own
   roleplay evidence for GLM-4.7-Flash is a single HuggingFace forum comment ("good in roleplay
   and creative writing"); no Creative Writing v3, EQ-Bench, or rp-benchmark score is cited for
   it specifically (only for the fallback, Qwen3-30B-A3B-Instruct-2507). Determine: does
   GLM-4.7-Flash actually outperform report 34's local-tier winners (Gemma 4 31B, Qwen3.6-27B,
   and RP fine-tunes on those bases like "Fable Fusion 711") on the same roleplay axis, or was it
   picked on architecture/general-benchmark grounds without ever being checked against the one
   property — roleplay/persona-voice quality — that matters most for Chronicle's actual NPC-voice
   use case? Also flag whether report 34's own axis (long free-form RP chat, SillyTavern-style)
   even transfers to Chronicle's actual workload shape (short, 1-3 sentence grounded utterances
   per interaction, not long chat sessions) — report 34 itself distinguishes "single-message
   charm" from "20-turn coherence" as different, sometimes-inverted axes, and neither has been
   checked for GLM-4.7-Flash under either framing.
2. **Does ADR-0011's "engine decides, LLM renders" survive report 39's own findings?** Report 39
   recommends free-text player input go through an LLM-drafted, player-confirmed suggestion layer
   rather than direct-to-claim — does that suggestion-drafting step itself require the LLM to
   exercise judgment ADR-0011 says belongs to the engine, and if so is that a real tension or a
   false one? (Note: the project has since decided this is moot in practice, because report 43's
   24%-of-outputs-fail-intent-correspondence finding means an automated filter ships regardless of
   which side of confirm-vs-autoplay is chosen — but confirm or refute that reasoning rather than
   taking it on faith; if the *filter itself* also requires engine-forbidden judgment, the "moot"
   conclusion doesn't actually hold.)
3. **Does report 47's GLM-4.7-Flash pick interact badly with report 35's structured-output
   findings?** If 35 makes claims about which models reliably produce structured/schema-bound
   output, and GLM-4.7-Flash wasn't a model 35 evaluated, is there a gap where the model pick and
   the structured-output requirements were researched independently and never cross-checked?
4. **Anything else you find** — a genuine, missed contradiction anywhere in 34–48 (or between one
   of them and 0011) is exactly what this task wants, more than confirmation of what's already
   known.

For each finding: state the contradiction precisely, cite the specific reports/sections/claims in
tension, and say whether it's load-bearing (changes a build decision) or not. Do not re-survey or
re-recommend what to build — that's already been done four times across reports 43/44/45/46/47;
this task is specifically about where those existing recommendations conflict with each other or
with reality, not about producing a fifth independent recommendation.