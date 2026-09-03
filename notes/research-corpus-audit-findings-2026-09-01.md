# Research-corpus audit — findings (Kimi, 2026-09-01)

**Task:** `notes/research-corpus-audit-review-prompt-2026-09-01.md` — internal-consistency audit of
`docs/research/34`–`48` against ADR-0011. Method: full re-read of reports 34, 35, 39, 43, 47
(primary texts, not summaries), plus live web verification against primary sources fetched
today (EQ-Bench Creative Writing v3 leaderboard data pulled from eqbench.com's own JS data
files; Z.ai announcements; independent Apple-Silicon throughput measurements).

Headline: **Item 1 is real and worse than stated — the one hard datum that exists for
GLM-4.7-Flash on a creative-writing axis is strongly negative.** Item 2 is a false tension
(but the "moot" reasoning has a scope limit worth stating). Item 3 is a real gap but
architecture-absorbed. Two new cross-report contradictions found (throughput figures, and the
silent 34-vs-38 ladder collision).

---

## Item 1 — The GLM-4.7-Flash roleplay-evidence gap: CONFIRMED, load-bearing

**The contradiction, precisely.** Report 34 (§1.3) ranks local RP models S/A/B/C using
rp-benchmark, EQ-Bench Creative Writing, and community pulse; it never evaluates
GLM-4.7-Flash (its GLM coverage is GLM-5.1/5.2, 744B-class, hosted-only ceiling rows).
Report 47 then picked GLM-4.7-Flash as the primary conversation-tier model with exactly one
piece of RP evidence: a single HuggingFace discussion comment ("good in roleplay and creative
writing," §3.1). Everything else in 47's capability case is (a) architecture screening and
(b) vendor reasoning/coding benchmarks (AIME, GPQA, SWE-bench, τ²-Bench) — axes Chronicle
explicitly switches off (non-thinking rendering workload).

**What I verified online today, and it changes the picture from "thin" to "negative":**
the EQ-Bench Creative Writing v3 leaderboard — the same instrument report 34 cites
(its aggregate gave GLM-5.2 1749; today's board shows GLM-5.2 at 1750.9, and 34's
"Claude Opus 5 leads at Elo 2105" matches today's 2116.1, so this is the same ladder,
newer snapshot) — **has tested GLM-4.7-Flash**:

| Model | CWv3 Elo | Rank (of 108) |
|---|---|---|
| GLM-4.7 (flagship) | 1410.5 | 68 |
| mistral-small-creative | 1367.3 | 73 |
| **gemma-4-31B-it** (34's S-tier local pick) | **1365.7** | 74 |
| gemma-4-26B-A4B-it (34's A-tier) | 1301.2 | 83 |
| **GLM-4.7-Flash** (47's primary pick) | **1122.3** | **99** |

GLM-4.7-Flash sits in the **bottom decile**, ~243 Elo below report 34's S-tier local winner
and ~288 Elo below its own flagship sibling. So the answer to "was it picked on
architecture/general-benchmark grounds without being checked on the RP axis" is: **yes,
demonstrably — and the check that now exists goes against it.** Report 47's "explicit positive
roleplay feedback" claim (one forum comment) does not survive contact with the benchmark.

**Sharper still — the collision nobody stated:** report 38's prefix-cache blocker disqualifies
*every* local model on report 34's RP ladder. Gemma 4 31B (50 sliding-window layers),
Gemma 4 26B-A4B (5:1 hybrid), Qwen3.6-27B (48 DeltaNet + 16 attention), Qwen3.6-35B-A3B
(the blocker itself), Qwen3.5-122B-A10B (hybrid DeltaNet per 35 §4.2) — the entire
quality-first candidate set is serving-incompatible. Reports 34 and 38 were each internally
rigorous but their conclusions share **zero surviving candidates**, and 47 never says this
out loud: it wasn't that GLM-4.7-Flash beat the RP winners, it's that the RP winners were
already dead on the serving requirement. The real question is therefore not "does GLM beat
Gemma 4 31B" (moot — Gemma can't run the workload) but "**is GLM-4.7-Flash good enough on
the voice axis, and is it even the best of the four survivors** (GLM-4.7-Flash,
Qwen3-30B-A3B-2507, Qwen3-32B, Mistral Small 3.2)?" On current evidence: unknown for the
latter three (none is on the CWv3 board — note 47's "Creative Writing v3: 86.0" for the
fallback is the **vendor model-card number on a 0–100 scale**, a different instrument from
EQ-Bench Elo, not cross-comparable) and negative for the primary.

**Axis-transfer flag (as requested):** report 34's discriminating axis — 12–20-turn
adversarial persona coherence, SillyTavern-shaped — only partially transfers. Chronicle's
workload is: 8–16k engine-curated grounded state in, **one 1–3-sentence line out**, with
memory deliberately held by the engine and re-injected each turn (34's own §1.4 mitigation,
which Chronicle implements architecturally). The axes that matter are single-line register
control, grounding fidelity (rp-benchmark's F13 buried-detail tracking), and not breaking
character under off-script input (F1) — *not* 20-turn transcript memory. CWv3 (long-form
prose quality) is an imperfect proxy for that too, in the opposite direction. The right
instrument doesn't exist off the shelf; it's the recorded-fixture replay harness ADR-0011's
testing section already specifies.

**Load-bearing?** Yes, but bounded. It doesn't reopen the *architecture* decision (the
full-attention requirement stands, and the survivor set is correct), and the fallback swap is
one line. It does mean: (a) "adopt GLM-4.7-Flash" should be downgraded to "candidate pending
voice-quality eval" — 47's own §6 verification recipe covers only `cache_n`, not quality;
(b) the first thing to run when the M5 Pro arrives is a **head-to-head fixture eval of
GLM-4.7-Flash vs Qwen3-30B-A3B-2507 on Chronicle's actual workload shape** (grounded
short-line rendering from voice cards), not a general RP benchmark; (c) report 47's §3.1
"positive roleplay feedback" sentence should be amended to cite the CWv3 result — currently
the report's own evidence section is misleading by omission.

---

## Item 2 — Report 39 vs ADR-0011: FALSE tension, but the "moot" reasoning has a scope limit

**The drafting-step question.** Report 39's Phase-1 pipeline (embed → top-k retrieve over the
engine's live valid-intent set → constrained-decode over {top-k, NONE_OF_THESE} → threshold →
player confirms) does not give the LLM engine-forbidden judgment. The engine owns the
candidate set, the threshold, and the vocabulary; the player owns the commit. The LLM's role
is *interpretation* (mapping free text onto an engine-supplied closed set), which is
structurally symmetric to *rendering* on the output side — advisory in both directions,
deciding in neither. This is exactly the division James Ryan converged on
(43 §2.2/§10.2 #6: "the model interprets; the engine owns the response space"). The tension
is false **provided** the confirmation gate is genuinely mandatory until 39's Phase-2
thresholds are measured (correction rate <2–3% AND OOV recall >90%) — the one thing that
would make the tension real is treating confirmation as a removable config option, because
39's own numbers (48.5% abstention ceiling) say the grounding guess is wrong too often to
commit unsupervised.

**Does the CICERO-style filter itself require engine-forbidden judgment? No.** The
intent-correspondence filter (43 §5.2) is a *veto-only* mechanism: it can discard a candidate
or force a re-roll; it cannot author, choose, or commit anything. That places it in the same
category as the grammar layer — validation machinery, not decision machinery. And there's a
stronger structural point the "moot" argument missed: per the design notes §2, **the
committed claim is built from the menu selection's grounding refs, not parsed from the LLM's
words**. The claim's semantics never pass through the model at all; a filter-evading bad line
degrades the player's experience (paraphrase mismatch), not the claim store. So the filter is
a *quality* gate, and integrity is protected structurally upstream of it. The "moot"
conclusion holds — but for a stronger reason than "the filter ships anyway."

**The scope limit, stated precisely:** the "filter ships regardless, so confirm-vs-autoplay
is moot" reasoning applies only to the **output side** (open question #1: NPC/player rendered
lines). It does **not** cover the **input side** (open question #6, report 39's free-text
grounding confirmation): the intent-correspondence filter inspects rendered text against a
conditioned intent; it does nothing for a mis-grounded input mapping ("player typed X, model
resolved it to the wrong rumor_id"). If anyone extends "the filter makes confirmation moot"
to the free-text path, that would be a real error — 39's mandatory one-tap confirmation
stands on its own evidence, independent of the output-side filter.

Also note the filter's own error profile: CICERO's ran at 65% recall (it *misses* a third of
contradictions, and discards some good lines). "Ships regardless" is correct; "sufficient" is
not claimed anywhere in 43 and shouldn't be assumed in the design.

**Load-bearing?** No — design direction unchanged. Worth one sentence in the design notes so
the two confirmation gates (input-side, output-side) don't get conflated in implementation.

---

## Item 3 — GLM-4.7-Flash vs report 35's structured-output findings: real gap, architecture-absorbed

**The gap is real but subtler than the task brief states.** Report 35's grade table *does*
contain a "GLM-4.7 class" row (A; 96.5% schema compliance, 80.4% value accuracy) — but the
row's own evidence note ("Strong BFCL lineage (GLM-4.5 led BFCL-V4)") makes clear it grades
the **flagship GLM-4.7** (the 300B+-class model), not GLM-4.7-Flash (30B-A3B MoE-lite). So 35
and 47 did talk past each other: the A grade cannot be assumed to transfer to a small
MoE-lite sibling, and 47 never cross-references 35 at all. I could not verify whether the
Interfaze SOB dataset includes GLM-4.7-Flash specifically (its public write-up doesn't
enumerate per-model rows at that granularity) — flag as unverified rather than guess.

**Why it's absorbed anyway:** the workload's structured-output needs are already engineered
around model variance, on three independent layers. (a) The spoken line is never wrapped in a
grammar (35 §2.2, design notes §3); TTS annotations are post-hoc regex-checked with one
re-roll. (b) 35's own split-call recommendation puts metadata in a separate constrained call
— which can be a 3–9B schema specialist (35 §6.1: Schematron-8B beat gpt-oss-20b at 2.5×
fewer params) — so the voice model's SOB grade needn't matter at all. (c) 39's grounding call
constrains syntax by grammar; its residual risk is forced-choice semantics, which is
model-agnostic and covered by confirmation. The one place GLM-4.7-Flash's unmeasured
structure behavior actually bites is the **in-prose annotation-tag emission rate** (design
notes §3's closed set) — a cheap thing to measure in the same fixture eval as Item 1.

**Load-bearing?** No. Add one probe to the fixture eval (annotation-schema compliance +
metadata value accuracy on Chronicle's actual schemas) and the gap is closed empirically.

---

## Item 4 — Additional contradictions found

**4a. Reports 39 and 47 cite irreconcilable throughput numbers for the same model on the same
machine — and external evidence says they're each measuring different runtimes without saying
so.** 39 (§Latency): "Qwen3-30B-A3B Q4 on an M4 Pro: llama.cpp 80.7, MLX 83.1 tok/s."
47 (§4): "35 tok/s on a 273GB/s M4 Pro under MLX" (llmcheck.net). Independent measurements
today: llama.cpp Q4_K_M on M4 Pro ≈ **29–43 tok/s** (willitrunai fit model; Ollama's old
llama.cpp backend benchmark), MLX on the same machine ≈ **80–130 tok/s** (Ollama 0.19's own
MLX-vs-llama.cpp benchmark on Qwen3-Coder-30B-A3B: 130 vs 43; llm-speed.com M3 Ultra MLX:
112). So 39's "llama.cpp 80.7" is almost certainly a mislabeled MLX/Benchmark-runtime number,
and 47's "35 tok/s under MLX" is almost certainly a llama.cpp number mislabeled as MLX.
**Load-bearing?** Not for model choice (both picks clear the 15 tok/s bar on either runtime),
but the design notes' §5 latency budget (tap-to-first-word 1–1.5s) should be recomputed with
runtime-correct figures, and the corpus should stop quoting these two reports' numbers
side-by-side. Related: the design notes' "MoE ~100+ tok/s" expectation cites Qwen3.6-35B-A3B
and Gemma 4 26B-A4B — both now disqualified; GLM-4.7-Flash lands ~24–26 tok/s, so the
speculative pre-render idea in notes §5 matters more than the notes assumed.

**4b. Reports 35 and 39 cite opposite effect-directions for constrained decoding on accuracy,
and never reconcile.** 35 (§2.2, citing the 2026 SE-tasks study): constraints "neither fix
nor materially harm content" (exact-match statistically indistinguishable). 39 (§The
mechanism, citing ExtractBench): validity *dropped* from 51% to 37% under structured-output
mode in one experiment. Both reports derive the same design rule (grammar for syntax only,
engine validates values), so this doesn't change any decision — but the corpus currently
contains both "the tax is ~0" and "the tax can be 14 points" with no flag connecting them.
The honest synthesis is in 35's own §2.2: the tax is workload-dependent (0–3% routine,
10–15% hard long-tail). **Load-bearing?** No; worth a cross-reference note in one of the two
reports.

**4c. (Framing, not error) Report 47's capability table compares GLM-4.7-Flash to
Qwen3-30B-A3B-*Thinking*-2507 on reasoning benchmarks** (AIME, GPQA, SWE-bench) — the
comparison class Chronicle explicitly disables. The decision-relevant comparator is the
*Instruct* (non-thinking) variant on creative/IF axes, where the fallback's vendor numbers
(CWv3 86.0, IFEval 84.7) are actually the stronger creative-quality evidence of the two
finalists. This doesn't flip the pick (architecture and serving maturity drive it), but it
reinforces Item 1: on voice-relevant axes, the fallback currently has the *better*
evidence base, not the weaker one.

## Claims I could not verify against primary sources

- rp-benchmark (LeviTheWeasel) and its per-model failure-mode grades — not re-fetched;
  report 34's characterization taken at face value.
- Whether the Interfaze SOB includes GLM-4.7-Flash (vs flagship GLM-4.7) — not determinable
  from the public write-up.
- Z.ai's published benchmark table for GLM-4.7-Flash (AIME etc.) — corroborated as existing
  (towardsai.net, Jan 2026) but not row-verified.
- Report 34's Gemma 4 community-engagement rankings (bigguyonstuff synthesis, HN thread) —
  not re-fetched.
- GLM-4.7-Flash's "200K-class context" and exact layer/expert counts — 47's citations
  (solarkyle GGUF card, mlx-lm source) not re-fetched; the model's existence, release date
  (Jan 19–20, 2026), 30B-A3B MoE shape, and coding-first positioning are independently
  confirmed.

## Bottom line for the project

One decision changes status: **"adopt GLM-4.7-Flash" → "GLM-4.7-Flash is the architecture
candidate; voice-quality unverified, with one negative public datum (CWv3 rank 99/108)."**
The fix is not a fifth research pass — it's one afternoon on the real hardware when it
arrives: the §6 `cache_n` recipe *plus* a head-to-head fixture eval (GLM-4.7-Flash vs
Qwen3-30B-A3B-2507, Chronicle's own grounded-short-line prompts, recorded and replayable),
with the fallback swap costing one line if the primary disappoints. Everything else in the
corpus's recommendation chain survives the audit.
