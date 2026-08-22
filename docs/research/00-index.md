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
| 07 | [07-skyrimnet-substrate.md](07-skyrimnet-substrate.md) | SkyrimNet ecosystem due-diligence — resolves ADR-0003 | 1 report (batch 3) | filed |
| 08 | [08-social-sim-literature-v2.md](08-social-sim-literature-v2.md) | Social simulation literature v2 — implementable specification | 1 report (batch 3) | filed |
| 09 | [09-save-sync-forensics.md](09-save-sync-forensics.md) | Save/reload sync — third independent pass, repository forensics | 1 report (batch 4) | filed — supersedes 05/06 on specifics |
| 10 | [10-skyrimnet-health.md](10-skyrimnet-health.md) | SkyrimNet health deep-dive — inverts ADR-0003's provider priority | 1 report (batch 5) | filed — amends ADR-0003 |
| 11 | [11-version-pin-and-transport.md](11-version-pin-and-transport.md) | Game version pin + HTTP/WebSocket bridge survey — resolves ADR-0008 | 3 reports (batch 6, merged) | filed — new ADR-0008 |
| 12 | [12-whiterun-dashboard-map-data.md](12-whiterun-dashboard-map-data.md) | Whiterun debug-dashboard map assets, coordinates, telemetry, licensing | 3 reports (batch 7, merged) + 1 session pass | filed — license claims verified directly |
| 13 | [13-dashboard-prior-art-source-read.md](13-dashboard-prior-art-source-read.md) | Dashboard prior art at source level — WS protocol, replay schema, projection | 1 source-reading pass (batch 8) | filed — resolves report 12's SkyrimWebSocket uncertainty |
| 14 | [14-isometric-render-foundations.md](14-isometric-render-foundations.md) | 2.5D/isometric render foundations — real Whiterun geometry without building a renderer | 1 session pass (batch 8) + hands-on smoke test | filed — **fo76utils verified on this machine 2026-08-22** |

