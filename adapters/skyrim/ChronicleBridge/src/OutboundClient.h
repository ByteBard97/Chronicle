#pragma once

// Design doc B4 (docs/design/chronicle-bridge-spatial-streamer.md): outbound
// only, matching the direction the Stage-0 spike actually proves (the game
// as an HTTP CLIENT, never a server -- see that doc for why the plugin does
// not embed a WebSocket server). Wire format is
// adapters/skyrim/contracts/chronicle-bridge.openapi.yaml -- if you change
// the payload shape here, update that spec first, this is hand-written to
// match it, not generated from it (OpenAPI-to-C++ codegen is immature/heavy
// for a payload this small).

#include <optional>
#include <string>
#include <vector>

#include "DeathEventSink.h"
#include "SpatialStreamer.h"

namespace ChronicleBridge {

    struct OutboundConfig {
        std::string host = "127.0.0.1";  // the Chronicle host's LAN IP once running on a separate machine.
        int port = 8765;
        std::string path = "/whiterun/positions";
        // Second slice (docs/design/chronicle-bridge-death-extraction.md):
        // discrete game events (currently: npc_died only) POST to a
        // separate path on the SAME host/port/sharedSecret -- not a second
        // config block, per that doc's §4 instruction. Kept as its own
        // field rather than reusing `path` so positions and events can
        // never accidentally collide on one endpoint.
        std::string eventsPath = "/whiterun/events";
        // Sent as the X-Chronicle-Bridge-Token header when set -- must match
        // the listener's --shared-secret exactly (adapters/skyrim/listener/
        // listener.py). Not real authentication (no TLS) -- a lightweight
        // bearer check so an accidental LAN neighbor can't write garbage into
        // the snapshot file. See that script's module docstring for the
        // trust model this is and isn't meant to cover.
        std::optional<std::string> sharedSecret;
    };

    // POSTs one PositionSnapshot (chronicle-bridge.openapi.yaml) to the
    // configured listener. Fire-and-forget: logs failures, never throws,
    // never blocks the caller waiting for a retry -- a dropped snapshot at
    // ~1Hz is fine, the next tick's snapshot supersedes it. Returns true if
    // the listener responded 2xx.
    bool PostPositionSnapshot(const OutboundConfig& config, double wallTimestamp, const std::vector<NpcPosition>& npcs);

    // A single discrete game event (chronicle-bridge.openapi.yaml's
    // GameEvent schema) -- currently only "npc_died" exists (design doc
    // §2). Unlike PostPositionSnapshot this is not a superseded-by-the-next-
    // tick fire-and-forget: a dropped death event is a real, permanent gap
    // in Chronicle's event log, not a stale position. It still never
    // retries or blocks past its 1s timeouts, though -- retry/backoff is
    // real future work, not attempted this slice (a queued-and-drained
    // sender thread is the mitigation this slice does take, see plugin.cpp).
    // Returns true if the listener responded 2xx.
    bool PostGameEvent(const OutboundConfig& config, const PendingGameEvent& event);

}  // namespace ChronicleBridge
