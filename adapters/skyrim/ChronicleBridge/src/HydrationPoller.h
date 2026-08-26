#pragma once

// Design doc docs/design/chronicle-bridge-hydration-out.md §3b/3c: the third
// ChronicleBridge slice, and the first WRITE to a live game object -- every
// prior slice (spatial streamer, death events) only ever read/observed game
// state.
//
// *** UNVERIFIED AT RUNTIME ***: this slice's write path (setting
// RE::BGSRelationship::level on a live game object) has only ever been
// compiled against the real CommonLibSSE-NG headers on the Windows build
// machine. It has NEVER been exercised against a live game or a real save
// from this development pass (no game running over this session's SSH
// access). "Builds with zero errors" and "safe to run against a real save"
// are two separate claims -- only the first is true as of this slice. Do
// not treat this as tested until someone confirms it manually in an actual
// play session.
//
// *** CLOSED GAP, formerly named here: the listener used to mark a pair
// "delivered" the moment it handed it out, not once this poller
// successfully applied it *** (listener.py's `_hydration_pairs` wrote into
// its `last_pushed` dedupe cache before returning the pair, in the same
// call that returned it -- see fad0d79's commit message for the original
// finding). This poller now reports back which of three outcomes actually
// happened for each pair via `PostHydrationAck` (OutboundClient.h's
// `HydrationApplyOutcome`): `kApplied` when the write succeeded;
// `kNoRelationship` when `GetRelationship()` returned null (a PERMANENT
// condition -- no authored vanilla relationship exists, so the listener
// should never re-offer that exact rank again); `kRetry` when either NPC
// failed to resolve or no game was active at all (a TEMPORARY condition --
// the listener should offer the pair again as if it had never been
// offered). The listener's own `_HydrationPairState` state machine
// (adapters/skyrim/listener/listener.py) is what actually acts on this --
// see that file for the full state machine this ack protocol drives.

#include "OutboundClient.h"

namespace ChronicleBridge {

    // Runs forever on its own thread -- same TimerThreadLoop-on-its-own-
    // thread pattern plugin.cpp already uses for the spatial streamer (a
    // periodic GET is exactly analogous to that periodic POST; see the .cpp
    // for the poll interval and its rationale). Never call this from the
    // main thread: it blocks on the network GET itself, then hops onto the
    // main thread (SKSE::GetTaskInterface()->AddTask) only for the actual
    // game-object resolution and write.
    void HydrationPollerThreadLoop(OutboundConfig config);

}  // namespace ChronicleBridge
