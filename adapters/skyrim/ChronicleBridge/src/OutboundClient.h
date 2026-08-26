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
        // Third slice (docs/design/chronicle-bridge-hydration-out.md §3b):
        // the ONE inbound-ish path this plugin ever calls -- a GET, not a
        // POST, but same host/port/sharedSecret, not a second config block,
        // matching eventsPath's own precedent above.
        std::string hydrationPath = "/whiterun/hydration";
        // Closes the "delivered before confirmed" gap named in fad0d79's
        // commit message and HydrationPoller.h's own header comment: a POST
        // back to the listener reporting what actually happened to each
        // pair FetchHydrationPairs handed out. Same host/port/sharedSecret
        // as every other path above -- not a second config block.
        std::string hydrationAckPath = "/whiterun/hydration/ack";
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

    // One changed (holder, target, bucketed rank) pair, matching the
    // listener's GET /whiterun/hydration response shape exactly (see
    // adapters/skyrim/listener/listener.py's _hydration_pairs): a JSON array
    // of {"holder_id": str, "target_id": str, "relationship_rank": int}.
    // Both ids are Chronicle npc_ids (IdentityMap's stable identity space),
    // not FormIDs.
    struct HydrationPair {
        std::string holderId;
        std::string targetId;
        int relationshipRank = 0;
    };

    // GETs the listener's pending-hydration queue and parses the response.
    // The listener already dedupes (only pairs whose bucketed rank actually
    // changed since the last poll are returned), so an empty result is the
    // common, expected case, not a failure signal -- and this function
    // deliberately can't distinguish "nothing changed" from "the request
    // failed" (both return empty), because the caller's response to either
    // is identical: do nothing and try again next poll (this is low-
    // frequency, non-critical state -- see HydrationPoller.h). Failures are
    // logged here, not surfaced to the caller as an error type.
    std::vector<HydrationPair> FetchHydrationPairs(const OutboundConfig& config);

    // What actually happened when HydrationPoller.cpp's ApplyHydrationPair
    // tried to apply one pair, mapped precisely onto that function's own
    // three control-flow branches (see HydrationPoller.cpp for exactly
    // where each is returned):
    //   kApplied      -- ResolveLiveNpc succeeded for both ids AND
    //                     GetRelationship() found an existing record AND
    //                     the .level write + AddChange happened. The
    //                     listener should mark this pair "applied" at this
    //                     rank (design doc §3b's idempotency requirement)
    //                     and never re-offer it at the same rank.
    //   kNoRelationship -- both ids resolved to live TESNPC*s but
    //                     GetRelationship() returned null -- no authored
    //                     vanilla relationship exists for this pair. This
    //                     is a PERMANENT condition per the ruled scope
    //                     (never creating one): retrying the same rank
    //                     forever would never succeed. The listener should
    //                     permanently skip this pair at this exact rank.
    //   kRetry        -- ResolveLiveNpc failed for either id (no active
    //                     game, or the NPC isn't currently resolvable) --
    //                     this is a TEMPORARY condition that may well
    //                     resolve itself by the next poll. The listener
    //                     should offer this pair again next time its
    //                     computed rank is still non-matching, i.e. treat
    //                     it as if it had never been offered at all.
    enum class HydrationApplyOutcome { kApplied, kNoRelationship, kRetry };

    // One pair's ack outcome, matching the listener's POST
    // /whiterun/hydration/ack body shape exactly: a JSON array of
    // {"holder_id": str, "target_id": str, "outcome": "applied" |
    // "no_relationship" | "retry"}.
    struct HydrationAckEntry {
        std::string holderId;
        std::string targetId;
        HydrationApplyOutcome outcome = HydrationApplyOutcome::kRetry;
    };

    // POSTs the outcomes of one poll's whole batch back to the listener.
    // Fire-and-forget, same discipline as PostPositionSnapshot/
    // PostGameEvent: logs failures, never throws, never retries -- a
    // dropped ack just means the affected pairs look like they were never
    // acked at all, which the listener's state machine already treats as
    // "offer again later" (retry semantics), so there is nothing unsafe
    // about losing one. Returns true if the listener responded 2xx.
    bool PostHydrationAck(const OutboundConfig& config, const std::vector<HydrationAckEntry>& acks);

}  // namespace ChronicleBridge
