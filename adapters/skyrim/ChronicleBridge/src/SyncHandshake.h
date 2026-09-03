#pragma once

// SyncHandshake.h/.cpp -- the SKSE glue layer for the save/reload
// sync-handshake feature (docs/design/chronicle-bridge-sync-handshake-out.md,
// implemented per the sync-wiring plan reviewed by advisor + Kimi,
// 2026-09-02). This is the "thin glue" half SyncHandshakeCore.h's own
// header comment reserves this exact file name for: everything here calls
// into the pure, fully-tested SyncHandshakeCore state machine (197 passing
// checks under ASan/UBSan) rather than reimplementing any of its logic.
// SyncHandshakeCore.h/.cpp are NEVER edited by this lane -- their test
// coverage is the only real coverage this feature has.
//
// Deliberately nested under ChronicleBridge::SyncHandshake, not flat
// ChronicleBridge:: -- the SerializationInterface callback registered as
// SetRevertCallback needs the name OnGameRevert (matching the design doc's
// own plugin.cpp snippet), which would otherwise collide with
// SyncHandshakeCore's OWN ChronicleBridge::OnGameRevert(SyncState) pure
// transition (different signature, so technically a legal overload, but
// confusing to read side by side). The nested namespace keeps the two
// clearly separate: ChronicleBridge::OnGameRevert (pure core, takes
// SyncState) vs. ChronicleBridge::SyncHandshake's own internal
// SetRevertCallback registrant (SKSE-facing, takes SerializationInterface*,
// not exposed here at all -- see SyncHandshake.cpp's anonymous namespace).
//
// Thread ownership (the sync-wiring plan's design decision 2, restated
// here for anyone reading just this header):
//   - Main thread: HandlePreLoadGame/HandlePostLoadGame/HandleNewGame/
//     HandleSaveGameMessage (forwarded from plugin.cpp's OnSkseMessage) and
//     the SerializationInterface Load/Revert callbacks (SKSE's own
//     contract -- registered internally, not exposed here).
//   - The dedicated sync-sender thread (SenderThreadLoop, spawned once from
//     SKSEPluginLoad): every POST-response-driven transition
//     (OnHelloResponse/OnHelloTimeout/OnHelloBackoffFire/OnMutationAccepted/
//     OnMutationRejected/OnMutationSendFailed), plus the actual HELLO/
//     mutation POSTs and spill-file I/O -- see SyncHandshake.cpp for the
//     per-effect dispatch table.
//   - The ONE exception: the actual co-save WriteRecord call happens
//     neither here nor on the sender thread, but inside the
//     SetSaveCallback registrant (internal), which fires later than
//     kSaveGame's OnSkseMessage case with an actually-open co-save stream
//     -- see HandleSaveGameMessage's own comment and SyncHandshake.cpp's
//     header comment for why WriteRecord CANNOT be called from
//     HandleSaveGameMessage itself.

#include "OutboundClient.h"
#include "SyncHandshakeCore.h"

namespace ChronicleBridge::SyncHandshake {

    // Registers SetUniqueID('CHRN')/SetSaveCallback/SetLoadCallback/
    // SetRevertCallback with SKSE::GetSerializationInterface(). Call once,
    // from SKSEPluginLoad, alongside every other GetXInterface()
    // registration this plugin already does -- NOT deferred to
    // kDataLoaded (unlike the RE:: event sinks): SerializationInterface
    // registration has its own SKSE-documented lifecycle, independent of
    // the messaging bus's kDataLoaded convention.
    void RegisterSerializationCallbacks();

    // Runs forever on its own thread -- the sync-sender thread (see this
    // header's own thread-ownership note above). Spawn once from
    // SKSEPluginLoad, same std::thread(...).detach() convention plugin.cpp
    // already uses for every other sender thread.
    void SenderThreadLoop(OutboundConfig config);

    // Forwarded from plugin.cpp's OnSkseMessage on
    // SKSE::MessagingInterface::kPreLoadGame. Main thread.
    void HandlePreLoadGame();

    // Forwarded from plugin.cpp's OnSkseMessage on
    // SKSE::MessagingInterface::kPostLoadGame -- but ONLY when the caller
    // has already confirmed the load succeeded. The real
    // SKSE::MessagingInterface::Message struct has no named success field,
    // but skse64's engine source (Hooks_SaveLoad.cpp, LoadGame_Hook) passes
    // the load's bool result as `data` with `dataLen == 1` anyway, cast
    // directly to a pointer-sized value (`(void*)result`, never `&result`)
    // -- confirmed by reading that call site, not assumed. plugin.cpp's
    // job (the sync-wiring plan's design decision 3) is to read that packed
    // byte via DecodePostLoadSuccessFlag (SyncHandshakeCore.h), never to
    // dereference `data` -- an earlier version of that check did
    // `*static_cast<bool*>(message->data)` and crashed on every real
    // successful load (confirmed live, 2026-09-03). Calling this on a
    // failed load would fire a HELLO against a world that failed to load --
    // exactly the wrong-branch event the handshake exists to prevent. Main
    // thread.
    void HandlePostLoadGame();

    // Forwarded from plugin.cpp's OnSkseMessage on
    // SKSE::MessagingInterface::kNewGame. Generates a fresh UUIDv4 (seeded
    // from std::random_device -- explicitly not deterministic) and fires
    // HELLO unconditionally (spec §4.2, B4's fix: resolve()'s NEW_TIMELINE
    // row already handles "service has never seen this save_uuid"
    // correctly). Main thread.
    void HandleNewGame();

    // Forwarded from plugin.cpp's OnSkseMessage on
    // SKSE::MessagingInterface::kSaveGame. Runs the pure OnSaveGame
    // transition and STASHES the resulting WriteCoSaveRecord payload for
    // the SetSaveCallback registrant to actually write later -- does NOT
    // call WriteRecord itself. kSaveGame fires before the actual save
    // begins (verified against skse64's Hooks_SaveLoad.cpp): there is no
    // open co-save stream at this point, so WriteRecord would silently
    // return false here and the manifest would never land in the .skse
    // file, with no error. See SyncHandshake.cpp's header comment for the
    // full split and the invariant this protects. Main thread.
    void HandleSaveGameMessage();

    // The "emit a mutation" entry point for a future sync-tracked event
    // producer. Wired completely and correctly (locks the shared state
    // briefly, calls the pure OnMutationReady transition, dispatches
    // whatever effects come back), but NOT currently called by any
    // ChronicleBridge slice -- none of the 7 existing slices emit
    // sync-tracked mutations today; they use their own pre-existing
    // endpoints, unrelated to /whiterun/sync/mutation. Rerouting them (or
    // wiring a future conversation-tier's utterance claims through this
    // gate) is real, separate future work. Safe to call from ANY thread --
    // this only ever locks briefly and enqueues; the actual network I/O (if
    // the transition decides to send now rather than buffer) happens on
    // the sync-sender thread.
    void SubmitMutation(const MutationEvent& event);

}  // namespace ChronicleBridge::SyncHandshake
