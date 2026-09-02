**STATUS (2026-08-31, later): 6 of 7 dispatches returned and filed.** Claude web's two
(→ `docs/research/38-llamacpp-mlx-kv-cache-prefix-reuse.md`,
`39-free-text-intent-grounding-dialogue.md`), Gemini's three (→
`40-tts-apple-silicon-chatterbox-qwen3.md`, `41-skyrim-lip-sync-feasibility.md`,
`42-comme-il-faut-versu-cicero-prior-art.md`), and Kimi's CICERO/prior-art pass (→
`43-prior-art-simulation-grounded-dialogue.md`, far more rigorous than 42 on the same brief —
read 43 first). **Still outstanding: Kimi's lip-sync deep pass** (the Prompt 38 original,
independent of Gemini's already-filed 41) — expect it to land as the next available report
number and cross-reference against 41 when it arrives.

**New follow-up dispatched 2026-08-31 (Prompt 44 below): model-selection fallout from report
38's hybrid-architecture finding.** Sent to Claude web as primary (this is a bounded technical
verification question, not a literature survey — Claude's demonstrated strength, see reports
38/39), with Gemini in parallel as a cheap cross-check since a wrong model pick here is costly
to discover later. Not sent to Kimi this round — it's tied up with the lip-sync pass and this
question doesn't need its literature-survey depth.

