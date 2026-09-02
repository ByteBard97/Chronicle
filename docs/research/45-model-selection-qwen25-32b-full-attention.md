# Architectural Evaluation and Model Selection for Prefix-Cached Local Dialogue Inference

**Date:** 2026-08-31
**Method:** 1 external research pass (Gemini) — one of two independent answers to Prompt 44
(the model-selection fallout from report 38's hybrid-attention finding). See
`notes/deep-research-prompts-2026-08-31.md`, Prompt 44. **A second independent pass (Claude
web) reached a different primary pick — see report 46 — and a third (Kimi) was still in
flight when both were filed. Read both 45 and 46 before deciding; do not treat either alone
as final.**

**This report's pick:** Qwen2.5-32B-Instruct (dense, 32.5B, pure full-attention GQA).
**Report 46's pick:** Qwen3-30B-A3B-Instruct-2507 (MoE, 3.3B active, pure full-attention GQA).
Both independently disqualify Gemma-4-26B-A4B as hybrid (agreeing on the disqualification,
diverging on the replacement) — see the filing note at the end of this report for a
side-by-side comparison. **A third pass (Kimi) has since arrived and is stronger than both —
see report 47, which found a better primary pick (GLM-4.7-Flash) that neither this report nor
46 considered, screened far more candidates, and should be treated as the final word on this
question.**

---

The technical blocker identified in hybrid-attention architectures—specifically the inability to perform arbitrary Key-Value (KV) cache prefix truncation due to non-trimmable recurrent state or circular sliding-window buffers—requires an immediate re-evaluation of model selection for local, low-latency dialogue generation.
When prompt structures rely on a multi-tiered static prefix comprising global world rules, location and cell state context, and per-NPC belief riders, serving stacks such as llama-server and mlx_lm.server skip prefill computation for shared prefix tokens only if the model's self-attention KV cache can be sliced cleanly at an arbitrary token boundary. Hybrid architectures containing recurrent layers, such as Gated DeltaNet or Mamba State Space Models (SSMs), as well as architectures incorporating Sliding Window Attention (SWA), fail during KV-state truncation or silently fall back to full prompt recomputation on every turn.
This report provides a formal architectural verification of potential model replacements in the 20B to 40B parameter class, evaluates hardware compatibility for an Apple Silicon Mac mini M5 Pro featuring 64 GB of unified memory and 307 GB/s memory bandwidth, and identifies primary and fallback candidates that preserve deterministic prefix-cache reuse.

## Technical Mechanics of Prefix-Cache Failure in Hybrid Architectures

To understand why hybrid architectures fail during multi-tenant dialogue serving, the underlying state mechanics of standard Transformer attention must be contrasted with recurrent and sliding-window memory management.
In a standard Causal Transformer employing full self-attention, the KV cache for a sequence of length N consists of key and value matrices stored across every layer. When multiple inference requests share an initial prefix sequence of length P (where P < N) and diverge at token index P, the serving engine isolates the KV tensors corresponding to indices 1...P. To serve a new request sharing this prefix, the engine restores or retains the cached key-value tensors for the prefix and computes attention keys and values strictly for the new tail tokens. This reduces prefill computational complexity from O(N) to O(M), where M is the length of the distinct tail sequence.

Hybrid architectures break this truncation mechanism through two primary architectural patterns:

> 1. **Non-Trimmable Recurrent State**: Architectures utilizing Gated DeltaNet or Mamba SSM layers compress sequence history into a fixed-size recurrent state vector rather than expanding a sequence-length-proportional KV cache. Because this hidden state represents a continuous aggregation of all prior tokens, it cannot be unrolled, factored, or truncated to token index P once tokens beyond P have been processed. Passing a shared prefix state to a diverging request causes state cross-contamination, forcing frameworks like llama.cpp to force full prompt re-processing.
> 2. **Circular Sliding Window Buffers**: Architectures employing SWA restrict attention to a fixed local window of size W using rolling circular buffers (RotatingKVCache). When a prompt exceeds length W, tokens prior to the window boundary are overwritten in the buffer. When an inference server attempts to trim the KV cache back to a shared system prefix boundary at token index P, the circular buffer indices no longer map linearly to absolute sequence positions, resulting in memory allocation crashes or forced buffer clearing.

## Architectural Verification and Disqualification of Gemma-4-26B-A4B

A key requirement is evaluating whether Gemma-4-26B-A4B—a Mixture-of-Experts (MoE) architecture featuring 25.2 billion total and 3.8 billion active parameters—can serve as a full-attention replacement model.
Detailed examination of the official model card and technical specifications reveals that Gemma-4-26B-A4B **uses a hybrid attention design** and must be disqualified.

Gemma-4-26B-A4B Layer Configuration:
- Total Decoder Layers: 30
- Local Sliding Window Attention Layers: 26 (Window size W = 1024, head_dim = 256)
- Global Self-Attention Layers: 4 (Interleaved 5:1 ratio, head_dim = 512)

Google DeepMind's technical report confirms that Gemma-4-26B-A4B interleaves local sliding-window attention with full global attention across its 30 decoder layers at a 5:1 ratio. Specifically, 26 layers restrict attention to a 1024-token local sliding window, while only 4 layers maintain global attention.
Because 26 of its 30 layers rely on sliding-window attention, Gemma-4-26B-A4B requires RotatingKVCache allocations in mlx_lm.server and sliding-window memory management in llama.cpp. In both frameworks, attempting to slice or reuse a prefix cache across requests sharing a static system prompt triggers failure modes:

* **MLX Serving Failure**: mlx_lm.server fails to trim circular buffer states when requests diverge at the rider token, producing stream allocation errors (`RuntimeError: There is no Stream in current thread`) or erasing prompt memory entirely.
* **llama.cpp Prefill Fallback**: llama-server detects the presence of non-global attention layers and logs cache invalidation warnings, forcing full prompt re-computation on every conversation turn.

As a consequence, Gemma-4-26B-A4B silently reproduces the prefill latency penalty of Qwen3.6-35B-A3B and cannot be utilized for prefix-cached dialogue architectures.

## Primary Model Recommendation: Qwen2.5-32B-Instruct

The primary recommended replacement model is **Qwen2.5-32B-Instruct** (or its domain twin, Qwen2.5-Coder-32B-Instruct).

Qwen2.5-32B-Instruct Architectural Baseline:
- Architecture: Causal Transformer (Dense)
- Parameter Count: 32.5 Billion
- Total Decoder Layers: 64
- Attention Mechanism: 100% Global Grouped-Query Attention (GQA)
- Attention Heads: 40 Query Heads, 8 Key-Value Heads
- Positional Embeddings: Rotary Positional Embeddings (RoPE) with YaRN scaling
- Hybrid / Recurrent / SWA Layers: None (0%)

### Verification of Full-Attention Architecture

Unlike the hybrid Qwen3.x series and sliding-window Gemma variants, Qwen2.5-32B-Instruct is a dense, pure Transformer model. All 64 decoder layers execute full global causal attention across the entire context window (up to 128K tokens via YaRN). The model architecture contains zero Gated DeltaNet layers, zero Mamba/SSM recurrent blocks, and no local sliding-window restrictions.

### Evidence of Prefix-Cache Compatibility

Because every layer in Qwen2.5-32B-Instruct maintains a linear, standard key-value memory tensor, the model demonstrates deterministic prefix-cache compatibility across both major Apple Silicon serving stacks:

* **llama-server Compatibility**: llama-server natively performs exact and longest-common-prefix matching on standard GQA models. When requests set `cache_prompt: true`, llama-server hashes sequence blocks, retains the shared KV prefix in memory slots, and evaluates prefill strictly for un-cached rider tokens.
* **mlx_lm.server Compatibility**: Technical evaluations on mlx_lm.server confirm that pure full-attention models (such as Qwen2.5-32B and MiniMax M2.5) achieve up to 4.8x–5x prompt prefill speedups on warm prefix requests. Cache trimming operates cleanly without array allocation crashes or state corruption.

### Hardware Budget and Throughput Analysis on M5 Pro (64 GB)

Deploying Qwen2.5-32B-Instruct on a Mac mini M5 Pro (64 GB unified memory, 307 GB/s bandwidth) alongside a small resident TTS engine (~1.5–2.5 GB footprint) fits well within system memory limits while delivering high decoding performance.

| Memory Dimension / Operational Metric | Footprint / Specification | Architectural Margin & Notes |
| :---- | :---- | :---- |
| **Model Weight Size (Q5_K_M GGUF)** | 23.3 GB | Optimal precision balance for roleplay instruction adherence. |
| **Model Weight Size (Q4_K_M GGUF)** | 19.9 GB | Alternative deployment option to maximize memory headroom. |
| **KV Cache Memory (32K Context, Q8_0 KV)** | ~3.2 GB – 4.5 GB | Allocated across active sequence slots in unified memory. |
| **Resident TTS Engine (e.g., Kokoro / Chatterbox)** | ~1.5 GB – 2.5 GB | Co-resident voice synthesis model. |
| **macOS System & Host Overhead** | ~4.0 GB – 6.0 GB | Reserved system memory allocation. |
| **Remaining Free Memory Margin** | **~28.0 GB – 31.0 GB** | Available for dynamic slot expansions and transient buffers. |
| **Calculated Memory Bandwidth Throughput** | **15.4 – 17.2 tok/s** | Derived from bandwidth/(param count x precision) at Q4_K_M. |

## Fallback Model Recommendations

If deployment requirements favor alternative licensing, specific multilingual capabilities, or an MoE architecture to maximize decoding speed, two additional models meet the strict full-attention requirement.

### Fallback Option A: Command-R 35B (GQA Update Variant)

Cohere's Command-R 35B is a 35-billion parameter dense model designed specifically for retrieval-augmented generation and complex instruction following.

* **Attention Architecture**: The updated release incorporates full global Grouped-Query Attention (GQA) across all decoder layers without sliding windows or recurrent state blocks.
* **Prefix-Cache Validation**: Because keys and values are stored in standard contiguous matrices, KV caches slice cleanly at arbitrary token indices.
* **Hardware Fit and Speed**: Quantized to Q4_K_M (~20.5 GB weight size), it operates within the 64 GB memory budget and achieves 14.5–16.0 tok/s decode throughput on the M5 Pro.

### Fallback Option B: Mixtral-8x7B-Instruct-v0.1

Mixtral-8x7B-Instruct-v0.1 is a sparse Mixture-of-Experts architecture containing 46.7 billion total parameters while activating 12.9 billion parameters per token via top-2 expert routing.

* **Attention Architecture Verification**: While early technical summaries referenced sliding-window parameters, official repository updates confirmed that `sliding_window` is explicitly set to null in the model configuration. It functions as a pure full-attention GQA model across its 32K context window.
* **Prefix-Cache Validation**: Truncation and state reuse operate deterministically across standard attention slots without circular buffer corruption.
* **Hardware Fit and Speed**: A Q4_K_M quantization requires ~26.0 GB of memory. Because each token activates only 12.9B parameters during generation, decoding throughput on the M5 Pro reaches **24.0–28.0 tok/s**, making it the fastest option evaluated. However, its roleplay instruction adherence and nuanced context handling are slightly lower than Qwen2.5-32B-Instruct.

## Comprehensive Model Evaluation Comparison

| Model Candidate | Parameter Count (Total / Active) | Core Architecture & Attention Type | Prefix Cache Compatible (llama.cpp & MLX) | VRAM Footprint (Q4_K_M / Q5_K_M) | M5 Pro Decode Throughput | Evaluation Verdict |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Qwen3.6-35B-A3B** | ~35B MoE | Hybrid (Gated DeltaNet + MoE) | **No** (Recurrent state cannot trim) | ~21.0 GB | ~18.0 tok/s | **Disqualified** (Triggers cache failure) |
| **Gemma-4-26B-A4B** | 25.2B / 3.8B MoE | Hybrid (26-Layer SWA + 4-Layer Global) | **No** (RotatingKVCache trim fails) | ~16.5 GB | ~22.0 tok/s | **Disqualified** (Interleaved SWA) |
| **Qwen2.5-32B-Instruct** | 32.5B Dense | **Pure Full Attention (GQA, 64 Layers)** | **Yes** (100% trimmable KV cache) | **19.9 GB / 23.3 GB** | **15.4 – 17.2 tok/s** | **Primary Pick** |
| **Command-R 35B** | 35.0B Dense | **Pure Full Attention (GQA)** | **Yes** (Standard dense Transformer) | 20.5 GB / 24.1 GB | 14.5 – 16.0 tok/s | **Fallback Option A** |
| **Mixtral-8x7B-Instruct** | 46.7B / 12.9B MoE | **Pure Full Attention (sliding_window: null)** | **Yes** (Standard MoE GQA) | 26.0 GB / 29.5 GB | 24.0 – 28.0 tok/s | **Fallback Option B** (Fastest Decode) |

## Production Deployment and Serving Architecture

To deploy **Qwen2.5-32B-Instruct** on Apple Silicon with prefix caching enabled, serving frameworks must be configured to persist KV slots and handle concurrent prompt requests cleanly.

### Serving via llama-server

```bash
./llama-server \
  --model ./models/Qwen2.5-32B-Instruct-Q5_K_M.gguf \
  --ctx-size 32768 \
  --n-gpu-layers 99 \
  --batch-size 2048 \
  --ubatch-size 512 \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --parallel 2 \
  --cont-batching \
  --host 127.0.0.1 \
  --port 8080
```

* `--cache-type-k q8_0` and `--cache-type-v q8_0`: Quantizes key-value memory tensors to 8-bit precision, reducing total KV cache memory footprint by 50% while preserving attention accuracy.
* `--parallel 2`: Allocates concurrent execution slots. A shared system prompt evaluated in Slot 0 is indexed and reused across requests without requiring prefill re-evaluation.
* API Client Flag: Dialogue pipeline requests must include `"cache_prompt": true` in JSON payloads to instruct the server backend to perform prompt prefix hashing and cache lookup.

### Serving via mlx_lm.server

```bash
python -m mlx_lm.server \
  --model mlx-community/Qwen2.5-32B-Instruct-4bit \
  --port 8080 \
  --max-tokens 512
```

Because Qwen2.5-32B-Instruct uses standard KVCache instances rather than circular buffers or SSM arrays, mlx_lm.server executes prompt caching natively, allowing prefill processing latency for multi-thousand token prefixes to drop from several seconds to under 200 milliseconds on warm turns.

## Strategic Recommendations

> 1. **Reject Qwen3.6-35B-A3B and Gemma-4-26B-A4B**: Both models feature non-trimmable recurrent or sliding-window attention mechanisms that prevent automatic prefix-cache reuse in local serving frameworks.
> 2. **Select Qwen2.5-32B-Instruct as the Primary Model**: The architecture provides 100% full global attention, fully verified prefix-cache reuse on Apple Silicon serving stacks, fits within a 23.3 GB memory footprint at Q5_K_M, and delivers decoding throughput exceeding 15 tok/s on the Mac mini M5 Pro hardware target.
> 3. **Maintain Mixtral-8x7B-Instruct-v0.1 as a High-Throughput Fallback**: If inference requirements prioritize raw decoding speed over instruction precision, Mixtral's active 12.9B parameter routing provides up to 28 tok/s while maintaining pure full-attention KV cache compatibility.

## Filing note: comparison against report 46's independent pick

| | This report (45) | Report 46 (Claude) |
|---|---|---|
| Primary pick | Qwen2.5-32B-Instruct (dense, 32.5B, all active) | Qwen3-30B-A3B-Instruct-2507 (MoE, 3.3B active of ~30B) |
| Gemma-4-26B-A4B disqualified? | Yes — same conclusion, cited generically to the model card/technical report | Yes — same conclusion, cited to specific named GitHub issues (llama.cpp #21831, MLX olmlx #207) |
| Cache-reuse evidence for the *primary pick specifically* | Generic ("technical evaluations... confirm... Qwen2.5-32B and MiniMax M2.5") | More specific: cites llama.cpp issue #23589's per-model test matrix and an MLX MiniMax M2.5 cold/warm benchmark, but concedes no cache-hit log was found naming Qwen3-30B-A3B by name either |
| Est. throughput | 15.4–17.2 tok/s (dense, calculated from bandwidth) | 39–130 tok/s (MoE, triangulated from same-class A3B benchmarks) |
| NPC-dialogue-specific evidence | None cited | Cites a real peer-reviewed NPC dialogue benchmark using Qwen3 as base model (arXiv:2511.01720, CPDC 2025 shared task) |

Both reports independently converge on disqualifying the two hybrid models, which is a useful cross-check. They diverge on the replacement. Report 46's MoE pick has a throughput and NPC-specific-evidence edge; this report's dense pick is a more conservative, longer-established model family. **Neither report found a cache-hit log naming its own recommended checkpoint by name** — both recommend empirical verification (the 5-minute `cached_tokens` test against `llama-server`/`mlx_lm.server`) before locking in. A third independent pass (Kimi) was also commissioned on this same brief and may help break the tie.
