#pragma once

// Design doc B4 (docs/design/chronicle-bridge-spatial-streamer.md): outbound
// only, matching the direction the Stage-0 spike actually proves (the game
// as an HTTP CLIENT, never a server -- see that doc for why the plugin does
// not embed a WebSocket server). Wire format is
// adapters/skyrim/contracts/chronicle-bridge.openapi.yaml -- if you change
// the payload shape here, update that spec first, this is hand-written to
// match it, not generated from it (OpenAPI-to-C++ codegen is immature/heavy
// for a payload this small).

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

#include "DeathEventSink.h"
#include "SpatialStreamer.h"
#include "SyncHandshakeCore.h"

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
        // Fourth slice (docs/design/chronicle-bridge-avoidance-mutagen-out.md
        // §2): same poll/ack shape as hydration, symmetric pair instead of
        // directed (holder, target). Same host/port/sharedSecret as every
        // path above -- not a second config block.
        std::string avoidancePath = "/whiterun/avoidance";
        std::string avoidanceAckPath = "/whiterun/avoidance/ack";
        // Fifth slice's optional read-only piece (BarterMenuSink.h,
        // docs/design/chronicle-bridge-vendor-markup-out.md): GET only, no
        // ack path -- this slice never writes a price, so there is nothing
        // to report back to the listener. Same host/port/sharedSecret as
        // every path above -- not a second config block.
        std::string vendorMarkupPath = "/whiterun/vendor-markup";
        // Seventh slice (docs/design/chronicle-bridge-diegetic-evidence-out.md
        // §2): same poll/ack shape as hydration/avoidance, single-key
        // (holder_id, belief_id) instead of a pair. Same host/port/
        // sharedSecret as every path above -- not a second config block.
        std::string evidencePath = "/whiterun/evidence";
        std::string evidenceAckPath = "/whiterun/evidence/ack";
        // Eighth slice (docs/design/chronicle-bridge-sync-handshake-out.md
        // §4.1): the save/reload sync handshake's two endpoints. Unlike
        // every path above, these are POST-only (no GET/ack pair) -- HELLO's
        // response body IS the ack (a decision, not a delivery
        // confirmation), and mutation's response status code IS its own
        // outcome signal (200/409/failure), so there is nothing left for a
        // second ack call to report. Same host/port/sharedSecret as every
        // path above -- not a second config block.
        std::string syncHelloPath = "/whiterun/sync/hello";
        std::string syncMutationPath = "/whiterun/sync/mutation";
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

    // One changed (npc_a, npc_b, avoiding) pair, matching the listener's GET
    // /whiterun/avoidance response shape exactly (adapters/skyrim/listener/
    // listener.py's _avoidance_pairs): a JSON array of {"npc_a": str,
    // "npc_b": str, "avoiding": bool}. Both ids are Chronicle npc_ids.
    // Unlike HydrationPair this is symmetric -- the listener always returns
    // npc_a/npc_b in canonical (lexicographically sorted) order, but nothing
    // here depends on that; AvoidancePoller.cpp/AvoidanceGlobals.cpp
    // canonicalize independently before any lookup.
    struct AvoidancePair {
        std::string npcA;
        std::string npcB;
        bool avoiding = false;
    };

    // GETs the listener's pending-avoidance queue and parses the response.
    // Same "empty means nothing changed OR the request failed, and the
    // caller's response to either is identical" contract as
    // FetchHydrationPairs -- see that function's comment.
    std::vector<AvoidancePair> FetchAvoidancePairs(const OutboundConfig& config);

    // What actually happened when AvoidancePoller.cpp's ApplyAvoidancePair
    // tried to apply one pair. Only two outcomes -- avoidance has no
    // hydration-style permanent-failure case (see listener.py's module
    // docstring and _AvoidancePairState's own comment):
    //   kApplied -- both actors resolved, a per-pair global was found for
    //               this pair, and its value was written. The listener
    //               should mark this pair "applied" at this avoiding value.
    //   kRetry   -- either actor failed to resolve, no game was active, OR
    //               (a case hydration's kRetry never had to cover) no
    //               ChronicleAvoidingPair_* global has been authored for
    //               this pair yet (AvoidanceGlobals.cpp). All three are
    //               TEMPORARY from the listener's point of view -- it
    //               should offer the pair again as if never offered.
    enum class AvoidanceApplyOutcome { kApplied, kRetry };

    // One pair's ack outcome, matching the listener's POST
    // /whiterun/avoidance/ack body shape exactly: a JSON array of
    // {"npc_a": str, "npc_b": str, "outcome": "applied" | "retry"}.
    struct AvoidanceAckEntry {
        std::string npcA;
        std::string npcB;
        AvoidanceApplyOutcome outcome = AvoidanceApplyOutcome::kRetry;
    };

    // POSTs the outcomes of one poll's whole batch back to the listener.
    // Fire-and-forget, same discipline as PostHydrationAck. Returns true if
    // the listener responded 2xx.
    bool PostAvoidanceAck(const OutboundConfig& config, const std::vector<AvoidanceAckEntry>& acks);

    // One (holder, target, markup_multiplier) entry, matching the listener's
    // GET /whiterun/vendor-markup response shape exactly (adapters/skyrim/
    // listener/listener.py's _vendor_markup_pairs): a JSON array of
    // {"holder_id": str, "target_id": str, "markup_multiplier": float}.
    // Directed like HydrationPair, not symmetric like AvoidancePair -- see
    // docs/design/chronicle-bridge-vendor-markup-out.md.
    //
    // BarterMenuSink.h/.cpp (the DETECTION slice) used to read this to log
    // an informational line; VendorMarkupCache.h/.cpp (the WRITE slice,
    // docs/research/28-vendor-price-hook-address-library-spike.md) is now
    // the ONE consumer -- see that file for why. It polls this fetch,
    // filters to target_id == "the_player" (a markup pair between two
    // other NPCs has no barter-menu meaning at all -- design doc's
    // resolved player-identity note), and caches the result for
    // VendorPriceHook.cpp's PostCreate override to read synchronously on
    // the main thread. Note this struct is directed and UNFILTERED here --
    // filtering to the player-relevant subset is the consumer's own job,
    // not this fetch's.
    //
    // Deliberately no ack POST for this fetch, unlike Hydration/Avoidance:
    // see VendorMarkupCache.h's own header comment for why a volatile,
    // in-process cache actively wants the listener's unacked-pair
    // re-offer/expiry behavior rather than suppressing it.
    struct VendorMarkupPair {
        std::string holderId;
        std::string targetId;
        double markupMultiplier = 1.0;
    };

    // GETs the listener's current vendor-markup pairs. Same "empty means
    // nothing changed OR the request failed, and the caller's response to
    // either is identical" contract as FetchHydrationPairs/
    // FetchAvoidancePairs -- see FetchHydrationPairs's comment.
    std::vector<VendorMarkupPair> FetchVendorMarkupPairs(const OutboundConfig& config);

    // One (holder_id, belief_id, claim_id) entry, matching the listener's GET
    // /whiterun/evidence response shape exactly (adapters/skyrim/listener/
    // listener.py's _evidence_entries): a JSON array of {"holder_id": str,
    // "belief_id": str, "claim_id": str}. Single-key, not a pair, unlike
    // Hydration/Avoidance/VendorMarkup -- there is no second party (design
    // doc §2's own ruling: evidence is bound to the believer's own position,
    // not the claim's subject). `claimId` is carried for logging/future
    // per-claim-kind object selection (design doc §3's non-goal: this cut's
    // consumer spawns one fixed base object regardless of claim kind), never
    // sent back in the ack body below.
    struct EvidenceEntry {
        std::string holderId;
        std::string beliefId;
        std::string claimId;
    };

    // GETs the listener's pending-evidence queue and parses the response.
    // Same "empty means nothing changed OR the request failed, and the
    // caller's response to either is identical" contract as
    // FetchHydrationPairs/FetchAvoidancePairs/FetchVendorMarkupPairs -- see
    // FetchHydrationPairs's comment.
    std::vector<EvidenceEntry> FetchEvidenceEntries(const OutboundConfig& config);

    // What actually happened when EvidencePoller.cpp's ApplyEvidenceEntry
    // tried to spawn one entry's evidence object. Two outcomes, like
    // avoidance/vendor-markup, not hydration's three -- design doc §2's own
    // reasoning: a PlaceObjectAtMe call has no permanent-failure mode the way
    // hydration's "no authored vanilla relationship" does (report 31's F1/F2
    // confirm PlaceObjectAtMe is a plain, unconditional, documented call).
    //   kApplied -- the believer's Actor* resolved and PlaceObjectAtMe was
    //               called. The listener should mark this entry "applied"
    //               (a true terminal state here -- see design doc §3: unlike
    //               every other slice's "applied", nothing ever re-offers
    //               this exact (holder_id, belief_id) again).
    //   kRetry   -- the believer's Actor* failed to resolve, or no game was
    //               active. TEMPORARY -- the listener should offer this
    //               entry again as if it had never been offered.
    enum class EvidenceApplyOutcome { kApplied, kRetry };

    // One entry's ack outcome, matching the listener's POST
    // /whiterun/evidence/ack body shape exactly: a JSON array of
    // {"holder_id": str, "belief_id": str, "outcome": "applied" | "retry"}.
    // Deliberately no claimId field here -- the ack protocol's dedupe key is
    // (holder_id, belief_id) only, per design doc §2.
    struct EvidenceAckEntry {
        std::string holderId;
        std::string beliefId;
        EvidenceApplyOutcome outcome = EvidenceApplyOutcome::kRetry;
    };

    // POSTs the outcomes of one poll's whole batch back to the listener.
    // Fire-and-forget, same discipline as PostHydrationAck/PostAvoidanceAck.
    // Returns true if the listener responded 2xx.
    bool PostEvidenceAck(const OutboundConfig& config, const std::vector<EvidenceAckEntry>& acks);

    // Eighth slice (docs/design/chronicle-bridge-sync-handshake-out.md §4.1,
    // the sync-wiring plan's design decision 6): the first outbound call in
    // this plugin whose response *body* the caller needs to branch on, not
    // just its status. A bare std::optional<HelloResponse> can't carry
    // enough information for SyncHandshake.cpp's three-way result mapping
    // (decision 6) -- a transport failure/timeout, a received-but-erroneous
    // HTTP status (401/403 misconfigured shared secret, 503
    // listener-up-but-gated), and a 2xx-with-unparseable-or-unrecognized
    // body are three DIFFERENT failure shapes that must be handled
    // differently (401/403 must NOT schedule a retry backoff; every failure
    // shape must log loudly, never silently default to some decision) --
    // so this returns a small result struct instead. `response` stays the
    // one field engaged on genuine success, matching the "not bool, the
    // caller needs the body" framing the plan itself gives this function.
    enum class SyncHelloTransportOutcome : std::uint8_t {
        kOk,                // 2xx, body parsed and `decision` recognized -- response is engaged.
        kTransportFailure,  // connection refused/timed out -- no HTTP response at all.
        kHttpErrorStatus,   // a real HTTP response came back, but status was not 2xx -- httpStatus is engaged.
        kUnparseableBody,   // 2xx status, but the body didn't parse or carried an unrecognized `decision` string.
    };

    struct SyncHelloResult {
        SyncHelloTransportOutcome outcome = SyncHelloTransportOutcome::kTransportFailure;
        std::optional<HelloResponse> response;  // engaged only when outcome == kOk
        int httpStatus = 0;                     // engaged only when outcome == kHttpErrorStatus
    };

    // POSTs one HELLO (spec §4.1's request body: the manifest fields as
    // JSON, `manifest_present`, `hello_seq`, `format_version`). Uses an
    // EXPLICIT 3-second read timeout, not the 1-second convention every
    // other Post*/Fetch* in this file inherits -- the spec (§4.5/§8b item 2,
    // still an open tuning question) calls this out specifically since
    // HELLO can involve a RESOLVE computation on the listener side. Never
    // throws; every failure mode is reported through SyncHelloResult's
    // outcome field, never a silent fallback to some default decision.
    SyncHelloResult PostSyncHello(const OutboundConfig& config, const SendHello& hello);

    // POSTs one mutation (spec §4.1's request body: epoch_id, save_uuid,
    // generation, seq, gamets, wall_ts, event). Returns the RAW HTTP status
    // code -- 200 (OnMutationAccepted), 409 (OnMutationRejected), and a
    // failure (OnMutationSendFailed) all mean something different to
    // SyncHandshakeCore, unlike every other fire-and-forget Post* in this
    // file, which only ever needs a bool. Returns 0 (never a real HTTP
    // status) on a transport failure -- connection refused or timeout, no
    // response received at all.
    int PostSyncMutation(const OutboundConfig& config, const SendMutation& mutation);

}  // namespace ChronicleBridge
