# Chronicle LLM Layers — Combined Research Report: NPC Roleplay Voice (Prompt 1) + Gamemaster Content Generation (Prompt 2)

**Date anchor:** August 30, 2026 (evaluating models available now and credible releases through December 2026)
**Project context:** "Chronicle," an external social-simulation engine for Skyrim SE/AE. A deterministic Python engine owns NPC beliefs, rumors, grudges, and relationships; an SKSE plugin relays game events in and behavior out over LAN HTTP. Two LLM layers are planned, served from a dedicated home-network machine (Mac mini M5 Pro 64GB, Mac Studio M5 Max 128GB, or NVIDIA DGX Spark 128GB):

1. **NPC voice layer (primary):** per-NPC LLM roleplay grounded in injected Chronicle state. Long prompts (8k–128k), short outputs (1–3 sentences), many concurrent streams, sub-2s first-token latency ideal.
2. **Gamemaster layer (secondary):** background storyteller generating quests/NPCs/encounters reacting to player behavior, emitting structured JSON.

---

## Executive Summary

**For NPC roleplay**, the mid-2026 landscape has crystallized around three families: Gemma 4 (the community's engagement favorite at the 26–31B class), Qwen 3.6/3.8 27B (the reliability workhorse with the strongest fine-tune ecosystem), and — on 128GB only — the 120B-class MoEs (Qwen3.5-122B-A10B, Mistral Small 4, gpt-oss-120b). Community RP benchmarking (rp-benchmark, May–June 2026) shows a real, measurable gap between "single-message charm" and "20-turn coherence": Gemma 4 26B ranks #1 in community single-message engagement but only mid-pack in multi-turn judging, while the frontier open-weights models that top multi-turn (DeepSeek V4 Pro, GLM 5.x, Kimi K2.5) are all far too large for a 128GB box [^10^]. The practical local sweet spot is the ~27–35B class, exactly as suspected.

**For gamemastering**, the single most important finding is negative: even the best frontier model tested (GPT-5.2) preserves narrative facts and commitments only 42% of the time after 20 adversarial turns, with fact conflicts occurring in 40–68% of interactions [^9^]. This means the gamemaster LLM must **not** be the system of record for world state — Chronicle's deterministic engine must remain the fact ledger, with the LLM proposing content against injected state and a validation step rejecting contradictions. Second, repetition collapse is measured and real: frontier models converge on shared structural templates ("the Sarah Chen Problem"), and adding prompt constraints *redirects* rather than *broadens* diversity [^32^]. The field consensus for game content is a constrained pipeline (planner → writer → critic/validator), not one big model free-writing [^19^][^35^].

**Bottom line for hardware:** the two layers want different models. The NPC layer is latency-bound and fits a 27–35B model comfortably at 64GB; the gamemaster layer is quality-bound but latency-tolerant (it runs in the background), and is where 128GB pays off — a 120B-class MoE gamemaster alongside a 27B voice model is only possible at 128GB. Details in §6.

---

## Part I — NPC Roleplay Capability Survey (Prompt 1)

### 1.1 Evidence base

Three independent 2026 signals were used, and they agree on the shape of the field while disagreeing on individual ranks (that disagreement is itself informative):

- **rp-benchmark** (LeviTheWeasel, May–June 2026 snapshot): the most RP-specific instrument available — 21 models, blind community arena (1,262 votes, 315 voters), 12-turn adversarial multi-turn sessions with scripted challenge turns, a 27-dimension rubric, and a "flaw hunter" that grades specific failure modes: F1 agency respect, F8 narrative momentum, F12 instruction drift, F13 buried-detail tracking [^10^].
- **EQ-Bench Creative Writing** (aggregated with LMArena, Aug 17, 2026): frontier prose-quality ranking. Claude Opus 5 leads at Elo 2105; among open weights, GLM-5.2 scores 1749, Kimi K2.6 1723, GLM-5.1 1589, DeepSeek V4 Pro 1552, Qwen3-235B 1459 [^5^].
- **r/LocalLLaMA April 2026 megathread + July 2026 community pulse** (300+ builders, upvote-weighted): Qwen 3.5/3.6 is the most-mentioned family across every category (27B dense = workhorse; 35B-A3B = speed champion; 122B = serious rigs); Gemma 4 is the writing-and-general-use favorite (26B-A4B = daily driver); GLM-5.1/5.2 dominate the >128GB creative conversation [^6^][^2^].

A fourth signal — SillyTavern ecosystem reporting — confirms GLM 5.2 and DeepSeek V4 as community-favorite *hosted* backends, with Gemma 4 31B the recommended budget *local* option [^4^].

**Critical caveat:** the models that top the RP quality lists (GLM-5.2 at 744–753B-A40B [^40^][^46^], Kimi K2.5 at ~1T class, DeepSeek V4 Pro) cannot run on any of the three candidate machines — GLM-5.2's Q4 weights alone are ~400GB [^46^]. They appear below only as the quality ceiling that defines what "S-tier" means. The ladder below is restricted to what actually fits ≤128GB unified memory, quantized.

### 1.2 Sub-skill gradations

Graded separately per the prompt, from the rp-benchmark failure-mode profiles and community reports [^10^][^6^]:

**(a) Persona consistency over long sessions.** The differentiator that separates tiers. Multi-turn adversarial testing reveals degradation patterns that single-turn testing hides — models that start strong and fall apart by turn 20 [^10^]. Best local evidence: Gemma 4 26B holds a 4.29/5 multi-turn judge mean (respectable for its size) [^10^]; the Qwen 27B line is consistently described as punching above its weight for structured, instruction-held sessions [^6^]. At the frontier (for reference), DeepSeek V4 Pro tops the multi-turn arena at 1582 ELO, ahead of Claude Opus 4.6 [^10^].

**(b) Staying in character under off-script/hostile player input.** This is the "accommodation" failure: models tend to yield to the player rather than maintain established reality — NCP-Bench identifies this as a core architectural weakness of current LLMs, exploited by adversarial inputs [^9^]. Within RP-specific testing, F1 (agency respect) separates models: Gemini 2.5 Flash floors at 2.8/5 by writing the *user's* character; Qwen 3.5 Flash is "catastrophic" on F1; Claude and DeepSeek hold up best [^10^]. For local models, Gemma 4 26B and Qwen 27B-class are mid-pack here — serviceable, but expect occasional capitulation when the player insists on something absurd.

**(c) Medieval-fantasy register without purple-prose slop.** Gemma 4 is the community's prose favorite — "excellent at role playing" per practitioner reports [^12^] — and its 26B took #1 community engagement with balanced SFW/NSFW win rates [^10^]. Qwen's flavor is more literal/grounded (less slop, less flourish). Mistral Small Creative is the stylistic specialist but at 24B with a 32k context it loses track of big character cards (F13 rank #10 of 21) [^10^][^30^]. Llama 4 Maverick sits at the bottom of the RP arena on both quality and engagement [^10^].

**(d) Incorporating injected facts without parroting.** Directly relevant to Chronicle-state injection. Sonnet 4.5 is the reference standard ("best at tracking buried details in long character cards") [^10^]. Among local models this correlates with instruction-following strength: Qwen 27B-class is the community-noted structured-output champion at its size ("27B quants punch above weight class for structured output") [^6^]. Mistral Small Creative's weakness on F13 is a warning for exactly this sub-skill [^10^].

**(e) Emotional range appropriate to disposition.** Frontier reference: Opus 4.7 → Opus 4.6 → Sonnet 4.5 → DeepSeek V4 Flash → GLM 5.1 on the emotional-scenes dimension [^10^]. Locally, this is where fine-tunes earn their keep: RP-tuned merges (Fable Fusion, Gembrain, SuperGemma4) specifically target emotional bandwidth and swipe variety over the base models' flatter affect [^11^][^16^][^54^].

### 1.3 NPC roleplay tier ladder (local, ≤128GB unified memory)

Memory footprints are weights-only approximations at standard GGUF quants; KV cache for long prompts adds on top (that math is Prompt 4's territory — budget headroom).

| Tier | Model | Params (active) | Q4 / Q8 footprint | License | Key evidence |
|---|---|---|---|---|---|
| **S** | **Qwen3.5-122B-A10B** | 122B (10B) MoE | ~70GB / ~130GB+ (Q8 won't fit) | Apache 2.0 | Community XL-tier co-pick; "beat them all, wasn't even close" at Q4 on 128GB-class hardware [^6^]; 262K native context [^37^] |
| **S** | **Gemma 4 31B** (dense) | 31B (31B) | ~19GB / ~33GB | Apache 2.0 [^63^] | SillyTavern-community budget-local pick [^4^]; "excellent at role playing" [^12^]; 256K context [^67^] |
| **A** | **Qwen3.6-27B** (+ RP tunes) | 27B (27B) dense | ~16GB / ~29GB | Apache 2.0 | Megathread workhorse, structured-output strength [^6^]; most active 2026 fine-tune base [^54^][^11^] |
| **A** | **Gemma 4 26B-A4B** | 26B (4B) MoE | ~15GB / ~27GB | Apache 2.0 [^63^] | **#1 community RP engagement** (1535 ELO, n=302); mid-pack multi-turn [^10^]; daily-driver pick [^6^] |
| **A** | **Qwen3.6-35B-A3B** | 35B (3B) MoE | ~20GB / ~37GB | Apache 2.0 | Speed champion for concurrent streams [^6^]; very fast prompt processing [^31^] |
| **A−** | **Qwen3.8-27B** *(new)* | 27B (27B) dense, hybrid DeltaNet | ~24GB reported Q4_K_M [^64^] / Q8 ~30GB | Apache 2.0 [^28^] | Released Aug 14, 2026 — strongest 27B on general/agentic benchmarks, 262K context, MTP [^24^][^29^]; **no RP-specific evals exist yet** |
| **B** | **Mistral Small 4** | 119B (6B) MoE | ~65GB / ~120GB+ | Apache 2.0 [^52^] | Native structured output + 256K context [^47^]; RP quality *unproven* — no RP benchmark coverage |
| **B** | **Mistral Small Creative** 24B | 24B | ~14GB / ~25GB | Apache 2.0 | Community #2, NSFW specialist (67% win rate) [^10^]; **deprecated 3/31/2026** → Ministral 3 8B [^33^]; 32k context limits Chronicle injection |
| **B** | **gpt-oss-120b** | 117B (~5B) MoE | ~61GB native MXFP4 / — | Apache 2.0 | Strong reasoning/structure [^20^]; creative writing rated mediocre by practitioners [^25^] |
| **B−** | **MiniMax M2.7** | 229B (10B) MoE | ~95GB Q3 / ~120GB+ Q4 | **Non-commercial** [^57^] | Strong RP engagement (#4 community, F8/F1 strong; weak POV/lore drift) [^10^]; license awkward for a distributed mod |
| **C** | **Llama 4 Scout / Maverick** | 109B (17B) / ~400B (17B) | ~60GB / too big | Llama Community License | Maverick: **bottom of RP arena on quality and engagement** (2.4 composite) [^10^] |
| **C** | **Nemotron Cascade 2** | 30B (3B) MoE | ~18GB / ~32GB | NVIDIA Open Model License | Throughput pick for 16GB systems [^6^]; no RP-quality evidence |
| **C** | **Gemma 4 E4B / 12B** | E4B MoE / 12B | ~2–8GB | Apache 2.0 [^63^] | "How far small models have come" [^6^] — competent but visibly gamey; fine for background peasants |
| — (ceiling) | GLM-5.2 / Kimi K2.5 / DeepSeek V4 Pro | 744B+ / ~1T / ~700B class | 400GB+ at Q4 | MIT / Modified MIT / — | Define the S+ tier; hosted-only for this project [^40^][^46^][^10^] |

**Notable RP fine-tunes (the "flavor" layer):**

- **DavidAU's Qwen3.6-27B "Fable Fusion 711"** — uncensored/heretic RP merge of the current Qwen 27B; ships with SillyTavern/KoboldCpp tuning notes (smoothing factor 1.5) [^11^].
- **SuperGemma4 26B / Gembrain 31B / Huihui abliterated series** — the Gemma 4 RP ecosystem: abliterated (low-refusal) merges targeting swipe variety and creative prose; SuperGemma4-26B uncensored was a top-trending HF download (267k) in May 2026 [^16^][^54^][^1^].
- Legacy legends (MythoMax, Midnight Rose/Miqu 70B–103B) still have followings but are architecturally obsolete against the 2026 bases [^1^].

**Failure flavor by family** (one paragraph each, as requested):

- **Gemma 4:** charming and engagement-forward, but the charm is partly snap-judgment appeal — the documented rank inversion (community #1 → mid-pack when humans read full 12-turn dialogues) means it can *feel* better than it *holds up* [^10^]. Failure looks like gradual persona drift and mid-pack performance on every specific probe rather than any dramatic break. Abliterated merges fix refusals but can trade away coherence ("agreeable nonsense wearing a confident tone" is the known risk pattern for merges) [^16^].
- **Qwen 3.x:** the reliable craftsman. Failures are tonal rather than structural: flatter affect, occasional literal-mindedness, and — in thinking-enabled modes — overthinking simple tavern small talk (early Qwen3.8 reports note an overthinking tendency) [^28^]. The Flash/small MoE variants are *catastrophic* on agency and instruction-holding in RP tests — do not use Qwen 3.5 Flash-class models for voices [^10^].
- **Mistral:** Small Creative writes with genuine stylistic flair and the best mature-content handling measured, but forgets what's on page 9 of the character card (F13 #10) [^10^]. Small 4 is an unknown quantity for RP — its strengths are structural, not vocal [^52^].
- **gpt-oss-120b:** the stage manager, not the actor. Excellent clarity and structure, but its creative writing draws practitioner complaints [^25^]; expect competent but soulless NPCs.
- **Llama 4:** the cautionary tale — last on most RP modes, with the weakest user-judged likability (3.96 Likert) [^10^].

**Long-system-prompt vs fine-tuned behavior flag:** Gemma 4 26B's #1 community ranking was achieved in card-driven (long system prompt) SillyTavern-style setups — its strength is substantially *prompt-mediated*, which suits Chronicle's injected-state design [^10^]. Conversely, the RP fine-tunes (Fable Fusion, Gembrain) bake voice into weights, which is more robust to prompt compression but costs instruction-following flexibility — the classic RP-tune tradeoff (Prompt 3's question). A hybrid is viable: base-model discipline + a persona LoRA is exactly the fine-tuning path the community validates for 27B-class models [^13^].

### 1.4 Known failure modes, cross-cutting

Beyond per-family flavors, three failure patterns matter specifically for a Skyrim deployment:

1. **Accommodation/sycophancy under hostile players** — models yield established facts when the player insists (architectural, not model-specific; NCP-Bench's core finding) [^9^]. Mitigation: keep truth in Chronicle, not in the transcript; inject state fresh each turn rather than relying on conversation history.
2. **"AI assistant" leakage & anachronism** — heavily RLHF'd instruct models moralize or break register (the reason the community runs abliterated/heretic variants) [^16^][^18^]. For dark-fantasy Skyrim content, the fine-tune/abliterated layer is close to mandatory.
3. **Fourth-wall breaks on off-script input** correlate with agency-respect scores (F1) — the same models that write the player's dialogue for them also tend to narrate themselves out of character [^10^].

---

## Part II — Gamemaster / Dynamic Content Generation (Prompt 2)

### 2.1 Long-horizon narrative coherence: the decisive evidence

**NCP-Bench** ("Can LLM Agents Stick to the Script?", August 2026) is the first benchmark to make narrative commitment preservation explicitly checkable: 100 environments with structured fact ledgers, commitments, and reference trajectories, audited automatically each turn against adversarial player agents [^9^]. Results across six frontier models (GPT-5.2, GPT-4o-mini, DeepSeek-V3.2, Qwen3-235B-A22B, Kimi-K2.5, Grok-4.1-Fast):

- Best model (GPT-5.2): **42% survival rate after 20 turns**; only isolated runs satisfied all commitments within 100 turns [^9^].
- **Fact conflicts dominate failures at 40–68% of interactions** [^9^].
- Failure taxonomy maps directly onto a gamemaster's duties: hallucinated contradictions of established world state; prematurely revealing plot-critical information ("triggering unknown facts"); forcibly rewriting reality to erase completed player actions [^9^].
- Behavioral trade-off worth stealing: DeepSeek-V3.2 advances plot aggressively (highest trajectory progress) but dies young; GPT-5.2 survives by pacing conservatively. A gamemaster should be tuned/selected for which of these you want [^9^].
- Kimi-K2.5 terminated earliest (2.88 average turns) — despite being a strong *roleplay* model, it's weak as a *narrator under adversarial pressure*. The two layers genuinely reward different models [^9^].

Root causes per the authors: no explicit state tracking (state is reconstructed implicitly from history → drift accumulates), next-token training doesn't penalize fluent inconsistency, and accommodation bias under adversarial input [^9^].

**Implication for Chronicle:** this is the strongest possible argument for your existing architecture. The deterministic engine already *is* the fact ledger — the exact component NCP-Bench had to bolt onto LLMs to make failures detectable. The gamemaster LLM should receive a curated state snapshot, propose content, and have outputs validated against the engine before instantiation. Never let the LLM's transcript be the world state.

### 2.2 Creative diversity vs. repetition collapse

Measured, and worse than intuition suggests. A 2026 cross-model study ("Many Stories, One Shape," N=50 outlines, 5 frontier models) found [^32^]:

- **Extreme intra-model repetition** — the "Sarah Chen Problem": all five Claude Sonnet-4.5 generations produced the identical protagonist (Sarah Chen, forensic accountant, Seattle), varying only surface details [^32^].
- **Cross-model convergence on shared templates**: under a baseline prompt, all models aligned on a "forensic procedural" blueprint (84% analytical female professionals, 96% Quest/Monster arcs) [^32^].
- **Prompt constraints redirect rather than broaden diversity**: an enhanced prompt successfully banned the first template — and produced an equally rigid second one (100% female caregivers aged 30–38, 96% tragedy arcs) [^32^].
- Residual diversity came disproportionately from outliers (Gemini 2.5 Flash, DeepSeek-v3) deviating from modal patterns [^32^].

Earlier game-specific work corroborates: LLM-generated quests in JSON degrade in accuracy as complexity rises, and unconstrained generators produce same-y quest lists requiring a validation/repair pass [^34^]. Game-dev practitioner consensus matches: any generation process "will inevitably lead to repetition — but only over time"; design target should be "doesn't feel repetitive for roughly the first N quests," with constraint richness determining N [^22^].

**Implication:** budget for a diversity mechanism *outside* the model — template libraries, combinatorial plot-graph assembly, forced-variety sampling (e.g., explicit "forbidden elements" lists rotated per generation), and deduplication against quest history. No 2026 model self-diversifies reliably across N generations.

### 2.3 Constraint-following creativity

Generating content that respects injected world facts (who's dead, who hates whom) is the intersection of §2.1's fact-preservation and instruction-following. The evidence says: models respect constraints **when the constraints are (a) explicit, (b) structured, and (c) checked**. The successful architectures all inject state as structured data (fact ledgers, annotated narrative steps) rather than prose lore [^9^][^19^], and all successful JSON quest generation used validation algorithms before instantiation [^34^]. Chronicle's provenance-tagged belief format is well-matched to this — keep it atomic and typed, per NCP-Bench's fact-ledger design principles (atomic facts, explicit negative knowledge, POV locking) [^9^].

### 2.4 One big model vs. pipeline — field consensus

The 2026 consensus for game content generation is a **constrained multi-stage pipeline**, explicitly chosen over open-ended single-model planning:

- **RPGAgent** (CHI 2026): three-stage agent pipeline — Narrative Designer (world/characters/dialogue scaffold) → Scene Designer → Mechanic Implementation — where the structured narrative is the "single source of truth" for all downstream stages. The authors deliberately prioritized output reliability over planning freedom: "constrained, cascading pipeline" beats open-ended planning for playable output [^19^].
- **Multi-agent storytelling practice** converges on role specialization: Architect (plot skeleton) → World Builder (lore/detail) → Drama Coach (inject conflict/interest) → Dependency Manager (fact-checker: "Is this supposedly dead character trying to speak?") [^35^].
- The NCP-Bench evaluation framework itself embodies the pattern: narrator agent + fixed auditing pipeline with conflict check → fact update → trajectory update → commitment check [^9^].

**Model-size implications per stage** (this is what drives hardware):

| Stage | What it needs | Minimum size class |
|---|---|---|
| Planner / Architect | Long-horizon reasoning over world state; creativity | 27B+ (122B-class if available) |
| Writer | Prose/voice quality | 27B-class RP-tuned (reuse your voice model!) |
| Critic / Dependency Manager | Structured comparison against fact ledger; JSON | 9–27B instruct (cheap, fast) |
| Validator (non-LLM) | Schema + referential integrity | 0B — pure Python against Chronicle's DB |

The elegant consequence: **the pipeline lets small models do the checking and the big model do the imagining**, and the Writer stage can literally be the same 27B voice model you already serve for NPCs.

### 2.5 Gamemaster capability ladder (local, ≤128GB)

| Tier | Model | Why for gamemastering | Footprint (Q4) | License |
|---|---|---|---|---|
| **S** | **Qwen3.5-122B-A10B** | Best local long-horizon agentic profile (BFCL-V4 72.2; 262K context for full state injection) [^48^][^37^]; community-validated at 128GB [^6^] | ~70GB | Apache 2.0 |
| **S** | **Mistral Small 4** | 119B-A6B with **native structured output/JSON** and function calling [^52^][^47^] — the schema-emitting gamemaster; 256K context | ~65GB | Apache 2.0 |
| **A** | **Qwen3.8-27B** | Generation's explicit gains are long-horizon *agentic* tasks [^24^][^28^]; 262K native context [^24^]; unproven specifically for narrative | ~24GB | Apache 2.0 |
| **A** | **Qwen3.6-35B-A3B** | Speed champion; very fast prompt processing makes generate→validate→regenerate loops cheap [^6^][^31^] | ~20GB | Apache 2.0 |
| **A−** | **Gemma 4 31B / 26B-A4B** | Creativity-first choice; agentic decision-making rated decent [^12^]; structured-output discipline below Qwen's | ~15–19GB | Apache 2.0 [^63^] |
| **B** | **gpt-oss-120b** | Ideal **critic/structure model**: strong reasoning and schema adherence [^20^], weak creative voice [^25^] — pair it with a creative writer, don't solo it | ~61GB (MXFP4) | Apache 2.0 |
| **B−** | **MiniMax M2.7** | Genuinely strong agentic/narrative profile (F8 #2, F1 #3) [^10^] but 229B (quant-squeezed at 128GB) and **non-commercial license** complicates mod distribution [^57^] | ~95GB (Q3) | Non-commercial |
| **C** | **Sub-12B models** | Validator/critic roles only; NCP-style fact-checking is within small-model reach when the ledger is explicit [^9^] | 2–8GB | various |
| — (ceiling) | **GLM-5.2** (MIT, 1M context) / **DeepSeek V4 Pro** | The strongest open-weight long-horizon models [^40^][^10^]; self-hosting needs 400GB+ — API-only for you | — | MIT / — |

**Diversity caveat applies to every row:** no model on this ladder escapes §2.2's convergence findings. The tier differences buy coherence and constraint-respect, not variety — variety comes from the harness.

---

## Part III — Putting Both Layers on One Machine (architecture + size implications)

The two layers decouple cleanly because their constraints are different: **NPC voice is latency-bound** (sub-2s TTFT, many concurrent streams, 1–3 sentence outputs) and **gamemaster is quality-bound but latency-tolerant** (background generation, seconds-to-minutes acceptable, retry loops affordable).

**Recommended architecture:** a **single-machine, two-model split** with a shared validation harness:

1. **Voice model (always resident, latency-optimized):** a 27–35B-class model with MTP/speculative decoding. Qwen3.6-35B-A3B (3B active) is the throughput king for 8+ concurrent streams [^6^]; Qwen3.6-27B or Gemma 4 31B are the quality-first alternates [^10^][^12^].
2. **Gamemaster model (swappable, batch-optimized):** the biggest MoE the memory budget allows after the voice model is resident. It runs the pipeline of §2.4: planner (itself) → writer (itself, or delegate to the voice model for dialogue-heavy content) → critic (a small instruct model, or constrained-decoding JSON + Python validation).
3. **Chronicle remains the fact ledger** — the strongest evidence-backed design decision in this report [^9^].

**Per-machine fit (weights + reasonable KV headroom):**

| Machine | Voice layer | Gamemaster layer | Both simultaneously? |
|---|---|---|---|
| **Mac mini M5 Pro 64GB** (307GB/s) | Qwen3.6-35B-A3B Q4 (~20GB) or 27B Q6–Q8 | Same model, or Gemma 4 26B (~15GB) as second resident | Yes — but gamemaster caps at ~35B-A3B class |
| **Mac Studio M5 Max 128GB** (614GB/s) | 27–35B at Q6/Q8 (~25–35GB) | **Qwen3.5-122B-A10B Q4 (~70GB)** or Mistral Small 4 Q4 (~65GB) | Yes — this is the tier where the 120B-class gamemaster + 27B voice coexist |
| **DGX Spark 128GB** (273GB/s, CUDA) | Same as Studio | Same as Studio, served via vLLM with better batching; NVFP4 Qwen quants give ~1.45–1.5× throughput on Blackwell [^29^] | Yes; CUDA serving maturity helps the many-stream NPC load |

**What the extra spend buys (previewing the synthesis question):** moving 64GB → 128GB upgrades the *gamemaster* from 35B-class to 120B-class — i.e., it buys long-horizon coherence and constraint-respect, the exact capabilities NCP-Bench shows are scarce [^9^]. The NPC layer gains much less from the same money, because RP quality at 27–35B is already near the local ceiling and the next real step up (GLM-5.2/Kimi class) doesn't fit any of these machines [^10^][^40^].

---

## Evidence Quality Flags

- **Single-source or thin claims:** Gemma 4 26B's community #1 rank rests on one benchmark's arena (n=302, though corroborated qualitatively) [^10^]; Qwen3.5-122B's XL-tier endorsement leans on a small number of high-effort community reports [^6^]; gpt-oss-120b's RP weakness is practitioner-anecdotal [^25^].
- **Vendor-reported until proven:** all Qwen3.8-27B capability claims (released Aug 14, 2026 — two weeks before this report); no RP-specific or narrative-coherence evals exist for it yet [^26^][^28^]. Same caution for Qwen3.8-Max's headline numbers [^24^].
- **Pre-2026 evidence still load-bearing:** the gpt-oss evaluation (Aug 2025) [^20^], the LLM-quest-JSON study (2024-era models) [^34^], and the procedural-quest practitioner discussion (2025) [^22^] are directionally consistent with 2026 findings but should not be treated as current-model verdicts.
- **Benchmark fragility:** rp-benchmark documents its own rank inversions as vote counts grew (GPT-4.1 dropped 7 ranks once samples grew); treat any single leaderboard as a gradient, not gospel [^10^]. EQ-Bench creative scores measure prose, not 20-turn persona discipline — the two correlate weakly [^5^][^10^].
- **MiniMax M2.7 license status** changed twice in 2026 (API-only → non-commercial weights) and its license drew community criticism for prohibited-use clauses that conflict with the GPL — verify current terms before building on it for a distributed mod [^55^][^57^][^62^].

---

## Sources

[^1^]: https://gist.github.com/swyxio/324fc884061bf20e97a2ecbe59bae34a — r/LocalLLaMA + r/SillyTavernAI preferred models list, Apr 2026
[^2^]: https://www.reddit.com/r/LocalLLaMA/comments/1sknx6n/best_local_llms_apr_2026/ — Best Local LLMs Megathread, Apr 2026
[^4^]: https://www.buildmvpfast.com/articles/best-llms-2026-guide/roleplay-ai — Best AI for Roleplay 2026 (SillyTavern backends)
[^5^]: https://evy.so/compare/best-llms-for-writing/ — EQ-Bench Creative Writing / LMArena aggregate, updated Aug 17, 2026
[^6^]: https://bigguyonstuff.com/best-local-llm-2026-megathread-synthesis/ — Best Local LLM 2026: 300+ community builders synthesis, updated Jul 2026
[^9^]: https://arxiv.org/html/2608.08160v1 — "Can LLM Agents Stick to the Script? NCP-Bench" (Aug 2026)
[^10^]: https://github.com/LeviTheWeasel/rp-benchmark — rp-benchmark roleplaying benchmark, May–Jun 2026 snapshot
[^11^]: https://huggingface.co/DavidAU/Qwen3.6-27B-Fable-Fusion-711-Uncensored-Heretic-NM-DAU-NEO-MAX-MTP-GGUF — Fable Fusion RP fine-tune model card
[^12^]: https://news.ycombinator.com/item?id=47654255 — HN: Gemma 4 31B practitioner discussion (Apr 2026)
[^13^]: https://zenvanriel.com/ai-engineer-blog/fine-tune-qwen-3-27b-on-consumer-hardware/ — QLoRA fine-tuning 27B on consumer hardware (May 2026)
[^16^]: https://partnerinai.com/blogs/gemma-4-gembrain-31b-uncensored-heretic-review — Gembrain 31B merge review (May 2026)
[^19^]: https://dl.acm.org/doi/10.1145/3772318.3790326 — RPGAgent: LLM multi-agent story-to-play generation (CHI 2026)
[^20^]: https://arxiv.org/html/2508.12461v1 — "Is GPT-OSS Good?" comprehensive evaluation (Aug 2025)
[^22^]: https://gamedev.stackexchange.com/questions/213231/ — Procedural quest generation practitioner discussion
[^24^]: https://huggingface.co/Qwen/Qwen3.8-27B — Qwen3.8-27B official model card (Aug 2026)
[^25^]: https://huggingface.co/openai/gpt-oss-120b/discussions/37 — gpt-oss-120b creative-writing discussion
[^26^]: https://www.orcarouter.ai/blog/qwen-3-8-27b-for-coding — Qwen3.8-27B expectations analysis (Aug 2026)
[^28^]: https://thenewstack.io/qwen38-27b-local-inference/ — The New Stack on Qwen3.8-27B local inference (Aug 14, 2026)
[^29^]: https://unsloth.ai/docs/models/qwen3.8 — Unsloth Qwen3.8 run guide, NVFP4 throughput data (Aug 2026)
[^30^]: https://openrouter.ai/mistralai/mistral-small-creative — Mistral Small Creative specs (Dec 2025)
[^31^]: https://overbring.com/blog/2026-08-17-qwen3-8-27b-wall-clock/ — Qwen3.8-27B vs Qwen3.6-35B-A3B hands-on (Aug 2026)
[^32^]: https://digital.kenyon.edu/cgi/viewcontent.cgi?article=1041&context=dh_iphs_ss — "Many Stories, One Shape: Narrative Convergence in AI-Generated Fiction" (2026)
[^33^]: https://docs.mistral.ai/models/mistral-small-creative-25-12 — Mistral Small Creative deprecation notice
[^34^]: https://www.octopus.ac/publications/b24g-1d42 — LLMs for procedural side-quest generation in JSON
[^35^]: https://blog.apiad.net/p/ai-driven-storytelling-with-multi-3ed — Multi-agent storytelling architecture (Architect/World Builder/Drama Coach/Dependency Manager)
[^37^]: https://huggingface.co/Qwen/Qwen3.5-122B-A10B — Qwen3.5-122B-A10B official model card
[^40^]: https://www.morphllm.com/glm-5-2 — GLM-5.2 overview: 753B-A40B, MIT, 1M context (Jun 2026)
[^46^]: https://simonwillison.net/2026/jun/17/glm-52/ — Simon Willison on GLM-5.2 (1.51TB weights; AA Intelligence Index leader)
[^47^]: https://www.spheron.network/blog/deploy-mistral-small-4-gpu-cloud/ — Mistral Small 4 deployment specs
[^48^]: https://www.digitalapplied.com/blog/qwen-3-5-medium-model-series-benchmarks-pricing-guide — Qwen 3.5 medium lineup specs (Feb 2026)
[^49^]: https://plotlightstudios.com/plotpoints/leaderboard — PlotPoints RP leaderboard (rp-benchmark composite)
[^52^]: https://mistral.ai/news/mistral-small-4/ — Mistral Small 4 announcement (Mar 16, 2026)
[^54^]: https://github.com/duanyytop/agents-radar/issues/1174 — Hugging Face trending models, May 19, 2026
[^55^]: https://news.ycombinator.com/item?id=47737928 — HN: MiniMax M2.7 open-weights license discussion (Apr 2026)
[^57^]: https://huggingface.co/MiniMaxAI/MiniMax-M2.7/discussions/5 — M2.7 license terms (non-commercial)
[^62^]: https://minimax-ai.chat/models/minimax-m2-7/ — MiniMax M2.7 specs/license summary (May 2026)
[^63^]: https://www.mindstudio.ai/blog/gemma-4-apache-2-license-commercial-use — Gemma 4 Apache 2.0 license analysis (Apr 2026)
[^64^]: https://www.promptquorum.com/local-llms/best-local-llms-2026 — Best Local LLMs Aug 2026 (Qwen3.8-27B footprint)
[^67^]: https://www.digitalapplied.com/blog/google-gemma-4-apache-2-open-source-complete-guide — Gemma 4 license shift + 31B vs Scout comparison (Apr 2026)
