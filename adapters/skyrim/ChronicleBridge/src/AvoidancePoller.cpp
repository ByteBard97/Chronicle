#include "AvoidancePoller.h"

#include <chrono>
#include <future>
#include <thread>

#include "AvoidanceGlobals.h"
#include "IdentityMap.h"

namespace ChronicleBridge {

    namespace {

        // Same cadence rationale as HydrationPoller.cpp's kPollInterval:
        // avoidance is occasional discrete state (rule 18 recomputes it
        // every tick, but the listener only returns a pair when its
        // bucketed `avoiding` value actually flips), not a ~1Hz telemetry
        // stream. Reusing the identical 8s interval rather than inventing a
        // second, arbitrarily-different tunable for a protocol this
        // structurally similar to hydration's.
        constexpr auto kPollInterval = std::chrono::seconds(8);

        // Reverse identity resolution: Chronicle npc_id -> live RE::Actor*.
        // Same chain as HydrationPoller.cpp's ResolveLiveNpc, stopping one
        // step earlier -- this slice needs the live Actor* itself (for
        // EvaluatePackage), not its TESNPC* base record.
        RE::Actor* ResolveLiveActor(const std::string& chronicleNpcId) {
            auto ref = ResolveChronicleNpcId(chronicleNpcId);
            if (!ref) {
                SKSE::log::trace("ChronicleBridge avoidance: '{}' has no reverse named-cast entry -- skipping",
                                  chronicleNpcId);
                return nullptr;
            }

            auto* dataHandler = RE::TESDataHandler::GetSingleton();
            if (!dataHandler) return nullptr;

            auto* actor = dataHandler->LookupForm<RE::Actor>(ref->localFormId, ref->pluginName);
            if (!actor) {
                SKSE::log::trace(
                    "ChronicleBridge avoidance: '{}' ({}:{:06x}) did not resolve to a live actor this poll -- "
                    "skipping",
                    chronicleNpcId, ref->pluginName, ref->localFormId);
                return nullptr;
            }
            return actor;
        }

        // Applies one avoidance pair to the live game. MUST run on the main
        // thread -- same rule every RE:: access in this plugin follows.
        //
        // Unlike HydrationPoller's ApplyHydrationPair, this write path has
        // NO unverified-API risk: TESGlobal::value is a plain float member
        // and Actor::EvaluatePackage's signature was already confirmed real
        // by this slice's design doc (§2b). It has still never been
        // exercised against a live game/save -- see AvoidancePoller.h's own
        // header comment for that same "compiles only" caveat.
        AvoidanceApplyOutcome ApplyAvoidancePair(const AvoidancePair& pair) {
            RE::Actor* actorA = ResolveLiveActor(pair.npcA);
            if (!actorA) return AvoidanceApplyOutcome::kRetry;
            RE::Actor* actorB = ResolveLiveActor(pair.npcB);
            if (!actorB) return AvoidanceApplyOutcome::kRetry;

            // See AvoidanceGlobals.h: a pair with no authored global yet
            // (tools/chronicle-patcher/ hasn't generated it, or never will)
            // is reported kRetry -- the ack protocol has no third,
            // permanent-skip outcome the way hydration's does.
            auto ref = ResolveAvoidancePairGlobal(pair.npcA, pair.npcB);
            if (!ref) {
                SKSE::log::trace(
                    "ChronicleBridge avoidance: no ChronicleAvoidingPair_* global authored yet for ({}, {}) -- "
                    "retrying later",
                    pair.npcA, pair.npcB);
                return AvoidanceApplyOutcome::kRetry;
            }

            auto* dataHandler = RE::TESDataHandler::GetSingleton();
            if (!dataHandler) return AvoidanceApplyOutcome::kRetry;

            auto* global = dataHandler->LookupForm<RE::TESGlobal>(ref->localFormId, ref->pluginName);
            if (!global) {
                SKSE::log::trace(
                    "ChronicleBridge avoidance: ChronicleAvoidingPair_* global for ({}, {}) ({}:{:06x}) did not "
                    "resolve this poll -- retrying later",
                    pair.npcA, pair.npcB, ref->pluginName, ref->localFormId);
                return AvoidanceApplyOutcome::kRetry;
            }

            // Unlike BGSRelationship::level (HydrationPoller.cpp), a global
            // variable's value is part of Skyrim's always-serialized
            // "Global Variables" savegame record, not gated behind
            // TESForm::AddChange the way most other TESForm-derived records
            // are -- so no AddChange call is made here. This is reasoned
            // from documented Bethesda engine behavior, not confirmed
            // against a real save round-trip from this development pass;
            // treat it with the same "compiles only" skepticism as every
            // other write in this file.
            global->value = pair.avoiding ? 1.0f : 0.0f;

            actorA->EvaluatePackage(true, true);
            actorB->EvaluatePackage(true, true);

            SKSE::log::info(
                "ChronicleBridge avoidance: set ChronicleAvoidingPair_{}_{} = {} (UNVERIFIED against a live save -- "
                "compiled only, see AvoidancePoller.h)",
                pair.npcA, pair.npcB, pair.avoiding ? 1 : 0);
            return AvoidanceApplyOutcome::kApplied;
        }

    }  // namespace

    void AvoidancePollerThreadLoop(OutboundConfig config) {
        while (true) {
            std::this_thread::sleep_for(kPollInterval);

            // The GET runs on this dedicated thread, never the main thread
            // -- same reasoning as HydrationPollerThreadLoop.
            auto pairs = FetchAvoidancePairs(config);
            if (pairs.empty()) continue;

            // Same std::promise/future main-thread hand-off pattern as
            // HydrationPollerThreadLoop -- see that function's comment for
            // why (shared_ptr-wrapped promise, std::function copyability).
            auto ackPromise = std::make_shared<std::promise<std::vector<AvoidanceAckEntry>>>();
            auto ackFuture = ackPromise->get_future();

            SKSE::GetTaskInterface()->AddTask([pairs, promise = ackPromise] {
                std::vector<AvoidanceAckEntry> acks;
                acks.reserve(pairs.size());

                // Same RE::Main::gameActive guard as
                // HydrationPollerThreadLoop's main-thread task -- see that
                // function's comment for the full reasoning.
                auto* main = RE::Main::GetSingleton();
                if (!main || !main->gameActive) {
                    SKSE::log::trace("ChronicleBridge avoidance: no active game -- reporting this poll's pairs as retry");
                    for (const auto& pair : pairs) {
                        acks.push_back(
                            {.npcA = pair.npcA, .npcB = pair.npcB, .outcome = AvoidanceApplyOutcome::kRetry});
                    }
                } else {
                    for (const auto& pair : pairs) {
                        auto outcome = ApplyAvoidancePair(pair);
                        acks.push_back({.npcA = pair.npcA, .npcB = pair.npcB, .outcome = outcome});
                    }
                }

                promise->set_value(std::move(acks));
            });

            auto acks = ackFuture.get();
            PostAvoidanceAck(config, acks);
        }
    }

}  // namespace ChronicleBridge
