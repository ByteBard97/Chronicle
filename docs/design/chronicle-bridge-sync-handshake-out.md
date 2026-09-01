# Design spec — ChronicleBridge's save/reload sync handshake (ADR-0004/0005 implementation)

**Status (2026-09-01, v2): spec, not yet implemented — rewritten after two review passes found
the v1 draft's foundation wrong.** An internal advisor review first fixed three real bugs in v1
(a `SetUniqueID` collision hazard, an unspecified `head_seq` write-ordering race, a missing
`Revert` handler — those fixes below are stable and re-confirmed). A second, external review
(Kimi, with live GitHub verification) then found that v1's claim **"nothing exists in code yet"
was false for the service half** — `chronicle/sync.py` (330 lines, tested) already implements
RESOLVE, and a real design doc (`docs/design/chronicle-sync-cli-integration.md`) already exists
for wiring it in — plus six blocking coherence/correctness issues in the transport and semantics
layer this doc actually owns. This version is a restructure, not a patch: see "What changed from
v1" at the bottom. `grep`ing ChronicleBridge's C++ source for `SYNC_TIMELINE`, `TIMELINE_READY`,
`g_isLoading`, `epoch_id`, or `GetSerializationInterface` still returns zero hits — the shim side
is genuinely unbuilt, and that's still what this spec's C++ sections are for.

**The one fact that reshapes this spec's scope**, from `chronicle-sync-cli-integration.md` §0
(read in full before writing this version): `chronicle/framelog.py`'s on-disk run format bakes
exactly one `(save_uuid, generation)` pair per run directory, and `EventLog.fork()`
(`chronicle/events.py:216`) has no on-disk counterpart at all. **`resolve()` can correctly
*decide* FORK or ADOPT; nothing in this repo can *act* on either decision yet.** That's a
separate, larger, unscoped milestone (fork-on-disk support), not something this spec can build
as a side effect of the handshake. §4 below names this scope cut explicitly rather than writing
a protocol that quietly assumes a capability that doesn't exist.

This spec implements `docs/decisions/0004-timeline-branching.md` (branch-key/DAG model, built
server-side in `chronicle/events.py`) and `docs/decisions/0005-sync-handshake.md` (the
HELLO/RESOLVE/ACK protocol) inside `adapters/skyrim/ChronicleBridge/` and
`adapters/skyrim/listener/listener.py`, **calling into** the already-built
`chronicle/sync.py::resolve()` rather than re-specifying it. One correction to ADR-0005 (§0) and
one proposed correction to ADR-0005 item 8 (§4.4) are folded in here rather than filed
separately, since both only matter in the context of the real implementation.

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

Two separate interfaces, confirmed from a fresh `CharmedBaryon/CommonLibSSE-NG` checkout,
`include/SKSE/Interfaces.h` (`kVersion = 4` for `SerializationInterface`, `kVersion = 2` for
`MessagingInterface`), and re-verified independently by the Kimi review pass:

**`SKSE::MessagingInterface`** (`SKSE::GetMessagingInterface()`) — the lifecycle event bus
ChronicleBridge already uses (`plugin.cpp`'s `OnSkseMessage`, currently handling only
`kDataLoaded`). Relevant message types: `kPreLoadGame, kPostLoadGame, kSaveGame, kDeleteGame,
kNewGame`. One `RegisterListener(callback)` per plugin; dispatch is a single callback switching
on `message->type`.

**`SKSE::SerializationInterface`** (`SKSE::GetSerializationInterface()`) — the co-save mechanism,
not currently called anywhere in ChronicleBridge:

```cpp
void SetUniqueID(std::uint32_t a_uid) const;
void SetLoadCallback(EventCallback* a_callback) const;
void SetSaveCallback(EventCallback* a_callback) const;
void SetRevertCallback(EventCallback* a_callback) const;

bool WriteRecord(std::uint32_t a_type, std::uint32_t a_version, const void* a_buf, std::uint32_t a_length) const;
bool OpenRecord(std::uint32_t a_type, std::uint32_t a_version) const;
bool GetNextRecordInfo(std::uint32_t& a_type, std::uint32_t& a_version, std::uint32_t& a_length) const;
std::uint32_t ReadRecordData(void* a_buf, std::uint32_t a_length) const;
```

- **Save/Load/Revert callbacks are independent of the messaging events.** The Load callback is
  where `ReadRecordData` actually runs, on the main thread during SKSE's load sequence —
  `kPostLoadGame` is a later, separate signal used only to know the engine has finished before
  firing the network HELLO. Do not do the HTTP call from inside the Load callback itself.
- **`SetUniqueID` is `'CHRN'`** (see §7.1 for the collision research and the corrected hex value
  — v1 miscalculated this).
