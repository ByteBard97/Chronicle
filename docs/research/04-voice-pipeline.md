---
date: 2026-08-20
sources: ["Procedural NPC Voice Pipeline Research.md"]
topic: "Voice and dialogue pipeline for procedural NPCs"
status: filed
---

# Voice and Dialogue Pipeline for Procedural NPCs

## Findings

- [BUILD-ON] Use Qwen3-TTS-VD (1.7B or 0.6B, Apache 2.0) as the one-time "voice creation" step: it synthesizes a persona from a natural-language description (age, pitch, timbre, pace) into a 5-10s reference WAV, with no human recording required — the correct fit for procedurally-generated NPCs that need a unique but non-infringing voice identity.
- [BUILD-ON] Use Chatterbox-Turbo (350M, MIT) as the runtime cloning/synthesis engine: it clones from the cached 5s reference clip, supports native inline paralinguistic tags (`[laugh]`, `[sigh]`, `[cough]`, `[gasp]`) and a continuous exaggeration slider (0.0-2.0), and runs at ~75ms TTFB / <1GB VRAM in FP16/ONNX — cheap enough to run per-line during gameplay.
- [DESIGN-INPUT] Adopt the "design-once-then-clone" pattern as Chronicle's core voice architecture: design the voice once per NPC at character-creation time (or cell-load cold start) and cache the reference WAV keyed by form ID; every subsequent dialogue line only pays the cheap cloning cost, not the design cost.
- [DESIGN-INPUT] Map internal simulation state (stress, hostility, mood) directly onto Chatterbox-Turbo's inline tags and exaggeration parameter (e.g., high stress -> append `[sigh]` + exaggeration 1.3, high hostility -> append `[grunt]`) — this gives emotional direction a concrete, low-latency implementation path rather than needing a separate expressive-TTS layer.
- [RISK] VRAM budget on a single 10-16GB consumer GPU is extremely tight: Skyrim SE/AE (6-9GB) + a 3B-8B local LLM for simulation reasoning (3.5-5GB) leaves only ~1-2GB for TTS. Only sub-1GB models (Chatterbox-Turbo/Nano) fit; Qwen3-TTS 1.7B (~3.5GB) or Orpheus 3B (~6GB) cannot run concurrently with gameplay on one GPU and must be offloaded (CPU, secondary GPU, or run only at cold-start/offline).
- [RISK] Coqui XTTS v2 — used by some existing Skyrim AI mods (Mantella) — is CPML-licensed (non-commercial), consumes 3-4GB VRAM, is slow, and drifts on long sentences; it should be avoided both for licensing ambiguity around free-mod distribution with donation tiers and for performance reasons.
- [RISK] Personality-rights/platform risk: Nexus Mods bans non-consensual AI clones of real voice actors used for objectionable content, with DMCA/ban consequences. Chronicle's use of Qwen3-TTS-VD (fully synthetic, description-driven personas rather than cloned from real actors) is the legally defensible path and should remain the only voice-origin method used — no cloning from real-world audio samples.
- [DESIGN-INPUT] Skyrim's Creation Engine cannot stream PCM directly — every generated line needs a physical WAV + a matching `.lip` phoneme file (via FaceFXWrapper/LipGenerator or a custom SKSE lip tool), ideally packed into `.fuz`. This is a hard architectural requirement, not optional, and adds ~15-30ms per line plus a packaging step to the pipeline.
- [DEFER] Cloud/managed TTS options (Groq/Fal.ai Orpheus, ~$0.022-$0.05 per 1,000 chars) are a viable fallback for players without capable local GPUs, but should be deferred as an optional/secondary backend rather than the primary design target, since Chronicle's stated goal is a local, free, self-hosted pipeline.
- [DEFER] Orpheus TTS (Llama-3B backbone) offers strong bracketed emotional control (`[cheerful]`, `[whisper]`, `[sarcastic]`) but its 3B footprint (~6GB VRAM, 130-200ms TTFB) is too heavy for the primary runtime tier under current VRAM constraints; revisit only if VRAM budgets improve or a secondary-GPU/cloud offload path is built.

## Details

### Voice-design-from-description models

