# Chronicle NPC Model Replacement: Qwen3-30B-A3B-Instruct-2507 (Primary) / Mistral-Small-3.2-24B (Fallback)

**Date:** 2026-08-31
**Method:** 1 external research pass (Claude web) — one of two independent answers to Prompt 44
(the model-selection fallout from report 38's hybrid-attention finding). See
`notes/deep-research-prompts-2026-08-31.md`, Prompt 44. **A second independent pass (Gemini)
reached a different primary pick — see report 45's filing note for a side-by-side comparison
— and a third (Kimi) was still in flight when both were filed.**

**This report's pick:** Qwen3-30B-A3B-Instruct-2507 (MoE, 3.3B active of ~30B, pure
full-attention GQA — the pre-3.5/3.6 Qwen3 generation, confirmed to predate the hybrid
Gated-DeltaNet architecture). **Report 45's pick:** Qwen2.5-32B-Instruct (dense). Both
independently disqualify Gemma-4-26B-A4B as hybrid.

**A third pass (Kimi) has since arrived as report 47 — treat it as the final word.** It found
a better primary pick (GLM-4.7-Flash, MLA-based full attention, best-in-30B-class benchmarks)
that neither this report nor 45 considered, screened roughly a dozen candidates neither of us
checked, and independently corroborates *this report's* pick (Qwen3-30B-A3B-Instruct-2507) as
the recommended zero-risk fallback — read 47 first.

---

