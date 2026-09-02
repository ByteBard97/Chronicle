<!--
INSTRUCTIONS FOR GEOFF (not part of the Kimi prompt — delete this comment or leave it, Kimi
will ignore an HTML comment):

1. Copy everything BELOW the "=====" divider and paste it as your first message to Kimi.
2. This review benefits from real web/GitHub search — if Kimi's session has browsing enabled,
   say so; if not, ask it to flag any claim it can't verify rather than guess at one.
3. Bring back whatever Kimi says (paste its reply back to me, or save its response as a file
   and hand me the path) and I'll fold anything useful into the spec.
-->

=====

You are reviewing a technical design spec for a Skyrim SE/AE SKSE C++ plugin's save/reload
sync-handshake feature, before implementation begins. You have no other context beyond what's
in this message — treat it as complete.

## Background

"Chronicle" is a Skyrim mod with a pure-Python event-sourced simulation core (`chronicle/`) and
a native SKSE C++ plugin (`ChronicleBridge`) that bridges game events to/from a local Python HTTP
service. The open design problem: when a player saves and reloads a game, the native plugin and
the Python service need to agree on which point in the Python-side event history the reloaded
save corresponds to — including correctly handling the case where the player loads an *older*
save, which should fork a new branch of history rather than silently reusing state that got
overwritten. This spec is the concrete implementation plan for that handshake.

Two upstream design docs already exist and are considered settled (do not relitigate their core
decisions unless you find a real defect):
- **ADR-0004 (timeline branching):** Skyrim's save topology is modeled as a DAG via
  `(save_uuid, generation)` branch keys. Reloading an older save forks a new `generation` rather
  than rewriting history. Reachability-based garbage collection (git-model), not
  timestamp-based.
- **ADR-0005 (sync handshake):** A HELLO / RESOLVE / ACK protocol between the native plugin and
  the Python service. On load, the plugin sends a HELLO with what it knows (a manifest read from
  the save's SKSE co-save file); the service RESOLVEs that against its own event history into one
  of six decisions (CONTINUE / FORK / ADOPT / NEW_TIMELINE / LEGACY_IMPORT / DEGRADED); the
  plugin ACKs and resumes. Hard rule: **must never block gameplay**, even if the Python service
  is slow or unreachable.

This spec has already been through one internal review pass (an independent advisor model) that
found and fixed three real bugs — a `SetUniqueID` collision hazard with no defense-in-depth, an
unspecified write-ordering race on the `head_seq` field between a synchronous engine callback and
an asynchronous network acknowledgment, and a missing `Revert`-callback handler — plus a second
pass where the author did direct GitHub code-search research (not simulated) against real shipped
SKSE plugins (JContainers, Soulsy) to validate design choices where no authoritative spec exists.
Both passes' findings are already folded into the spec text below, marked as such. **Do not
re-raise those three already-fixed issues as if they were undiscovered** — instead, sanity-check
whether the fixes are actually correct and sufficient, and focus fresh scrutiny on what's still
open (§7's numbered list, especially items 2–5, which remain genuinely unresolved) and on
anything else a careful native-plugin engineer would catch that hasn't been raised yet.

## Your task

1. **Adversarial technical review** of the full spec below, as if you were the engineer about to
   implement it and wanted to catch mistakes before writing code. Look especially for: race
   conditions, thread-safety issues around the SKSE main thread vs. the HTTP client's callback
   thread, cases where the "never block gameplay" rule could be silently violated, and any gap
   in the RESOLVE decision table or the scenario-coverage table (§5) that doesn't actually hold
   up under scrutiny.
2. **Spot-check the cited research claims.** Where the spec says "researched directly... real
   examples found: X" with a repo/file citation, do you find those citations accurate if you
   can look them up? Report anything that looks fabricated, wrong, or out of date.
3. **Weigh in on the five open questions in §7**, especially #2 (the unquantified "large jump"
   threshold for forcing a player confirmation) and #5 (whether the new endpoints need the same
   `--live-run` gating as the rest of the codebase) — these are genuine unresolved design
   decisions, not just verification gaps.

Be concrete: cite the exact section/line of the spec you're responding to, and if you disagree
with a design choice, say what you'd do instead and why.

---

## The spec

