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
// *** A KNOWN, NAMED GAP: the listener marks a pair "delivered" the moment
// it hands it out, not once this poller successfully applies it ***
// (listener.py's `_hydration_pairs` writes into its `last_pushed` dedupe
// cache before returning the pair, in the same call that returns it). This
// poller skips a pair whenever either NPC doesn't resolve, no game is
// active, or GetRelationship() returns null (the common, ruled-scope
// case). Every one of those skips is therefore a SILENT, PERMANENT drop
// from the listener's point of view -- it will never resend that exact
// rank again unless the underlying grudge/reputation bucket changes to
// something else and back first. Given §3c's own finding that most
// Chronicle-relevant pairs have no authored vanilla relationship at all,
// the expected steady state is that most computed pushes are consumed by
// the listener and never actually applied in-game. This is a real,
// named gap, not solved by this slice.

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