- **Qwen3-TTS** (Apache 2.0), 0.6B and 1.7B parameter variants. Dual-track language model paired with Qwen3-TTS-Tokenizer-12Hz (a multi-codebook speech encoder, 12.5Hz, 16-layer causal ConvNet) that captures fine-grained acoustic, prosodic, and paralinguistic attributes.
- The **Qwen3-TTS-VD** (Voice Design) variant takes free-form text prompts (gender, age, pitch, timbre, vocal tics, pace) and synthesizes a novel vocal identity with no prior human recording — e.g. "a low male pitch with upward inflections, fast-paced delivery, and raspy timbre."
- TTFB for Qwen3-TTS is reported as low as ~97ms in streaming mode, though the *voice design* step itself (generating the initial reference clip) is a one-time ~1.5-3.0 second operation, not a per-line cost.
- Qwen3-TTS-VC (voice-clone variant) and Chatterbox-Turbo are the two named options for the lightweight runtime cloning step that follows voice design.

### Design-once-then-clone caching pattern

- When a procedural NPC is instantiated, its attributes (age, race, faction, emotional disposition) are mapped into a natural-language voice-description prompt fed to the voice-design model.
- The model synthesizes a brief 5-10 second reference waveform containing representative phonemes and baseline prosody. This reference WAV is stored locally in a persistent voice bank indexed by the NPC's unique form ID (e.g. `/voice_bank/{npc_id}.wav`).
- At runtime, dynamic dialogue lines are generated by feeding the cached reference clip into a lightweight zero-shot cloning model (Qwen3-TTS-VC or Chatterbox-Turbo), avoiding the cost of running voice design per line.
- Lifecycle management proposed in the source:
  - **Cell Attach Warm-Up**: on SKSE cell-load event, check for and pre-load the NPC's cached reference WAV into memory.
  - **Cold-Start Generation**: if no cached seed clip exists, invoke Qwen3-TTS-VD in a background thread during cell load to synthesize it before dialogue can occur.
  - **LRU Latent Management**: runtime worker keeps an LRU cache of active voice latents, capping total VRAM for cached voices at ~500MB regardless of total world NPC count.

### Expressive control / inline tags

- **Chatterbox-Turbo** (Resemble AI, MIT, 350M params): native inline paralinguistic tags — `[laugh]`, `[sigh]`, `[cough]`, `[chuckle]`, `[gasp]` — interpreted as acoustic instructions rather than stripped/mispronounced. Also exposes a continuous exaggeration parameter: 0.1-0.3 = flat/monotone, 0.6-0.9 = natural conversational, 1.2-2.0 = dramatic/theatrical. This lets internal character state (stress, panic, anger) map directly to acoustic intensity.
- **Chatterbox-Nano** (110M, MIT): same single-step decoder architecture as Turbo, optimized for CPU; ~25ms TTFB on CPU, 3x faster than real-time on 8 cores, minor fidelity loss versus Turbo.
- **Orpheus TTS** (Llama-3B backbone, open source, not clearly permissive-licensed per the table): treats speech as causal token generation; supports bracketed vocal directions (`[cheerful]`, `[whisper]`, `[excited]`, `[deadpan]`, `[sarcastic]`, `[gravelly whisper]`); empathetic prosody but a much larger footprint (~6GB VRAM, 130-200ms TTFB) than the 350M-class models.
- Comparison table from the source:

| Model | Params | License | TTFB | Voice Design | Zero-Shot Cloning | Inline Tags | Emotion Control |
|---|---|---|---|---|---|---|---|
| Qwen3-TTS 1.7B | 1.7B | Apache 2.0 | ~97ms | Native (VD) | Native (3s clip) | Instruction-based | Semantic adaptation |
| Qwen3-TTS 0.6B | 0.6B | Apache 2.0 | ~97ms | Native (VD) | Native (3s clip) | Instruction-based | Semantic adaptation |
| Chatterbox-Turbo | 350M | MIT | ~75ms | External seed needed | Native (5s clip) | Native bracket tags | Continuous slider (0.0-2.0) |
| Chatterbox-Nano | 110M | MIT | ~25ms (CPU) | External seed needed | Native (5s clip) | Native bracket tags | Continuous slider (0.0-2.0) |
| Orpheus TTS | 3.0B | Open Source | ~130-200ms | Limited/Pre-set | Native zero-shot | Bracket directions | Temperature tuning |
| Coqui XTTS v2 | 450M | CPML (Non-Comm) | ~250-400ms | No | Native (6s clip) | Unstable/Poor | No native controls |