## TL;DR
- **Primary pick: Qwen3-30B-A3B-Instruct-2507** — a pure full-attention GQA Mixture-of-Experts model (48 transformer layers, Grouped Query Attention with 32 query heads and 4 key-value heads, 128 experts with 8 activated per token, RoPE + SwiGLU, no DeltaNet/SSM/sliding-window layers). It is architecturally in the exact "cache reuse works normally" class, fits in ~18–20 GB at 4-bit alongside a resident TTS model in 64GB, and its 3.3B-active MoE decode clears the 15 tok/s bar with wide margin on Apple Silicon.
- **Fallback: Mistral-Small-3.2-24B-Instruct-2506** — a dense full-attention model whose published `config.json` explicitly sets `"sliding_window": null`, eliminating even the sliding-window variant of the cache-reuse landmine. Slower (dense 24B, all parameters active each token) but bulletproof on the one non-negotiable requirement.
- **Gemma-4-26B-A4B is DISQUALIFIED** — it is NOT full-attention. Its own model card describes a "hybrid attention mechanism that interleaves local sliding window attention with full global attention," and it is explicitly named as a model that reproduces the exact prefix-cache bug on both llama.cpp (issue #21831) and MLX (RotatingKVCache non-trimmable, olmlx issue #207). The "fastest answer of all" the survey hoped for does not exist.

## Key Findings

1. **The hybrid landmine catches Gemma-4-26B-A4B too — this is the pivotal finding.** The original survey flagged Gemma-4-26B-A4B as the comparable-capability fallback and hoped it might already be full-attention. It is not: it is a 50-sliding-window-layer / 10-global-layer hybrid, and it silently reproduces the identical "forcing full prompt re-processing" behavior on both target stacks. It must be discarded.

2. **Qwen3-30B-A3B (the pre-3.5 "Qwen3" generation, NOT Qwen3.5/3.6) is a standard full-attention transformer.** It shares no Gated DeltaNet / SSM / Mamba layers with the Qwen3.5/3.6 hybrids. Per the APXML architecture spec: it is "structured with 48 transformer layers and utilizes Grouped Query Attention (GQA) with 32 query heads and 4 key-value heads … 128 experts, with 8 experts selected via a routing mechanism for each token … Rotary Position Embedding (RoPE) and SwiGLU activation." There is no recurrent state to split at a token boundary.

3. **Cache reuse is confirmed working for the full-attention class on both target stacks.** On llama.cpp, the maintainer-verified bug tracker states that dense and non-hybrid MoE models "keep pos_min low enough that the threshold check passes and existing KV cache is reused normally"; on MLX, the tracking issue states prefix caching "only works for pure full-attention models" — placing both recommended models on the working side.

4. **Throughput clears the bar comfortably for the MoE.** A 3.3B-active MoE is bandwidth-cheap to decode. Independent Apple Silicon measurements of same-class A3B MoE models range from ~39 tok/s (Qwen3-Coder-30B via Ollama on M4 Pro) up to ~130 tok/s (Qwen3-Coder-30B via MLX on M4 Pro 64GB); the M5 Pro at 307 GB/s lands solidly above the 15 tok/s decode floor. Dense Mistral-Small-24B is heavier per token and sits lower.

## Details

### Requirement 1 (non-negotiable): Full attention, confirmed from actual architecture

**Qwen3.6-35B-A3B (the blocked model) — confirmed hybrid.** Its Hugging Face model card gives the hidden layout verbatim as "10 × (3 × (Gated DeltaNet → MoE) → 1 × (Gated Attention → MoE))" — 30 of 40 layers are recurrent Gated DeltaNet. That recurrent state cannot be split at an arbitrary token boundary, which is the root cause of the prefix-reuse failure.

**Gemma-4-26B-A4B — confirmed hybrid, DISQUALIFIED.** The Google model card: "The models employ a hybrid attention mechanism that interleaves local sliding window attention with full global attention, ensuring the final layer is always global." The NVIDIA NIM card confirms "sliding-window attention" and "30 layers"; an independent operator writeup describes "a hybrid attention architecture with 50 sliding-window layers and 10 global attention layers." llama.cpp issue #21831 explicitly names "Gemma-4-26B-A4B" as reproducing "forcing full prompt re-processing due to lack of cache data (likely due to SWA or hybrid/recurrent memory)." MLX olmlx issue #207: "Prompt caching is completely ineffective for Gemma 4 models (e.g. gemma-4-26b-a4b-it). Every request triggers a full prefill from scratch because trim_prompt_cache always returns 0." It fails requirement 1 on both stacks.

**Qwen3-30B-A3B-Instruct-2507 (primary) — confirmed full attention.** Causal MoE LM; 48 layers; GQA with 32 Q heads and 4 KV heads; 128 experts, 8 activated; RoPE; SwiGLU; no DeltaNet/SSM/sliding-window layers. This is the pre-hybrid Qwen3 generation and behaves like any standard full-attention transformer for KV-cache purposes.

**Mistral-Small-3.2-24B-Instruct-2506 (fallback) — confirmed full attention.** The published `config.json`: `"architectures": ["MistralForCausalLM"]`, `"num_hidden_layers": 40`, `"num_attention_heads": 32`, `"num_key_value_heads": 8`, and critically `"sliding_window": null`. Per the Hugging Face transformers implementation, explicitly setting `sliding_window` to null disables it entirely — so this is pure global full attention across all 40 layers, with no SWA edge case at all.

### Requirement 2: Comparable capability for NPC roleplay/instruction-following

Qwen3-30B-A3B's model card explicitly claims "Superior human preference alignment, excelling in creative writing, role-playing, multi-turn dialogues, and instruction following." A dedicated roleplay fine-tune (allura-org's Q3-30B-A3B-Designant) reports it "punched well above its weight class in terms of active parameters" with "minimal" repetition. Most directly on point: Qwen3 was the base model for a peer-reviewed NPC dialogue agent — Nuriyev et al., "Efficient Tool-Calling Multi-Expert NPC Agent for Commonsense Persona-Grounded Dialogue" (arXiv:2511.01720, Nov 3 2025) — which states "Using Qwen3 as the base model and Low-Rank Adaptation (LoRA) … our method ranked second overall" in the Sony-hosted CPDC 2025 shared task (Wordplay Workshop @ EMNLP 2025), delivering responses "in an average of 3 seconds (well under the 7-second limit) on L40S GPUs while utilizing less than 30GB of the available 48GB VRAM." This is essentially Chronicle's exact use case.

Mistral-Small-3.2-24B is a strong instruction-follower: per Mistral's model card (reported by VentureBeat, June 21 2025), WildBench v2 rose 55.60%→65.33% and Arena Hard v2 "more than doubled, jumping from 19.56% to 43.10%" over 3.1, internal instruction-following accuracy went 82.75%→84.78%, and the infinite-generation rate dropped 2.11%→1.29% (relevant for avoiding runaway NPC responses). It is more "neutral" in tone and slightly less roleplay-tuned than Qwen.

