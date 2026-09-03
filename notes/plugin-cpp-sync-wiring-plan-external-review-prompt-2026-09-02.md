<!--
INSTRUCTIONS FOR GEOFF (not part of the Kimi prompt — delete this comment or leave it, Kimi
will ignore an HTML comment):

1. Copy everything BELOW the "=====" divider and paste it as your first message to Kimi.
2. This review benefits from real GitHub code search against CommonLibSSE-NG / cpp-httplib if
   Kimi's session has browsing enabled — ask it to flag any claim it can't verify rather than
   guess at one.
3. Bring back whatever Kimi says (paste its reply, or save it as a file and hand me the path)
   and I'll fold anything useful into the plan before implementation starts.
-->

=====

You are reviewing an implementation *plan* (not code yet) for wiring a C++ state machine into an
SKSE (Skyrim Special Edition scripting extension) native plugin, before any code is written.
You have no other context beyond what's in this message — treat it as complete.

## Background

"Chronicle" is a Skyrim mod with a pure-Python event-sourced simulation core (`chronicle/`) and a
native SKSE C++ plugin (`ChronicleBridge`) that bridges game events to/from a local Python HTTP
service. Two of three layers of a save/reload "sync handshake" feature are already built and
independently verified:

1. **`SyncHandshakeCore.h/.cpp`** — a pure, SKSE-independent state machine, `197 passing checks`
   under ASan/UBSan. It has 12 pure transition functions, each `SyncState -> (SyncState,
   SyncSideEffects)`, where `SyncSideEffects` is a closed `std::variant` of plain-data effect
   descriptions (`SendHello`, `SendMutation`, `WriteCoSaveRecord`, `BufferMutationLocally`,
   `SpillMutationToFile`, `RotateSpillFile`, `ScheduleHelloRetryBackoff`,
   `CancelScheduledHelloRetry`, `LogWarning`, `LogInfo`, `NotifyPlayerNonModal`). This file never
   performs I/O itself — it only decides what should happen. The 12 transitions are:
   `OnPreLoadGame`, `OnLoadCallback`, `OnPostLoadGame`, `OnHelloResponse`, `OnHelloTimeout`,
   `OnHelloBackoffFire`, `OnNewGame`, `OnSaveGame`, `OnMutationReady`, `OnMutationAccepted`,
   `OnMutationRejected`, `OnMutationSendFailed`, `OnGameRevert`.
2. **Python listener HTTP endpoints** (`/whiterun/sync/hello`, `/whiterun/sync/mutation`) — 94
   passing tests, calls a pre-existing `chronicle.sync.resolve()` function.

The third layer — the actual SKSE glue that calls real `SerializationInterface`/
`MessagingInterface` APIs and makes real HTTP calls, wiring the pure state machine above into the
live plugin — has not been built yet. This plan is for that third layer.

**Confirmed real SKSE APIs in play** (verified against a real CommonLibSSE-NG header checkout):
`SKSE::MessagingInterface` fires one callback (`RegisterListener`) with a `message->type` field,
whose relevant values are `kPreLoadGame`, `kPostLoadGame`, `kSaveGame`, `kDeleteGame`, `kNewGame`,
`kDataLoaded`. Separately, `SKSE::SerializationInterface` offers `SetUniqueID`,
`SetLoadCallback`/`SetSaveCallback`/`SetRevertCallback`, and `WriteRecord`/`OpenRecord`/
`GetNextRecordInfo`/`ReadRecordData` for a plugin's own save-file co-save data. These are two
separate interfaces with separate callback registration.

**Existing `plugin.cpp` conventions** (7 existing feature slices, all following the same shape):
each slice with outbound HTTP traffic uses a mutex + condition-variable + `std::deque` queue,
drained by one dedicated sender thread spawned once in `SKSEPluginLoad`; all slices share one
`OutboundConfig` struct (one field per endpoint path, shared host/port/shared-secret). The closest
existing analog to "discrete, must-not-drop event, not a droppable 1Hz stream" is
`EventSenderThreadLoop`/`g_pendingEvents`/`EnqueueDeathEvent`. `OnSkseMessage` currently only
handles `kDataLoaded`.