- **`WriteRecord`'s `a_type` parameter is `'TMNL'`**, the record type inside the `'CHRN'`-scoped
  section. Reusing a FourCC for both the plugin uid and its sole record type is a real, verified
  pattern (JContainers does exactly this with `'JSTR'`) — the two are independent namespaces, so
  no adjustment needed here.

## 2. Verified ChronicleBridge HTTP client model

**v1 got this wrong; this is the single most consequential correction in this revision.**
`OutboundClient.cpp`/`.h` (confirmed by direct read) is **fully synchronous cpp-httplib**: every
`Post*` function constructs a fresh `httplib::Client` per call with 1-second connect/write/read
timeouts, blocks on `client.Post(...)`, and checks the returned `httplib::Result` inline in the
same function. There is no async API, no callback registration, no persistent client object.
"Asynchronous, off the main thread" in this codebase means *running this blocking call on a
dedicated sender thread*, not a callback-based client.

Two consequences this spec must price in, that v1 didn't:

- **Correction (2026-09-01, second review pass):** the original claim here — "HELLO is the first
  request/response round-trip in the plugin's history" — was wrong and overstated the remaining
  work. `OutboundClient.cpp` already has real field-level response parsers (`ParseJsonStringField`,
  `ParseJsonBoolField`, `ParseJsonIntField`, `ParseJsonDoubleField`), used by existing `client.Get`
  call sites (e.g. hydration/vendor-markup pair fetches) that already parse a response *body*, not
  just a status code. **What's actually true, verified directly:** those parsers are narrow and
  per-field, with no null-literal handling — parsing HELLO's response (`decision` string,
  nullable `replay_from_seq`, two bools) is extending an existing, working pattern, not building
  one from scratch. The real remaining gap is narrower: a nullable-`uint64` field, and confirming
  HELLO is still the first response the *glue layer* needs to make a control-flow decision on
  (the existing parsers feed data structures, not RESOLVE-shaped branching).
- There is no "callback thread" to reason about — there is one sender thread that makes a
  blocking call and then, still on that same thread, updates shared state. This actually
  *simplifies* §5's atomic-write discipline (one writer thread, not an arbitrary callback
  context) but v1's wording ("whatever thread the HTTP client's callback fires on") would have
  sent an implementer looking for a mechanism that doesn't exist.
- The proposed 3-second HELLO timeout (§4.3) is longer than the established 1-second
  per-request convention. Reusing the existing client config verbatim gives 1s, not 3s — pick
  knowingly (§7.3).

## 3. The manifest — binary layout (co-save side) and wire shape (HTTP side)

**Co-save record** (`WriteRecord('TMNL', version=1, ...)`, read via
`OpenRecord`/`GetNextRecordInfo`/`ReadRecordData`), adopting ADR-0005's field table:

| Field | Type | Bytes | Notes |
|---|---|---|---|
| `save_uuid` | `uint8_t[16]` | 16 | UUIDv4, generated once per playthrough on `kNewGame` |
| `generation` | `uint64_t` | 8 | ADR-0004's fork counter |
| `parent_generation` | `uint64_t` | 8 | 0 sentinel for the root generation — **converted to Python `None` at the HTTP boundary** (§4.1a), since `chronicle.sync.Manifest.parent_generation: int \| None` treats `None` as the meaningful "no ancestor" value, not `0` |
| `head_seq` | `uint64_t` | 8 | last **durably-committed** event sequence — see §4.4, this definition changed from v1 |
| `gamets` | `double` | 8 | bitemporal valid time (ADR-0004) |
| `wall_ts` | `int64_t` | 8 | bitemporal transaction time (ADR-0004), Unix ms — **`chronicle.events.Event.wall_ts` is a `float` of Unix *seconds*; convert `ms → s` at the HTTP boundary (§4.1a), never inside the co-save or the C++ layer** |
| `char_name_hash` | `uint64_t` | 8 | display/debug only, never a lookup key |

Sum of the seven fields: `16 + 8×6 = 64` bytes (**v1 miscounted this as 56 — a plain arithmetic
error that a `static_assert` would have caught immediately; see C1's fix below**). Plus a
mandatory 4-byte magic sentinel prefixed to the struct (`0x43485243`, `'CHRC'` — distinct from
the `'CHRN'` uid and `'TMNL'` record-type FourCCs): **total struct size is 68 bytes, not 60.**
The sentinel defends against a `SetUniqueID` collision: `a_version` alone can't detect a
*different* plugin's same-length record landing in this Load callback, but a magic value a
legitimate write always sets and a coincidental collision almost certainly won't is real
defense-in-depth. **On Load: reject the record unless `GetNextRecordInfo`'s length ==
`sizeof(Manifest)` (68), the leading 4 bytes match the sentinel, `a_version` is recognized, AND
`ReadRecordData`'s own return value also equals 68** (checking only `GetNextRecordInfo`'s
reported length and not the actual bytes read is an easy way to silently accept a truncated
read). Fall through to LEGACY_IMPORT on any mismatch — never deserialize a manifest that fails
this check.

