#pragma once

// Design doc §1 (docs/design/chronicle-bridge-spatial-streamer.md): sample
// every actor currently outdoors in WhiterunWorld. Enumeration approach is
// docs/research/22-native-skse-plugin-prior-art.md's own verified pattern
// (RE::ProcessLists::highActorHandles) -- a native-only structure, which is
// why this can't be done from Papyrus at all (checked directly before this
// design was written).

#include <vector>

#include "IdentityMap.h"

namespace ChronicleBridge {

    struct NpcPosition {
        std::string id;    // resolved per IdentityMap -- never a raw FormID.
        // The actor's in-game display name (e.g. "Idolaf Battle-Born"), read
        // directly off the actor -- not IdentityMap's hand-maintained
        // kNamedCast table. Display purposes only (dashboard click-to-reveal),
        // orthogonal to `id`'s stable-identity contract: most actors in a
        // Whiterun snapshot aren't in Chronicle's own named-cast fixture and
        // never will be, but they still have a perfectly good vanilla name.
        // Empty string if the game reports none.
        std::string name;
        float x;
        float y;
    };

    // WhiterunWorld's form ID, confirmed against dashboard/map/whiterun_map.json's
    // "worldspace" field: "WhiterunWorld (0x0001A26F)".
    inline constexpr RE::FormID kWhiterunWorldFormId = 0x0001A26F;

    // One snapshot pass: every actor currently loaded, 3D-attached, alive, and
    // in an EXTERIOR WhiterunWorld cell. An actor who has gone indoors since
    // the last call simply isn't in the returned vector -- no stale entry, per
    // the design doc's binary has-position/no-position rule.
    std::vector<NpcPosition> SampleWhiterunExteriorPositions();

}  // namespace ChronicleBridge
