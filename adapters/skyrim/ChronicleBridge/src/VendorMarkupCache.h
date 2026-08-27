#pragma once

// Sixth ChronicleBridge slice -- the network/threading half of the WRITE
// side of docs/design/chronicle-bridge-vendor-markup-out.md's grudge-driven
// vendor markup feature (see VendorPriceHook.h for the game-side hook this
// feeds). docs/research/28-vendor-price-hook-address-library-spike.md's
// Recommendation step 3 calls for "ChronicleBridge's own already-polled
// markup_multiplier cache for that npc_id" as the handoff between the
// network poll thread and the main-thread PostCreate hook, which can never
// block on network I/O itself -- this file is that cache.
//
// Threading shape: same TimerThreadLoop-off-main-thread pattern
// HydrationPoller.h/AvoidancePoller.h already use. Every poll interval,
// GETs /whiterun/vendor-markup, filters the response to target_id ==
// "the_player" (design doc's resolved player-identity note: a markup pair
// between two other NPCs -- pure NPC<->NPC Grudge state -- has no
// barter-menu meaning at all), and merges that filtered result into a
// mutex-guarded (holder_id -> markup_multiplier) map. VendorPriceHook.cpp's
// PostCreate override reads this cache synchronously via
// GetPlayerMarkupMultiplier -- a plain mutex-guarded map lookup, safe to
// call from the main thread at barter-menu-construction time.
//
// This is also the ONE consumer of GET /whiterun/vendor-markup --
// BarterMenuSink.cpp's own detection path used to fetch it too (for a
// read-only log line), but that call has been removed: listener.py's
// _vendor_markup_pairs is a DELTA feed with the same dedupe/awaiting-ack
// discipline hydration/avoidance's own GETs use (a pair is only returned
// once, until its value changes again or its awaiting-ack entry expires),
// so two independent pollers racing for the same GET would silently starve
// each other -- whichever call landed first would consume the delta the
// other needed. BarterMenuSenderThreadLoop's log line now reads this
// cache's GetPlayerMarkupMultiplier instead of calling
// FetchVendorMarkupPairs a second time, so it reports the exact number
// PostCreate would apply (or "no entry"), not a stale/racy second read.
//
// Deliberately NO ack POST to the listener, unlike HydrationPoller.cpp/
// AvoidancePoller.cpp. Those two ack "applied" because their write lands
// in a PERSISTENT game record (a save-file field) that survives process
// restarts -- "never offer this pair again at this value" is correct
// there. This cache is the opposite: it is pure in-process memory that
// dies with the plugin. If this poller acked "applied" the moment a pair
// landed in the cache, the listener (a separate, longer-lived process)
// would mark that exact multiplier as delivered and stop re-offering it --
// so a later game session starting with an EMPTY cache would never
// receive that vendor's markup again unless the underlying grudge's
// multiplier changed to a new value first. Sending "retry" unconditionally
// instead would just be a noisier way to get the listener's existing
// dropped-ack-timeout re-offer behavior (60s, listener.py's
// _AWAITING_ACK_TIMEOUT_SECONDS) -- so this file skips the ack call
// entirely and relies on that same timeout to self-heal a cold cache
// (e.g. after a plugin/game restart) within one timeout window of the
// next poll. This is a deliberate divergence from the sibling pollers'
// ack discipline, not an oversight -- see listener.py's
// _VendorMarkupPairState docstring for the state machine this plays into.

#include <optional>
#include <string>

#include "OutboundClient.h"

namespace ChronicleBridge {

    // Runs forever on its own thread. Never call from the main thread --
    // it blocks on the network GET itself, same discipline as every other
    // poller in this plugin.
    void VendorMarkupCachePollerThreadLoop(OutboundConfig config);

    // Returns the current player-directed markup multiplier for a vendor's
    // npc_id, or std::nullopt if no target_id == "the_player" pair exists
    // for it in the most recent successful poll. Safe to call from any
    // thread (mutex-guarded), in particular the main thread from
    // VendorPriceHook.cpp's PostCreate override, and the barter-menu
    // detection/log path in plugin.cpp.
    //
    // Per docs/research/28-vendor-price-hook-address-library-spike.md's
    // Recommendation step 5 / this slice's own instructions: a
    // std::nullopt here means VendorPriceHook.cpp should install NO
    // callback swap at all for that vendor, rather than installing one
    // that multiplies by a no-op 1.0 -- simpler and strictly safer (a
    // vendor with no markup entry gets literally zero code added to its
    // barter-menu callback chain).
    std::optional<double> GetPlayerMarkupMultiplier(const std::string& vendorNpcId);

}  // namespace ChronicleBridge