**CORRECTION (2026-09-01): Kimi ran Prompt 44 too, and won decisively.** All three came back:
Gemini → report 45 (Qwen2.5-32B-Instruct), Claude → report 46 (Qwen3-30B-A3B-Instruct-2507),
Kimi → report 47 (GLM-4.7-Flash, screening ~12 candidates neither other pass considered,
finding a better pick than either, and corroborating report 46's pick as fallback). **Lesson
for next time: don't assume Kimi's literature-survey strength doesn't transfer to bounded
technical questions — it screened far more candidates than the other two combined and found
the actual best answer.** All research now complete for this batch: 38-47 filed, including
Kimi's independent lip-sync pass (44) which also reached a different, more actionable
recommendation than Gemini's (41).

# Deep research prompts — conversation-tier / voice layer (2026-08-31)

**UPDATE 2026-08-31 (later same day):** Prompt 42, as originally written below,
turned out to be largely redundant. `docs/research/comparative-systems/
ai-directors-and-drama-management.md` through `-v4.md` (four independent
passes), `docs/research/02-social-simulation-literature.md`, and
`docs/research/papers/` already cover Talk of the Town, Comme il Faut/Prom
Week, Versu, Façade, DeepMind Concordia, Friends & Fables/ACE-1, and Radiant
Story in real depth, with citations and a verdict (the "engine decides, LLM
renders" pattern is independently validated by ACE-1's shipped post-mortem).
**Do not dispatch Prompt 42 as originally written.** The one confirmed gap:
**CICERO** (Meta AI, Diplomacy) appears nowhere in the repo. Prompt 42R below
replaces it — much narrower, one slot instead of three.

Four self-contained prompts (38, 39, 40, 41) plus one narrow replacement
(42R), for dispatch to external research agents (no shared context — each
assumes the reader has never seen this conversation). Suggested report
numbers 38-42, filed under `docs/research/` once done — check
`docs/research/00-index.md` for collisions first, other sessions may have
added reports since this was written.

## Revised engine allocation (7 slots: 2 Kimi / 2 Claude web / 3 Gemini)

| # | Topic | Engine | Why |
|---|---|---|---|
| 42R | CICERO architecture + confirm no other gaps in existing prior-art research | Kimi | the one real gap, worth one thorough pass |
| 38 | Skyrim lip-sync feasibility | Kimi | blocking decision, needs rigor |
| 40 | llama.cpp/MLX KV-cache reuse | Claude web | bounded technical verification |
| 41 | Free-text-to-intent grounding | Claude web | spans current practice + one academic precedent |
| 39 | TTS on Apple Silicon | Gemini | narrow, fast lookup |
| 38 (dup) | Skyrim lip-sync feasibility | Gemini | cheap fact-check against Kimi's deeper pass |
| 40 (dup) | llama.cpp/MLX KV-cache reuse | Gemini | cheap fact-check against Claude's pass — freed up since Prompt 42 dropped from 3 slots to 1 |

---

## Prompt 42R — CICERO's architecture, and a gap-check against existing research (replaces original Prompt 42)

Researching one specific gap for Chronicle, a Skyrim mod building a social
simulation with a planned dialogue-generation layer. The project has already
done extensive prior-art research (on file, not for you to redo) covering:
Talk of the Town (James Ryan), Comme il Faut/Prom Week (Ben Samuel/Mateas/
Wardrip-Fruin), Versu (Richard Evans/Emily Short), Façade (Mateas & Stern),
Daggerfall's QBN/QRC template system, storylet theory, PaSSAGE, DeepMind
Concordia (a grounded-validation LLM Game Master), and Friends & Fables/
ACE-1 (a shipped commercial product whose post-mortem validates "separate the
AI's face from the campaign engine's truth" almost word for word). The one
system missing from all of that research is **CICERO** (Meta AI's
Diplomacy-playing agent).

1. Verify the actual, real architectural separation in CICERO between its
   strategic/planning module (which decides what moves/deals to pursue) and
   its controllable dialogue model (which renders that intent into natural
   language to other players). Don't take headline claims at face value --
   find the actual paper (Meta AI / Science, 2022, "Human-level play in the
   game of Diplomacy by combining language models with strategic reasoning")
   and describe precisely how intent flows into generated text, what
   constrains the dialogue model from free-lancing beyond the planned intent,
   and whether that constraint is enforced or just usually-true.
2. Is CICERO's dialogue model ever allowed to say something the planning
   module didn't intend (i.e., does generation ever get to invent facts/
   deals/betrayals), or is generation strictly bound to render pre-decided
   state? This is the one property that matters most for comparison to
   Chronicle's own "engine decides, LLM renders, never authors" rule.
3. Has anything published since CICERO (2022) extended or critiqued this
   plan-then-render pattern specifically -- in games, or in adjacent agent
   architectures? A few post-2022 candidates worth checking if you have
   capacity: any successor Diplomacy-playing agents, or general "grounded
   dialogue generation" papers that cite CICERO as precedent.
4. Separately -- a sanity check, not a full re-research: skim (don't deep
   research) whether any of Talk of the Town / Comme il Faut / Versu /
   Façade / Concordia / ACE-1 has had a notable public update, successor
   project, or critique published recently that the existing on-file research
   might have missed. Flag only if you find something concrete; don't pad
   this section if there's nothing new.

Deliverable: does CICERO's actual mechanism match or refine Chronicle's
"engine decides, LLM renders" principle, and is there anything about its
specific implementation (how intent gets encoded and handed to the language
model, what stops it drifting) worth borrowing concretely -- not just
thematically similar.

---

---

## Prompt 38 — Skyrim dynamic-speech lip sync feasibility

You're researching for Chronicle, a Skyrim SE/AE mod (external social-simulation
service). We're designing a "voice" tier: an LLM renders one grounded dialogue
line per player interaction, a TTS model synthesizes audio, and it needs to play
back on an NPC (or the player character) in-game. The blocker: **Skyrim's
lip-sync system expects a pregenerated `.lip` file per audio file** (FaceFX-based
viseme data), which is fundamentally at odds with synthesizing audio at runtime
from a model that didn't exist when the game shipped.

Answer, with primary sources (mod pages, GitHub source, SKSE plugin docs — not
just forum claims):

1. Does any existing Skyrim mod solve runtime TTS + lip sync (not pregenerated)?
   Specifically check **Mantella** (github.com/art-from-the-machine/Mantella) —
   it's known to do TTS-based NPC dialogue; find out exactly what it does for
   lip movement (accepts no lip sync? procedural fallback? calls an external
   FaceFX-compatible tool at runtime?).
2. Does open-source tooling exist to generate `.lip` files
   programmatically/headlessly from an audio file + phoneme/text, fast enough
   for a runtime pipeline (not just Creation Kit's manual lip generator)? Look
   at FaceFX Studio's file format, community-reverse-engineered lip generators
   (e.g., `LipFuzer`, `Lip Sync Utility`, or anything referenced by
   Mantella/CHIM/SkyrimNet's toolchains), and whether any run outside
   Windows/without the CK.
3. Is there a "no lip movement, audio only" fallback that's actually acceptable
   in practice (does it look broken in first person / with an NPC facing the
   player, or is it unnoticeable)? Cite any dev/modder commentary on how bad
   this looks.
4. What's the realistic latency of generating a `.lip` file at runtime (if any
   tool can) versus just accepting no lip movement for v1?

Deliverable: a decision-oriented report — does Chronicle need to solve lip sync
before shipping spoken dialogue, or can it ship voice-only with no/frozen mouth
movement as an honest v1? Cite every claim to a primary source (repo file, mod
page changelog, not a forum post repeating a rumor).

---

## Prompt 39 — TTS model selection for Mac mini M5 Pro (Apple Silicon/MLX)

A sibling project ran a rigorous local TTS bake-off (ECAPA speaker-similarity +
WER via faster-whisper) on NVIDIA CUDA hardware and identified two
release-candidate engines: **Chatterbox-Turbo** (MIT, similarity 0.640, WER
0.097, ~0.15-0.4x realtime) and **Qwen3-TTS Base** (Apache 2.0, similarity
0.642, WER 0.041 — most intelligible, but slowest at ~0.7-1.4x realtime).
IndexTTS-2.5 scored close (0.628 sim / 0.067 WER) but is non-commercial-licensed
and was disqualified as a release candidate; Fish Audio S2 was dropped entirely
(non-commercial + hung on smoke test). Neither Chatterbox nor Qwen3-TTS has been
tested on Apple Silicon. A separate project (Chronicle, a Skyrim mod) needs a
sub-1.5B-class TTS model running well on a **Mac mini M5 Pro, 64GB unified
memory, 307GB/s bandwidth**, via MLX or another Metal-accelerated path,
alongside a resident ~30-35B MoE LLM (most of the 64GB budget goes to the LLM).

Answer, with primary sources (repo issues/PRs, model cards, benchmark threads —
not marketing pages):

1. Does **Chatterbox** (resemble-ai/chatterbox) or **Qwen3-TTS** have any MLX
   port, CoreML export, or community-reported Apple Silicon inference path
   today? Real throughput numbers if reported anywhere (GitHub issues often
   have this from Mac users trying unsupported platforms).
2. If neither ports cleanly, what's the best MLX-native or Metal-accelerated
   alternative in the same class (Kokoro is a candidate — check if it has an
   MLX build; also check CosyVoice, Zonos, and any other current sub-1.5B
   open-weights TTS model) — with the same measurement lens: does it support
   multi-speaker/original-voice assignment (no cloning real people, including
   Skyrim's own voice actors, without documented consent — this is a hard
   requirement), and does it expose *some* delivery control lever (inline
   tags, parameters) an adapter could translate an existing engine-neutral
   annotation schema onto (see schema below)?
3. Streaming/incremental synthesis support (sentence-fragment-at-a-time), since
   the design wants TTS to start before the LLM finishes generating the full
   line.

For reference, the existing annotation schema to check compatibility against
(built and working in the sibling project, not a proposal): `emotion` (enum:
neutral/happy/sad/angry/fear/surprised/sarcastic/dramatic/whisper/commanding/
pleading/amused), `intensity` (0-1 float), `pace` (slow/normal/fast),
`nonverbal` (array: laugh/chuckle/sigh/gasp/groan/sniff/cough/clear_throat/
shush), `instruct` (free text, <=300 chars) — Chatterbox maps this to leading
`[tags]` + an `exaggeration` param; report whether your recommended Mac-viable
engine can support an equivalent mapping.

Deliverable: does the existing CUDA bake-off winner survive the move to Mac, or
does the hardware target change the pick? Be decisive, not just descriptive.

---

## Prompt 40 — KV-cache / prefix-cache reuse on llama.cpp and MLX

You're verifying a technical assumption for Chronicle, a Skyrim mod's
LLM-serving architecture. The design (internal doc, not public) assumes:
prompts share a stable prefix (world rules -> location/cell state -> per-NPC
belief "rider" -> conversation turns), and the serving stack can **reuse the KV
cache for the shared prefix across many different NPC-specific completions**,
so each new NPC's first response only pays prefill cost for its own short
"rider" segment, not the whole prefix. The doc claims: *"vLLM block-hash prefix
caching, SGLang radix tree [do this automatically]; llama.cpp/MLX need explicit
per-location warm cache files"* — i.e., it assumes llama.cpp and MLX (the two
frameworks realistic for a Mac mini, Apple Silicon target) require you to
manually save/reload a serialized KV-cache state file per shared prefix, rather
than doing automatic prefix-cache lookup like vLLM.

This assumption needs to be checked against real, current capability — it may
be stale, generously optimistic, or missing an existing better mechanism.
Answer with primary sources (project docs/source, not summaries):

1. Does **llama.cpp** support saving/loading KV cache state to/from a file
   today (`--prompt-cache` / session files, or the
   `llama_state_save_file`/`llama_state_load_file` API)? What are its real
   constraints — does it require an *exact* token-prefix match to reuse, does
   it support partial/longest-prefix reuse automatically (some servers do
   prefix matching against multiple cached sessions), and what's the practical
   reload latency for a multi-thousand-token prefix on Apple Silicon?
2. Does **MLX** (mlx-lm or a wrapping server) have an equivalent mechanism for
   saving/restoring/reusing KV cache across generation calls? Is this a
   first-class feature or something the project would have to hand-roll?
3. Is there a server wrapping either (llama.cpp's own `llama-server`, or any
   MLX-based serving project) that does **automatic** longest-common-prefix
   cache reuse across concurrent requests (i.e., behaves like vLLM's
   block-hash caching) rather than requiring the caller to manage explicit
   warm-cache files per location? If one exists, that changes the architecture
   from "we manage cache files" to "the server just does it."
4. Given the target model class (MoE, ~30-35B total params, ~3-4B active, e.g.
   Qwen3.6-35B-A3B) on a 64GB M5 Pro Mac mini — is there a known-good serving
   stack combo (specific project + version) other Apple Silicon LLM-serving
   setups actually use for this kind of shared-prefix/multi-tenant workload, as
   of your knowledge?

Deliverable: confirm, correct, or refute the "llama.cpp/MLX need explicit
per-location warm cache files" claim, and recommend the concrete implementation
approach (which library/server, which API calls) rather than leaving it as an
architectural aspiration.

---

## Prompt 41 — Grounding free-text player input to a closed intent vocabulary

You're researching a design problem for Chronicle, a Skyrim mod's dialogue
system. The core design principle: everything the player "says" must resolve to
a **closed, engine-computed vocabulary of grounded parameterized intents**
(e.g., `(confront, rumor_id=X)`, `(boast, quest_id=Y)`) — never raw free text —
because the committed line becomes a trackable, propagating claim in a
simulation, and an ungrounded/unparseable claim would break provenance
tracking. However, the project is considering (undecided) offering a free-form
text input "advanced path" as an escape valve for players who want to say
something not covered by the menu.

The risk: if free text is allowed, something has to map it back onto the closed
vocabulary (or reject it) without becoming a moderation/hallucination problem,
and without silently inventing a claim the engine can't actually ground (an NPC
can't "believe" a rumor with `rumor_id=null`).

Research, with primary sources:

1. How do modern LLM function-calling / structured-extraction techniques handle
   "map this free-text utterance onto the closest matching item in this closed,
   engine-provided list of N valid options, or return NONE" reliably? What's
   the current best practice — constrained decoding restricted to valid IDs, a
   classifier head, or an LLM call with the option list injected and
   forced-choice output? Cite concrete tooling/papers/frameworks (e.g.
   instructor, outlines, guided decoding via vLLM/llama.cpp grammars), not just
   "LLMs are good at this."
2. What's the realistic false-positive rate / failure mode when the true answer
   is "none of the current options match" — does forced-choice decoding tend to
   pick a wrong-but-plausible option instead of correctly abstaining, and is
   there a known mitigation (e.g., always including an explicit
   "NONE_OF_THESE" option in the choice set)?
3. Is there prior art from other games/interactive fiction for this exact
   problem — free text input constrained back to a closed action/response
   space? (Facade's NLU-to-authored-beats mapping is the classic academic
   example — assess how well it actually worked and why, and look for any more
   recent commercial or indie attempts at the same pattern.)
4. Given Chronicle's target hardware (a single Mac mini serving a ~30-35B MoE
   model, low latency budget), is real-time free-text grounding realistic as an
   extra LLM call in the conversation loop, or does it meaningfully blow the
   latency budget compared to the menu-tap path?

Deliverable: a recommendation on whether a free-form advanced path is a safely
implementable feature today (with a concrete mechanism), or whether it should
stay cut until a specific capability matures — be decisive, not just
descriptive.

---

## Prompt 42 (SUPERSEDED — do not dispatch, kept only for record) — Prior art: simulation-grounded dialogue/narrative generation

**Do not send this one.** Most of it duplicates `docs/research/comparative-
systems/ai-directors-and-drama-management.md` (v1-v4), `02-social-simulation-
literature.md`, and `docs/research/papers/`. Use Prompt 42R above instead.

Researching architectural precedent for Chronicle, a Skyrim mod building a
social simulation (per-NPC beliefs with provenance/confidence, rumors that
mutate as they propagate between NPCs, grudges from witnessed events) that's
about to add a dialogue-generation layer. The core design principle already
adopted: **a deterministic simulation/engine decides what's true and what can
be said; a language model only renders that into natural-language dialogue —
it never decides plot, memory, or social state.**

Find and assess prior art -- academic and shipped/prototype games -- that
combines a reactive social/political simulation with a dialogue or narrative
generation layer, and specifically how each one **connects the two**: does
generation ever get to invent facts, or is it strictly rendering pre-decided
state? Cover at minimum, verify/correct these priors and go deeper:

1. **Talk of the Town** (James Ryan, UC Santa Cruz PhD dissertation + related
   papers) -- a life-simulation engine centered on gossip propagation and
   mutation between NPCs, rendered as dialogue. This looks like the closest
   academic precedent to Chronicle's rumor-mutation mechanic; find the actual
   mechanism (is dialogue templated/grammar-based NLG, not LLM?) and whether
   anyone has since rebuilt or extended it with an LLM.
2. **Comme il Faut / Prom Week** (Ben Samuel, Michael Mateas, Noah
   Wardrip-Fruin) -- the "social physics" authored-exchange-selection engine.
   How exactly does simulated relationship/status state select/gate which
   authored dialogue fires?
3. **Versu** (Richard Evans, Emily Short) -- BDI-modeled (belief-desire-
   intention) characters with generated dialogue; what happened to it (it was
   pulled from the App Store), and is any of its design documented well enough
   to learn from?
4. **CICERO** (Meta AI, Diplomacy) -- verify the actual claimed separation
   between its strategic/planning module and its controllable dialogue model;
   this is the strongest modern parallel to "engine decides intent, LLM
   renders it" and needs to be checked for accuracy, not assumed from
   headlines.
5. **Facade** (Mateas & Stern) -- the free-text-to-authored-beats NLU
   approach; how well did it actually work in practice, and has anything since
   (indie or academic, especially post-LLM) revisited that pattern more
   successfully?
6. Any **post-2023 (LLM-era) academic work** explicitly on grounding
   LLM-generated dialogue in a separate simulation/knowledge-graph to prevent
   hallucination/plot invention -- this is a live research area
   (retrieval-grounded NPC dialogue, "LLM as narrator not author" framings)
   and there may be directly relevant recent papers neither of us knows about
   yet.
7. Any shipped or prototype game (not just academic) that has tried
   **provenance-tracked or mutating rumors/information specifically**, beyond
   what's already been checked (Chronicle's own prior research already
   confirmed Mantella/SkyrimNet/HerikaServer/IntelEngine do NOT do this --
   don't re-cover that ground, it's settled; focus on non-Skyrim, non-modding
   titles and academic systems).

