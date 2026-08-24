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
        std::string id;  // resolved per IdentityMap -- never a raw FormID.
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
