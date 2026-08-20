# Research index

One row per filed report. `[BUILD-ON]`/`[RISK]` lists below are merged across
all reports — see each file for full detail and citations.

| # | File | Topic | Sources | Status |
|---|------|-------|---------|--------|
| 01 | [01-skyrim-modding-substrate.md](01-skyrim-modding-substrate.md) | Skyrim modding substrate (Mantella/CHIM/SkyrimNet/SKSE) | 2 independent reports | filed — contains an unresolved disagreement, see below |
| 02 | [02-social-simulation-literature.md](02-social-simulation-literature.md) | Social-sim literature for game-scale belief systems | 1 report | filed |
| 03 | [03-hybrid-llm-symbolic-architecture.md](03-hybrid-llm-symbolic-architecture.md) | Hybrid LLM + symbolic simulation architectures | 3 reports (high overlap) | filed |
| 04 | [04-voice-pipeline.md](04-voice-pipeline.md) | Voice/dialogue pipeline for procedural NPCs | 1 report | filed |
| 05 | [05-save-reload-sync-protocol.md](05-save-reload-sync-protocol.md) | Save/reload timeline consistency — protocol design | 1 report (batch 2) | filed |
| 06 | [06-save-reload-timeline-sync.md](06-save-reload-timeline-sync.md) | Save/reload timeline consistency — DAG model and wire protocol | 1 report (batch 2) | filed |

## Merged [BUILD-ON] list

- **Belief data model**: James Ryan et al.'s Talk of the Town facet model (Value/Predecessor/Evidence/Strength/Accuracy) — near-direct template for `chronicle`'s belief dataclass, already Python. (02)
- **Rumor propagation**: Daley–Kendall SIR spread (who hears it) + Bartlett/Griffiths serial-reproduction mutation (how it changes), both O(edges) per tick. (02)
- **Memory decay**: ACT-R base-level activation (closed-form log-decay) + Generative Agents recency×importance×relevance score — cheap, LLM-free. (02)
- **Tier interface**: LLM text → numeric scalar (opinion/stance) → symbolic update, per HiSim/RumorSphere — symbolic state stays authoritative, LLM output is an annotated view, not a source of truth. (03)
- **Write-back mechanism**: constrained JSON decoding (XGrammar/Outlines/Guidance) is now near-zero-overhead and the field's dominant pattern; still needs a downstream semantic validator since format-valid ≠ content-valid. (03)
- **Local LLM tier**: 1B–8B models (Qwen3/2.5, Llama-3.x, Mantella-Skyrim-Llama-3-8B fine-tune) at Q4_K_M are practical alongside Skyrim on consumer GPUs — concrete VRAM/tok-s numbers converge across all 3 hybrid-architecture reports. (03)
- **Voice design**: Qwen3-TTS-VD (1.7B/0.6B, Apache 2.0) for one-time description-driven voice design; Chatterbox-Turbo (350M, MIT) as the runtime cloning engine (~75ms TTFB, <1GB VRAM, native inline tags + exaggeration slider). Adopt "design-once-then-clone": design at NPC creation, cache reference WAV by form ID, clone per line. (04)
- **Event transport**: never route high-frequency events through Papyrus (script-queue lag) — a CommonLibSSE-NG SKSE plugin hooking native dispatchers, forwarding via HTTP/WebSocket, is the pattern both substrate reports converge on. (01)
- **NPC data ingestion**: Mutagen or the xEdit Info NPC Extractor script, plus UESP CC-BY-SA bios. (01)
- **Save/reload identity**: embed a `SaveUUID` + `ParentSaveUUID` + monotonic `generation`/`SaveSequence` in the SKSE co-save (`TMNL` record) — strictly stronger than any existing mod's approach (CHIM's clock-only `gamets`, Mantella's none, SkyrimNet's in-process-only). See ADR-0004. (05, 06)
- **Timeline model**: model Skyrim's save topology as a DAG of branches keyed by `(save_uuid, generation)`; fork on reload, never roll back; derive state by path traversal from root to head. See ADR-0004 and the `chronicle/events.py` branch-key change. (05, 06)
- **Sync handshake**: gate writes on an explicit watermark/epoch handoff between the SKSE shim and the service, not on `kPostLoadGame` alone; buffer/suppress events during the load window. See ADR-0005. (05, 06)

## Merged [RISK] list