Deliverable: for each system, state plainly whether generation was allowed to
invent facts/plot or was strictly a renderer of pre-decided state, and pull out
any concrete mechanism (data structure, algorithm, interface pattern) Chronicle
could actually borrow -- not just "this is thematically similar." End with a
direct recommendation on whether the "engine decides, LLM renders" principle
has been validated by this landscape or whether there's a better-proven
alternative pattern being missed.

---

## Prompt 44 — Model-selection fallout: the hybrid-attention prefix-cache blocker

Researching a model-selection problem for Chronicle, a Skyrim mod building a
local LLM-serving pipeline for NPC dialogue. Prior research (an internal
hardware/model survey) picked **Qwen3.6-35B-A3B** as the conversation-tier
model, based on capability and throughput on the target hardware — a **Mac
mini M5 Pro, 64GB unified memory, 307GB/s bandwidth**, serving one ~30-35B-
class LLM alongside a small resident TTS model. The architecture depends on a
**shared prompt prefix** (world rules -> location/cell state -> per-NPC belief
"rider" -> conversation turns) with the serving stack reusing the KV cache for
that shared prefix across many different NPCs, so each NPC's first response
only pays prefill cost for its own short "rider" segment.

A separate, later research pass discovered a blocker the original model pick
didn't account for: **Qwen3.6-35B-A3B is a hybrid architecture (per its own
Hugging Face model card: "10 x (3 x (Gated DeltaNet -> MoE) -> 1 x (Gated
Attention -> MoE))" -- 3 of every 4 layers are recurrent Gated DeltaNet, not
full attention), and as of Aug/Sep 2026, automatic KV-cache prefix reuse is
broken for hybrid/recurrent-attention models on BOTH realistic serving stacks
for this hardware** -- llama.cpp logs "forcing full prompt re-processing due
to lack of cache data (likely due to SWA or hybrid/recurrent memory)" every
turn for this model class, and MLX has an open, confirmed issue ("Prefix
cache reuse is broken for all hybrid-architecture models (sliding window,
SSM/Mamba)") with the same root cause: recurrent state can't be split at an
arbitrary token boundary the way full-attention KV cache can. This isn't a
tuning problem -- it defeats the entire "pay prefill only for the rider"
premise the architecture depends on. The upstream llama.cpp fix exists only
in forks as of this writing, not merged to master.

Find the best replacement model. Requirements:

1. **Full-attention (non-hybrid, non-recurrent, no SSM/Mamba/DeltaNet
   layers)** -- confirmed from the model's actual architecture description
   (Hugging Face model card, technical report), not assumed from its name or
   vendor. This is the one non-negotiable requirement; a model that fails
   this silently reproduces the exact problem being fixed.
2. **Comparable capability to Qwen3.6-35B-A3B or Gemma-4-26B-A4B** for
   NPC-roleplay/instruction-following dialogue rendering -- check specifically
   whether **Gemma-4-26B-A4B** itself is full-attention (it was flagged
   alongside Qwen3.6-35B-A3B in the original survey as a comparable-capability
   MoE candidate; if it turns out to already be full-attention, that may be
   the fastest answer of all, requiring no new model search).
3. **Runs at usable throughput (>15 tok/s decode) on a 64GB Mac mini M5 Pro**
   via llama.cpp or MLX, in the ~20-40B total-parameter class (dense or MoE,
   doesn't matter as long as requirement 1 holds and it fits alongside a
   small resident TTS model in 64GB).
4. **Confirm automatic prefix-cache reuse actually works for the recommended
   model** -- ideally a GitHub issue, benchmark, or maintainer statement
   showing `cached_tokens`/`cache_n` behavior for that specific model on
   llama.cpp's `llama-server` or `mlx_lm.server`, not just "it's full
   attention so it should work in theory."

Deliverable: name one primary pick and one fallback, with the specific
evidence that the hybrid-architecture landmine does not apply to either. Be
decisive -- this is blocking a model-selection decision, not an open survey.

**STATUS: answered three times over (reports 45, 46, 47). Report 47 (Kimi) is
the final word: GLM-4.7-Flash primary, Qwen3-30B-A3B-Instruct-2507 fallback.**

---

## Prompt 48 -- Deep read: CIF-CK ("Prom Week meets Skyrim")

Both independent prior-art passes (reports 42 and 43) flagged the same paper
as the single most relevant piece of prior art neither of us had found before
this research batch, and neither pass did more than a secondhand
characterization of it via search snippets. It deserves an actual close read.

**Background, for a reader with zero context:** Chronicle is a Skyrim SE/AE
mod: an external social-simulation service where NPCs hold beliefs with
provenance, rumors mutate as they propagate, and grudges/obligations
accumulate from witnessed events -- all computed by a deterministic Python
engine, then written back into the game as behavior (relationship ranks,
AI-package overrides, vendor pricing, physical evidence objects). Chronicle is
now designing a conversation/dialogue layer on the same principle: the engine
computes a ranked menu of what an NPC or player can plausibly say (grounded in
real belief/grudge/rumor state), and a language model only renders the chosen
option into natural-language text -- it never invents facts or decides
outcomes.

**The paper:** Guimaraes and Santos, "CIF-CK" -- an adaptation of Comme il
Faut (CiF, the "social physics" engine behind the academic game *Prom Week*)
into Bethesda's Creation Kit, shipped as the "Social NPCs" mod on Steam
Workshop/Nexus Mods in 2017. Two versions exist: a conference paper often
titled "Prom Week Meets Skyrim" (NC State Digital Games Initiative,
https://www.games.ncsu.edu/wp-content/uploads/sites/13/2017/05/prom-week-meets.pdf)
and an IEEE TCIAIG journal version. Prior research already extracted this
much secondhand: CiF's four components (a Social Facts Database, an
influence-rule volition scorer, salience-ranked authored "instantiations,"
and trigger rules for consequences) were mapped onto Creation Kit structures
without needing engine source access; the mod shipped publicly; the authors
report positive player reception; and it modeled *perceived* social state
(an NPC can act on a belief about another NPC's feelings that's factually
wrong) -- a feature Chronicle already has via its own belief/observer-local
model. None of that has been verified against the actual paper text, and none
of the *how* has been extracted -- only the *that*.

**What to actually do:** get the real text of the paper (the NC State PDF
link above, or the IEEE Xplore listing if that one is more complete --
ieeexplore.ieee.org/document/8080425) and do a genuine close read, not
another secondhand search-snippet pass. Extract concrete, implementation-
level answers to:

1. **The volition-to-behavior mapping, exactly.** CiF's own volition score
   ranks *social exchanges* an NPC might initiate. How did CIF-CK translate a
   ranked exchange into an actual Skyrim mechanism -- did it write to
   `GetRelationshipRank`, drive AI package conditions, trigger dialogue
   topics, or something else? Chronicle needs exactly this mapping for its
   own menu-ranking design (a still-open question: what determines which
   3-10 of many eligible grounded intents actually appear in the player's
   or NPC's option list).
2. **What "Social NPCs" actually looked like to a player.** Was dialogue
   authored-instantiation text (per CiF's normal design) injected into
   Skyrim's native dialogue menus, or delivered some other way (floating
   text, notifications, scripted scenes)? Concretely, what did a player see
   and click?
3. **The Social Facts Database's storage mechanism inside a Bethesda game.**
   Creation Kit/Papyrus has no native graph-database concept. What data
   structure did CIF-CK actually use to hold the social-facts history inside
   Skyrim's save/script-variable system, and did it survive save/reload?
   (Chronicle's own hardest unsolved problem, per its research report 37, is
   exactly this class of question for its own state.)
4. **Scale and scope actually shipped.** How many NPCs, how many authored
   microtheories/instantiations, and how large a slice of Skyrim (one town?
   a few named NPCs? all of Whiterun-equivalent?) did the shipped mod
   actually cover? This calibrates how much of "it worked and players liked
   it" generalizes to Chronicle's much larger ambition (all named NPCs,
   propagating claims, LLM rendering).
5. **What the player-reception evaluation actually measured.** The paper is
   cited as reporting "positive reception" and "surveys supporting improved
   engagement" -- get the actual study design (sample size, what was
   measured, what the comparison condition was, if any) so this can be cited
   accurately rather than as a vague positive gesture.
