# On-device model eval: GLM-4.7-Flash vs. Qwen3-30B-A3B for Chronicle's conversation tier

**Read this first if you're a fresh Claude Code session on Geoff's MacBook Pro (M4, 24GB unified
memory).** You have no context from any other session on this project — this file is meant to be
everything you need to get oriented and start working. Ask Geoff if something here turns out to
be stale (models, tools, and file paths can drift between when this was written and when you're
reading it) rather than guessing past a contradiction.

## What "Chronicle" is, in one paragraph

Chronicle is a Skyrim SE/AE mod: a pure-Python, event-sourced social-simulation engine
(`chronicle/`) that models NPC beliefs, rumors, grudges, and relationships, bridged to the game
via an SKSE C++ plugin (`adapters/skyrim/ChronicleBridge/`) and a Python HTTP listener
(`adapters/skyrim/listener/`). A planned "conversation tier" will let NPCs speak lines rendered by
a locally-hosted LLM, grounded in what the engine actually knows — the model never decides
anything, it verbalizes what the deterministic engine already computed. That design is
`docs/decisions/0011-player-persona-and-voice.md` (player's side) and
`docs/design/conversation-tier-design-notes-2026-08-30.md` (serving-side amendments). **None of
this is built yet** — you're doing research to inform it, not implementing it.

## The task, and why it exists

A research pass (`docs/research/47-model-selection-glm-4.7-flash-final.md`) picked
**GLM-4.7-Flash** (30B total params, ~3B active, MoE, MLA-based full attention) as the primary
conversation-tier model, mainly on architecture grounds — it's one of the few 30B-class models
whose attention mechanism doesn't break KV-cache prefix reuse on llama.cpp/MLX (see
`docs/research/38-llamacpp-mlx-kv-cache-prefix-reuse.md` for why that matters at all). Its
roleplay/voice-quality evidence at the time was thin: one HuggingFace forum comment.

A later corpus-audit pass (`notes/kimi-research-corpus-audit-findings-2026-09-01.md`, item 1)
checked that claim against the actual EQ-Bench Creative Writing v3 leaderboard and found it
**negative** — independently re-verified against eqbench.com's raw data on 2026-09-02:

