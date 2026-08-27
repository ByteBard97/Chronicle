#pragma once

// Design doc docs/design/chronicle-bridge-avoidance-mutagen-out.md §2/§4
// step 2/3: the fourth ChronicleBridge slice, mirroring HydrationPoller's
// shape almost exactly -- same OutboundConfig-taking thread-loop pattern,
// same main-thread task hop via SKSE::GetTaskInterface()->AddTask() for the
// actual game-object writes, same poll-then-ack shape. See HydrationPoller.h
// for the pattern this file was written against.
//
// *** DESIGN CHANGE FROM THE ORIGINAL DOC, RESOLVING ITS NAMED OPEN
// QUESTION ***: the design doc flagged as genuinely unverified "whether
// RE::TESObjectREFR::SetLinkedRef (the Papyrus-native's underlying virtual)
// is directly callable." It is NOT. Verified 2026-08-26 against the real
// CommonLibSSE-NG headers on the Windows build machine
// (vcpkg_installed/x64-windows-static-md/include/RE/):
//   - RE/T/TESObjectREFR.h exposes only `GetLinkedRef(BGSKeyword*)` (a
//     getter). No setter of any name exists on TESObjectREFR.
//   - RE/E/ExtraLinkedRef.h shows the underlying storage is a raw
//     BSTSmallArray<LinkedRef> (LinkedRef = {BGSKeyword*, TESObjectREFR*})
//     living in the object's ExtraDataList -- there is no documented, safe
//     CommonLibSSE-NG API to insert/replace an entry in that array.
//     Reaching into it directly (matching the game's own internal
//     allocation/RTTI conventions for a BSExtraData subtype by hand) is
//     exactly the kind of unverified-as-safe raw memory manipulation this
//     project has consistently avoided (see HydrationPoller.h's own
//     AddChange caveat for the bar this project holds writes to).
//   - RE/B/BGSRefAlias.h (the quest-ref-alias route, a plausible second
//     candidate for "runtime-determined package target") exposes
//     `GetReference()`/`GetActorReference()` -- getters only. The
//     Papyrus-native `ForceRefTo` is not surfaced as a callable RE::
//     virtual in this header set either.
//
// **Fallback chosen** (the design doc's own §2 named exactly this as the
// next-best option if linked-ref didn't pan out): per-PAIR globals instead
// of per-NPC globals + a linked-ref target. Concretely:
//   - Instead of one `ChronicleAvoiding_<NpcId>` global per NPC (whose
//     package still needed a linked-ref to know WHO to avoid), there is one
//     `ChronicleAvoidingPair_<npc_a>_<npc_b>` global per (npc_a, npc_b)
//     pair (AvoidanceGlobals.h/.cpp).
//   - tools/chronicle-patcher/ (separate, parallel work -- not touched by
//     this slice) authors one Flee package PER PAIR, hardcoding both actual
//     NPCs as that package's target. The pair itself picks the target at
//     AUTHORING time, not runtime, so no runtime target-selection
//     mechanism (linked-ref, ref-alias, or otherwise) is needed at all.
//   - Tradeoff named honestly: this trades "one shared PACK + linked-ref
//     resolved at runtime" for "N authored PACKs, one per pair actually
//     needed" -- more content for the patcher to generate, but every piece
//     of it uses ONLY already-confirmed-real APIs (ConditionGlobal,
//     TESGlobal::value, Actor::EvaluatePackage -- see IdentityMap.cpp/
//     HydrationPoller.cpp precedent), with zero remaining unverified-API
//     risk on the C++ side. Given no safe native SetLinkedRef-equivalent
//     exists, this is the more conservative -- and only fully-verified --
//     path, same "pick a reasonable path, document why" instruction this
//     doc's own §2 gave for exactly this contingency.
//
// This means this file's write path, unlike HydrationPoller's, involves NO
// unverified-signature API at all: TESGlobal::value is a plain float member
// (RE/T/TESGlobal.h) and Actor::EvaluatePackage's signature was already
// confirmed real by the design doc's own earlier research (§2b). What
// remains unverified is only the same class of thing hydration's own header
// already flags: this has been compiled against the real headers, but NEVER
// exercised against a live game or save.

#include "OutboundClient.h"

namespace ChronicleBridge {

    // Runs forever on its own thread -- same TimerThreadLoop-on-its-own-
    // thread pattern as HydrationPollerThreadLoop. Never call this from the
    // main thread: it blocks on the network GET itself, then hops onto the
    // main thread (SKSE::GetTaskInterface()->AddTask) only for the actual
    // game-object resolution and write.
    void AvoidancePollerThreadLoop(OutboundConfig config);

}  // namespace ChronicleBridge