6. **Any documented failure modes or limitations the authors themselves
   name.** Every other system in this research batch (Façade, Versu, CiF,
   Slice of Life) came with an honest catalog of what didn't work. Find
   CIF-CK's equivalent -- authorial burden, engine friction, player confusion,
   whatever it turned out to be.

Deliverable: a report that lets Chronicle actually reuse CIF-CK's engineering
decisions (not just cite it as encouraging precedent) -- specifically, a
direct answer to "should Chronicle's own volition/menu-ranking design copy
CIF-CK's specific mapping mechanism, or does CIF-CK's approach not transfer
because of a limitation this deep read surfaces?"

**STATUS: answered directly, no dispatch needed.** Both the AAMAS 2017 paper
and the 2022 arXiv follow-up turned out to be freely fetchable (no paywall,
no bot-block on the actual PDF/HTML) -- confirmed by checking first, per the
user's own good catch that a research-agent dispatch is pointless when the
source is just directly readable. Filed as
`docs/research/48-cif-ck-skyrim-social-npcs-primary-source.md`. Verdict: the
architectural principle transfers (real player data validates Chronicle's
"expected randomness" doctrine specifically); the concrete mechanisms
(argmax-over-12-moves, Player-actor storage piggyback, co-location-only
scope) don't scale past CIF-CK's own admitted 7-NPC deployment and were never
asked to survive save/reload.

