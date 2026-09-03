# Kimi architecture-delta audit (2026-08-27)

Read-only classification of the architecture-delta proposal from an
external Kimi conversation (vision.md/architecture.md/v0.2-spec.md/
ui-spec.md changes, a new "Behavior/AI Spec (v0.3+)", and a table of 4
proposed new ADRs — Tick Fidelity Tiers, a Versioned Handoff Protocol,
Named Pipes IPC, Diegetic Evidence). No foundational docs edited, no
ADRs created. This report is the input for a decision, not the decision.

The save/reload subset of this same Kimi conversation was already
reconciled against ADR-0004/0005 in
`docs/decisions/open-questions.md`'s "Mostly-closed, one real gap"
section — not re-litigated here.

| Delta | Bucket | Citation / reasoning | Recommendation |
|---|---|---|---|
| **Tick Fidelity Tiers** (full sim near player, coarser for distant/offscreen NPCs) | Already decided | `docs/decisions/0006-data-ownership-layers.md` Consequences: "full evaluation for the active scene, eligibility-only for nearby NPCs, scheduled batch for offscreen NPCs, no global computation for reputation" (from report 08 §8.7). Same tiering concept, already load-bearing in the ADR. `0010-tick-quantum.md` separately pins the *unit* (1 tick = 1 game-hour) — a different, already-settled question the Kimi conversation didn't distinguish from fidelity tiering. | No doc change needed. If Kimi's version adds a concrete tier schedule (specific tick-count thresholds per tier) not in 0006, that's a small addition to 0006's Consequences, not a new ADR. |
| **Versioned Handoff Protocol** (save/reload state versioning) | Already decided | `docs/decisions/0004-timeline-branching.md` (fork-not-rollback, `(save_uuid, generation)` DAG) + `0005-sync-handshake.md` (HELLO/RESOLVE/ACK six-way table, SKSE co-save manifest schema, DEGRADED never-block rule) — both more precise than the Kimi proposal per the existing `open-questions.md` reconciliation. | No action. Already fully covered and already fact-checked once. |
| **Named Pipes IPC** (replace HTTP transport) | Genuinely new, expensive | `docs/decisions/0001-external-service-architecture.md` explicitly named HTTP as "the likely default" transport and gave the rationale (Mantella/CHIM precedent); `0005-sync-handshake.md` says exact transport "is not [pinned]" but the *handshake* is HTTP-shaped. In the time since 0001, HTTP has become load-bearing in practice: `chronicle/sync.py`, the listener (`adapters/skyrim/listener/`), the OpenAPI contract, and all six built ChronicleBridge slices (hydration, avoidance ×2, vendor-markup ×3) all speak HTTP today. Swapping transport touches every one of those, plus re-verifies the SSH-tunnel-based dev workflow (`docs/research/25-devbench-skse-mcp-verification.md`) that already depends on HTTP being loopback-TCP. | Do not adopt without a name-it-explicitly decision from the owner — this is a seam-wide rewrite, not a doc edit, and no concrete problem with HTTP has been identified yet (latency budget was 0001's own named risk, and nothing since has shown it's binding). |
| **Diegetic Evidence** (physical in-world objects/notes reflecting belief/evidence state) | Genuinely new, moderate-to-expensive | No existing doc (vision.md, architecture.md, `0006-data-ownership-layers.md`'s Evidence record, `0007-inspectability.md`) proposes surfacing evidence as *placed game objects* — today "evidence" is a data record (`Evidence(id, belief_id, evidence_type, source_id, ...)`) consumed by the dashboard/query layer, not the game world. Building this for real needs a new ChronicleBridge write path (spawn/place refs or items keyed to evidence records) plus new authored game content (items, maybe leveled lists, via the already-proven Mutagen pipeline) — comparable scope to the avoidance or vendor-markup slices already shipped, not a "cheap" add. | Genuinely interesting and buildable with tools already proven this session (Mutagen headless authoring), but it's a new full-stack slice, not a doc note — treat it as a candidate for its own design-prep pass (mirroring `chronicle-bridge-avoidance-mutagen-out.md`'s process) if/when the owner wants to prioritize it, not something to fold into vision.md as a stated commitment yet. |
| **New "Behavior/AI Spec (v0.3+)" document** | N/A (meta, not a mechanism) | This is a proposal to reorganize docs, not a design decision. `docs/v0.1-spec.md` currently holds the 20-rule registry; nothing prevents a future v0.3+ doc once v0.3 content (avoidance, vendor-markup, crime-witness) stabilizes enough to warrant its own spec file rather than living in `next-phases-2026-08.md`. | Low cost whenever it happens, but premature while v0.3's slices (crime-witness's C++ half, live-game verification of everything built) are still open — wait until they settle so the spec reflects what's actually true, rather than needing another correction pass like the ones `open-questions.md` and this audit already did twice. |
| **4 new ADRs (table, unspecified individual content)** | Mixed — see rows above | The conversation's own 4-ADR table maps directly onto the four rows above (tick fidelity → already-0006; handoff protocol → already-0004/0005; IPC transport → the one real expensive item; diegetic evidence → the one real new-and-buildable item). No 5th distinct ADR-worthy idea was found in the proposal beyond these four. | Write only the IPC-transport and diegetic-evidence ADRs if/when the owner decides to act on either — the other two would just restate 0004/0005/0006 with less precision, repeating a pattern already found twice this session. |

## Overall recommendation

Of four proposed deltas, two are already decided (and more precisely) in
existing ADRs, one (Named Pipes IPC) is a real but expensive seam-wide
rewrite with no demonstrated problem to justify it yet, and one (Diegetic
Evidence) is genuinely new, moderately-scoped, and buildable with tooling
already proven this session — a reasonable next full-stack slice if the
owner wants to prioritize it, but not something to fold into the
foundational docs as a standing commitment before a design-prep pass.
Recommend: do nothing to vision.md/architecture.md/ui-spec.md now; treat
Diegetic Evidence as a candidate for the same design-prep → implement
pipeline used for avoidance/vendor-markup if the owner picks it up, and
leave Named Pipes IPC parked unless a concrete HTTP limitation surfaces.