### Latency & VRAM budgets

- Target hardware: single consumer GPU, 10-16GB VRAM, running Skyrim SE/AE alongside a local LLM and TTS worker.
- Modded Skyrim client (textures, SKSE plugins, shaders): 6.0-9.0GB VRAM.
- Local quantized LLM (3B-8B, INT4/FP8) for simulation reasoning and dialogue generation: 3.5-5.0GB VRAM.
- Residual budget for TTS: ~1.0-2.0GB. Qwen3-TTS 1.7B (~3.5GB) and Orpheus 3B (~6.0GB) do not fit and risk VRAM swapping/stutter/frame drops if run concurrently on the primary GPU.
- Mitigation strategies given in the source:
  - **Lightweight GPU inference**: Chatterbox-Turbo at FP16/ONNX uses <1.0GB VRAM — fits the residual budget.
  - **Host CPU offloading**: Chatterbox-Nano on 8 CPU cores runs at 3x real-time, freeing the GPU entirely (minor fidelity cost).
  - **Secondary machine/GPU**: heavier models (Qwen3-TTS 1.7B, Orpheus 3B) can be hosted remotely via REST/WebSocket to avoid primary GPU contention.
- Streaming/TTFB: Qwen3-TTS emits first audio packet after as little as one input character (~97ms end-to-end first-packet latency) via dual-track LM decoding. Chatterbox-Turbo distills the token-to-mel decoder to a single step (from 10+ iterations), reaching ~75ms latency and 6x real-time throughput. Orpheus via Simplismart (decoupled backbone/decoder, FP8, continuous batching) reaches TTFB under 130ms.

### How Mantella/CHIM handle voices today, and the integration seam

