---
status: accepted
date: 2026-08-20
---

# 0005: Sync handshake between the SKSE shim and the service

## Context

`0004-timeline-branching.md` establishes *what* Chronicle's state model
looks like across saves/reloads. This ADR covers *how* the SKSE-side shim
and the external Python service stay synchronized in real time, given two
concrete, documented race conditions from research
(`docs/research/05-save-reload-sync-protocol.md`,
`docs/research/06-save-reload-timeline-sync.md`):

- `kPostLoadGame` (native, fires early) and Papyrus's `OnPlayerLoadGame`
  (fires later, and never on a brand-new game) are two non-synchronized
  "load done" signals — neither alone means the game is actually ready to
  be queried.
- A stale-write race: an in-flight async operation (an LLM call, a network
  round trip) started before a reload can complete *after* the reload and
  write its result into the wrong timeline if nothing fences it.
- Documented crash evidence (SkyrimNet issue #465): querying Papyrus form
  properties immediately on `kMessage_PostLoadGame`, before the engine
  finishes populating property caches, null-pointer-dereferences.

## Decision

**Writes are gated on watermark receipt plus an explicit `game_ready`
ping — never on `kPostLoadGame` alone.**

1. **New-game vs. reload detection uses both hooks.** The shim runs its
   init routine from *both* `OnInit()` (fires on brand-new game only) and
   `OnPlayerLoadGame()` (fires on every subsequent load, never on new
   game) — this is the standard idiom for covering both cases, since
   neither hook alone fires in all situations.
2. **The shim owns a `g_isLoading` flag.** Set true on
   `kMessage_PreLoadGame`; while true, all event-generation hooks
   (dialogue, location transitions, relationship shifts) are suppressed
   and queued locally, not transmitted.
3. **Watermark handshake, not a bare load signal.** On `kPostLoadGame`,
   once the co-save's timeline record (`save_uuid`, `generation`,
   `event_seq`/`gamets`) has been parsed, the shim sends it to the service
   as a `SYNC_TIMELINE` message. The service compares it against its
   branch head (per ADR-0004: equal → continue, in the past → fork,
   unknown `save_uuid` → switch/create that character's branch), then
   replies `TIMELINE_READY` with an **epoch fencing token**.
4. **Epoch fencing gates every subsequent write.** Every load or new game
   increments an `epoch_id`. Every `MUTATION_EVENT` the shim sends must
   carry the epoch it was issued under. The service discards any mutation
   whose epoch is older than its current active epoch — this is what
   prevents a stale async response from a pre-reload operation landing in
   the post-reload timeline.
5. **`g_isLoading` clears only after the full handshake completes** —
   `kPostLoadGame` fired, the timeline record was transmitted, and
   `TIMELINE_READY` was received. Only then does the shim resume sending
   live events, and only under the new epoch.
6. **Papyrus-derived triggers get an extra guard.** To avoid the
   property-cache-warmup crash class (SkyrimNet #465), the shim delays
   firing any event trigger that reads Papyrus form properties until a
   minimum delay after `kPostLoadGame` (research suggests ~200ms as a
   starting point, not a verified constant) or until an explicit Papyrus
   init heartbeat, whichever comes first.
7. **Idempotency and back-pressure.** The service dedupes on
   `(save_uuid, generation, event_seq)` — necessary because network
   retries or rapid quicksave/quickload can plausibly redeliver or
   reorder messages. SkyrimNet's own bug tracker documents it "cannot keep
   up with game load" during bursts; the service must tolerate a burst of
   buffered events arriving right after `TIMELINE_READY`, not assume
   steady-state throughput.
8. **Uncommitted state between saves is volatile.** Events since the last
   save live in a buffer keyed to the active `(save_uuid, generation)`. A
   `SAVE_CREATED` notification commits the buffer. A reload/death without
   saving discards it — those events never happened in any surviving
   timeline, so they must not be folded into any branch's derived state.

## The co-save manifest schema

`docs/research/09-save-sync-forensics.md` specifies a concrete, minimal
record for the co-save chunk this ADR's watermark handshake reads and
writes. Adopted as-is, with field names aligned to ADR-0004's
`(save_uuid, generation)` branch key:

| Field | Type | Purpose |
|---|---|---|
| `format_version` | uint16 | schema evolution — SKSE co-save records carry a version natively; bump this, never reinterpret an old layout |
| `save_uuid` | 16 bytes | which playthrough/timeline (ADR-0004) |
| `generation` | 16 bytes or uint64 | which branch of that timeline (ADR-0004's fork counter) |
| `parent_generation` | 16 bytes or uint64 | fork ancestry; null/zero for the root |
| `head_seq` | uint64 | the **last service-ACKed** event sequence on this branch — not "last attempted," so a save can never reference uncommitted state |
| `gamets` | float64 | in-game clock at save time — bitemporal valid time (ADR-0004) |
| `wall_ts` | int64 | real time at save — bitemporal transaction time (ADR-0004) |
| `char_name_hash` | uint64 | **display/debug only, never a key** — Mantella's name-keyed identity is the documented counterexample (its community resources page maintains a manual list of vanilla NPCs who change name/refID mid-game, precisely because name-keyed identity ages badly) |

Keep this record small — a manifest, not a database. SKSE's unbuffered
per-call co-save writes are slow for large payloads (the S.L.A.C.K.
plugin exists solely to fix this for other mods); everything bulky stays
server-side, and this record should cost well under a hundred bytes.

## The HELLO/RESOLVE/ACK handshake

This is the concrete protocol underlying the watermark handshake in the
Decision section above — `SYNC_TIMELINE` below is the HELLO, the
service's branch-head comparison is RESOLVE, and `TIMELINE_READY` is the
ACK. Three messages, initiated only after the load has already succeeded:

1. **Manifest capture** — during the co-save Load callback (after Revert
   has cleared the prior session's copy), read the manifest into memory.
   No manifest present means a legacy/first-run save.
2. **HELLO** (`SYNC_TIMELINE`) — on `kPostLoadGame(success=true)`, the
   shim asynchronously posts `{save_uuid, generation, head_seq, gamets,
   wall_ts}` to the service. Non-blocking — gameplay continues regardless
   of the answer (see "never block," below).
3. **RESOLVE → ACK** (`TIMELINE_READY`) — the service classifies the
   manifest against its branch head and responds with a decision, per the
   six-way table below; the shim applies it and only then clears
   `g_isLoading` and starts tagging outbound events with the resolved
   `(save_uuid, generation)` (and epoch, per this ADR's fencing rule).

| Condition at RESOLVE | Decision | Service action |
|---|---|---|
| Same branch, `head_seq` ≥ manifest's, `gamets` equal/newer | **CONTINUE** | Resume branch; replay any un-ACKed gap events |
| Same `save_uuid`, `gamets` older than branch head | **FORK** | Create child generation at the nearest checkpoint ≤ loaded `gamets` (ADR-0004); mark old branch orphaned + start its grace timer; new events route to the child |
| `save_uuid` known, `generation` unknown (e.g. a copied/cloud-restored save) | **ADOPT** | Treat as a fork from the manifest's `head_seq`; link ancestry via `parent_generation` |
| `save_uuid` unknown, character/profile seen before | **NEW TIMELINE** | Open a fresh branch; optionally offer import of that character's public knowledge |
| No manifest present | **LEGACY IMPORT** | Bootstrap from heuristics (save filename's embedded save ID, character name), then write a manifest on the next save |
| Service unreachable at HELLO | **DEGRADED** | See "never block," below |

**Fork resolution is automatic for small jumps, confirmed only for large
ones.** Dying and reloading a save from seconds-to-minutes ago on the same
branch resolves as a **silent CONTINUE or small FORK** — no player-facing
prompt. A confirmation prompt (mirroring SkyrimNet's own
`ClearTimelineMessage`/`msgClearHistory`, which is exactly this UX for its
own rollback — see `open-questions.md`'s now-closed SkyrimNet-reload-
behavior item) is reserved for jumps large enough to plausibly represent
the player deliberately returning to an old save, not every death-retry. A
prompt on every death is, per report 09, "the fast path to users disabling
the system."

## The never-block rule (DEGRADED mode)

**The game side is optimistic and never blocks; the service side is
pessimistic and validates every event against the currently-ACKed branch
head.** Concretely: if the service is unreachable at HELLO time, or slow,
the shim does not stall the loading screen or gameplay — it buffers
outbound events in a bounded local queue (spilling to disk if the queue
fills) and reconciles on reconnect. This is a stronger, explicit version
of this ADR's existing back-pressure tolerance requirement (item 7,
below): DEGRADED is what happens *before* a connection exists at all, not
just under load. On the service side, every incoming event is still
validated against the ACKed branch head/epoch regardless of how it
arrived (live, or replayed from a DEGRADED buffer) — the asymmetry is
deliberate: the game must never choose correctness over responsiveness,
and the service must never choose responsiveness over correctness.

## Rationale

All four save/reload research reports converged on gating writes on an
explicit handshake rather than trusting the native load message alone, and
all four independently proposed a fencing-token-style mechanism (report
06 names it explicitly as "epoch fencing"; report 05 describes the same
effect as "gate writes on receipt of the watermark"; report 07, arrived at
while researching SkyrimNet's platform risk rather than save/reload
directly, proposes its own `SYNC_READY`/mute-the-pipeline handshake with
the same shape; report 09 names it HELLO/RESOLVE/ACK and is the one this
ADR's manifest schema and decision table are adopted from directly, since
it grounds the same mechanism in actual CHIM/SkyrimNet bug history rather
than architecture alone). Treating these as one mechanism avoids building
several overlapping race-prevention systems, and the four-way independent
convergence is stronger evidence for the design than any single report
would be alone.

## Consequences

- The wire protocol between `adapters/skyrim/` and the Python service needs
  at minimum four message types: `CLIENT_INIT` (handshake), `SYNC_TIMELINE`
  (shim → service, post-load — the HELLO), `TIMELINE_READY` (service →
  shim, carries the epoch token — the ACK), `MUTATION_EVENT` (shim →
  service, carries the epoch). Exact transport (HTTP vs. WebSocket) is not
  decided by this ADR — see `0001-external-service-architecture.md`; per
  ADR-0003 the choice is a property of which SAL provider (SkyrimNet vs.
  the standalone bridge) is active, not a separate open question.
- `chronicle/`'s event-derivation logic must reject (or the adapter layer
  must never forward) events carrying a stale epoch — this is an adapter
  concern, not a `chronicle/` concern, since `chronicle/` stays engine-
  agnostic and doesn't know what an "epoch" is, only what branch an event
  belongs to.
- The 200ms Papyrus-property-cache delay is a starting tunable, not a
  verified constant — needs empirical tuning once the shim exists against
  a real game process.

## Implementation-risk notes

See `docs/decisions/open-questions.md` — the `.skse`/`.ess` pairing is
atomic by convention only, so a crash between the co-save write and the
`.ess` write remains a residual risk this handshake doesn't fully close;
a scenario test for that case is worth adding once the shim exists
(`scenarios/sync/crash-mid-save`, see below).

Report 09's failure matrix and six-pattern race catalog are converted
directly into named regression scenarios under `scenarios/sync/` — see
that directory for the full list. Each scenario stub names a specific
race or failure this ADR's handshake must survive, so "does the handshake
actually work" stays a testable claim rather than a design-doc assertion.