Capability tradeoff vs. the original pick: the older-generation Qwen3-30B-A3B scores below Qwen3.6-35B-A3B on hard agentic/coding benchmarks, but for NPC dialogue rendering — persona adherence, instruction following, multi-turn coherence — the gap is far smaller, and both remain in the same usable tier.

### Requirement 3: Throughput on M5 Pro 64GB

Memory footprint: Qwen3-30B-A3B MLX 4-bit occupies roughly 18–20 GB of weights, plus a modest KV cache (GQA with only 4 KV heads keeps this small). That leaves ample room in 64GB for a small resident TTS model. Because it is a 3.3B-active MoE, decode is bandwidth-cheap: measured same-class A3B-MoE rates on Apple Silicon span ~39 tok/s (Qwen3-Coder-30B via Ollama/llama.cpp on M4 Pro) to ~130 tok/s (Qwen3-Coder-30B via MLX on M4 Pro 64GB), with Qwen3.5-35B-A3B NVFP4 measured at ~64 tok/s on an M4 Pro. Apple's own M5 MLX writeup reports a 30B MoE processing a long prompt in under 3 seconds TTFT. The M5 Pro (confirmed by Apple at "up to 307 GB/s" unified memory bandwidth) will land well above the 15 tok/s decode floor — use MLX for best decode, llama.cpp for portability/layer flexibility.

Dense Mistral-Small-24B is heavier per token (all 24B parameters active every decode step), so its M5 Pro throughput will be materially lower than the MoE and closer to the 15 tok/s floor — usable but not fast. This is the price of its architectural certainty.

### Requirement 4: Confirmed automatic prefix-cache reuse for the recommended class

**llama.cpp — positive evidence.** Issue #23589 tests cache reuse across many models and states directly: "Other models (including Qwen3.6-27B, Qwen3.5-4B, Gemma dense/MoE/SWA) keep pos_min low enough that the threshold check passes and existing KV cache is reused normally. I was not able to reproduce it with the other models I tried." The same issue documents the full-attention warm-cache cliff you want to see: a repeated 17,614-token request went from 5,141 ms prefill (0 cached) to 88 ms prefill (17,610 cached — 99.98%). The cross-model "miss" table shows dense/MoE full-attention models recomputing only 12–16 tokens per turn, versus 4,108 for the hybrid Qwen3.6-35B-A3B. The reuse pathway is intact for the full-attention class; only the hybrid breaks.

**MLX — positive evidence.** Issue #980 (ml-explore/mlx-lm) states the scope explicitly: "Prompt prefix caching — the mechanism that reuses computed KV states across requests sharing a common prefix — only works for pure full-attention models. Any model using sliding window attention, Mamba/SSM layers, or mixed attention types silently falls back to full prompt recomputation on every request." The same issue benchmarks a pure full-attention MoE (MiniMax M2.5): cold 29.33 s → warm 2.79 s (10.5×), classified "Works."

**Qwen3-32B corroboration.** An llm-d benchmark (on vLLM) shows the dense full-attention Qwen3-32B TTFT dropping from 4.3 s to 0.6 s on a repeated ~10,000-token prompt — confirming the full-attention Qwen3 generation is prefix-cache-friendly at the architecture level.

The honest gap: I did not find a log naming "Qwen3-30B-A3B" by name with cache-hit counters on llama-server/mlx_lm.server specifically. The evidence is (a) the confirmed architectural rule (pure full-attention = works), (b) same-class dense/MoE examples empirically working on both stacks, and (c) a Qwen3-32B warm-TTFT benchmark. All three point the same way. Recommendation 2 closes this residual gap with a 5-minute test.

## Recommendations

1. **Adopt `Qwen/Qwen3-30B-A3B-Instruct-2507` (4-bit MLX for max decode, or Q4_K_M GGUF for portability) as the conversation-tier model.** It satisfies requirement 1 unambiguously, matches the roleplay/instruction-following need (with a published NPC-dialogue precedent), and its MoE efficiency gives throughput headroom for the shared-prefix architecture.

