# Home-Server Hardware Allocation, Model Sizing, and TTS Architecture — Session Notes

**Date:** 2026-09-15
**Method:** 1 session pass (Claude Code, interactive conversation with the project owner,
2026-09-15) — planning discussion covering headless Mac mini setup, KV-cache/context
economics for the confirmed GM model, 4-machine hardware allocation, and TTS placement.
Not a commissioned external research pass like most other reports in this index; treat
citations to secondary web sources below with the same skepticism this project applies
elsewhere, and treat this report itself as provisional until validated against real
hardware. Cross-references and partially corrects/extends reports 34, 38, and 40.

---

## TL;DR

- **The GM model is confirmed: Qwen3.5-122B-A10B** (122B total / 10B active MoE, Apache
  2.0, native 262,144-token context). It is a **hybrid Gated DeltaNet + MoE architecture**
  (48 layers, 3:1 linear:full-attention ratio) — the same architectural family as the
  model report 38 found breaks cross-conversation prefix caching. This was not previously
  flagged against this specific model in report 34's table.
- **Target GM context: 120,000 tokens (~3GB KV budget)**, not the full 262K native
  window — chosen because effective long-context recall degrades before the nominal
  window fills regardless of architecture, so the extra window wouldn't buy proportional
  value, and the smaller target leaves more memory for concurrent NPC sessions.
- **The hybrid architecture's cheap per-token KV cost (~25KB/token, only 12/48 layers grow
  with context) also makes concurrent NPC sessions far cheaper than the generic
  full-attention estimate** — roughly 100MB/session instead of 500-600MB, meaning 30-60
  NPCs could plausibly stay resident in RAM simultaneously on a few GB of budget. This
  significantly weakens memory as an argument against using one model for both GM and NPC
  roles; the remaining open question is per-NPC-turn latency, not memory.
- **Whole-session KV state save/restore to SSD should work fine even on this hybrid
  architecture** (distinct from the broken cross-conversation prefix-sharing mechanism) —
  a way to support more NPCs than fit resident at once, at a real but modest
  (hundreds-of-ms) reload cost instead of a full multi-second reprocess.
- **TTS placement settled on the RTX 5080 box** (the machine running Skyrim + the
  agentic harness), not the Mac mini, the 12GB Windows/Linux box, or the MacBook — because
  audio playback happens locally where the game runs (only text crosses the network),
  and it sidesteps a real Metal/MLX-specific GPU-driver lockup risk documented in report
  40 that doesn't apply to CUDA.
