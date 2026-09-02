# Review — plugin.cpp sync-wiring plan (Kimi, 2026-09-02)

**Subject:** `notes/kimi-review-plugin-cpp-sync-wiring-plan-2026-09-02.md` (the "plan" below).
**Method:** plan read against `SyncHandshakeCore.h` (full read), spec v2 §4–§5, the existing
plugin.cpp/OutboundClient conventions as previously verified, and **fresh primary-source
verification against the skse64 engine source** (`ianpatt/skse64@master`,
`Hooks_SaveLoad.cpp`, `InternalSerialization.cpp` — fetched today).

Verdict: the plan's architecture (pure core + thin glue, single mutex-guarded `g_syncState`,
dispatch-outside-lock, dedicated sync-sender thread, honest scope cut) is sound and should be
built. But there is **one blocker**: the plan as written would call `WriteRecord` from the
wrong callback, in a context where SKSE has no open co-save — verified against engine source,
below. Plus one correction-to-a-correction on `kPostLoadGame`, and four smaller findings.

---

## F1 (BLOCKER) — `WriteRecord` cannot be dispatched from the `kSaveGame` handler; the plan never says what the registered Save callback does

The plan's decision 2 says `OnSaveGame` runs "via `OnSkseMessage`" and that its transition
**and its `WriteCoSaveRecord` dispatch** happen inside the lock. Decision 5 says
`SyncHandshake.cpp` owns "the actual `ReadRecordData`/`WriteRecord`/`GetNextRecordInfo`
calls." Read literally, the implementer dispatches `WriteCoSaveRecord` → `WriteRecord` in the
`kSaveGame` message handler. That call is not legal there.

Verified against skse64 source today (`Hooks_SaveLoad.cpp:12-30`):

```cpp
void BGSSaveLoadManager::SaveGame_Hook(UInt64 *unk0) {
    ...
    PluginManager::Dispatch_Message(0, SKSEMessagingInterface::kMessage_SaveGame, ...);
    CALL_MEMBER_FN(this, SaveGame_HookTarget)(unk0);   // the actual save runs AFTER the message
}
```

`kSaveGame` fires **before the save begins**. The `SerializationInterface` Save callback —
the only context with an open co-save stream to write into — runs *inside* the real save
(SKSE's own core does its mod-index write in `Core_SaveCallback`,
`InternalSerialization.cpp:218-234`, and every shipped precedent we verified — JContainers,
Soulsy — only ever calls `WriteRecord`/`OpenRecord` inside the registered Save/Load
callbacks). A `WriteRecord` issued from the messaging handler has no open record target: at
best it returns false and the manifest silently never lands in the `.skse`; that's the
"compiles clean, silently does nothing" failure the plan's own verification section warns
about, in its most literal possible form.

Note the spec v2 does **not** have this defect — its §5 registers
`SetSaveCallback(SyncHandshake::OnGameSave)` *and* lists a `kSaveGame` messaging case as
separate things. The plan dropped the distinction when it wrote "OnSaveGame (via
OnSkseMessage)."

**Fix (state it explicitly in the plan):**
- The `kSaveGame` messaging case runs the pure `OnSaveGame` transition and **stashes** the
  resulting `WriteCoSaveRecord` payload (a 68-byte by-value struct — trivial). No `WriteRecord`
  here.
- `SyncHandshake::OnGameSave` (the `SetSaveCallback` callback) performs the actual
  `WriteRecord('TMNL', kManifestRecordVersion, ...)`.
- The advisor's race fix (transition-and-dispatch under one lock) moves with it: the Save
  callback locks `g_syncState`, reads/re-validates the stashed manifest against current state,
  writes, unlocks. Whether the Save callback writes the kSaveGame-stashed copy or re-reads
  `currentManifest` at write time is a semantic choice — with v2's commit-on-ACK model, both
  are safe (the manifest only ever advances on 2xx ACKs, so any skew under-reports, which is
  the CONTINUE-safe direction; over-reporting is the corrupting direction and is structurally
  impossible). Spec §5's D5 "same atomic read" note was written for the since-deleted
  `save-created` endpoint pair, so it's largely moot now — but the plan should say so rather
  than leave the reader wondering.

**On the question the task poses directly** — is holding the plugin mutex across `WriteRecord`
safe? Yes, *in the Save callback*: `WriteRecord` is a leaf call into SKSE's in-memory
co-save stream (JContainers runs a full Boost-serialization pass inside this callback;
Soulsy serializes its whole cycle buffer there), it cannot re-enter plugin code, and no other
plugin lock is ever acquired under `g_syncState` as long as the under-lock dispatch does
*only* the `WriteRecord`. Keep it that way: no logging, no queue touches under the lock.

## F2 — Correction to a correction: `kPostLoadGame` *does* carry a success flag (in `data`, not in the struct)

Spec §0 (and my earlier review, which endorsed it) dropped ADR-0005's
`kPostLoadGame(success=true)` on the grounds that the `Message` struct has no success field.
Structurally true, but the engine source shows the payload carries it anyway
(`Hooks_SaveLoad.cpp:51`):

```cpp
bool result = CALL_MEMBER_FN(this, LoadGame_HookTarget)(...);
PluginManager::Dispatch_Message(0, SKSEMessagingInterface::kMessage_PostLoadGame, (void*)result, 1, NULL);
```