2. **Verify cache reuse empirically before locking in — do this first, it takes five minutes.**
   - **llama.cpp:** Launch `llama-server` with `--slots`, send the world-rules + cell + rider prefix twice with different final turns, and inspect the response `timings.cache_n` and `prompt_tokens_details.cached_tokens`. Expect `cached_tokens ≈ shared-prefix length` on the second call and a large prefill-time drop. Confirm you do NOT see "forcing full prompt re-processing" in the logs.
   - **MLX:** Run `mlx_lm.server`, issue the same two requests, and confirm `cached_tokens > 0` on the warm request. Use the plain instruct checkpoint; avoid engines that call `mx.clear_cache()` after every request (mlx-vlm issue #999) and avoid any MTP speculative-decoder variant on multi-turn (mlx-lm issue #1292 shows 1-token truncation when a system prompt is reused with a different user turn).

3. **Threshold that flips the decision:** If the empirical test shows `cached_tokens = 0` or persistent full re-prefill on the plain Qwen3-30B-A3B instruct checkpoint (which the architecture says should not happen), fall back to **`mistralai/Mistral-Small-3.2-24B-Instruct-2506`**, whose `sliding_window: null` removes even the SWA edge case. Accept the lower decode throughput as the cost of certainty.

4. **Pin your llama.cpp build and re-test after upgrades.** Issue #23589 documents a narrow regression (build b9235; last good b9222) where even full-attention reuse dropped one batch's worth of tokens per turn. Pin to a known-good build and re-run the Recommendation 2 verification after any bump.

5. **Keep the shared prefix byte-stable and put the rider at the END of it.** Prefix reuse depends on an identical leading token sequence; any change at the start of the prompt (even whitespace or an attribution block — the documented "Claude Code cache killer") forces full recompute. Maintain the exact order: world rules → location/cell state → per-NPC rider → conversation turns, and never mutate earlier segments once cached.

## Caveats

- **No by-name cache-hit log for Qwen3-30B-A3B specifically.** The recommendation rests on the architectural rule plus same-class empirical evidence (Qwen3.6-27B dense, Qwen3.5-4B dense, Gemma MoE on llama.cpp; MiniMax MoE on MLX; Qwen3-32B on vLLM), not a benchmark naming this exact checkpoint. The verification step in Recommendation 2 exists precisely to close this — do not skip it.
- **Naming hazard.** "Qwen3-30B-A3B" (full attention, recommended) and "Qwen3.5-35B-A3B" / "Qwen3.6-35B-A3B" (hybrid Gated DeltaNet, blocked) are one keystroke apart and all are "A3B MoE." Download exactly `Qwen/Qwen3-30B-A3B-Instruct-2507`. Any model whose card mentions "Gated DeltaNet," "linear attention," "SSM," "Mamba," or "sliding window" is disqualified — confirm from the card, never from the name.
- **The upstream llama.cpp hybrid fix is still fork-only.** This is why we switch models rather than wait; do not assume a master merge has landed.
- **Qwen3-30B-A3B is the older Qwen3 generation** and is genuinely less capable than Qwen3.6-35B-A3B on hard agentic/coding tasks. For NPC dialogue this is an acceptable trade; if dialogue rendering later demands stronger reasoning, re-evaluate against newer *full-attention* releases (re-confirming architecture each time).
- **Some MLX serving front-ends carry their own cache bugs** unrelated to model architecture (clearing Metal cache each request; MTP-variant truncation). Choose the plain instruct checkpoint and a server that persists KV cache across requests.
- **Throughput figures are triangulated from same-class models, not the exact instruct checkpoint on an M5 Pro.** The ~39–130 tok/s range spans Ollama/llama.cpp vs. MLX and M4-class hardware; treat the M5 Pro number as "comfortably above 15 tok/s" pending your own measurement, not as a precise guarantee.

## Filing note

See report 45's filing note for a side-by-side comparison table against Gemini's independent
pick (Qwen2.5-32B-Instruct, dense). Both reports agree on disqualifying Qwen3.6-35B-A3B and
Gemma-4-26B-A4B; they diverge on the replacement. This report's MoE pick has better cited
throughput and a directly-relevant published NPC-dialogue benchmark; report 45's dense pick is
a more conservative, longer-established model. Neither report found a cache-hit log naming its
own recommended checkpoint by name — both prescribe the same 5-minute empirical verification
(`cached_tokens` on a repeated-prefix request) before committing. Do that test on both
candidates before deciding; a third independent pass (Kimi) on this same brief may also help.
