#include "VendorMarkupCache.h"

#include <chrono>
#include <mutex>
#include <thread>
#include <unordered_map>

namespace ChronicleBridge {

    namespace {

        // Same "occasional discrete state, not a telemetry stream" cadence
        // reasoning as HydrationPoller.h's kPollInterval -- Chronicle's
        // grudge/markup state decays over game-hours, not seconds, and the
        // listener's own dedupe cache means a poll with nothing changed is
        // a cheap no-op response. Matches HydrationPoller/AvoidancePoller's
        // own 8-second value exactly -- no reason for a different cadence
        // for a third instance of the same poll shape.
        constexpr auto kPollInterval = std::chrono::seconds(8);

        // design doc's resolved player-identity note / chronicle/fixtures/
        // north_star.py's KILLER convention: the one established identity
        // for "the player" anywhere in this project's Chronicle-side state.
        constexpr std::string_view kPlayerTargetId = "the_player";

        std::mutex g_mutex;
        std::unordered_map<std::string, double> g_multiplierByHolderId;

    }  // namespace

    std::optional<double> GetPlayerMarkupMultiplier(const std::string& vendorNpcId) {
        std::lock_guard lock(g_mutex);
        auto it = g_multiplierByHolderId.find(vendorNpcId);
        if (it == g_multiplierByHolderId.end()) return std::nullopt;
        return it->second;
    }

    void VendorMarkupCachePollerThreadLoop(OutboundConfig config) {
        while (true) {
            std::this_thread::sleep_for(kPollInterval);

            // The GET runs on this dedicated thread, never the main thread
            // -- same reasoning as every other poller in this plugin: a
            // slow/unreachable listener must never stall the game. This
            // file's own header comment explains why this is now the ONE
            // caller of FetchVendorMarkupPairs.
            auto pairs = FetchVendorMarkupPairs(config);
            if (pairs.empty()) continue;

            // Filter to target_id == "the_player" before merging into the
            // cache -- an NPC-to-NPC pair has no barter-menu meaning and
            // must never end up in the map VendorPriceHook.cpp's
            // PostCreate reads from (design doc's resolved player-identity
            // note; this project's own step 4 instruction for this slice).
            // This is a MERGE into the existing cache, not a wholesale
            // replace: the listener's GET only returns pairs whose
            // multiplier actually CHANGED since the last poll (same dedupe
            // discipline as FetchHydrationPairs/FetchAvoidancePairs), so a
            // pair absent from this particular response still has a valid,
            // unchanged multiplier that must stay cached, not be dropped.
            //
            // No ack POST here -- see this file's header comment for why
            // this consumer deliberately relies on the listener's own
            // dropped-ack-timeout re-offer behavior instead of confirming
            // delivery.
            std::unordered_map<std::string, double> changed;
            for (const auto& pair : pairs) {
                if (pair.targetId == kPlayerTargetId) {
                    changed[pair.holderId] = pair.markupMultiplier;
                }
            }
            if (changed.empty()) continue;

            std::lock_guard lock(g_mutex);
            for (auto& [holderId, multiplier] : changed) {
                g_multiplierByHolderId[holderId] = multiplier;
                // info, not trace: this is a state CHANGE, not per-poll
                // spam -- `changed` is only non-empty when the listener
                // reported a genuinely new multiplier for a player-facing
                // pair, so an unattended harness reading the log can treat
                // each of these as one real cache write.
                SKSE::log::info("ChronicleBridge vendor-markup: cached {:.2f}x for vendor '{}' (target the_player)",
                                 multiplier, holderId);
            }
        }
    }

}  // namespace ChronicleBridge
