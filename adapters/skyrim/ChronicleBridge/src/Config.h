#pragma once

// Loads OutboundConfig from Data/SKSE/Plugins/ChronicleBridge.ini -- the
// conventional SKSE-plugin config path (README.md's "Runtime configuration"
// section). Needed once Skyrim runs on its own machine and the listener is
// no longer reachable at the hardcoded 127.0.0.1 default.

#include "OutboundClient.h"

namespace ChronicleBridge {

    // Everything one read of the ini produces. LogLevel is deliberately NOT
    // a field on OutboundConfig -- that struct is the outbound HTTP contract
    // (host/port/paths/secret) copied into every poller thread, and a
    // diagnostics knob has no business travelling with it. Kept in one
    // struct returned by one read so plugin.cpp still reads the ini exactly
    // once at startup.
    struct BridgeConfig {
        OutboundConfig outbound;
        // Applied via spdlog::set_level right after this read in plugin.cpp
        // -- the logger is created BEFORE the ini can be read, so the banner
        // lines above that point are always written at info.
        spdlog::level::level_enum logLevel = spdlog::level::info;
    };

    // Reads host/port/sharedSecret/log level from the ini next to this DLL.
    // Any key that's missing, or the file itself being absent, falls back to
    // the built-in default for that field -- so a fresh install with no ini
    // yet behaves exactly like before this existed.
    BridgeConfig LoadConfigFromIni();

}  // namespace ChronicleBridge