- **Realistic GM throughput estimate: ~20-25 tokens/sec** on the M5 Pro (307GB/s memory
  bandwidth, Apple's published spec), extrapolated from sibling-model MLX benchmarks —
  not measured. This comfortably clears the ~3-5 tok/s needed to keep pace with spoken
  dialogue once using a sentence-streamed TTS pipeline; **time-to-first-token, not
  steady-state throughput, is the metric that actually governs perceived NPC
  responsiveness.**

---

## 1. Hardware inventory

Four machines are available, with a settled division of labor:

| Machine | Specs | Role |
|---|---|---|
| Mac mini M5 Pro | 64GB unified memory, 307GB/s bandwidth (Apple official spec), headless/closet-mounted | GM model (Qwen3.5-122B-A10B), possibly the NPC model too pending the single-vs-two-model decision below |
| Windows/Linux dual-boot box | 12GB NVIDIA GPU | NPC model candidate host, if a separate smaller model is used |
| Linux gaming rig | Big AMD CPU, RTX 5080 (16GB, 960GB/s bandwidth), 64GB RAM | Runs Skyrim itself + the agentic harness; **also now hosts TTS** (see §5) |
| MacBook Pro M4 | 24GB unified memory | Owner's daily driver — explicitly **not** part of the serving pipeline; too unreliable as an always-on host given how it's actually used day to day |

The Mac mini is intended to run headless (no monitor). Setup notes from earlier in this
session, not yet written into any other doc:
- Use an $8-10 HDMI dummy plug for stable headless operation (EDID emulation).
- The GPU/Metal memory ceiling, not disabling the GUI, is the main memory lever — see §4.
- `mdutil -i off` on the models directory (Spotlight indexing large GGUF/safetensors
  files wastes CPU/disk I/O continuously); exclude models from Time Machine; disable
  iCloud/Photos/Siri sync; `pmset` for no-sleep + autorestart after power loss.
- **Active cooling was investigated and explicitly ruled unnecessary.** Chronicle's LLM
  usage is bursty/intermittent (DM + NPCs taking turns, not sustained inference), and
  multiple sources indicate LLM token generation is memory-bandwidth-bound with minimal
  measured thermal throttling in that regime (unlike sustained video-export/rendering
  workloads, which is where the commonly-cited "20-30% throttling after 10 minutes"
  figures actually originate). Do not re-litigate this without a specific new reason —
  it was researched carefully and closed.

## 2. GM model: Qwen3.5-122B-A10B

Confirmed via direct verification (not previously locked down in report 34, which lists
it in the S-tier table without flagging its architecture): **hybrid Gated DeltaNet + MoE**,
48 layers arranged as 12 × (3 × (Gated DeltaNet → MoE) → 1 × (Gated Attention → MoE)) — i.e.
36 linear-attention layers, 12 full-attention layers. 256 experts, 8 routed + 1 shared,
10B active parameters per token. Apache 2.0. Native context 262,144 tokens, extensible to
1,010,000.

**This matters because it's the same architectural family report 38 found breaks
cross-conversation prefix-cache reuse** on both llama.cpp and MLX (the recurrent state
"can't be split at an arbitrary token boundary"). Report 38 was about a different model
(Qwen3.6-35B-A3B); this is a new, not-yet-independently-verified inference that the same
limitation likely applies to Qwen3.5-122B-A10B given the identical layer pattern. **Action
item: confirm this empirically once the model is running** (watch server logs for "forcing
full prompt re-processing" on llama.cpp, or the MLX equivalent) rather than assuming.

Weight size at 3-bit quantization: not directly measured, estimated at **~50-55GB**
(scaled down from report 34's cited ~70GB Q4 figure). This is why 3-bit was chosen over
Q4 — Q4 alone likely doesn't fit a 64GB Mac mini with any headroom at all.

## 3. Context length and KV cache economics

Because only 12 of 48 layers grow their KV cache with context length (the other 36 keep a
fixed-size recurrent state regardless of sequence length), this architecture's memory cost
per token of context is dramatically lower than a standard transformer.

Reference figure (from the closely related sibling model Qwen3-Next-80B, same 48-layer/3:1
architecture — **not a confirmed measurement of Qwen3.5-122B-A10B itself**, treat as a
planning estimate pending real config-file verification): **~25GB KV cache for 1,000,000
tokens ≈ 25KB/token**, not perfectly linear (fixed recurrent-state baseline plus linear
growth from the attention layers, more accurate at longer contexts).

| KV budget | Approx. context |
|---|---|
| 3GB | ~120,000 tokens |
| 6GB | ~240,000 tokens (~full 262K native window) |
| 8GB | ~320,000 tokens |

**Decision: target 120,000 tokens (~3GB) for the GM's working context**, not the full
native 262K window. Rationale: effective long-context recall degrades well before the
nominal window fills regardless of architecture (the "lost in the middle" effect is
observed broadly across transformer-family models; no strong reason to assume this hybrid
is immune), so chasing the full native window wouldn't yield proportional value, and the
smaller target leaves substantially more memory headroom for other uses.

**Same math applied to NPC sessions**: a generic full-attention estimate used earlier in
this session assumed ~100-150KB/token, giving ~500-600MB per NPC session. At this model's
actual ~25KB/token, a single NPC session costs closer to **~100MB**. A 3GB budget set
aside for concurrent "hot" NPC sessions could therefore support **roughly 30-60 NPCs
resident in RAM simultaneously** — almost certainly more than would ever be on-screen at
once in a given scene. This meaningfully weakens the case that memory pressure from many
concurrent NPCs is a reason to avoid using one model for both GM and NPC roles (see §6).

## 4. Increasing usable GPU memory on macOS

The default macOS GPU/Metal memory ceiling is roughly 66-75% of total RAM, not the full
amount — this, not the OS/GUI overhead itself (which is only 1-4GB headless), is the real
lever for fitting a large model:

```
sudo sysctl iogpu.wired_limit_mb=58368   # ~57GB, leaving ~7GB for the OS on a 64GB machine
```

- Runtime-only; resets on reboot — set it via a LaunchDaemon at boot, alongside whatever
  daemon launches the model server.
- General guidance leaves 8-16GB of headroom; given this machine will be headless with
  minimal background services, real overhead may be closer to 2-4GB, potentially allowing
  a more aggressive ceiling — but increase incrementally and monitor for memory pressure
  rather than assuming the aggressive number is safe.

At ~50-55GB estimated model weight size, a ~57-58GB ceiling leaves roughly 3-8GB for KV
cache across the GM's context (§3) and any resident NPC sessions (§3) — tight, but
workable at the 120K-token GM context target.

## 5. TTS: model choice and placement

### Model landscape (all permissively licensed — Apache 2.0 or MIT, compatible with
Chronicle's AGPL-3.0):
- **Orpheus TTS** (3B, Apache 2.0) — highest quality/emotional range, heaviest
- **Chatterbox / Chatterbox-Turbo** (350M, MIT) — low-latency, good for co-locating with
  an LLM on shared/constrained hardware
- **Kokoro-82M** (Apache 2.0) — tiny, native MLX support (`kokoro-mlx`, `mlx-audio`)
- **OpenVoice v2** (MIT) — decouples voice timbre from speaking style: clone once, drive
  many emotional deliveries from that one clone
- **Qwen3-TTS** (Apache 2.0, Base/CustomVoice/VoiceDesign variants, 0.6B/1.7B) — **the
  owner's own hands-on testing found this gives good results with well-chosen zero-shot
  clone clips; this is the practical front-runner**, ahead of the above list which was
  compiled before that testing.

Report 40 (filed 2026-08-31, predates this session) already covers Qwen3-TTS and
Chatterbox-Turbo on Apple Silicon/MLX in real depth and should be read alongside this
report, not duplicated here. Key facts from it that shaped this session's decisions:
- **A real Metal/MLX-specific GPU-driver lockup risk exists**: concurrent independent MLX
  processes issuing `generate(stream=True)` can hang the GPU driver indefinitely (not
  crash — hang). Report 40's mitigations: single-process async architecture with a global
  inference queue, cross-process mutex locking, or a dedicated serialized server process.
  This is a bigger risk than memory fit for co-locating TTS with an LLM on Apple Silicon
  specifically.
- Qwen3-TTS/Chatterbox's inline emotion/paralinguistic tags (`[laugh]`, `[sigh]`,
  `[Angry]`, etc., switching per-sentence within one generation call) are reportedly
  **already compatible with an existing "engine-neutral annotation schema"
  (`tools/annotate/schema.py`) in a "sibling project"** not accessible from this repo —
  worth locating if that project becomes reachable, since it may mean this tag-driven
  delivery design is already a settled decision elsewhere rather than something to
  design from scratch.
- Model footprints range from ~808MB (aggressively pruned 4-bit 0.6B) to ~8GB (1.7B fp16)
  on the MLX path specifically — the CUDA-native PyTorch implementation's footprint is
  **not** covered by report 40 and hasn't been characterized for this project.

### Placement decision

Considered and ruled out, in order:
1. **Mac mini (co-located with GM)** — technically fits on memory, but inherits the
   Metal GPU-driver lockup risk above for no compensating benefit once GM turns are
   understood to be latency-tolerant (see §6).
2. **Windows/12GB box (co-located with NPC model, if a separate NPC model is used)** —
   sidesteps the Metal-specific risk (CUDA doesn't have it) and matches "co-locate LLM+TTS
   for latency," but 12GB VRAM shared between an NPC LLM and a TTS model is not
   comfortably confirmed to fit; would need real numbers per whichever NPC quant is
   chosen.
3. **MacBook Pro M4 (this session's assistant's own machine)** — technically the easiest
   fit (24GB, and report 40's MLX benchmarks were measured on M1-M4 hardware, a better
   match than the M5 Pro they were originally scoped for) but rejected: it's the owner's
   daily driver, not a fixed always-on home-network machine, making it an unreliable
   foundation for a real-time pipeline.
4. **Settled: the RTX 5080 machine** (runs Skyrim + the agentic harness). The decisive
   reason not present in any of the other options: **audio playback happens locally where
   the game runs**, so only text — not audio, which is much heavier — ever needs to cross
   the network. It also sidesteps the Metal-specific driver risk entirely (CUDA), and the
   load shape (small model, short bursts, long idle gaps) is much closer to how the game
   itself behaves than to a sustained-decode LLM workload, unlike the earlier (correct)
   advice against putting a full LLM on the gaming GPU.

**Not yet verified, flagged for real hardware testing**: actual VRAM headroom against the
owner's real Skyrim mod list (modded texture packs can consume anywhere from a few GB to
well over half of 16GB), real frame-time impact during a TTS synthesis burst mid-game, and
the CUDA-native (not MLX-port) memory footprint for Qwen3-TTS, which no existing report
covers.

### Latency pipeline design (applies regardless of final model/placement choices)

- **Stream/pipeline, don't serialize**: dispatch completed sentences/clauses to TTS as the
  LLM generates them, rather than waiting for the full response — the single biggest
  latency win.
- Chunk on sentence/clause boundaries, not words — word-level chunking breaks prosody.
- Prefer a smaller, streaming-capable TTS model when it must share a GPU with an LLM.
- No network hop between the LLM output and its own machine's local TTS — already ensured
  by the RTX 5080 co-location decision above for whichever model speaks through it.
- Mask any residual gap with a short filler sound (a common voice-assistant trick).
- Consider speculative pre-synthesis for predictable/scripted lines, where applicable.

## 6. Open question: one model for both GM and NPCs, or two?

**Not decided — contingent on real hardware benchmarking.** Restated with the numbers
from this session:

**In favor of one model (Qwen3.5-122B-A10B) for everything:**
- Report 34 ranks it S-tier for RP/roleplay quality — using it for NPCs would likely be a
  quality upgrade over a dedicated smaller model, not a compromise.
- 10B active parameters means decode speed tracks roughly like a 10B model, not the full
  122B — much faster than the raw parameter count suggests.
- §3's KV-cache economics substantially weaken the "too much memory for many concurrent
  NPCs" concern — that's no longer a strong argument against this option.
- Eliminates the entire multi-machine LLM-hosting split; one model, one machine.

**Against, or at least unresolved:**
- **Per-NPC-turn latency**: a purpose-built smaller/faster model (report 34 calls
  Qwen3.6-35B-A3B, 3B active, "the speed champion for concurrent streams") would still be
  faster per turn than a shared 10B-active model, even though the 10B-active model is
  itself reasonably fast. Whether this difference actually matters for felt
  responsiveness is unresolved — see §7's point that TTFT, not raw throughput, is what
  drives perceived responsiveness, which may make this concern smaller in practice than
  it first appears.
- **Prefix-cache breakage** (§2) may apply equally whether NPCs use their own model or
  share the GM's — this isn't actually a point in favor of splitting, since a hybrid NPC
  model (if one were chosen from the same family) would have the same limitation.

**If the single-model hypothesis is chosen and works out**, the Windows/12GB box becomes
genuinely free — not inheriting TTS either, since that's now slated for the RTX 5080 box.
It could serve as a backup NPC host for scaling beyond one Mac mini instance's concurrent
capacity, a dev/test machine, or simply not be part of Chronicle's pipeline at all.

**Recommended next step**: benchmark Qwen3.5-122B-A10B directly for NPC-shaped short-turn
latency (not just steady-state tokens/sec) once real M5 Pro hardware is available, before
committing to either architecture.

## 7. Throughput and responsiveness estimates

Apple's published spec for the M5 Pro Mac mini: **307GB/s memory bandwidth**. Decode is
memory-bandwidth-bound, so a naive theoretical ceiling is `bandwidth ÷ bytes read per
token`. At 10B active params, 3-bit quantization (~3.75GB/token): **~82 tokens/sec
theoretical peak**.

Real MLX implementations don't hit theoretical peak. Calibrating against a sibling
model's published benchmarks (Qwen3.5-35B-A3B, 3B active, on M4 Max at 546GB/s bandwidth,
reported ~55-115 tok/s real-world — roughly 25-30% of that model's own theoretical peak),
applying the same efficiency ratio here gives a **realistic estimate of ~20-25 tokens/sec**
for Qwen3.5-122B-A10B on the M5 Pro. **This is an extrapolation, not a measurement** —
neither this model nor the M5 Pro has published benchmarks as of this writing; verify on
real hardware before relying on this number for any downstream decision.

**Reframing responsiveness** (the more important finding from this section): the owner's
intuition that NPCs need to be more responsive than the GM is correct, but the relevant
metric is **time-to-first-token (TTFT)**, not steady-state tokens/sec. Average
conversational speech (~150 words/minute, ~1.3 tokens/word) only requires **~3-5 tokens/sec**
to keep pace with TTS in a sentence-streamed pipeline (§5) — the ~20-25 tok/s estimate above
clears that bar by 4-8x regardless of which role is speaking. Industry voice-AI TTFT
targets found via web research: **150-400ms is "good," ~500ms is a common practical
target, responses feel noticeably delayed above ~800ms, and conversations feel "broken"
above ~1,500ms.**

The actual lever for NPC responsiveness is therefore **keeping each turn's incremental
prefill small** — i.e., relying on a warm, resident KV-cache session per NPC so each turn
only needs to process the new delta (the player's latest line, typically 10-50 tokens)
rather than the whole conversation history — not picking a smaller/faster model per se.
This is an architecture property (whether sessions stay resident, per §2's caching
mechanics) more than a model-size property.

## 8. Serving stack notes (supplementary to reports 38/40, not yet independently verified)

- **`ml-explore/mlx-swift`** (core Swift MLX bindings) + **`ml-explore/mlx-swift-lm`**
  (LLM/VLM layer) ship a `ChatSession` class with per-conversation persistent KV cache,
  disk save/load (`.safetensors`), `maxKVSize`/`kvBits` tuning, and a documented (but
  **not yet verified against current source**) claim of "wired-memory coordination so
  multiple inference tasks can share one GPU budget" — potentially solving much of the
  per-NPC session-management problem at the library level rather than requiring custom
  engineering. Pair with **Hummingbird** (lightweight, SwiftNIO-based) rather than Vapor
  for the HTTP layer.
- Existing fuller attempts worth reading before building anything: `SharpAI/SwiftLM`
  (native MLX Swift inference server, OpenAI-compatible API) and "maclocal-api" (unifies
  Apple Foundation Models + MLX under one OpenAI-compatible API).
- **Correction to an earlier claim made informally during this session**: `llama.cpp`'s
  shared-prefix mechanism is **not** `--system-prompt-file` (that flag was asserted
  without verification against this repo's own research) — per report 38, the actual
  current mechanism is `cache_prompt` (default-on, automatic in-slot reuse),
  `--cache-ram`/`--cache-reuse` (PR #16391, automatic cross-request/cross-slot reuse), and
  explicit `/slots` save/restore as a deterministic fallback. Use report 38 as the
  authoritative source on this, not this report or informal recollection.

## Outstanding / next steps

1. Confirm the exact 3-bit quantized file size for Qwen3.5-122B-A10B once available,
   rather than the ~50-55GB estimate used throughout this report.
2. Empirically verify whether prefix-cache reuse is actually broken for this specific
   model (not just inferred from architectural similarity to report 38's model) once it's
   running.
3. Benchmark real tokens/sec and, more importantly, real TTFT for short NPC-shaped turns
   on actual M5 Pro hardware — replace §7's extrapolated estimates.
4. Verify real VRAM headroom on the RTX 5080 box against the owner's actual Skyrim mod
   list before assuming TTS coexists comfortably with the game.
5. Verify `mlx-swift-lm`'s `ChatSession` multi-session GPU-sharing claim against current
   source before architecting around it.
6. Locate the "sibling project"'s `tools/annotate/schema.py` (report 40's reference) if
   it becomes accessible from this project, to avoid re-deriving an already-settled
   emotion-tag design.
7. Decide the single-model-vs-two-model question (§6) empirically once hardware allows
   direct benchmarking of NPC-shaped short turns against the GM model.
8. Test whole-session KV state save/restore to SSD (§0/TL;DR, distinct from broken
   cross-conversation prefix sharing) against this specific hybrid model once running, to
   confirm the reasoning in §2/§3 holds in practice and not just in theory.
