#pragma once

// Design doc §2 (docs/design/chronicle-bridge-death-extraction.md): the
// second ChronicleBridge slice. Sinks RE::TESDeathEvent (research/22's
// verified mapping -- a clean top-level BSTEventSink, no inline hook
// required, unlike crime/bounty) and turns each death into a
// PendingGameEvent for the caller to hand off to a sender thread.
//
// Deliberately NOT doing the network POST itself (that's OutboundClient::
// PostGameEvent, called from plugin.cpp's own dedicated sender thread) --
// ProcessEvent runs synchronously on the main thread (research/22: "Dispatched
// synchronously when an actor's health reaches zero"), so it must do only
// main-thread-safe, fast work: resolve identities via IdentityMap (already
// main-thread-only-safe, same as SpatialStreamer's usage) and push the
// resolved struct into a thread-safe queue. Never touches httplib.

#include <functional>
#include <optional>
#include <string>

namespace ChronicleBridge {

    struct PendingGameEvent {
        double gamets = 0.0;    // ADR-0010: 1 tick = 1 gamets = 1 game-hour.
        double wallTs = 0.0;    // wall-clock observation time, auxiliary only (contract's wall_ts).
        std::string npcId;      // resolved per IdentityMap -- never a raw FormID.
        std::string cause = "unknown";  // fixed per design doc D2 -- no structured cause detection this slice.
        std::optional<std::string> killerId;
        std::optional<std::string> locationId;
    };

    // Registers the death-event sink with RE::ScriptEventSourceHolder. Must
    // be called during/after SKSE::MessagingInterface::kDataLoaded (design
    // doc §2, research/22's documented registration lifecycle) -- calling
    // earlier risks null singletons.
    //
    // onDeath is invoked synchronously, on the main thread, for every
    // resolved death -- the caller (plugin.cpp) is responsible for getting
    // the event off the main thread before doing any network I/O, exactly
    // as SpatialStreamer's snapshot loop hands off to a separate sender
    // thread rather than posting inline.
    void RegisterDeathEventSink(std::function<void(PendingGameEvent)> onDeath);

}  // namespace ChronicleBridge
