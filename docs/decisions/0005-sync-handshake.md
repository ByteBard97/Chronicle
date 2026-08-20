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

## Rationale

Both source reports converged on gating writes on an explicit handshake
rather than trusting the native load message alone, and both independently
proposed a fencing-token-style mechanism (report 06 names it explicitly as
"epoch fencing"; report 05 describes the same effect as "gate writes on
receipt of the watermark"). Treating these as the same mechanism avoids
building two overlapping race-prevention systems.

## Consequences

- The wire protocol between `adapters/skyrim/` and the Python service needs
  at minimum four message types: `CLIENT_INIT` (handshake), `SYNC_TIMELINE`
  (shim → service, post-load), `TIMELINE_READY` (service → shim, carries
  the epoch token), `MUTATION_EVENT` (shim → service, carries the epoch).
  Exact transport (HTTP vs. WebSocket) is not decided by this ADR — see
  `0001-external-service-architecture.md` and `open-questions.md`'s
  SkyrimNet due-diligence item, since the choice may depend on which
  integration path ADR-0003 ultimately picks.
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
a scenario test for that case is worth adding once the shim exists.