## Lesson for future prompts in this file

Before drafting a dispatch prompt for any named, specific source (a paper, a
repo, a mod page) -- try fetching it directly first. Only fall back to an
external research dispatch when the source can't be reached directly, or the
task is genuinely a broad multi-source search/synthesis rather than "read
this one specific thing closely."

# Review prompt -- ChronicleBridge sync-handshake spec (2026-09-01)

**Target for Kimi.** The spec under review is
`docs/design/chronicle-bridge-sync-handshake-out.md` (implementation plan for
ADR-0004/0005's save/reload sync handshake, verified against a real
`CommonLibSSE-NG` header checkout, then already passed once through an
internal advisor review that fixed a SetUniqueID-collision hazard, a
head_seq write-ordering race, and an underspecified Revert-callback). Don't
ask for a general "review this doc" pass -- restating the prose back isn't
useful. Instead, answer three narrow, searchable questions the header alone
can't settle:

1. **Is there a real registry or informal convention for SKSE co-save
   `SetUniqueID` FourCC values across the Skyrim SE/AE modding ecosystem?**
   The spec proposes `'CHRN'` as a placeholder, unchecked against what any
   other shipped SKSE plugin (Mfg Fix, PapyrusUtil, SkyrimNet, Mantella, CHIM,
   any co-save-using mod you can find source or a public uid list for) has
   already claimed. Find actual examples of `SetUniqueID()` calls in shipped
   plugin source (GitHub is fine) and report what values are taken, and
   whether the community has any de facto collision-avoidance practice (a
   wiki page, a shared registry, a naming convention like "use your mod's
   Nexus IDor plugin name's first 4 chars") or whether it's genuinely
   unmanaged and collisions are just rare by chance.

2. **How do shipped SKSE plugins with asynchronous external state (an HTTP
   service, a background thread, anything that isn't synchronously available
   at Save-callback time) handle the ordering problem between "engine calls
   my synchronous Save callback" and "my last external ACK might still be in
   flight"?** Look specifically at CHIM (there was a documented bug, PR #572,
   in roughly this class -- find it and read what the actual bug and fix
   were), and at Mantella/SkyrimNet if they persist any external-service-
   derived state into the co-save at all. Report what pattern (if any) they
   use -- an atomic/lock-free published value, a "always write the
   last-known-good, never block Save on a pending call" rule, or something
   this spec hasn't considered. If none of them actually solve this problem
   (many co-save plugins only write purely local, synchronously-available
   state), say so plainly -- that's still a useful, correctness-relevant
   finding rather than a null result.