Source PDFs worth keeping locally (not re-reads, schema/rule-authoring
references): see [`papers/README.md`](papers/README.md).

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
- **Sync handshake**: gate writes on an explicit watermark/epoch handoff between the SKSE shim and the service, not on `kPostLoadGame` alone; buffer/suppress events during the load window. See ADR-0005. (05, 06, independently re-derived by 07, and superseded on specifics by 09's HELLO/RESOLVE/ACK protocol with a six-way decision table and a DEGRADED mode for service-down-at-load)
- **Save-sync forensics**: report 09 goes past architecture into repository forensics (specific CHIM PRs #560/#572/#558/#681, SkyrimNet issues #251/#487/#119/#391) and resolves the SkyrimNet-reload-behavior conflict left open after 05/06: SkyrimNet *asks* the player before clearing (`ClearTimelineMessage`/`msgClearHistory`), confirmed via issue #251 — it neither silently ignores (05's read) nor runs a fully automatic cleanup (06's read). Agrees with 05/06/07 on architecture (event-sourced, fork-not-rollback, save-embedded UUID); upgrades ADR-0004/0005 on specifics (bitemporal columns, reachability-based GC, the manifest schema, the handshake decision table). (09)
- **Substrate Abstraction Layer**: a generic Python provider interface in `chronicle/`, both implemented under `adapters/`. Resolves ADR-0003 (07); **provider priority inverted by report 10** — the PO3-Extender+SKSE_HTTP standalone path is the reference implementation built first, SkyrimNet is an optional adapter pinned to one beta/API version with a startup handshake. See ADR-0003's amendment.
- **Five-layer data ownership**: canonical events → claims/variants → subjective beliefs → social state → narrative/query. Only the first layer is objective. See ADR-0006. (08)
- **Sparse-graph rule**: never maintain a complete N×N social matrix — sparse acquaintance/witness/family/faction edges only, evidenced by Socialog's 15-25ms→600ms per-tick cost growth from 50→450 characters. See ADR-0006. (08)
- **Observer-local reputation**: Beta-distribution `(alpha, beta)` per `(observer, subject, context)`, never one global score. See ADR-0006. (08)
- **Inspectability**: every derived social outcome must answer "who believes this, from what evidence, through whom, since when." See ADR-0007. (08)
- **Dashboard map backdrop**: no permissively-licensed Whiterun map exists; generate the backdrop yourself (CK `Create Local Maps` over `WhiterunWorld`, or esm-geometry parsing at install time) and treat the *generator* as the distributable artifact, never the rendered image. Whiterun is its own worldspace (`0x0001A26F`) with interior cells on local coordinates — the map tool needs per-cell layers. (12)
- **Dashboard frontend prior art**: uesp-gamemap code is MIT (tile pyramid + marker layer); Stanford's generative_agents is Apache-2.0 and its successor StanfordHCI/genagents is MIT (both verified 2026-08-22) — contributing time-scrubbed replay, the key pattern for rumor/belief debugging. Coordinate extraction: skyrim-cell-dump (**MIT** — Cargo.toml declaration, verified) + Mutagen or a short xEdit script; NPC schedule targets need PACK records. WhiterunWorld FormID `0x0001A26F`; cell math `floor(gameX/4096)`, two-point affine calibration is exact for Skyrim's linear projection. (12)
- **Live telemetry channel**: in-process SKSE plugin hosting a local WebSocket (SkyrimWebSocket — MIT verified, CommonLibSSE-NG multi-runtime, 1.6.1170-compatible, active 2026-08) is the adopted reference; its wire protocol and spatial JSON block are Chronicle's canonical transport/ActorLocation schema (13). Fork plan for the bulk-actor stream (`RE::ProcessLists` resolver) has exact hook points. Reject external memory-reading. (12, 13)
- **Sim trace/replay format**: adopt Smallville's step-file schema + delta compression (only-changed agents per step) for the headless JSONL trace; dashboard adds the scrubber Smallville lacks. One frontend, two feeds (headless sim now, SkyrimWebSocket later). (13)
- **Isometric/2.5D backdrop**: renderable from real game geometry without a from-scratch renderer — fo76utils (MIT, pending TES5-statics verification) or ByroRedux (MIT, verified rendering WhiterunWorld, heavier); both read the user's own game files so no Bethesda assets ship. The downloaded 1.6.1170 depot files serve as the render corpus without touching the live install. (14)

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
- **SkyrimNet direct coupling rated HIGH RISK** as a sole dependency: closed C++ core, no LICENSE file, single Ko-fi-funded maintainer, in-process design means a core exception is a crash-to-desktop. Mitigated, not eliminated, by the SAL (07).
- **API version drift, with concrete integrator damage**: v6→v9 in ~1 month (Beta18→Beta20); Beta21 shipped explicit breaking changes; IntelEngine hard-gated on a specific version and once blocked on an unreleased build; SeverActions hit an init-ordering deadlock and a schema break. This concrete evidence is what moved SkyrimNet from "primary provider, hedged" (07) to "optional adapter, pinned" (10) — see ADR-0003's amendment. (07, sharpened by 10)
- **No LICENSE/continuity statement, now confirmed via exhaustive-as-possible targeted search** (not just "not found in passing") across GitHub, docs, FAQ, Patreon, Ko-fi, Reddit. Action item tracked in `notes/ideas.md`: ask the maintainer directly. (10)
- **Dashboard asset licensing traps**: every ready-made Whiterun map asset is non-redistributable (Prima-guide-derived GameMapScout map; CC BY-NC-ND DeviantArt maps; proprietary MapGenie; Bethesda-derived UESP/CK renders); modmapper/esper/SkyrimNet-GamePlugin are source-available with no LICENSE — internal use OK, no vendoring. Bulk-downloading Nexus mods violates Nexus ToS. (12)

## Open questions raised

See [`docs/decisions/open-questions.md`](../decisions/open-questions.md):

- **Resolved by direct repo verification**: MinAI is deprecated (confirmed), Mantella's latest release is v0.14 published 2026-04-21 (confirmed), CHIM/HerikaServer is MIT-licensed (confirmed). Report 01 has been corrected in place.
- **Closed by research**: save/reload timeline consistency — reports 05 and 06 answered the drafted prompt. ADR-0004 (timeline branching) and ADR-0005 (sync handshake) are now drafted from their recommendations, and `chronicle/events.py` carries a branch key. Two implementation-risk uncertainties carried forward (not fully resolved): CHIM's exact fork trigger is reconstructed, not confirmed; the save-embedded-UUID pattern has no confirmed Skyrim precedent. A third disagreement surfaced between reports 05 and 06 on how SkyrimNet itself handles reloads (implicit/none vs. an explicit but unverified cleanup protocol) — logged, not resolved, since Chronicle doesn't depend on SkyrimNet's own reload behavior for its own protocol either way.
- **Closed by research**: SkyrimNet build-vs-study — report 07 resolves ADR-0003 with a Substrate Abstraction Layer, rating direct SkyrimNet coupling HIGH RISK and the SAL hedge MEDIUM RISK. ADR-0003 is now `accepted`.
- **Deferred, not forgotten**: economic simulation (prices, supply, trade ripple) — out of scope until the belief tier is proven, slated v0.4.
- **Closed by research (batch 6, out of cycle)**: game version pin — three independent reports, fired in response to the 1.7.99 patch breaking the plugin ecosystem on 2026-08-20, unanimously recommend pinning to 1.6.1170 + SKSE 2.2.6. Resolved as [ADR-0008](../decisions/0008-game-version-pin.md). This was flagged as a real gap in `notes/ideas.md` before any report addressed it. **This closes the last tracked open item — nothing remains open.**
- **Closed by research (batch 7, dashboard)**: Whiterun map assets / licensing for the debug dashboard — report 12 answers "can we build and distribute a 2D Whiterun map tool" (yes: generate the backdrop, ship the generator, reuse MIT/Apache prior art, in-process SKSE WebSocket for live telemetry). Feeds the dashboard slice, not an ADR — no decision-record change needed.

## Research phase: complete (pre-build); build-phase reports continue

11 reports across 6 batches covered the pre-build questions (batch 6 arrived after v0.1 was
already accepted and build had started — the 1.7.99 patch forced an
out-of-cycle research pass). Build-phase research continues as needed:
batch 7 (report 12, dashboard map assets/licensing, 3 reports merged)
arrived during the
v0.1 build. Every ADR the research surfaced a need for
has been drafted: 0001/0002 (accepted at scaffold time), 0003 (substrate,
amended once), 0004/0005 (timeline branching / sync handshake —
independently confirmed four times over), 0006 (data ownership layers),
0007 (inspectability), 0008 (game version pin). The project is in build:
`chronicle/claims.py` (layer 2/3 claim/variant/belief store) is the first
code milestone, per `docs/v0.1-spec.md`.
