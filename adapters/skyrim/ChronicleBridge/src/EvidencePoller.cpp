#include "EvidencePoller.h"

#include <chrono>
#include <future>
#include <thread>

#include "IdentityMap.h"

namespace ChronicleBridge {

    namespace {

        // Same cadence rationale as HydrationPoller.cpp/AvoidancePoller.cpp's
        // kPollInterval: evidence reveals are occasional discrete state (a
        // belief's decayed confidence crossing a threshold), not a ~1Hz
        // telemetry stream, and the listener's own dedupe/awaiting-ack cache
        // means a poll with nothing new is a cheap no-op response. Reusing
        // the identical 8s interval rather than inventing a second,
        // arbitrarily-different tunable for a protocol this structurally
        // similar to the other three poll/ack slices.
        constexpr auto kPollInterval = std::chrono::seconds(8);

        // PLACEHOLDER EVIDENCE BASE OBJECT -- replace once a real evidence
        // base object is authored (design doc §5 step 2, separate/deferred
        // work; report 31's recommendation 2 scopes the first cut's object
        // to "a single pre-authored MISC or WEAP item").
        //
        // "Gold" (EditorID Gold001, MISC, Skyrim.esm, FormID 0x0000000F) --
        // chosen not for thematic fit (it plainly isn't "evidence") but for
        // being the single most reliably-known vanilla MISC FormID across
        // every TES-engine game (Morrowind/Oblivion/Skyrim all use
        // 0x0000000F for Gold001) -- an obviously-throwaway placeholder that
        // reads as clearly wrong-on-purpose if ever spotted in-game, the
        // same "obviously placeholder, not a real content decision" spirit
        // AvoidanceGlobals.h's own pre-real-FormID phase named for its
        // pair-global table. UNLIKE AvoidanceGlobals.cpp's now-real FormIDs
        // (filled in from an actual tools/chronicle-patcher/ run against
        // Skyrim.esm), this FormID has NOT been independently verified
        // against a real Skyrim.esm read in this pass -- confirm it (or
        // replace it with a real evidence base object, per design doc §5
        // step 2) before this is ever exercised in an actual play session.
        // ResolveLiveActor's LookupForm below fails safe (returns nullptr ->
        // ApplyEvidenceEntry reports kRetry forever) if this FormID is
        // somehow wrong, so a bad value here cannot crash or corrupt
        // anything, it just silently never spawns.
        constexpr std::string_view kPlaceholderPluginName = "Skyrim.esm";
        constexpr std::uint32_t kPlaceholderLocalFormId = 0x0000000F;

        // Reverse identity resolution: Chronicle npc_id -> live RE::Actor*.
        // Same chain as AvoidancePoller.cpp's ResolveLiveActor -- this slice
        // needs the live Actor* itself (PlaceObjectAtMe is a TESObjectREFR
        // method, and RE::Actor derives from TESObjectREFR), not a TESNPC*
        // base record the way HydrationPoller.cpp's write does.
        RE::Actor* ResolveLiveActor(const std::string& chronicleNpcId) {
            auto ref = ResolveChronicleNpcId(chronicleNpcId);
            if (!ref) {
                SKSE::log::trace("ChronicleBridge evidence: '{}' has no reverse named-cast entry -- skipping",
                                  chronicleNpcId);
                return nullptr;
            }

            auto* dataHandler = RE::TESDataHandler::GetSingleton();
            if (!dataHandler) return nullptr;

            auto* actor = dataHandler->LookupForm<RE::Actor>(ref->localFormId, ref->pluginName);
            if (!actor) {
                SKSE::log::trace(
                    "ChronicleBridge evidence: '{}' ({}:{:06x}) did not resolve to a live actor this poll -- "
                    "skipping",
                    chronicleNpcId, ref->pluginName, ref->localFormId);
                return nullptr;
            }
            return actor;
        }