- **SkyrimNet build-vs-study disagreement** — see Open Questions below; this is the sharpest unresolved item and bears directly on ADR-0003. (01)
- **VRAM contention**: Skyrim (6–9GB) + local LLM (3.5–5GB) + TTS must coexist on a single 10–16GB consumer GPU — forces the voice tier to sub-1GB models (Chatterbox-Turbo/Nano); larger/expressive TTS models must be one-time/offline use only. (04)
- **Licensing/personality-rights**: Coqui XTTS v2 (Mantella's current TTS) is CPML non-commercial-only; Nexus Mods bans non-consensual real-voice-actor clones. Fully synthetic description-driven voices (Qwen3-TTS-VD) are the only legally defensible path for a distributed free mod. (04)
- **Sparse vanilla relationship data**: only ~586 relationships across 397 NPCs found in one RELA audit — most of Chronicle's social graph must be synthesized, not extracted. (01)
- **Engine-update fragility**: SKSE plugins (including any custom bridge) break on Bethesda engine updates (one flagged Aug 14 2026) — keep the Python/simulation side fully decoupled from the thin in-game bridge so an update only breaks the adapter, not the sim. (01)
- **"More LLM agents degrades fidelity"** is real but nuanced — it's a cost/diversity/calibration effect, not a hard population ceiling; scaling total population is fine, scaling the *LLM-driven share* of it is what hurts. (03)
- **Persona drift, formality collapse, memory fabrication** are documented and quantified in long-running LLM agents (Multi-IF, Laban et al., Lifelong-SOTOPIA, GATSim); mitigated by provenance-typed writes and per-turn persona re-injection, not by longer context windows. (03)
- **Evaluation is the field's acknowledged bottleneck**, not model capability — plan for regression scenarios against designer-defined curves plus held-out human rating from day one; never validate with an LLM judge that was also used to generate the content being judged. (03)
- **City of Gangsters' >20-rule ceiling**, CK3's throttle from ~300 to ~30 AI interactions per character per century post-launch — legibility and a per-tick interaction budget cap matter more than model sophistication at ~1,000-NPC scale. (02)
- **No prior Skyrim reputation/rumor mod actually implements propagation** — confirms this is a genuine gap, not reinvention, but also means there's no prior art to lean on for the game-side UX of surfacing rumors to the player. (01)
- **No existing mod solves save/reload consistency cleanly** — Mantella ignores it (drift), CHIM prunes globally by clock comparison (not per-slot), SkyrimNet's reload story is disputed between the two batch-2 reports (in-process/no fork vs. an explicit but unverified cleanup protocol). This is now addressed by ADR-0004/0005, but remains one of the least-precedented parts of the design — expect to implement and test from scratch. (05, 06)
- **FormID instability**: a stored 32-bit FormID becomes invalid if the player's load order changes (mod add/remove/reorder shifts the ModIndex bits). Chronicle must never persist raw FormIDs. (06)

## Open questions raised

See [`docs/decisions/open-questions.md`](../decisions/open-questions.md):

- **Resolved by direct repo verification**: MinAI is deprecated (confirmed), Mantella's latest release is v0.14 published 2026-04-21 (confirmed), CHIM/HerikaServer is MIT-licensed (confirmed). Report 01 has been corrected in place.
- **Closed by research**: save/reload timeline consistency — reports 05 and 06 answered the drafted prompt. ADR-0004 (timeline branching) and ADR-0005 (sync handshake) are now drafted from their recommendations, and `chronicle/events.py` carries a branch key. Two implementation-risk uncertainties carried forward (not fully resolved): CHIM's exact fork trigger is reconstructed, not confirmed; the save-embedded-UUID pattern has no confirmed Skyrim precedent. A third disagreement surfaced between reports 05 and 06 on how SkyrimNet itself handles reloads (implicit/none vs. an explicit but unverified cleanup protocol) — logged, not resolved, since Chronicle doesn't depend on SkyrimNet's own reload behavior for its own protocol either way.
- **Open — bears on ADR-0003**: the SkyrimNet build-vs-study disagreement between the two report-01 sources. A short due-diligence research prompt (SkyrimNet ecosystem health/sustainability) is drafted and ready to fire before this ADR is finalized. This is now the only queued research task.
- **Deferred, not forgotten**: economic simulation (prices, supply, trade ripple) — out of scope until the belief tier is proven, slated v0.4.

## Batch 2 — complete

Save/reload consistency (reports 05, 06) is filed and closed out into
ADR-0004/0005 plus an `events.py` change. One research task remains queued:
SkyrimNet ecosystem due-diligence, gating ADR-0003.