| Model | CWv3 Elo | Rank (of ~129) |
|---|---|---|
| GLM-4.7 (flagship, much bigger, not what we'd run) | 1410.5 | 68 |
| gemma-4-31B-it (a top pick on a *different* research pass, disqualified on architecture grounds) | 1365.7 | 74 |
| **GLM-4.7-Flash** (the pick in question) | **1122.3** | **99** |
| **Qwen3-30B-A3B-Instruct-2507** (the current fallback) | *not on this leaderboard at all* | — |

GLM-4.7-Flash sits in the bottom decile on a general creative-writing benchmark. That doesn't
necessarily mean it's bad for *Chronicle's specific* workload — see the axis-transfer caveat
below — but it means the pick currently rests on architecture-fit alone, with one negative and
zero positive hard data points on the property that actually matters most (does it sound good as
an NPC). **Your job is to generate that missing data point directly**, on Chronicle's actual
workload shape, not a generic RP benchmark. Full report status:
`docs/research/47-model-selection-glm-4.7-flash-final.md`'s correction note at the top.

**Important axis-transfer caveat, from the same audit** (don't skip this — it changes what a
"good" line looks like): published RP benchmarks (including EQ-Bench above) measure long,
multi-turn free-form chat coherence. Chronicle's actual workload is different: **one engine-chosen,
already-grounded intent in, one 1–3 sentence line out**, with the engine re-injecting fresh state
every turn rather than the model holding conversation memory. The axes that actually matter here
are: does it stay in the voice-card's register, does it use *only* the grounding it was given
(no hallucinated facts), does it stay in character under an off-script nudge, and does it emit
*only* the closed TTS annotation set (never invent new tags). A model that's mediocre at 20-turn
persona coherence could still be excellent at this narrower, more constrained task — that's
exactly the open question.

## Hardware reality check (24GB unified memory)

- GLM-4.7-Flash weights are ~17–19GB at Q4 (per report 47). Qwen3-30B-A3B-Instruct-2507 is the
  same order of magnitude. **Run one model at a time** — don't try to hold both resident, and
  don't try to add a TTS model into the same run. This eval is text-only.
- Absolute throughput numbers (tokens/sec) from this machine are **not meaningful for the model
  decision** — the eventual target machine is a 64GB Mac mini M5 Pro (307GB/s memory bandwidth,
  on order, arriving end of month) with much higher bandwidth than this M4. Don't let a slow
  tok/s reading on this machine count against a model; only *quality* and *architecture behavior*
  transfer, not speed.
- If either model doesn't comfortably fit or thrashes on this machine, that's itself worth noting
  in your findings — it's real information — but don't force it past the point of useful signal.

## Step 1 — environment

You'll need a local inference server capable of running GGUF or MLX-format weights on Apple
Silicon. Two reasonable choices, either is fine (report 47 recommends llama-server as primary,
mlx-lm as the alternative — pick whichever you get working first):

- **llama.cpp** (`llama-server`) — install via `brew install llama.cpp` or build from source
  (`ggml-org/llama.cpp` on GitHub). Get GGUF quants from the unsloth/community quants referenced
  in report 47 (e.g. `unsloth/GLM-4.7-Flash-GGUF`, search Hugging Face for the equivalent
  Qwen3-30B-A3B-Instruct-2507 GGUF).
- **MLX** (`mlx-lm`, `pip install mlx-lm` or `uv pip install mlx-lm`) — `mlx_lm.server` can serve
  either model; check `mlx-community` on Hugging Face for pre-quantized MLX builds of both.

Confirm whichever you pick actually launches and answers a basic completion request before
moving on — a working "hello world" call is cheap insurance against debugging two problems
(harness + model) at once later.

## Step 2 — the `cache_n` architecture check (do this first, it's fast and decisive)

This verifies GLM-4.7-Flash's prefix-cache reuse actually works as the architecture analysis in
report 47 predicts — a yes/no property that's identical on any Apple Silicon chip, so this M4 is
just as valid for this specific check as the eventual M5 Pro. Exact recipe (report 47 §6):

1. Start the server at trace verbosity (`llama-server`'s `-lv 4`, or the MLX server's equivalent
   logging level).
2. Send two requests that share a long, byte-identical prefix (e.g. a long fake "world rules"
   block) with different short suffixes appended (different "riders").
3. Read the `timings.cache_n` field in each response (llama-server reports this natively; if
   using mlx-lm, check its response metadata for an equivalent prefix-hit count — note in your
   findings if this isn't directly exposed and how you inferred it, e.g. via prefill latency).
4. **Healthy result**: the second request's `cache_n` ≈ the shared prefix's token length, and its
   time-to-first-token is much lower than the first request's. **Disqualifying result**: any
   `forcing full prompt re-processing` log line, or `cache_n` near zero on the second request.

Run this for **both** GLM-4.7-Flash and Qwen3-30B-A3B-Instruct-2507 (the latter is already
expected to pass — it's the "reference case" for working prefix caching per report 47 — so it
doubles as a sanity check that your test methodology itself is correct).

## Step 3 — build Chronicle-shaped eval prompts

Chronicle's real prompt structure has four segments, ordered stable-first (this matters for cache
behavior in production, but for this eval just replicate the *content* shape, not necessarily a
live cache-hit measurement):

1. **Global**: world rules, NPC instruction block, output contract, the closed TTS annotation
   schema (see below), the player's voice card if relevant to the scenario.
2. **Location**: cell-local ground truth (e.g. "this is Belethor's General Goods, mid-morning,
   three other patrons present").
3. **NPC rider**: this specific NPC's beliefs, disposition, and memories — this is where
   observer-local material goes, even for things that "really happened," because different NPCs
   believe different things about the same event.
4. **Turn**: the actual prompt for this line — a parameterized intent tuple, not a bare verb.
   Example shape (from `conversation-tier-design-notes-2026-08-30.md` §2):
   `(confront, rumor_id=X)`, `(boast, quest_id=Y)`, `(inquire, topic=missing_person)`.

The closed TTS annotation set the model must emit *only* from (nothing else):
**emphasis, pause, laugh, and a tone enum** (angry/wry/hushed/etc. — see design notes §3 for the
full rationale; treat any tag outside this set as a failure).

Build 10–15 test cases spanning ADR-0011's intent taxonomy (greet, inquire, negotiate, persuade,
deceive, intimidate, charm, mock, farewell) plus a few of the parameterized examples above, each
with a small but concrete voice card (2-3 sentences of character voice + a hard constraint, e.g.
"never apologizes") and a specific, invented-but-realistic belief-state rider. Keep them varied —
at least one deceive case (to check register under a lie), one mock/intimidate case (to check it
doesn't break character or moralize), and one where the grounding explicitly contradicts what a
"generic NPC" would say (to check it uses the given state rather than defaulting to genre
cliché).

## Step 4 — run both models, judge the same way

For each test case, run it against both models with the same prompt. Judge each output on:

- **Register fidelity** — does it sound like the voice card, not a generic assistant or a
  generic "gruff Nord" cliché?
- **Grounding fidelity** — does it only reference facts actually present in the rider/location
  segments? Flag any hallucinated detail immediately — this is the single most disqualifying
  failure mode for Chronicle's design (the model must never invent facts the engine didn't give
  it).
- **Character integrity** — does it stay in character, including under the deceive/mock/
  intimidate cases, without moralizing or breaking the fourth wall?
- **Annotation compliance** — does it use only the closed tag set, correctly bracketed, nothing
  invented?
- **Length discipline** — is it actually 1–3 sentences, not a paragraph?

A simple side-by-side table (test case × model × pass/fail per axis + the raw output text) is
enough — this doesn't need a formal statistical eval, just enough real examples that a human
reading them can tell which model is actually better for this job.

## Step 5 — file the findings

Follow this project's research-filing convention: a new numbered report under `docs/research/`.
**Check `docs/research/00-index.md` for the current highest report number before picking one** —
more research may have been filed since this was written; use the next number after whatever's
currently highest (48 as of this writing, so likely 49, but verify). Match the existing format:
a `# Report NN — <title>` header, a `**Date:**`/`**Method:**` block (method here is "on-device
eval, Geoff's M4 MacBook, 2026-09-XX" not a dispatched research pass), then your findings —
include the `cache_n` results, the side-by-side eval table, and a clear recommendation (keep
GLM-4.7-Flash, switch to the fallback, or "inconclusive, needs the M5 Pro / more cases"). Add a
row to `docs/research/00-index.md`'s table. If your finding changes report 47's status, add a
dated correction note there too, the same way the 2026-09-02 correction was added — don't
silently overwrite it.

**Bonus, if you have time**: your test cases and outputs are also exactly the "recorded-fixture
replay" evaluation ADR-0011's own testing section calls for (LLM output quality is meant to be
evaluated via recorded fixtures, never asserted in CI). Consider saving your prompt/response
pairs in a structured, reusable form (e.g. JSON) alongside your report — even a rough version
gives whoever eventually builds the real eval harness a real starting fixture set instead of
nothing.

## What NOT to do (scope guardrails)

- **Don't re-litigate the architecture decision.** The full-attention/prefix-cache requirement
  (report 38) is settled and correct — don't spend time re-evaluating hybrid/recurrent models,
  they're disqualified regardless of voice quality.
- **Don't start building the conversation tier.** This is research only. The owner has
  explicitly deferred conversation-tier *implementation* until other, unrelated Chronicle
  infrastructure is live-verified (see `GOALS.md`'s "Current state" section, 2026-09-02 entry, if
  you want the full reasoning) — that gate has nothing to do with this eval and doesn't block it,
  but don't read "do the model eval" as "start implementing ADR-0011."
- **Don't chase TTS or lip-sync in this pass.** Those are separate, already-researched questions
  (reports 40, 41, 44) — stay scoped to text generation quality.
- **Don't treat tok/s numbers from this machine as decision-relevant** — see the hardware note
  above.

## If something here is wrong or stale

This file was written 2026-09-02, in a separate session on a different machine, based on the
state of `docs/research/47-model-selection-glm-4.7-flash-final.md` and
`notes/kimi-research-corpus-audit-findings-2026-09-01.md` at that time. If either has moved on
since, trust the current files over this summary. If a tool, model name, or file path mentioned
here doesn't exist anymore, say so in your findings rather than silently working around it.