        // Applies one evidence entry to the live game. MUST run on the main
        // thread -- same rule every RE:: access in this plugin follows.
        //
        // *** THIS IS A WRITE, AND UNLIKE EVERY PRIOR SLICE IT SPAWNS A NEW
        // REFERENCE INTO THE WORLD *** rather than mutating an existing
        // record's field. See EvidencePoller.h's own header comment for the
        // full "compiles only, never exercised against a live save"
        // caveat -- treat this as experimental.
        EvidenceApplyOutcome ApplyEvidenceEntry(const EvidenceEntry& entry) {
            RE::Actor* believer = ResolveLiveActor(entry.holderId);
            if (!believer) return EvidenceApplyOutcome::kRetry;

            auto* dataHandler = RE::TESDataHandler::GetSingleton();
            if (!dataHandler) return EvidenceApplyOutcome::kRetry;

            auto* evidenceObject =
                dataHandler->LookupForm<RE::TESObjectMISC>(kPlaceholderLocalFormId, kPlaceholderPluginName);
            if (!evidenceObject) {
                SKSE::log::warn(
                    "ChronicleBridge evidence: placeholder evidence base object ({}:{:06x}) did not resolve -- "
                    "retrying later (see EvidencePoller.cpp's kPlaceholderLocalFormId comment)",
                    kPlaceholderPluginName, kPlaceholderLocalFormId);
                return EvidenceApplyOutcome::kRetry;
            }

            // a_forcePersist = true: unlike report 31's F3 prior-art
            // examples (Styyx1/SurpriseSpawner, HarperZ9/skyrimbridge), both
            // of which spawn short-lived combat/visual props that are
            // expected to despawn or get cleaned up, this slice's whole
            // point is a physical object that stays in the world for the
            // player to find later -- an evidence object the engine's
            // ordinary reference-cleanup pass silently deleted before the
            // player ever saw it would defeat the entire feature. Named
            // explicitly per this project's own discipline: this is a
            // deliberate choice, not report 31's literal recommendation 1
            // snippet copied verbatim (which passed `true` too, but without
            // explaining why) -- and it is a real, accepted tradeoff, not a
            // free one: a forced-persistent reference is never garbage
            // collected, so every successful spawn is a small permanent
            // addition to the save file for the lifetime of that save,
            // compounding with §3's own "no retraction, ever" limitation.
            // Not verified against a real save's long-run size/behavior in
            // this pass.
            auto spawned = believer->PlaceObjectAtMe(evidenceObject, true);
            if (!spawned) {
                SKSE::log::warn(
                    "ChronicleBridge evidence: PlaceObjectAtMe returned null for holder '{}' belief '{}' (claim "
                    "'{}') -- retrying later",
                    entry.holderId, entry.beliefId, entry.claimId);
                return EvidenceApplyOutcome::kRetry;
            }

            SKSE::log::info(
                "ChronicleBridge evidence: spawned placeholder evidence object at '{}''s position for belief '{}' "
                "(claim '{}') (UNVERIFIED against a live save -- compiled only, see EvidencePoller.h)",
                entry.holderId, entry.beliefId, entry.claimId);
            return EvidenceApplyOutcome::kApplied;
        }

    }  // namespace

    void EvidencePollerThreadLoop(OutboundConfig config) {
        while (true) {
            std::this_thread::sleep_for(kPollInterval);

            // The GET runs on this dedicated thread, never the main thread
            // -- same reasoning as every other poller in this plugin.
            auto entries = FetchEvidenceEntries(config);
            if (entries.empty()) continue;

            // Same std::promise/future main-thread hand-off pattern as
            // HydrationPollerThreadLoop/AvoidancePollerThreadLoop -- see
            // HydrationPollerThreadLoop's comment for why (shared_ptr-wrapped
            // promise, std::function copyability).
            auto ackPromise = std::make_shared<std::promise<std::vector<EvidenceAckEntry>>>();
            auto ackFuture = ackPromise->get_future();

            SKSE::GetTaskInterface()->AddTask([entries, promise = ackPromise] {
                std::vector<EvidenceAckEntry> acks;
                acks.reserve(entries.size());

                // Same RE::Main::gameActive guard as
                // HydrationPollerThreadLoop's/AvoidancePollerThreadLoop's
                // main-thread task -- see HydrationPollerThreadLoop's
                // comment for the full reasoning.
                auto* main = RE::Main::GetSingleton();
                if (!main || !main->gameActive) {
                    SKSE::log::trace("ChronicleBridge evidence: no active game -- reporting this poll's entries as retry");
                    for (const auto& entry : entries) {
                        acks.push_back({.holderId = entry.holderId,
                                         .beliefId = entry.beliefId,
                                         .outcome = EvidenceApplyOutcome::kRetry});
                    }
                } else {
                    for (const auto& entry : entries) {
                        auto outcome = ApplyEvidenceEntry(entry);
                        acks.push_back({.holderId = entry.holderId, .beliefId = entry.beliefId, .outcome = outcome});
                    }
                }

                promise->set_value(std::move(acks));
            });

            auto acks = ackFuture.get();
            PostEvidenceAck(config, acks);
        }
    }

}  // namespace ChronicleBridge