3. **Find real examples of a `SerializationInterface::SetRevertCallback`
   handler doing something non-trivial** (not just an empty stub) in a
   shipped plugin, and report what state they reset and why. The spec's own
   Revert handler (dropping the outbound event queue and resetting
   epoch_id/manifest) is reasoned from SKSE's documented semantics
   ("Revert fires between kPreLoadGame and the Load callback, discard your
   stale in-memory state") rather than copied from a working precedent --
   confirm whether that's actually the general pattern other plugins follow,
   or whether there's a common mistake/edge case (e.g. state that should
   survive Revert but commonly doesn't, or vice versa) worth flagging.

Report back concretely: cite the actual repo/file/line or wiki page for each
finding, not just a general impression. If a question turns out unanswerable
from public sources (e.g. no plugin does #2 in a way that generalizes),
that's a valid and useful answer -- don't pad it with speculation.

**STATUS (2026-09-01): answered directly, Kimi dispatch abandoned.** The Kimi
MCP tools (`kimi_agent`, `kimi_research`, and even plain `kimi_web_search`)
became unreliable mid-session -- every call after the first one timed out at
120s/600s regardless of parallel-vs-sequential dispatch. Rather than keep
retrying a flaky backend, answered all three questions directly via
`gh api search/code` (GitHub code search) against real shipped SKSE plugin
source. Findings folded into
`docs/design/chronicle-bridge-sync-handshake-out.md` inline (§7 item 1, and
two new bracketed notes in §4.1's state machine): JContainers and Soulsy give
real precedent for Q1 (no formal FourCC registry exists, only an informal
~18-entry catalog hardcoded in a community cosave-inspector tool) and Q3
(Revert = full in-memory wipe, confirmed by two independent shipped mods).
Q2 came back a genuine null result -- no shipped plugin with async external
state was found serializing it into the cosave at all; CHIM's actual
game-side plugin has no public source (only satellite tools are public under
Dwemer-Dynamics/*), so the "CHIM PR #572" reference in this prompt could not
be verified and should not be cited as fact going forward.