# Design spec — ChronicleBridge's save/reload sync handshake (ADR-0004/0005 implementation)

**Status (2026-09-01): spec, not yet implemented.** Nothing in this doc exists in code yet —
`grep`ing ChronicleBridge's source for `SYNC_TIMELINE`, `TIMELINE_READY`, `g_isLoading`,
`epoch_id`, or `GetSerializationInterface` returns zero hits. The 12 scenario stubs under
`scenarios/sync/` are unexecutable for the same reason ("the SKSE shim and sync protocol don't
exist yet," per that directory's own README). This spec is the concrete build plan closing that
gap, written against the **actual verified SKSE API** (a fresh checkout of
`CharmedBaryon/CommonLibSSE-NG`, `include/SKSE/Interfaces.h`), not just ADR-0005's prose.

This spec implements `docs/decisions/0004-timeline-branching.md` (the branch-key/DAG model,
already built server-side in `chronicle/events.py`: `BranchKey`, `EventLog.fork()`) and
`docs/decisions/0005-sync-handshake.md` (the HELLO/RESOLVE/ACK protocol) inside
`adapters/skyrim/ChronicleBridge/` and `adapters/skyrim/listener/listener.py`. One correction to
ADR-0005 is folded in here (§1) rather than filed separately, since it only matters in the
context of the real implementation.

## 0. One correction to ADR-0005

ADR-0005 §3 writes `kPostLoadGame(success=true)`. The real `SKSE::MessagingInterface::Message`
struct has no `success` field:

```cpp
struct Message {
    const char*   sender;
    std::uint32_t type;
    std::uint32_t dataLen;
    void*         data;
};
```

`kPostLoadGame` fires unconditionally when SKSE's load sequence completes; there is no
false-flavored variant to distinguish. **Fix**: drop `(success=true)` from ADR-0005's text;
the handshake's own DEGRADED-mode / manifest-absent paths (§4 below) are what already cover
"load didn't go the way we expected," not a message-level success flag.

## 1. Verified SKSE API surface

Two separate interfaces, confirmed from `include/SKSE/Interfaces.h` (`kVersion = 4` for
`SerializationInterface`, `kVersion = 2` for `MessagingInterface`, this checkout):

**`SKSE::MessagingInterface`** (accessed via `SKSE::GetMessagingInterface()`) — the lifecycle
event bus ChronicleBridge already uses (`plugin.cpp`'s `OnSkseMessage`, currently handling only
`kDataLoaded` for the death-event sink). Relevant message types, confirmed verbatim:
`kPreLoadGame, kPostLoadGame, kSaveGame, kDeleteGame, kNewGame` (also present:
`kPostLoad, kPostPostLoad, kInputLoaded, kDataLoaded`). One `RegisterListener(callback)` per
plugin; dispatch is a single callback switching on `message->type`.

**`SKSE::SerializationInterface`** (accessed via `SKSE::GetSerializationInterface()`) — the
actual co-save mechanism. Not currently called anywhere in ChronicleBridge. Real methods:

```cpp
void SetUniqueID(std::uint32_t a_uid) const;
void SetLoadCallback(EventCallback* a_callback) const;    // EventCallback = void(SerializationInterface*)
void SetSaveCallback(EventCallback* a_callback) const;
void SetRevertCallback(EventCallback* a_callback) const;

bool WriteRecord(std::uint32_t a_type, std::uint32_t a_version, const void* a_buf, std::uint32_t a_length) const;
bool OpenRecord(std::uint32_t a_type, std::uint32_t a_version) const;      // read side: seek to a record of this type
bool GetNextRecordInfo(std::uint32_t& a_type, std::uint32_t& a_version, std::uint32_t& a_length) const;
std::uint32_t ReadRecordData(void* a_buf, std::uint32_t a_length) const;
```

Two things this confirms about ADR-0005's design, and one gap it leaves for us to decide:

- **The Save/Load/Revert callbacks are independent of the messaging events.** ADR-0005 already
  gets this right structurally ("manifest capture during the co-save Load callback... HELLO on
  `kPostLoadGame`") — the Load callback is where `ReadRecordData` actually runs; `kPostLoadGame`
  is a separate, later signal used only to know the engine has finished its own load sequence
  before we fire the network HELLO. Keep them separate in the implementation; do not try to do
  the HTTP call from inside the Load callback itself (SKSE serialization callbacks run on the
  main thread during the load sequence — network I/O there would stall the load).
- **`SetUniqueID` is mandatory and not yet decided.** Every plugin using `SerializationInterface`
  must pick a `uint32_t` identifying its section of the co-save file, distinct from every other
  mod's. **Decision needed (flagged for review, §7)**: pick a FourCC, e.g. `'CHRN'` (`0x4E524843`
  little-endian, or whatever byte order the codebase's existing FormID/type-tag conventions use —
  check `IdentityMap.cpp` for the established pattern before inventing a new one).
- **`WriteRecord`'s `a_type` parameter is exactly report 06's proposed `TMNL` FourCC marker** —
  the two designs (ADR text and real API) line up without adjustment. Use `'TMNL'` as the record
  type inside ChronicleBridge's `SetUniqueID`-scoped section.

## 2. New files

```
adapters/skyrim/ChronicleBridge/src/
  SyncHandshake.h / .cpp     -- new: owns g_isLoading, epoch_id, the manifest struct,
                                 SerializationInterface registration, and the state machine
                                 below. Analogous in shape to DeathEventSink.h/BarterMenuSink.h.
```

`plugin.cpp`'s existing `OnSkseMessage` gains new `case` branches for `kPreLoadGame`,
`kPostLoadGame`, `kSaveGame`, `kDeleteGame`, `kNewGame`, each forwarding into
`SyncHandshake::On*()`. `plugin.cpp`'s load routine gains one new call alongside its existing
`SKSE::GetMessagingInterface()` registration:

```cpp
if (auto* serialization = SKSE::GetSerializationInterface()) {
    serialization->SetUniqueID('CHRN');  // see open question, §7
    serialization->SetSaveCallback(SyncHandshake::OnGameSave);
    serialization->SetLoadCallback(SyncHandshake::OnGameLoad);
    serialization->SetRevertCallback(SyncHandshake::OnGameRevert);
} else {
    SKSE::log::error("ChronicleBridge: SKSE::GetSerializationInterface() returned null -- "
                      "save/reload sync will NOT function");
}
```

Server side: `adapters/skyrim/listener/listener.py` gains three new HTTP endpoints, following
the existing per-slice pattern exactly (same `X-Chronicle-Bridge-Token` bearer auth, same
`--live-run` 503-gating where applicable, a new `_SyncState` dataclass alongside
`_HydrationPairState`/`_AvoidancePairState`/etc.).

## 3. The manifest — binary layout (co-save side) and wire shape (HTTP side)

**Co-save record** (written via `WriteRecord('TMNL', version=1, ...)`, read via
`OpenRecord`/`GetNextRecordInfo`/`ReadRecordData`) — adopting ADR-0005's field table exactly,
sized concretely:

| Field | Type | Bytes | Notes |
|---|---|---|---|
| `save_uuid` | `uint8_t[16]` | 16 | UUIDv4, generated once per playthrough on `kNewGame` |
| `generation` | `uint64_t` | 8 | ADR-0004's fork counter |
| `parent_generation` | `uint64_t` | 8 | 0 for the root generation |
| `head_seq` | `uint64_t` | 8 | last **service-ACKed** event sequence — never "last attempted"; see §4.1 for the required atomic-read discipline on this field |
| `gamets` | `double` | 8 | bitemporal valid time (ADR-0004) |
| `wall_ts` | `int64_t` | 8 | bitemporal transaction time (ADR-0004), Unix ms |
| `char_name_hash` | `uint64_t` | 8 | display/debug only, never a lookup key |

Total: 56 bytes, **plus a mandatory 4-byte magic sentinel prefixed to the struct**
(`0x43485243`, `'CHRC'` — distinct from the `'CHRN'` `SetUniqueID` FourCC and the `'TMNL'`
record-type FourCC, so a mismatch on any of the three is independently detectable). This is not
redundant with `WriteRecord`'s own `a_version` parameter: `a_version` tells you *this plugin's*
schema version, but says nothing if a `SetUniqueID` collision (§7.1) routed a *different*
plugin's same-length record into this Load callback — a magic value that a legitimate write
always sets and a coincidental collision almost certainly won't is the actual defense there.
**On Load, before trusting any field: reject the record unless `GetNextRecordInfo`'s reported
`a_length == sizeof(Manifest)` (60 bytes total), the leading 4 bytes equal the magic sentinel,
and `a_version` is a version this build recognizes.** Fall through to LEGACY_IMPORT (§4) on any
mismatch — never deserialize a manifest that fails this check, since a `SetUniqueID` collision
producing a plausible-looking `save_uuid`/`generation` is silent timeline corruption, not a
loud failure.

**Wire shape** (HTTP, since ChronicleBridge already links `cpp-httplib` per `vcpkg.json` — no
new transport dependency): the same 56-byte manifest fields, JSON-encoded, become the body of
the three new listener endpoints below. `save_uuid` renders as a lowercase hex string (32 chars,
no dashes — match whatever convention `IdentityMap.cpp`/existing listener code already uses for
byte-string fields, check before inventing a second convention).

## 4. The HTTP protocol

Three endpoints on the listener, in the sequence ADR-0005 names (HELLO → RESOLVE → ACK), plus
one for steady-state event delivery:

### `POST /whiterun/sync/hello` (shim → service, on `kPostLoadGame`)

Body: the manifest fields as JSON (`save_uuid`, `generation`, `parent_generation`, `head_seq`,
`gamets`, `wall_ts`, `char_name_hash`), plus `manifest_present: bool` (false = LEGACY IMPORT
path, no co-save record was found — first run against a save predating this feature, or the
save/co-save pairing was lost).

Response: `{"decision": "CONTINUE"|"FORK"|"ADOPT"|"NEW_TIMELINE"|"LEGACY_IMPORT", "epoch_id": <uint64>, "resume_from_seq": <uint64 | null>, "confirm_required": <bool>}`
— implements ADR-0005's six-way RESOLVE table server-side. `confirm_required` is set true only
for large jumps per ADR-0005's "confirmed only for large jumps" rule (§7 names the threshold as
an open question, not yet a verified constant). `resume_from_seq` tells the shim where to
resume streaming `MUTATION_EVENT`s from (covers scenario 09,
`co-save-read-vs-notification-race`: any events the service already has past `head_seq` don't
need to be resent).