**Existing `OutboundClient.h/.cpp` conventions**: every slice adds config fields for its own
path(s), a small POD payload struct, and a free `Post*`/`Fetch*` function doing one synchronous
`httplib::Client` call with a 1-second timeout (fully synchronous library — no async/callback
API; "asynchrony" is achieved purely by running the blocking call on a dedicated thread).
Existing JSON field parsers (`ParseJsonStringField`, `ParseJsonBoolField`, `ParseJsonIntField`,
`ParseJsonDoubleField`) are narrow, hand-rolled, single-field parsers with **no support for a
JSON `null` literal** — a real, confirmed gap, not something to assume already handled.

This plan has already been through one internal review pass by an independent advisor model,
which found and the plan below already incorporates fixes for:
- A cross-thread race on `WriteCoSaveRecord` (see design decision 2 below) — flagged as needing
  the transition-and-dispatch pair to happen under the same lock for that one effect only.
- An unpinned HELLO timeout that would otherwise silently inherit the existing 1-second
  convention instead of the value the spec calls for (see design decision 4 below).
- A scope-cut sanity check on mutation-send wiring (design decision 3) — confirmed as the right
  cut, not a hedge to relitigate.

**Do not re-raise those three already-addressed points as if undiscovered** — instead, sanity-
check whether the fixes described below are actually correct and sufficient, and focus fresh
scrutiny on anything else a careful native-plugin engineer would catch that hasn't been raised.

## Your task

1. **Adversarial review of the design decisions below**, as if you were about to implement this
   and wanted to catch a race, a deadlock, a lifetime bug, or a wrong SKSE-API assumption before
   writing code. Pay particular attention to:
   - Whether locking `g_syncState` for the *entire* `OnSaveGame` transition-plus-`WriteRecord`
     dispatch (described in decision 2) is actually safe — `WriteRecord` runs inside SKSE's
     `SetSaveCallback`, which the engine itself may call under constraints this plan doesn't
     enumerate. Is holding a plugin-owned mutex across that call actually risk-free, or could it
     interact badly with anything else touching co-save state at the same time?
   - Whether there's a deadlock or ordering hazard between the main thread (handling
     `kPreLoadGame`/`kPostLoadGame`/`kSaveGame`/`kNewGame` and the `SerializationInterface`
     callbacks) and the new dedicated sync-sender thread (handling `OnHelloResponse`/
     `OnHelloTimeout`/`OnHelloBackoffFire`), beyond the one race already fixed.
   - Whether mapping both an `httplib` timeout *and* a connection-failure result to the single
     `OnHelloTimeout` transition (decision 4) loses information `SyncHandshakeCore` actually
     needs, or is a safe simplification.
   - Anything about `SetUniqueID`/co-save record versioning that a real shipped SKSE plugin does
     differently than what's implied here (this project's spec previously found real, useful
     examples this way — JContainers and Soulsy are known real prior art for co-save patterns,
     if you have GitHub search available).
