#pragma once

// Loads OutboundConfig from Data/SKSE/Plugins/ChronicleBridge.ini -- the
// conventional SKSE-plugin config path (README.md's "Runtime configuration"
// section). Needed once Skyrim runs on its own machine and the listener is
// no longer reachable at the hardcoded 127.0.0.1 default.

#include "OutboundClient.h"

namespace ChronicleBridge {

    // Reads host/port/sharedSecret from the ini next to this DLL. Any key
    // that's missing, or the file itself being absent, falls back to
    // OutboundConfig's built-in defaults for that field -- so a fresh
    // install with no ini yet behaves exactly like before this existed.
    OutboundConfig LoadConfigFromIni();

}  // namespace ChronicleBridge