**Never blocks gameplay.** The shim fires this asynchronously off the main thread (the existing
listener HTTP client pattern in ChronicleBridge already does this for other slices — reuse it,
don't add a second HTTP client). If unreachable or slow, `g_isLoading` clears anyway after a
bounded timeout (see DEGRADED, §4.3) rather than stalling forever — this is what scenario 01
(`service-unreachable-at-load`) and scenario 12 (`load-time-spike-nonblocking`) assert.

### `POST /whiterun/sync/mutation` (shim → service, steady-state)

Body: `{"epoch_id": <uint64>, "save_uuid": ..., "generation": ..., "seq": <uint64>, "event": {...}}`
— the event payload itself is whatever shape the relevant slice already sends (hydration,
avoidance, etc.); this endpoint is a fencing wrapper around the existing per-slice injection
paths, not a new event schema. Server rejects (`409`, not `500` — this is an expected,
routine condition, not a server error) any mutation whose `epoch_id` is older than the
service's current active epoch for that `(save_uuid, generation)`. Dedupes on
`(save_uuid, generation, seq)` — idempotent replay, covers scenario 08
(`quicksave-autosave-spam`) and the documented SkyrimNet "cannot keep up with load" burst
condition.

### `POST /whiterun/sync/save-created` (shim → service, on `kSaveGame`)

Body: `{"save_uuid": ..., "generation": ..., "committed_through_seq": <uint64>}`. This is
ADR-0005 item 8's "uncommitted state between saves is volatile" rule made concrete: the service
buffers events since the last save keyed to the active branch, and this call is what commits
that buffer. No response body needed beyond a 2xx; fire-and-forget like the mutation endpoint.

### 4.1 State machine (shim side, in `SyncHandshake.cpp`)

```
g_isLoading:  bool, default false
epoch_id:     uint64, default 0
acked_head_seq: std::atomic<uint64_t>, default 0  -- see note below
outbound_queue: bounded ring buffer of pending MUTATION_EVENTs (DEGRADED spillover)

on kPreLoadGame:        g_isLoading = true
on SerializationInterface::Load callback (fires between kPreLoadGame and kPostLoadGame):
                        ReadRecordData into local manifest struct; if OpenRecord fails,
                        manifest_present = false
on kPostLoadGame:       fire POST /whiterun/sync/hello asynchronously (never blocks);
                        on response (or timeout -> DEGRADED): epoch_id = response.epoch_id;
                        g_isLoading = false; resume forwarding events, tagged with epoch_id
on kNewGame:            generate save_uuid = UUIDv4, generation = 0; treat as NEW_TIMELINE,
                        no HELLO round-trip needed (nothing to resolve against)
on kSaveGame:           fire POST /whiterun/sync/save-created (fire-and-forget)
on SerializationInterface::Save callback (OnGameSave, fires synchronously during the engine's
                        save sequence): WriteRecord's head_seq field is one relaxed load of
                        acked_head_seq -- never a value computed inline from in-flight request
                        state. The HTTP response handler for /whiterun/sync/mutation is the
                        *only* writer of acked_head_seq (store-release on each successful ACK,
                        monotonic -- never move it backward on an out-of-order response). This
                        is load-bearing: OnGameSave runs on the main thread mid-save, ACKs land
                        on whatever thread the HTTP client's callback fires on, and a torn or
                        optimistic head_seq written into the co-save produces a CONTINUE on next
                        load that silently skips events the service never actually committed --
                        exactly the condition scenario 08 (quicksave-autosave-spam) is meant to
                        stress.
on kDeleteGame:         no-op for this spec (co-save deletion is automatic/atomic-by-
                        convention per ADR-0005's residual-risk note; not this spec's job)

[Researched directly, 2026-09-01: no shipped SKSE plugin with asynchronous external state was
found that persists that state into the co-save at all. CHIM's actual game-side plugin has no
public source (only satellite tools -- installer, dashboard, TTS bridges -- are public under
Dwemer-Dynamics/*), so the "CHIM PR #572" reference earlier attributed to this class of bug
could not be verified and should be treated as unconfirmed, not cited as precedent. SkyrimNet's
game-side plugin (MinLL/SkyrimNet-GamePlugin) is pure Papyrus with no SerializationInterface use;
Mfg Fix NG (KrisV-777/Mfg-Fix-NG) is C++ but stateless, no SetUniqueID call. Every real
SetUniqueID user found (JContainers, Soulsy) only ever serializes state that's already
synchronously resident in-process at Save time -- none of them have this spec's specific
problem, because none of them bridge to an external async service at all. This atomic
acked_head_seq design has no negative precedent to contradict it, but also no positive precedent
to lean on; it should be treated as this spec's own reasoned design, not an industry-standard
pattern, when reviewed.]

on SerializationInterface::Revert callback (OnGameRevert, fires between kPreLoadGame and the
                        Load callback -- SKSE's designated "discard stale in-memory state" hook):
                        reset the in-memory manifest struct to empty, epoch_id = 0,
                        g_isLoading stays true (Load/kPostLoadGame haven't run yet). The
                        outbound_queue is dropped, not carried across -- anything still queued
                        belongs to the pre-reload branch and was, by definition, never
                        service-ACKed (else it wouldn't be in the queue), so ADR-0005 item 8's
                        "uncommitted state between saves is volatile" rule already covers it as
                        abandoned. This is the mechanism that makes scenario 06
                        (same-process-second-reload) actually correct, not just "no crash": without
                        an explicit Revert handler, a second reload in the same process would
                        start its HELLO with the *previous* load's stale epoch_id/manifest still
                        resident.

[Researched directly, 2026-09-01: two real shipped plugins confirm "wipe everything" is the
right shape for a non-trivial Revert handler, not an edge case this spec invented. Soulsy's
`revertHandler` (`ceejbot/soulsy`, `src/plugin/cosave.cpp`) is a one-line `clear_cache()`.
JContainers' `revert()` (`SilverIce/JContainers`, `src/skse_callbacks.cpp`) calls
`domain_master::master::instance().clear_state()` -- a full wipe of its entire in-memory
container graph. Neither example surfaced a documented "should survive Revert but commonly
doesn't" mistake to flag; both simply drop everything and rebuild from the next Load. This
spec's outbound-queue-drop + manifest-reset matches that pattern directly.]

while g_isLoading:      all per-slice event-generation hooks (dialogue, death, barter, etc.)
                        queue locally instead of transmitting -- this is the existing
                        per-sink pattern, just gated on one new flag they all check
```

### 4.2 State machine (service side, in `listener.py`)

New `_SyncState` per `(save_uuid, generation)`: `active_epoch: int`, `head_seq: int`,
`abandoned_at: float | None`. `RESOLVE` (inside the `/hello` handler) implements ADR-0005's
six-row table directly as a Python `match`/`if`-chain — this is plain, testable logic, no new
infra needed beyond what the listener already has (in-memory dict state, matching every other
slice's `_*_pairs`/`_apply_*_ack` pattern).

### 4.3 DEGRADED mode

Per ADR-0005's "never-block rule": if `/whiterun/sync/hello` doesn't respond within a bounded
timeout (proposed: 3 seconds — a starting tunable per this spec's own convention of flagging
unverified numbers, not a researched constant), the shim proceeds as if `epoch_id = 0` /
`decision = DEGRADED`, buffers outbound mutations in the ring buffer (spill to a local file if
the ring fills — mirroring the pattern already used elsewhere in the project for "sidecar file
as an out-of-process fallback"), and retries the HELLO on a backoff. On eventual reconnect,
buffered events replay through `/whiterun/sync/mutation` tagged with whatever epoch the (now-late)
HELLO response returns — the service-side idempotency/dedupe (§4, mutation endpoint) makes this
safe even if some of them raced ahead via a different path. Covers scenario 01 exactly.

## 5. Mapping to the 12 scenario stubs

Every stub in `scenarios/sync/` should become executable once this spec is built; this table is
this spec's own acceptance criterion, not aspirational:

| # | Scenario | Closed by |
|---|---|---|
| 01 | service-unreachable-at-load | §4.3 DEGRADED mode |
| 02 | crash-mid-save | Not fully closed — ADR-0005's own residual-risk note stands (`.skse`/`.ess` atomicity is convention-only); this spec doesn't add new mitigation beyond what ADR-0005 already flagged as open |
| 03 | save-copied-or-cloud-restored | RESOLVE's `ADOPT` branch, §4 |
| 04 | manifest-version-newer-than-plugin | `WriteRecord`'s `a_version` parameter + `GetNextRecordInfo` reporting a version the plugin doesn't recognize → treat as LEGACY_IMPORT, never crash on an unknown version |
| 05 | concurrent-second-writer-lost-update | Out of scope for *this* spec — this is a dashboard/API-vs-game race at the `chronicle/` state-store level, not the SKSE handshake; flag as a `chronicle/` concern in §7 |
| 06 | same-process-second-reload | The `OnGameRevert` handler in §4.1 — it wipes the in-memory manifest/epoch_id and drops the outbound queue between reloads, so a second reload's HELLO never starts from stale state left by the first |
| 07 | mod-uninstalled-mid-playthrough | Reachability-based GC (ADR-0004, already specified, server-side only) — no shim-side change needed; branches for an uninstalled mod's saves simply stop receiving HELLOs and eventually fall out of the retention window |
| 08 | quicksave-autosave-spam | §4, mutation endpoint's dedupe |
| 09 | co-save-read-vs-notification-race | §4, `/hello` response's `resume_from_seq` |
| 10 | unanchored-write-meets-gc-sweep | ADR-0004's mandatory (never-null) bitemporal fields — already specified, this spec doesn't touch it further |
| 11 | death-retry-silent-fork-vs-large-jump-confirm | RESOLVE's `confirm_required` flag, §4 (threshold itself is an open question, §7) |
| 12 | load-time-spike-nonblocking | §4.3 DEGRADED mode + the async-fire requirement in §4's HELLO description |

## 6. Test plan

Unit-testable without a live game (mirroring every other slice's `test_listener.py` pattern):
the six-way RESOLVE decision table (one test per row), epoch-fencing rejection (a mutation with
a stale epoch gets `409`, not applied), dedupe on `(save_uuid, generation, seq)` (a replayed
mutation is a no-op, not double-applied), and the DEGRADED buffering path (simulate an
unreachable service, assert the ring buffer fills and replays on reconnect). These become real
`adapters/skyrim/listener/test_listener.py` cases, same file every other slice's tests live in.

Live-game-only (needs the project's existing pytest-based live-test harness against a real
Skyrim process): an actual save→reload cycle asserting a `CONTINUE` decision with no data loss,
and a save→reload to an *earlier* save asserting a `FORK` with the abandoned suffix intact but
unreachable from the new branch head. **Blocked, currently**, on an open, separately-tracked
`game action=load` no-op bug in the live-test harness itself — that bug means `load` can't
currently be exercised via the test harness at all, independent of anything in this spec. The
unit-level tests above don't depend on that bug being fixed; the live-game tests do.

**Ship-gate, not a footnote:** FORK is the single highest-risk decision in the whole RESOLVE
table — it's the one path that deliberately abandons a branch of history — and it cannot be
empirically exercised end-to-end until the `game action=load` bug is fixed. Building this spec
now is still the right call (the unit tests validate the decision table's logic in isolation,
and the bug is orthogonal to this code), but "unit-tested" should not be read or reported as
"verified real reload produces a correct fork" — that claim stays open until the blocker clears
and the live-game tests above actually run.

## 7. Open questions for review

1. **`SetUniqueID`'s FourCC value** — proposed `'CHRN'`, not checked against whether any other
   installed mod in the project's test instances already claims it. Needs a real collision
   check, not just a plausible-looking tag. **Researched directly (GitHub code search across
   shipped SKSE plugin sources), 2026-09-01: there is no formal registry.** Real examples found:
   JContainers hardcodes `'JSTR'` (`0x4A535452`) for both `SetUniqueID` and its sole record type
   (`SilverIce/JContainers`, `src/jcontainers_constants.h`) — confirms reusing the same FourCC
   for both purposes is safe, since they're independent namespaces (uid scopes the plugin's
   co-save section; record types are only disambiguated *within* that section). Soulsy
   (`ceejbot/soulsy`, `src/plugin/cosave.cpp`) defaults to `'SOLS'` but makes it a
   **player-configurable INI setting** (`sSKSEIdentifier`) precisely so a collision can be
   resolved by the end user without a mod update — worth considering as a fallback mitigation if
   a real collision is ever reported, though not needed as a v1 requirement since Chronicle
   controls both ends of its own uid choice. The community's only informal cross-plugin catalog
   found is `SpookyPirate/spookys-cosave-cleaner`'s hardcoded `KNOWN_PLUGINS` dict (~18 entries,
   including JContainers, RaceMenu/SKEE `'SKEE'`, PapyrusUtil, OStim, others) — assembled by
   observing real save files, not any authoritative source; several entries are non-ASCII
   arbitrary hashes rather than readable FourCCs, meaning some mods already forgo the
   human-readable-tag convention entirely. **Conclusion: `'CHRN'` does not collide with any of
   the ~20 UIDs in that catalog or in the JContainers/Soulsy source, but "not in the one informal
   catalog anyone has bothered to compile" is the ceiling of due diligence available here** —
   there is no way to formally guarantee uniqueness. Proceed with `'CHRN'`.
2. **The "large jump" threshold for `confirm_required`** (scenario 11) — ADR-0005 explicitly
   leaves this unquantified ("death-retry silent-fork vs. large-jump confirm," no number given).
   Candidate: a `gamets` delta threshold (e.g. >1 in-game day), but this is a genuine design
   decision, not something this spec should silently pick.
3. **The DEGRADED-mode HELLO timeout** (proposed 3s, §4.3) and a Papyrus-property-cache delay
   ADR-0005 already flags (~200ms, "not a verified constant") both need empirical tuning against
   a real game process — neither can be verified from headers alone.
4. **Scenario 02 (crash-mid-save) and scenario 05 (concurrent-second-writer)** are named above
   as not fully closed by this spec — confirm that's the right scope cut (leave 02 as ADR-0005's
   already-documented residual risk, push 05 to a `chronicle/`-side design note) rather than
   silently expanding this spec to cover them.
5. **Whether `/whiterun/sync/*` should require `--live-run`** like the other slice endpoints, or
   run unconditionally (since the sync handshake needs to work even before a `--live-run` demo
   run exists, e.g. on a player's first-ever launch) — this spec assumes the latter but doesn't
   argue for it explicitly.