**Struct packing:** the field order above (16-byte array, then eight-byte scalars) puts the
first `uint64_t` at offset 20 under natural alignment, which is not 8-byte aligned — the struct
must be `#pragma pack(push, 1)` (or reordered 8-byte-fields-first) with a
`static_assert(sizeof(Manifest) == 68)` right next to the definition. Do not rely on eyeballing
the arithmetic (see above).

**Wire shape** (HTTP, `cpp-httplib` already linked): the manifest fields as JSON, `save_uuid` as
lowercase 32-char hex (no dashes), forming the body of the endpoints in §4.

**Golden fixture (generated 2026-09-01, `<I` + raw 16 bytes + `<QQQdqQ`, little-endian, matching
`#pragma pack(push, 1)`):** given `magic=0x43485243`,
`save_uuid=0123456789abcdef0123456789abcdef` (16 raw bytes), `generation=0`,
`parent_generation=0`, `head_seq=42`, `gamets=123.5`, `wall_ts=1735689600123` (int64 ms),
`char_name_hash=0xdeadbeefcafebabe`, the 68-byte struct is exactly:

```
435248430123456789abcdef0123456789abcdef000000000000000000000000000000002a000000000000000000000000e05e407b7c291f94010000bebafecaefbeadde
```

**Both the C++ struct-packing test and the Python boundary-layer test must reproduce this exact
byte string from these exact field values** (and parse it back to the same values) — a
cross-language round-trip fixture, not just an in-language one. This is what catches an
arithmetic or byte-order error mechanically instead of by hand (this spec has already produced
two: the 56-vs-64 field-sum error and the `'CHRN'` byte-order slip, §7). Note `generation=0` /
`parent_generation=0` here means the co-save's `0`-sentinel for root — the Python side must
still convert `parent_generation` to `None` before constructing a `chronicle.sync.Manifest` (§3
above); the fixture's raw bytes stay `0`, only the parsed Python value differs.

## 4. Scope: what this spec makes actionable, and what it names but cannot close

`chronicle.sync.resolve()` returns six decisions. Given the fork-on-disk gap named at the top of
this doc, this spec splits them:

- **CONTINUE, NEW_TIMELINE, DEGRADED — fully actionable end-to-end. Build these.**
- **FORK, ADOPT, LEGACY_IMPORT — `resolve()` correctly decides these; nothing in the repo can
  act on them yet** (no on-disk fork mechanism, no live-run-creation path wired to this
  handler). The `/hello` response carries the decision honestly (so logging, telemetry, and a
  future actionable implementation all see real data) plus `"actionable": false`. **The shim's
  behavior on `actionable: false` is identical to DEGRADED**: buffer outbound mutations locally,
  log loudly (visible to the player as "a save conflict was detected; timeline forking isn't
  supported yet in this build" — exact copy is a UX decision outside this spec), and do not tag
  or send events under a branch identity the service can't actually create. This is the same
  "refuse loudly at the boundary, don't silently no-op" idiom `chronicle/cli.py`'s
  `_inject_write` already uses for the same underlying gap.

This means **scenario 03 (save-copied-or-cloud-restored) and scenario 11
(death-retry-silent-fork-vs-large-jump-confirm) cannot be closed by this spec** — both require
ADOPT/FORK to be actionable. §6's scenario table reflects this; treat it the same way §8's
ship-gate paragraph already treats FORK-verification: named, not silently claimed.

### 4.1 The HTTP protocol

Two endpoints for v1 (v1 draft had three; `save-created` is folded into the mutation endpoint's
commit semantics, §4.4):

#### `POST /whiterun/sync/hello` (shim → service, on `kPostLoadGame`)

Body: the manifest fields as JSON, plus `manifest_present: bool` (false = no co-save record
found — pre-feature save, or the save/co-save pairing was lost) and `hello_seq: uint64` (§4.2,
B2's fix — a per-load monotonic counter the shim assigns).

Response: `{"decision": "CONTINUE"|"FORK"|"ADOPT"|"NEW_TIMELINE"|"LEGACY_IMPORT"|"DEGRADED", "actionable": bool, "epoch_id": <uint64>, "replay_from_seq": <uint64 | null>, "confirm_required": <bool>, "hello_seq": <uint64>}`
— `hello_seq` echoes the request's, so the shim can discard a stale response (§4.2). `actionable`
per §4 above. `replay_from_seq` is `resolve()`'s own CONTINUE-row output (populated when the
*service's* committed head_seq is ahead of the manifest's — **not** the shim replaying anything
to the service; v1 had this backwards, see §4.4).

**Handler implementation: constructs a `chronicle.sync.Manifest` and `chronicle.sync.BranchState`
from the HTTP body plus this service's durable per-`save_uuid` session state (§4.3), then calls
`chronicle.sync.resolve()` directly — this spec adds transport, session durability, and the C++
shim; it does not re-derive the six-way decision table.** `parent_generation`'s `0`-sentinel →
`None` conversion and `wall_ts`'s `ms`→`s` conversion (§3) happen here, at the boundary, once.

**`BranchState` simplifies for v1.** `BranchState.known_generations` is a `frozenset[int]` in
general (`sync.py` supports multiple generations per `save_uuid` — real fork history). But since
FORK/ADOPT are not actionable yet (§4), this service **never creates a second generation**: the
durable sidecar (§4.3) only ever needs to store one `(generation, head_seq, head_gamets)` triple
per `save_uuid`, and `BranchState` is built as `known=True, head_generation=<that generation>,
known_generations={<that generation>}` (or `known=False` if the sidecar has no entry yet).
`resolve()` still correctly returns FORK/ADOPT when a manifest doesn't match that single
generation — the service just can't act on it — so this simplification costs nothing in
correctness and removes real complexity from the v1 implementation. Revisit when fork-on-disk
lands.

**Never blocks gameplay.** Fired asynchronously off the main thread via the existing sender-thread
pattern (§2) — reuse it, don't add a second client. If unreachable or slow, `g_isLoading` clears
anyway after a bounded timeout (§4.5) rather than stalling forever.

#### `POST /whiterun/sync/mutation` (shim → service, steady-state)

Body: `{"epoch_id": <uint64>, "save_uuid": ..., "generation": ..., "seq": <uint64>, "event": {...}}`.
Server rejects (`409`) any mutation whose `epoch_id` is older than the session's current active
epoch (`chronicle.sync.mutation_admissible()`, already built). **On acceptance, the handler
calls `EventLog.append(event)` synchronously, in the same request, before replying 2xx** — this
is the commit point (§4.4). Dedup on `(save_uuid, generation, seq)` is `EventLog.append()`'s
existing idempotent-no-op behavior, already built and tested (`events.py:206-214`) — no second
dedup mechanism needed.

**Shim-side 409 handling (§5, B3's fix, unspecified in v1):** drop the rejected event (it belongs
to an epoch this session has moved past), log loudly, increment a per-session counter; if 409s
exceed a small threshold in a short window, re-fire HELLO (possible epoch desync) rather than
looping silently.

### 4.2 Epoch/hello fencing against quickload spam (B2's fix)

v1 fixed the `acked_head_seq` write race and then left two more of the same shape:
`g_isLoading` and `epoch_id` must also be `std::atomic` (or folded into one mutex-guarded state
struct) — both are written from the sender thread and read from the main thread and per-slice
sinks.

Beyond that: a bare HELLO round-trip has its own race under rapid quickload-quickload. Sequence:
`kPreLoadGame` → HELLO A in flight → player quickloads again before A answers → Revert wipes
state → HELLO B fires. If A's response arrives after B's, it would overwrite `epoch_id` with the
stale, previous load's value — exactly the wrong-epoch condition fencing exists to prevent,
reintroduced one layer up. **Fix:** a monotonic `hello_seq`, incremented on every `kPostLoadGame`,
sent with the request and echoed in the response (§4.1); discard any response whose `hello_seq`
isn't the current one. The DEGRADED backoff-retry loop (§4.5) needs the same discipline: cancel
it on `kPreLoadGame`/Revert, or a retry from the previous load can land mid-new-load.

**`kNewGame` sends HELLO too (B4's fix).** v1 skipped HELLO on `kNewGame` ("nothing to resolve
against"), which leaves epoch 0 simultaneously meaning "legitimate genesis epoch" and "DEGRADED
placeholder," undefined fencing for an unknown branch, and a same-session immediate autosave
(the Helgen-intro case) racing ahead of the service ever learning the branch exists. Sending
HELLO unconditionally is cheaper than special-casing: `resolve()`'s NEW_TIMELINE row already
handles "service has never seen this save_uuid" correctly.

### 4.3 Session durability (A3's fix)

`_SyncState` (`active_epoch`, `committed_head_seq`, `hello_seq`) **cannot live only in the
listener's in-memory dicts**, unlike `_HydrationPairState`/`_AvoidancePairState`/etc. Those are
safe to lose on restart because their state is recomputable by re-polling a run's frame log.
Branch/epoch/commit state is not recomputable from anything the listener currently reads — after
a restart, service `head_seq` would silently reset to 0 while the co-save manifest says N,
producing spurious ADOPT/amnesia on the next HELLO while the shim still believes prior sequences
were committed. **This is the one slice where a listener restart is silent timeline corruption,
not a soft retry, if left in-memory.**

**v1 scope for this fix:** a durable sidecar (e.g. one JSON file per `save_uuid` under a
sync-state directory, written synchronously on every epoch bump and every committed `head_seq`
advance) — not the larger "move branch/epoch state into `chronicle/`, listener as thin
transport" architecture Kimi's review also raised as the *correct* long-term direction. That
larger move is real and worth doing, but it's a bigger project than this spec (it also implies
resolving the run/live-session model mismatch named in §4 below) — name it, don't build it here.
**Required test:** restart the listener process, re-send the same manifest as a HELLO, assert
CONTINUE (not ADOPT, not amnesia).

### 4.4 `head_seq`: ACKed *is* committed, not "ACKed pending a separate commit" (A4/A5's fix)

ADR-0005 item 8 describes a *volatile buffer* between mutation-ACK and `SAVE_CREATED`-triggered
commit. **No such buffer exists anywhere in this codebase** — `chronicle.events.EventLog` is a
plain in-memory Python object with no staging/commit distinction, and there is no other
candidate implementation. Building a real volatile-buffer-plus-commit-signal mechanism from
scratch, on top of everything else in this spec, is more machinery than the actual risk
justifies. **This spec instead makes the mutation endpoint's 2xx response the commit point**
(§4.1): a mutation is durably in `EventLog` (and, once §4.3's durability lands, in the
session's durable state) before the shim is told it succeeded. There is no gap in which an
event can be "ACKed but not really there."

Consequence: `head_seq` in the manifest means exactly one thing — the last event sequence the
service has durably appended, full stop — which is what ADR-0005's own field-table description
already said ("last service-ACKed... so a save can never reference uncommitted state"); this
fix makes that description *true by construction* instead of aspirational. `SAVE_CREATED`
becomes a lighter-weight signal: a natural trigger for the service to checkpoint/flush its
per-branch state to durable storage (§4.3's sidecar, or eventually a `framelog.py` run
directory), not a commit gate. **This is a proposed correction to ADR-0005 item 8's language** —
flag it there, not just here, since another design doc may still be reading item 8 literally.

This also resolves v1's replay-direction confusion (A5): `resolve()`'s CONTINUE row already
computes `replay_from_seq` for exactly the case where the *service* has committed more than the
manifest's `head_seq` claims (e.g. after the crash-recovery scenario A4 originally worried
about) — that's server-side derived-state bookkeeping the shim doesn't need to act on, since the
shim never consumes committed events back from the service in this architecture. v1's
`outbound_queue` (§4.5) is not a "replay buffer" in the ADR-0005 sense at all — it's purely the
shim's local holding pen for mutations *not yet successfully POSTed*, and Revert correctly drops
it: anything still queued was never committed (by this section's new definition), so dropping it
on reload matches ADR item 8's "discarded, never happened in any surviving timeline" intent
exactly, just for the right reason now.

### 4.5 DEGRADED mode

If `/whiterun/sync/hello` doesn't respond within a bounded timeout (proposed 3s — a tunable,
picked knowingly per §2/§7.3, not inherited silently from the 1s per-request default), the shim
proceeds as `decision = DEGRADED`, buffers outbound mutations in a bounded ring buffer (spilling
to a local file if the ring fills; **the spill file I/O runs on the sender thread, never the
main thread** — D2's fix), and retries HELLO on a backoff **that is cancelled on the next
`kPreLoadGame`/Revert** (§4.2) rather than allowed to fire mid-new-load. On reconnect, buffered
mutations replay through `/whiterun/sync/mutation` under whatever epoch the (now-late) HELLO
returns — service-side dedup makes this safe even if some raced ahead another way. **Revert must
also delete/rotate the spill file**, not just the in-memory ring (v1 only mentioned the ring) —
otherwise stale pre-reload events replay into the new branch.

`actionable: false` (§4) is handled identically to DEGRADED for outbound buffering purposes.

### 4.6 `confirm_required` — deferred to notification-only for v1 (A6's fix)

v1 specified a `confirm_required` flag with no owner, no rendering mechanism, and — the real
problem — no meaning: by `kPostLoadGame` the engine has already loaded the world; there is no
game-state action a "confirm" can gate, since you cannot un-fork state that's already loaded.
**v1 for this spec: `confirm_required` (when the large-jump threshold, §7.2, trips) produces a
non-modal notification plus a permanent audit record of the FORK (silent or flagged) written to
the service's log/dashboard.** No blocking dialog, no "decline" branch to define, because no one
has specified what declining would do. Interactive confirm is deferred until that's answered.

## 5. New files and callback wiring

```
adapters/skyrim/ChronicleBridge/src/
  SyncHandshake.h / .cpp     -- owns g_isLoading, epoch_id, hello_seq, acked/committed head_seq
                                 tracking, the manifest struct, SerializationInterface
                                 registration, and the state machine in §4.
```

**Requirement, not a preference (D4's fix, upgraded on this build-readiness pass):** the state
machine in §4 MUST be written as a pure transition function — `(current state, event) -> (new
state, side effects)`, no `SKSE::` types, no I/O, in its own translation unit with no
SKSE/Windows dependency in its signature — mirroring why `chronicle.sync.resolve()` being a pure
function is what made it testable at all. This project has **no C++ test harness today**, and
the live-game path is separately blocked (§7); a pure transition function is the *only* way the
riskiest new component in this spec gets any test coverage before it ships. `SyncHandshake.h/.cpp`
splits into two pieces on this basis: the pure state machine (testable by a plain C++ test `main`,
no SKSE runtime needed), and thin SKSE glue (callback registration, the actual
`ReadRecordData`/`WriteRecord` calls, the actual `httplib` call) that calls into it — the glue is
honestly untestable until the `action=load` harness bug clears (§7), but the state machine it
wraps does not have to be.

`plugin.cpp`'s `OnSkseMessage` gains `case` branches for `kPreLoadGame`, `kPostLoadGame`,
`kSaveGame`, `kDeleteGame`, `kNewGame`, forwarding into `SyncHandshake::On*()`. Its load routine
gains:

```cpp
if (auto* serialization = SKSE::GetSerializationInterface()) {
    serialization->SetUniqueID('CHRN');  // 0x4348524E — see §7.1
    serialization->SetSaveCallback(SyncHandshake::OnGameSave);
    serialization->SetLoadCallback(SyncHandshake::OnGameLoad);
    serialization->SetRevertCallback(SyncHandshake::OnGameRevert);
} else {
    SKSE::log::error("ChronicleBridge: SKSE::GetSerializationInterface() returned null -- "
                      "save/reload sync will NOT function");
}
```

**`OnGameRevert`** (fires between `kPreLoadGame` and the Load callback — SKSE's "discard stale
in-memory state" hook, confirmed by two shipped-plugin precedents: Soulsy's one-line
`clear_cache()`, JContainers' `domain_master::master::instance().clear_state()`): reset the
manifest struct, `epoch_id = 0`; drop the outbound ring buffer and delete/rotate the spill file
(§4.5); `g_isLoading` stays true. **D3's correction to v1's reasoning:** Revert does *not* only
fire mid-load — it also fires on quit-to-main-menu with no subsequent load (harmless here,
nothing gates on the menu state) and does *not* fire on the very first load after process start
(no prior session to revert) — initial-state cleanliness must come from construction defaults,
not from assuming Revert always runs first.

**Event-generation gating (D1's fix):** gate the *drain* — the sender threads — on
`g_isLoading`/`actionable`, not every individual per-slice event-generation hook. The existing
architecture already funnels output through mutex'd sender queues; touching the drain point is
less invasive and less race-prone than instrumenting every sink individually.

**`OnGameSave` / `kSaveGame` timing (D5's fix):** whatever value is written into the co-save's
`head_seq` field and whatever value the service later sees for `committed_through_seq`-equivalent
bookkeeping must be the *same* atomic read, sampled once, not two separate reads that can skew
under a concurrent ACK landing between them.

## 6. Mapping to the 12 scenario stubs

| # | Scenario | Status |
|---|---|---|
| 01 | service-unreachable-at-load | Closed — §4.5 DEGRADED mode |
| 02 | crash-mid-save | Substantially mitigated, not fully closed — `resolve()`'s manifest-ahead-of-service row (ADOPT-shaped) is the standing partial mitigation for a service that lost committed state; `.skse`/`.ess` atomicity itself is still convention-only per ADR-0005's residual-risk note |
| 03 | save-copied-or-cloud-restored | **Not closed by this spec** — needs `resolve()`'s ADOPT to be actionable, blocked on fork-on-disk (§4) |
| 04 | manifest-version-newer-than-plugin | Closed — `resolve()`'s `format_version` gate → LEGACY_IMPORT, already built and tested |
| 05 | concurrent-second-writer-lost-update | Out of scope for this spec — a `chronicle/` state-store concern, not the SKSE handshake |
| 06 | same-process-second-reload | Closed — `OnGameRevert` (§5) wipes manifest/epoch/queue between reloads |
| 07 | mod-uninstalled-mid-playthrough | Closed — reachability-based GC (ADR-0004, server-side only, no shim change needed) |
| 08 | quicksave-autosave-spam | Closed — §4.1 mutation endpoint's `EventLog.append()` idempotency |
| 09 | co-save-read-vs-notification-race | Closed — §4.1's `replay_from_seq`, correctly understood as service-side bookkeeping (§4.4) |
| 10 | unanchored-write-meets-gc-sweep | Closed — ADR-0004's mandatory bitemporal fields, untouched by this spec |
| 11 | death-retry-silent-fork-vs-large-jump-confirm | **Not closed by this spec** — needs FORK to be actionable, blocked on fork-on-disk (§4); the threshold itself is answered in §7.2 regardless |
| 12 | load-time-spike-nonblocking | Closed — §4.5 DEGRADED mode + async-fire requirement |

## 7. Test plan

Unit-testable without a live game: the Python side re-uses `chronicle/tests/test_sync.py`'s
existing coverage of `resolve()` directly (no new tests needed for the decision table itself);
new tests belong in `adapters/skyrim/listener/test_listener.py` for the transport/session layer
this spec adds — epoch-fencing rejection (409), the mutation-endpoint commit-on-2xx behavior
(§4.4), and the §4.3 listener-restart→CONTINUE durability test.

C++-side (**D4's fix — v1 claimed a Python test for a C++ component, which is impossible**):
the project has no C++ test harness at all today. If `SyncHandshake.cpp`'s state machine is
structured as a pure transition function (§5), it becomes unit-testable in principle the same
way `resolve()` is — but building that harness is itself new scope this spec should name, not
assume. Until it exists, the state machine's correctness rests on the live-game tests below plus
careful review.

Live-game-only: an actual save→reload cycle asserting CONTINUE with no data loss, and (once
fork-on-disk unblocks ADOPT/FORK) a reload to an earlier save asserting FORK with the abandoned
suffix intact but unreachable. **Blocked, currently**, on the open `game action=load` no-op bug
in the live-test harness — `load` can't be exercised via the harness at all right now,
independent of anything in this spec. **D6's addition:** the harness does have a working
`loadLast` workaround already documented (`livetest/test_30_hydration.py:75-89`) — by-name
`load` no-ops, but `loadLast` works — which may partially unblock live reload testing for the
CONTINUE path sooner than the underlying bug fix.

**Ship-gate, not a footnote:** FORK is the highest-risk decision in the whole table and — even
setting aside that it's currently unactionable (§4) — cannot be empirically exercised end-to-end
until the `action=load` bug clears. "Unit-tested" should never be read as "verified a real
reload produces a correct fork."

## 8. Decisions and open questions

### 8a. Decided — an implementer should treat these as settled, not as things to relitigate

- **§4.4's commit-on-mutation-ACK redefinition of `head_seq`.** No volatile pre-commit buffer
  exists anywhere in the codebase (verified directly against `chronicle/events.py`); building one
  from scratch to satisfy ADR-0005 item 8's literal wording would be new machinery in service of
  a gap that doesn't otherwise need to exist. Decision: commit-on-ACK, as specified in §4.4. This
  is also a proposed correction to ADR-0005 item 8 itself — flag it there when this spec lands,
  since another doc may still read item 8 literally.
- **`SetUniqueID`'s FourCC.** Researched directly (GitHub code search across shipped SKSE plugin
  sources, corroborated independently by the Kimi review pass), 2026-09-01: **no formal registry
  exists.** JContainers hardcodes `'JSTR'` (`0x4A535452`) for both `SetUniqueID` and its sole
  record type (`SilverIce/JContainers`, `src/jcontainers_constants.h`) — confirms reusing one
  FourCC for both purposes is safe (independent namespaces). Soulsy (`ceejbot/soulsy`,
  `src/plugin/cosave.cpp`) defaults to `'SOLS'` but makes it a **player-configurable INI setting**
  (`sSKSEIdentifier`) so a collision can be resolved without a mod update. The only informal
  cross-plugin catalog found, `SpookyPirate/spookys-cosave-cleaner`'s hardcoded `KNOWN_PLUGINS`
  dict (24 entries, confirmed by the Kimi pass — corrected from an earlier undercount of 18),
  doesn't contain `'CHRN'` in either byte order. A C++ multichar literal `'CHRN'` is `0x4348524E`
  — v1 of this spec had `0x4E524843`, byte-reversed, the exact class of error this section warned
  readers to check for; compare `'CHRC'` (§3) computed correctly as `0x43485243`. **Decision:
  proceed with `'CHRN'` (`0x4348524E`), exposed as an INI-overridable setting from day one**
  (Soulsy's pattern, adopted now rather than as a future fallback) — ChronicleBridge already has
  an ini-backed `Config.cpp`, so this is nearly free and turns a future collision report into a
  config edit instead of a mod update.
- **Scenario 02 and scenario 05's scope cuts** — confirmed correct on review (§6); 02 now cites
  `resolve()`'s ADOPT-shaped mitigation rather than reading as wholly unmitigated, 05 stays a
  `chronicle/`-side concern.

### 8b. Genuinely open — needs a decision or empirical data before/soon after implementation

1. **The "large jump" threshold for `confirm_required`** (now notification-only, §4.6):
   proposed `(head_gamets − manifest.gamets) > 24 game-hours OR (head_seq − manifest.head_seq) >
   50 events`, both INI-tunable, every FORK decision (silent or flagged) logged with its inputs.
   Never `wall_ts` — real-time delta measures a player's lunch break, not the jump. The seq leg
   catches a short, event-dense session; the gamets leg catches a long in-game skip with few
   events. Neither alone is ungameable; the OR is honest, not perfect — the *shape* of the rule
   is decided, the two constants are the open part, pending real play data.
2. **The DEGRADED-mode HELLO timeout** (proposed 3s, §4.5 — deliberately longer than the 1s
   per-request convention since this is once-per-load, not steady-state) and a
   Papyrus-property-cache delay ADR-0005 already flags (~200ms, unverified) both need empirical
   tuning against a real game process.
3. **`--live-run` gating:** don't gate `/whiterun/sync/*` (keep bearer-token auth) — gating would
   break the case the feature exists for (a real player's first launch, no demo run active), and
   sync state is keyed by `save_uuid`, orthogonal to demo runs. The deeper issue this surfaces:
   the listener's whole model today is "one developer-designated live run," with per-process
   state that's recomputable for every *other* slice — sync is the first feature whose state
   must outlive both the listener process and any single run (§4.3). That argues, longer-term,
   for durable branch/epoch state living in `chronicle/` with the listener as thin transport —
   which is also the direction `chronicle-sync-cli-integration.md` already pointed, and which
   §4.3 deliberately scopes down to a minimum-viable sidecar rather than building here.
4. **`save_uuid` format reconciliation** — the co-save writes a real UUIDv4 (16 bytes → 32-char
   hex on the wire); existing `chronicle` runs use human-readable string ids
   (`"save-listener-1"`, `"livetest-<run_id>"`, per `chronicle-sync-cli-integration.md`).
   `chronicle.sync.Manifest.save_uuid`/`BranchState` treat this as an opaque string key, so the
   two formats coexist without collision by construction — no unification needed for v1, but
   worth a one-line note wherever `save_uuid` is documented so a future reader doesn't assume a
   single canonical format exists.

### 8c. Research-accuracy correction (not a design question)

- **SkyrimNet's co-save usage.** An earlier draft of this spec's research notes said SkyrimNet's
  game-side plugin "is pure Papyrus with no `SerializationInterface` use." That's misleading: the
  public `MinLL/SkyrimNet-GamePlugin` repo is Papyrus-only, but SkyrimNet's actual native
  component is a closed-source DLL, and its own release notes describe persisting voice-effect
  assignments to the SKSE co-save. Corrected claim: **SkyrimNet's native plugin is closed-source,
  so its co-save usage can't be studied from public source** — which if anything strengthens this
  spec's "no positive precedent for the async-state-vs-Save-ordering problem exists" point
  (§4.4's rationale), it just isn't evidence of the *opposite* either.

## What changed from v1 (2026-09-01)

Two review passes: an internal advisor review (fixed the `SetUniqueID` collision hazard,
`head_seq` write-ordering race, and missing `Revert` handler — all three still stand, unchanged
in this revision) and an external Kimi review with live GitHub re-verification, which found the
"nothing exists in code yet" framing was false for the service half and six blocking issues
(A1–A6 in Kimi's written review, `docs/design/chronicle-bridge-sync-handshake-review-kimi-2026-09-01.md`).
This version: calls `chronicle.sync.resolve()` instead of re-implementing it (§4.1); corrects the
HTTP client model from async-callback to synchronous-blocking (§2); scopes FORK/ADOPT/LEGACY_IMPORT
as decided-but-not-actionable pending fork-on-disk support, a gap this author found independently
while reading `chronicle-sync-cli-integration.md` for the A1 fix (§4); adds durable session state
(§4.3); redefines `head_seq` as commit-on-ACK rather than a separate volatile buffer (§4.4);
downgrades `confirm_required` to notification-only (§4.6); adds `hello_seq` fencing (§4.2); fixes
the manifest's byte count (56→68, a plain arithmetic error) and the `'CHRN'` FourCC's byte order
(§3, §7.3); and corrects the SkyrimNet research claim (§7.8). All research citations Kimi could
verify held up; this revision keeps them.