- Mantella (the source's primary reference; CHIM is named in the task but not detailed in the source report) runs a dedicated SKSE C++ plugin (MantellaLauncher) linked to a background Python app that handles STT input, LLM dialogue routing, TTS generation, temp audio file writing, and SKSE script commands to trigger NPC dialogue animations.
- Three TTS backends supported by Mantella today:
  - **Piper TTS**: CPU-based, ~0.1GB VRAM/RAM, fast and easy but monotone/robotic, no dynamic emotion.
  - **xVASynth**: neural models trained on extracted Bethesda voice-actor files; runs on CPU or GPU; requires extensive manual voice installation; no native natural-language voice design.
  - **Coqui XTTS v2**: external API server, human-like quality, zero-shot cloning from a 6s clip; but 3-4GB VRAM, slow inference, pronunciation drift on long sentences.
- **Integration seam for a custom voice bank** (the pipeline Chronicle needs to build, per the source's runtime injection steps):
  1. **Dynamic Voice Assignment** — simulation assigns each NPC a unique voice ID; an SKSE plugin hooks Skyrim's DialogueMenu and actor interaction events to intercept dialogue requests.
  2. **Audio File Generation** — Python backend synthesizes speech using the NPC's cached voice seed clip, writing an uncompressed 16-bit 24kHz or 48kHz WAV to a temp staging directory.
  3. **Phoneme Lip-Sync Generation** — a headless utility (FaceFXWrapper.exe, LipGenerator.exe, or custom SKSE lip-sync library) generates a matching `.lip` file from the WAV + transcript.
  4. **Archive Packaging (.fuz)** — WAV + `.lip` combined into a Bethesda `.fuz` file (e.g. via Unfuzer) to avoid disk I/O stutter during gameplay.
  5. **Engine Audio Triggering** — SKSE plugin notifies Papyrus the asset is staged; engine plays the line via 3D positional audio and updates SubtitleManager/UI subtitles.

### Licensing/legal

- **Apache 2.0** (Qwen3-TTS, CosyVoice 2): fully permissive — embed, modify, host, and distribute weights/inference code in commercial or non-commercial mod packages, provided copyright notices are preserved.
- **MIT** (Chatterbox-Turbo, Chatterbox-Nano): fully permissive, unrestricted self-hosting/modification/bundling in distributed free mods with minimal attribution.
- **CPML/Non-Commercial** (Coqui XTTS v2): free for community mods, but redistribution becomes legally complicated if the mod author monetizes via Patreon/donation-key tiers.
- Vocal timbre/speech patterns are not copyrightable in isolation (US law), but an actor's voice likeness is protected by state Right of Publicity statutes and torts against non-consensual commercial exploitation, deepfakes, and false endorsement.
- Nexus Mods (the primary distribution hub) explicitly prohibits mods using non-consensual AI clones of real voice actors for NSFW, hate-speech, or defamatory content, enforcing DMCA takedowns and bans.
- Using natural-language Voice Design (Qwen3-TTS-VD) rather than cloning real actors' recordings is called out as the legally safer path: seed waveforms are synthesized from abstract text prompts, producing novel acoustic identities with no likeness-infringement risk and clean platform-policy compliance.
- Chatterbox-Turbo embeds PerTh implicit neural watermarking in all generated output, surviving transcoding (OGG/XWM/WAV) and edits, enabling verification of synthetic provenance and impersonation prevention.

## Recommended pipeline

Three-tier architecture, as given in the source:

1. **Voice Creation Tier (offline, one-time per NPC)**: Qwen3-TTS 1.7B-VD generates a persona from a natural-language description derived from the NPC's procedural attributes, producing a 5-second reference WAV saved to `/voice_bank/{npc_id}.wav`. Runs on primary GPU transiently (or cloud) — ~3.5GB VRAM, ~1.5-3.0 sec, one-time cost only.
2. **Runtime Synthesis Tier (in-game dialogue)**: Chatterbox-Turbo (350M, FP16/ONNX, primary GPU) as the default, or Chatterbox-Nano (110M, host CPU) as the fallback. Internal state vectors from the simulation LLM translate to inline tags and exaggeration values (e.g., high stress -> `[sigh]` + exaggeration 1.3; high hostility -> `[grunt]`). Text + cached reference WAV go to Chatterbox-Turbo, which streams audio back in under 80ms.
3. **Engine Delivery Tier (asset packaging + SKSE)**: audio buffer sent to a headless C++ worker wrapping FaceFXWrapper/LipGenerator to produce a synced `.lip` file; WAV+`.lip` packed to `.fuz`; SKSE Papyrus hook triggers positional 3D audio playback and subtitle rendering.

Caching strategy: LRU cache of active voice latents capped at ~500MB VRAM regardless of world NPC density; cell-load triggers a warm-up check against the on-disk voice bank, falling back to a background cold-start generation via Qwen3-TTS-VD if no cached seed exists yet.

Estimated per-line/per-NPC cost (from the source's performance table):

| Component | Stack | Compute Target | VRAM | TTFB | Cost |
|---|---|---|---|---|---|
| Voice Creation (per NPC, one-time) | Qwen3-TTS 1.7B-VD | Primary GPU (transient) / Cloud | ~3.5GB (transient) | ~1.5-3.0s | $0.00 local / ~$0.001 per NPC (cloud) |
| Primary Runtime TTS (per line) | Chatterbox-Turbo (350M) | Primary GPU (CUDA/ONNX) | ~0.8-1.0GB | ~75ms | $0.00 (self-hosted) |
| CPU Fallback TTS (per line) | Chatterbox-Nano (110M) | Host CPU (8 cores) | ~0GB VRAM / ~300MB RAM | ~25-50ms | $0.00 (self-hosted) |
| Lip-Sync Generator (per line) | Headless FaceFXWrapper/SKSE | Host CPU | ~0GB VRAM / ~50MB RAM | ~15-30ms | $0.00 (local) |
| Managed Cloud Option (fallback, per line) | Groq/Fal.ai Orpheus | External REST API | 0GB VRAM | ~130-200ms | ~$0.022-$0.05 per 1,000 chars |

Net result per the source: one-time voice design plus a sub-100ms, sub-1GB runtime clone/synthesis step yields persistent, expressive, legally compliant voices for thousands of procedural NPCs on a single consumer gaming PC.
