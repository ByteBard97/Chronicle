#pragma once

// Design doc docs/design/chronicle-bridge-avoidance-mutagen-out.md §2 named
// this as a "real open question": whether RE::TESObjectREFR's native
// SetLinkedRef equivalent is directly callable. It is NOT -- see
// AvoidancePoller.h's header comment for the full header-verification
// finding and the fallback this table exists to support (per-PAIR globals
// instead of per-NPC globals + a linked-ref target).
//
// One TESGlobal, "ChronicleAvoidingPair_<npc_a>_<npc_b>", per unordered
// Chronicle npc_id pair that tools/chronicle-patcher/ has actually authored
// a Flee package for (both actors hardcoded as that package's target --
// the pair itself picks the target, so no runtime target-selection
// mechanism is needed at all once linked-ref is off the table). Mirrors
// IdentityMap.cpp's kNamedCast table shape exactly, per the design doc's
// own instruction, so filling in real FormIDs later is a trivial,
// mechanical edit.
//
// *** ALL FormIDs BELOW ARE PLACEHOLDERS (0x000000) ***. tools/chronicle-
// patcher/ (a separate, parallel piece of work -- not touched by this
// slice) has not generated ChroniclePatcher.esp yet, so there is no real
// global to point at. This table's SHAPE and lookup logic are real and
// compile-checked; the VALUES are not. Fill them in once that .esp exists
// and is load-ordered, by reading the actual FormIDs Mutagen assigned to
// each ChronicleAvoidingPair_* global out of the generated plugin.
//
// Only a representative handful of pairs are listed here (illustrative,
// not exhaustive -- rule 18 can, in principle, put ANY two named-cast NPCs
// into avoidance, so the real table's final size is however many pairs
// tools/chronicle-patcher/ ends up authoring a package for, not a fixed
// combinatorial constant). A pair missing from this table resolves to
// std::nullopt, which AvoidancePoller.cpp treats as a (temporary) `retry`
// outcome -- exactly the right behavior for both "not yet authored" and
// "genuinely never going to be authored" until the patcher's own coverage
// decision is known; the ack protocol offers no third, permanent-skip
// outcome (see OutboundClient.h's AvoidanceApplyOutcome), so retry-forever
// is the honest, protocol-correct thing to report either way.

#include <optional>
#include <string_view>

#include "IdentityMap.h"

namespace ChronicleBridge {

    // Looks up the ChronicleAvoidingPair_<a>_<b> global for the unordered
    // pair {npcA, npcB} -- order doesn't matter, this canonicalizes
    // internally the same way the listener's own _avoidance_pairs does
    // (tuple(sorted((a, b)))). Returns std::nullopt if no global has been
    // authored for this pair yet (see this header's own comment above).
    std::optional<FormRef> ResolveAvoidancePairGlobal(std::string_view npcA, std::string_view npcB);

}  // namespace ChronicleBridge