`kPostLoadGame` arrives with `dataLen == 1` and `data` = the load's bool result. The glue's
`kPostLoadGame` handler should check it (`message->dataLen == 1 && *static_cast<bool*>(message->data)`)
and **not fire HELLO on a failed load** — HELLOing a timeline against a world that failed to
load is exactly the kind of wrong-branch event the handshake exists to prevent. One line of
glue; amend spec §0's wording ("no named field" — accurate; "no signal" — inaccurate) so the
next reader doesn't un-learn this.

## F3 — Spill-file I/O must leave the main thread, not just leave the mutex

Decision 1/2's rule is "network/file I/O never happens while holding the state mutex."
Necessary, not sufficient. `DispatchSideEffects` executes effects on whatever thread ran the
transition. `OnMutationReady` is callable from sinks on the main thread, and its buffering
branch can emit `SpillMutationToFile` when the ring fills — as written, that's a **file write
on the main thread during gameplay**, the never-block violation my spec review's D2 flagged.
`RotateSpillFile` fires from `OnGameRevert`, which (per the same hook source) runs inside
`LoadGame_HookTarget`, **under SKSE's global `g_loadGameLock`** — another reason not to do it
inline. Fix: file effects (`SpillMutationToFile`, `RotateSpillFile`) are queued to the
sync-sender thread like network effects; only `WriteCoSaveRecord` (context-bound to the Save
callback) and log lines dispatch locally. The plan should state per-effect dispatch
*destinations* in a small table, not just "not under the mutex."

## F4 — Decision 4 (timeout ≡ connection-failure → `OnHelloTimeout`) is a safe simplification — with one hole

The core needs nothing beyond "no resolution arrived"; both failure shapes correctly yield
DEGRADED + backoff. But a *received* HTTP error response is a third case the plan doesn't
name: 401/403 (misconfigured shared secret) or 503 (listener up but gated) would otherwise
enter the same retry-forever path. Retrying a 401 at backoff is harmless to correctness but
spams forever and hides a config error behind a DEGRADED story. Fix: define the mapping as
2xx-and-parseable → `OnHelloResponse`; transport failure/timeout → `OnHelloTimeout`;
**HTTP error status → `OnHelloTimeout` + `LogWarning` with the status, and do not schedule
the retry on 401/403.** Also: a 2xx with an unparseable body or an unknown `decision` string
must map to failure-and-log, never to a silent `kUnknown` accept.

## F5 — Decision 3 (mutation path ships uncalled): acceptable — but make the one new parser earn its keep

The scope cut is honestly stated and I agree with it: rerouting existing slices is separate
work, and the pure mutation transitions are already covered by the 197-check suite. What's
*not* covered by anything is the lane's one genuinely new hand-rolled component: the HELLO
**response** parsing (nullable-uint64 `replay_from_seq`, the `decision` string→`SyncDecision`
map, `hello_seq` echo, bools). That code is plain string manipulation — it compiles and runs
under the existing Linux `tests/` Makefile harness with no SKSE. Two cheap asks: (a) add
parser unit tests there; (b) extend the existing cross-language wire-contract test to pin the
HELLO *response* JSON shape (the Python emitter's exact keys/nulls against what the C++ parser
expects). That converts the riskiest untestable-in-game piece into something with an
executable contract before the live path unblocks.

## F6 — Smaller items

- **Thread-ownership list (decision 2) is incomplete**: `OnMutationAccepted`/
  `OnMutationRejected`/`OnMutationSendFailed` aren't listed. They're POST-response-driven, so
  they run on the sync-sender thread — say so, since the plan's stated purpose for that
  paragraph is "the thing an implementer would otherwise invent."
- **Backoff timer mechanics**: `OnHelloBackoffFire` "from a simple timed retry on that same
  thread" — implement as a condvar `wait_for` on the sender thread's queue so
  `CancelScheduledHelloRetry` wakes it promptly; the core's stale-fire no-op already makes a
  late wake safe, so this is a polish note, not a hazard.
- **UUIDv4 generation** for `OnNewGame` lives in the glue: name the source
  (`std::random_device`-seeded, explicitly *not* deterministic) in the plan so nobody wires a
  fixed seed for testing and ships it.
- **Files list**: complete as far as it goes (`CMakeLists.txt` gets both new .cpps — that
  closes the core header's documented "silently won't ship in the DLL" trap). One addition:
  the `tests/Makefile`/wire-test extension from F5.
- **Plugin unload/lifetime**: non-issue (SKSE plugins never unload; the new thread matches the
  existing 8-detached-thread pattern).

## Check on the advisor's three already-fixed items (sanity, as requested)

1. *WriteCoSaveRecord race (lock across transition+dispatch)* — the fix is correct in spirit
   and safe (F1's leaf-lock analysis), **but it was attached to the wrong callback**; F1's
   rewiring moves it to the Save callback, where it remains needed and sufficient.
2. *HELLO timeout pinned to 3s explicitly* — correct and necessary; matches spec §4.5/§8b's
   "deliberately different from the 1s convention" reasoning. Keep the comment pointing at §8b.
3. *Mutation-send scope cut* — confirmed as the right cut; see F5 for how to make it not
   *fully* unexercised.

## Bottom line

Architecture: build it. One blocker (F1) that must be fixed **in the plan text** before
implementation, because the plan as written instructs the implementer to make an illegal SKSE
call whose failure mode is silent; one spec-wording amendment (F2); one never-block fix (F3);
one failure-mapping hole (F4); one cheap test-coverage win (F5). All five are
one-paragraph plan edits, and F1/F2 should also be folded back into spec v2 §5/§0 so the spec
and the plan don't diverge.