2. **Check the mutation-send scope cut (decision 3) is honestly stated.** The plan says the
   send/accept/reject/retry mutation path will be wired and correct, but nothing currently calls
   into it (no existing plugin slice emits sync-tracked mutations yet), so it ships as
   compiled-but-unexercised code. Is this an acceptable scope cut for a first landing, or does it
   hide a risk (e.g., should it not even be wired yet if it can't be tested)?
3. **Anything else** a careful reviewer would flag — file/thread lifetime issues at plugin
   unload, whether the two new `OutboundClient` functions should share more/less code with
   existing `Post*`/`Fetch*` functions, or gaps in the "files to create/change" list.

Be concrete: cite the exact numbered decision or file you're responding to, and if you disagree,
say what you'd do instead and why.

---

## The plan

# Wire SyncHandshakeCore into ChronicleBridge's plugin.cpp

## Context

The save/reload sync-handshake feature (`docs/design/chronicle-bridge-sync-handshake-out.md`) has
two of its three layers built and independently verified this session: the pure, SKSE-independent
`SyncHandshakeCore` state machine (`adapters/skyrim/ChronicleBridge/src/SyncHandshakeCore.h/.cpp`,
197 passing checks under ASan/UBSan) and the Python listener endpoints
(`adapters/skyrim/listener/listener.py`, 94 passing tests). Both were deliberately scoped to be
testable without the SKSE SDK or a live game. The third layer — the actual SKSE glue that calls
`SerializationInterface`/`MessagingInterface` and makes real HTTP calls — was explicitly deferred
because it's "honestly untestable until the `action=load` harness bug clears" (spec §7). That bug
is still open, but the owner has decided to close out this remaining piece of infrastructure now
rather than wait, since it's on the critical path to the live-verification gate GOALS.md records
(2026-09-02 entry): no real save/reload cycle can be exercised live until this wiring exists and
compiles.

This is genuinely new integration work, not mechanical transcription — it's the first time the
pure state machine, real `SerializationInterface` calls, and real `httplib` calls run together,
and it introduces this plugin's first persistent, cross-thread-written state machine (every
existing slice is either a pure poll/fetch/post loop or a fire-and-forget queue-drain). Given the
project's own established pattern this session (spec review before building caught 6 blocking
issues before any code existed), this plan is written to be reviewed by `advisor` and externally
by Kimi before implementation starts.

## What already exists (verified by direct reading, not assumed)

- `SyncHandshakeCore.h` (529 lines, read in full): 12 pure transition functions
  (`OnPreLoadGame`, `OnLoadCallback`, `OnPostLoadGame`, `OnHelloResponse`, `OnHelloTimeout`,
  `OnHelloBackoffFire`, `OnNewGame`, `OnSaveGame`, `OnMutationReady`, `OnMutationAccepted`,
  `OnMutationRejected`, `OnMutationSendFailed`, `OnGameRevert`), each `SyncState -> (SyncState,
  SyncSideEffects)`. Side effects are a closed `std::variant` (`SendHello`, `SendMutation`,
  `WriteCoSaveRecord`, `BufferMutationLocally`, `SpillMutationToFile`, `RotateSpillFile`,
  `ScheduleHelloRetryBackoff`, `CancelScheduledHelloRetry`, `LogWarning`, `LogInfo`,
  `NotifyPlayerNonModal`) — plain data, never performed by this file. The 68-byte `Manifest`
  struct, `ManifestToBytes`/`ManifestFromBytes`, and `kManifestMagic`/`kManifestRecordVersion`
  constants live here too.
- `plugin.cpp`'s existing pattern (read in full): `OnSkseMessage` dispatches on `message->type`
  (currently only `kDataLoaded`); every slice with outbound traffic uses a mutex+condvar+deque
  queue drained by one dedicated sender thread, all spawned in `SKSEPluginLoad`, all sharing one
  `OutboundConfig`. `EventSenderThreadLoop`/`g_pendingEvents`/`EnqueueDeathEvent` is the closest
  existing analog (discrete, must-not-drop events, not a 1Hz droppable stream).
- `OutboundClient.h/.cpp` (read in full): every slice adds fields to `OutboundConfig` for its own
  paths, a small POD payload struct, and a free `Post*`/`Fetch*` function doing one synchronous
  `httplib::Client` call with 1s timeouts. Existing JSON parsers (`ParseJsonStringField`,
  `ParseJsonBoolField`, `ParseJsonIntField`, `ParseJsonDoubleField`) handle single fields with no
  null-literal support — confirmed by this session's audit as a real, narrow gap, not built from
  scratch.
