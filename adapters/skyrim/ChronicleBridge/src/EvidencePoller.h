#pragma once

// Design doc docs/design/chronicle-bridge-diegetic-evidence-out.md §5 step 3:
// the seventh ChronicleBridge slice, and the C++ consumer of the Python-only
// first cut that doc's own header now marks "implemented" for the
// chronicle/+listener half. Mirrors HydrationPoller's exact shape (same
// TimerThreadLoop-on-its-own-thread pattern, same std::promise/future
// main-thread hop via SKSE::GetTaskInterface()->AddTask(), same
// IdentityMap-based Actor* resolution chain) but resolves to a live
// RE::Actor* directly rather than a TESNPC* base record -- this slice calls
// RE::TESObjectREFR::PlaceObjectAtMe() on the believer's own actor reference,
// it never reads/writes a TESNPC*-hung record the way HydrationPoller's
// BGSRelationship write does. Closer in shape to AvoidancePoller.cpp for
// exactly this reason (both need Actor*, not TESNPC*), and its two-outcome
// ack matches evidence's shape rather than hydration's three -- see
// OutboundClient.h's EvidenceApplyOutcome comment for why there is no
// permanent-failure outcome here.
//
// *** UNVERIFIED AT RUNTIME ***: this slice's write path (spawning a new
// TESObjectREFR into the actor's own cell via PlaceObjectAtMe) has only ever
// been compiled against the real CommonLibSSE-NG headers on the Windows
// build machine. It has NEVER been exercised against a live game or a real
// save from this development pass (no game running over this session's SSH
// access). docs/research/31-diegetic-evidence-object-placement-spike.md's
// F1-F3 verified the call itself against real headers and two independent
// shipped SKSE plugins, but F3's own caveat is explicit: whether a
// dynamically-created PlaceObjectAtMe reference persists correctly across a
// save/reload was NOT verified there either. "Builds with zero errors" and
// "safe to spawn into a live cell/save" are two separate claims -- only the
// first is true as of this slice. Do not treat this as tested until someone
// confirms it manually in an actual play session.
//
// PLACEHOLDER EVIDENCE OBJECT: this slice spawns ONE fixed base object
// regardless of claim kind (design doc §3's non-goal, report 31's
// recommendation 2) -- a real evidence base object has not been authored
// (design doc §5 step 2, separate/deferred work). See EvidencePoller.cpp's
// kPlaceholderEvidenceObject comment for the exact FormID chosen and why it
// is explicitly a placeholder, not a real evidence prop, mirroring
// AvoidanceGlobals.cpp's own placeholder-then-real-FormID precedent.

#include "OutboundClient.h"

namespace ChronicleBridge {

    // Runs forever on its own thread -- same TimerThreadLoop-on-its-own-
    // thread pattern HydrationPoller.h/AvoidancePoller.h already use. Never
    // call this from the main thread: it blocks on the network GET itself,
    // then hops onto the main thread (SKSE::GetTaskInterface()->AddTask)
    // only for the actual game-object resolution and PlaceObjectAtMe spawn.
    void EvidencePollerThreadLoop(OutboundConfig config);

}  // namespace ChronicleBridge