- `CMakeLists.txt`: `SyncHandshakeCore.cpp` is deliberately not yet in `add_commonlibsse_plugin`'s
  `SOURCES` list (per that file's own header comment) — needs adding once glue code calls it.

## Design decisions this plan makes (the actual new thinking, not just transcription)

1. **New files: `SyncHandshake.h`/`.cpp`**, exactly the name `SyncHandshakeCore.h`'s own header
   comment reserves for this. Owns the one piece of real mutable state this plugin will have:
   a mutex-guarded `SyncHandshakeCore::SyncState g_syncState`. Every entry point below follows the
   same shape: lock, call the pure transition function, copy out the new state and effects, unlock,
   *then* dispatch the effects — network/file I/O never happens while holding the state mutex.
2. **Thread ownership, stated explicitly** (this is the thing an implementer would otherwise
   invent): `OnPreLoadGame`/`OnPostLoadGame`/`OnNewGame`/`OnSaveGame` (via `OnSkseMessage`) and
   `OnLoadCallback`/`OnGameRevert` (via `SerializationInterface` callbacks) all run on the main
   thread, per SKSE's own contract and this codebase's existing comments. `OnHelloResponse`/
   `OnHelloTimeout` run on a **new dedicated sync-sender thread** (the HELLO POST blocks there,
   never on the main thread) — same never-block discipline as every existing sender thread.
   `OnHelloBackoffFire` fires from a simple timed retry on that same thread.

   **Locking pattern, with one deliberate exception:** every entry point locks `g_syncState`, calls
   the pure transition function, unlocks, then dispatches the returned effects — network/file I/O
   never happens while holding the mutex. The one exception is `OnSaveGame`: because the main
   thread and sync-sender thread both transition the same state and release the lock before
   dispatching, a `WriteCoSaveRecord` effect from one thread's transition could still be written
   after the *other* thread's later transition has already superseded it, producing a co-save
   whose bytes don't match the state that (nominally) produced them. Since `WriteCoSaveRecord` is
   pure local memory-to-`WriteRecord` (no network, no blocking), `OnSaveGame`'s transition *and*
   its `WriteCoSaveRecord` dispatch both happen **inside** the lock — the only side effect in this
   plan dispatched under the mutex. Every other effect keeps dispatch-outside-lock.
3. **Mutation-send scope, named honestly:** `OnMutationReady`/`OnMutationAccepted`/
   `OnMutationRejected`/`OnMutationSendFailed` are wired correctly and completely, but **no
   current ChronicleBridge slice actually calls `OnMutationReady` yet** — none of the 7 existing
   slices emit sync-tracked mutations today; they use their own pre-existing endpoints, unrelated
   to `/whiterun/sync/mutation`. Rerouting them (or wiring the future conversation-tier's
   utterance claims through this gate) is real, separate future work, not this lane's job — named
   here so nobody assumes mutation traffic exists yet just because the plumbing compiles.
4. **New `OutboundClient.cpp` work**: two new `OutboundConfig` paths (`syncHelloPath =
   "/whiterun/sync/hello"`, `syncMutationPath = "/whiterun/sync/mutation"`, matching the existing
   naming convention exactly), a `PostSyncHello` function returning `std::optional<HelloResponse>`
   (not `bool` — this is the first response whose *body* the plugin needs to parse, not just
   whose status matters), and a `PostSyncMutation` returning the raw HTTP status (200 vs. 409 vs.
   failure all mean different things to `SyncHandshakeCore`, unlike every existing fire-and-forget
   `Post*`). Parsing needs one genuinely new piece: a nullable-`uint64` field parser (for
   `replay_from_seq`), following `ParseJsonIntField`'s existing pattern, extended to detect a
   literal `null` before attempting to parse a number.

   **`PostSyncHello`'s timeout is explicit, not copied.** Every existing `Post*`/`Fetch*` function
   inherits `httplib::Client`'s 1s read timeout by copying an existing function body. The spec
   (§4.5, still open per §8b item 2) proposes 3s for HELLO specifically, since it can involve a
   RESOLVE computation on the listener side. `PostSyncHello` calls `set_read_timeout(3, 0)`
   explicitly with a comment pointing at §8b — do not let this silently inherit 1s. `httplib`
   surfaces a timeout and a connection failure as different `Result` error codes, but
   `SyncHandshakeCore` has only one transition for both (`OnHelloTimeout` — there's no separate
   "send failed" event for HELLO, unlike mutations which do have `OnMutationSendFailed`); map
   both error codes to `OnHelloTimeout`.
5. **`SyncHandshake.cpp` also owns**: `SetUniqueID('CHRN')`/`SetSaveCallback`/`SetLoadCallback`/
   `SetRevertCallback` registration (per the spec's own plugin.cpp snippet), the actual
   `ReadRecordData`/`WriteRecord`/`GetNextRecordInfo` calls translating to/from
   `SyncHandshakeCore::LoadRecordInfo`/`WriteCoSaveRecord`, and a `DispatchSideEffects` function
   that pattern-matches every `SyncSideEffect` variant to a real action (network call, co-save
   write, log line, or — for `BufferMutationLocally`/`SpillMutationToFile`/`RotateSpillFile` — the
   in-memory ring/spill-file mechanics the pure core already decided the *logic* for).

## Files to create/change

- **New**: `adapters/skyrim/ChronicleBridge/src/SyncHandshake.h`/`.cpp` — the glue described above.
- **`plugin.cpp`**: add `#include "SyncHandshake.h"`; add `kPreLoadGame`/`kPostLoadGame`/
  `kSaveGame`/`kNewGame` cases to `OnSkseMessage` (forwarding to `SyncHandshake::On*`); in
  `SKSEPluginLoad`, add the `SerializationInterface` registration block (spec's own snippet, fixed
  FourCC `0x4348524E`) and spawn the new sync-sender thread alongside the existing ones.
  `kDeleteGame` is deliberately NOT forwarded (`SyncHandshakeCore.h`'s own header comment explains
  why — it's pure plumbing with no sync-state bearing).
- **`OutboundClient.h`/`.cpp`**: the two new config paths, `PostSyncHello`, `PostSyncMutation`, and
  the new nullable-uint64 parser.
- **`CMakeLists.txt`**: add `src/SyncHandshakeCore.cpp` and `src/SyncHandshake.cpp` to `SOURCES`.

## Build/verify loop (cross-machine — Windows for compiling, this Linux box for everything else)

1. Write and commit the code here, push to `origin`.
2. `git pull` on the Windows checkout (`C:\Users\geoff\Desktop\Chronicle`), then build with the
   project's real, confirmed commands (checked directly against `CMakePresets.json`/README before
   writing this plan, not assumed): `cmake --preset release` followed by
   `cmake --build build/release`. Requires VS2022 + the "Desktop development with C++" workload,
   CMake 3.25.1+, vcpkg (`VCPKG_ROOT` set, `bootstrap-vcpkg.bat` already run), and Ninja — all
   already set up on that checkout from prior sessions' builds.
3. Read back compiler errors over SSH, fix, repeat. **No live-game verification is expected or
   claimed at the end of this — that's still blocked on `action=load` and is explicitly out of
   scope for this lane.**

## Verification

- C++ unit suite still green after the change: `cd adapters/skyrim/ChronicleBridge/tests && make
  clean && make && ./test_sync_handshake_core` (197 checks, unaffected by this lane, since it adds
  a caller rather than a modification to that file).
- Windows build succeeds cleanly via SSH using the commands above.
- **Success criteria for this lane is "it compiles cleanly," not "mutation sync works."** No
  current slice calls `OnMutationReady`, so the mutation send/accept/reject/retry path ships as
  real, complete, but *uncalled and therefore untested-in-practice* code — a clean build is the
  honest bar for roughly half of what this lane writes. Don't let a future reader mistake a clean
  build for verified mutation plumbing.
- No live-game test is part of this lane's success criteria — named explicitly so it isn't
  silently expected later.
