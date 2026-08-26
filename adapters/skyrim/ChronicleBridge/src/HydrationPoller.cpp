#include "HydrationPoller.h"

#include <chrono>
#include <future>
#include <thread>

#include "IdentityMap.h"

namespace ChronicleBridge {

    namespace {

        // Chronicle's grudge/reputation state decays over game-hours, not
        // seconds (chronicle/hydration.py's bucketing is keyed on gamets),
        // and the listener's own "last pushed" cache means a poll with
        // nothing changed is a cheap no-op response. 8 seconds: frequent
        // enough that a fresh grudge push shows up in-game well within one
        // play session, far below the ~1Hz spatial-streamer cadence (this is
        // occasional discrete state, not a telemetry stream), and low
        // enough overhead to never matter either way. A first-cut tunable,
        // not a measured constant -- same discipline as every other
        // interval/threshold placeholder in this codebase.
        constexpr auto kPollInterval = std::chrono::seconds(8);

        // Chronicle's {0, -1, -2} integer rank scale (chronicle/hydration.py's
        // relationship_rank_for) has no natural one-to-one mapping onto
        // Skyrim's 9-value RELATIONSHIP_LEVEL enum -- notably 0 has no
        // single correct target, since the enum has no "neutral" value.
        // This mapping is a first-cut placeholder, exactly like every other
        // tunable constant in this project -- not load-bearing precision,
        // and worth revisiting once this is actually observed in-game:
        //   rank >= 0   -> kAcquaintance (mildest non-adversarial value on
        //                  offer; "no grudge" is not the same as "close
        //                  friend", so this deliberately doesn't reach for
        //                  kFriend/kAlly/kConfidant/kLover)
        //   rank == -1  -> kRival
        //   rank <= -2  -> kFoe (kEnemy/kArchnemesis are reserved for a
        //                  more severe band this slice's bucketing never
        //                  actually produces -- chronicle/hydration.py's
        //                  bands top out at -2)
        RE::BGSRelationship::RELATIONSHIP_LEVEL LevelForRank(int rank) {
            using Level = RE::BGSRelationship::RELATIONSHIP_LEVEL;
            if (rank >= 0) return Level::kAcquaintance;
            if (rank == -1) return Level::kRival;
            return Level::kFoe;
        }

        // Reverse identity resolution: Chronicle npc_id -> live RE::TESNPC*.
        //
        // 1. IdentityMap::ResolveChronicleNpcId gives back the (pluginName,
        //    localFormId) pair for the placed actor reference (the same
        //    FormRef SpatialStreamer resolves FORWARD off a live RE::Actor*
        //    -- see IdentityMap.cpp's kNamedCast comment: these FormIDs are
        //    the placed reference's, not the base NPC record's).
        // 2. RE::TESDataHandler::LookupForm<RE::Actor>(localFormId,
        //    pluginName) resolves that back to a live RE::Actor*.
        //    Verified against the real header on the build machine: this
        //    template checks `form->Is(T::FORMTYPE)` internally, and
        //    RE::Actor::FORMTYPE == FormType::ActorCharacter -- the exact
        //    form type a placed actor reference's own FormID carries -- so
        //    LookupForm<RE::Actor> resolves DIRECTLY to a live Actor*, no
        //    separate LookupForm<TESObjectREFR>() + .As<RE::Actor>() step
        //    needed. This is a small divergence from the design doc's own
        //    pre-implementation guess (docs/design/
        //    chronicle-bridge-hydration-out.md §3c named that chain as
        //    unverified and to be checked here) -- the two-step chain would
        //    also have worked, but the direct one-step form is what this
        //    code actually uses.
        // 3. RE::Actor::GetActorBase() gives the TESNPC* BGSRelationship::
        //    GetRelationship needs.
        //
        // Returns nullptr if any step fails. Unlike SpatialStreamer's
        // highActorHandles-based enumeration (which really does only see
        // actors the engine is actively simulating nearby), LookupForm
        // resolves out of the form table -- a placed reference is
        // resolvable there once its master file is loaded, not only when
        // the actor is instantiated/nearby -- and BGSRelationship hangs off
        // the always-resident TESNPC base record. So in practice this is
        // expected to resolve successfully most of the time regardless of
        // where the NPC currently is; a null here more likely means the
        // reverse-cast table lookup missed, or (per the caller's own gate)
        // no save is loaded yet. Still handled as a plain skip, not an
        // error, since a null is always a legitimate "can't act on this
        // pair right now" outcome either way.
        RE::TESNPC* ResolveLiveNpc(const std::string& chronicleNpcId) {
            auto ref = ResolveChronicleNpcId(chronicleNpcId);
            if (!ref) {
                SKSE::log::trace("ChronicleBridge hydration: '{}' has no reverse named-cast entry -- skipping",
                                  chronicleNpcId);
                return nullptr;
            }

            auto* dataHandler = RE::TESDataHandler::GetSingleton();
            if (!dataHandler) return nullptr;

            auto* actor = dataHandler->LookupForm<RE::Actor>(ref->localFormId, ref->pluginName);
            if (!actor) {
                SKSE::log::trace(
                    "ChronicleBridge hydration: '{}' ({}:{:06x}) did not resolve to a live actor this poll -- "
                    "skipping",
                    chronicleNpcId, ref->pluginName, ref->localFormId);
                return nullptr;
            }

            return actor->GetActorBase();
        }

        // Applies one hydration pair to the live game. MUST run on the main
        // thread (RE::TESDataHandler lookups and the actual TESForm-derived
        // write below follow the same main-thread-only rule every other
        // RE:: access in this plugin already follows -- SpatialStreamer,
        // DeathEventSink -- via SKSE::GetTaskInterface()->AddTask).
        //
        // *** THIS IS A WRITE, NOT A READ ***, unlike every prior
        // ChronicleBridge slice. It mutates a persistent TESForm-derived
        // record (RE::BGSRelationship::level) that is part of the save
        // file. This exact write has been compiled against the real headers
        // but has NEVER been exercised against a live game or save -- there
        // is zero runtime verification beyond "it compiles." Treat it as
        // experimental.
        //
        // Returns the outcome for OutboundClient.h's PostHydrationAck to
        // report back to the listener -- see HydrationApplyOutcome's own
        // comment for the exact mapping (this function's three branches
        // below are that mapping's source of truth).
        HydrationApplyOutcome ApplyHydrationPair(const HydrationPair& pair) {
            RE::TESNPC* npc1 = ResolveLiveNpc(pair.holderId);
            if (!npc1) return HydrationApplyOutcome::kRetry;
            RE::TESNPC* npc2 = ResolveLiveNpc(pair.targetId);
            if (!npc2) return HydrationApplyOutcome::kRetry;

            // Ruled scope (design doc §3c): only ever set .level on an
            // EXISTING BGSRelationship. GetRelationship() returning null
            // means this pair has no authored vanilla relationship record
            // at all -- creating one is explicitly out of scope for this
            // slice (a real save-integrity risk this project doesn't yet
            // understand well enough to take on), so this is a skip, not an
            // error, and is expected to be the common case: most
            // Chronicle-relevant grudge pairs won't have an authored
            // vanilla relationship. PERMANENT per HydrationApplyOutcome's
            // comment -- retrying the same rank forever cannot change this.
            auto* relationship = RE::BGSRelationship::GetRelationship(npc1, npc2);
            if (!relationship) {
                SKSE::log::info(
                    "ChronicleBridge hydration: no existing BGSRelationship for ({}, {}) -- skipping per ruled "
                    "scope (never creating one)",
                    pair.holderId, pair.targetId);
                return HydrationApplyOutcome::kNoRelationship;
            }

            const auto level = LevelForRank(pair.relationshipRank);
            relationship->level = level;
            // BGSRelationship::ChangeFlags::kRelationshipData (the real
            // header's own struct, RE/B/BGSRelationship.h) exists
            // specifically to mark this field dirty for save serialization
            // -- Bethesda's savegame format only writes a form into the
            // ChangeForms list if something calls TESForm::AddChange on it;
            // otherwise the form is silently reconstructed from the plugin
            // at next load, and this write would vanish on save/reload
            // without ever erroring. Calling it is the documented API for
            // "this field changed," so it's called here -- but whether that
            // is actually SUFFICIENT for a safe, correct save round-trip of
            // a BGSRelationship record is NOT verified; this has never been
            // tested against a real save. Treat "calls AddChange" as "does
            // the documented thing," not as "confirmed safe."
            relationship->AddChange(RE::BGSRelationship::ChangeFlags::kRelationshipData);
            SKSE::log::info(
                "ChronicleBridge hydration: set relationship({}, {}).level = {} for incoming rank {} (UNVERIFIED "
                "against a live save -- compiled only, see HydrationPoller.h)",
                pair.holderId, pair.targetId, static_cast<int>(level), pair.relationshipRank);
            return HydrationApplyOutcome::kApplied;
        }

    }  // namespace

    void HydrationPollerThreadLoop(OutboundConfig config) {
        while (true) {
            std::this_thread::sleep_for(kPollInterval);

            // The GET runs on this dedicated thread, never the main thread
            // -- same reasoning as SpatialStreamer's sender thread: a
            // slow/unreachable listener must never stall the game. Only the
            // actual game-object resolution + write below needs the main
            // thread.
            auto pairs = FetchHydrationPairs(config);
            if (pairs.empty()) continue;

            // The main-thread task below needs to hand its per-pair
            // outcomes back to THIS thread so the ack POST (network I/O)
            // never runs on the main thread -- same discipline as every
            // other network call in this plugin. A std::promise/future is
            // the simplest correct handoff for this one-shot
            // request-then-single-response shape (unlike the
            // producer/queue+condvar pattern plugin.cpp's sender threads
            // use for an ongoing stream of independent items). Blocking
            // this poller thread on future.get() is fine: it is not the
            // main thread, and the main-thread task itself is bounded,
            // synchronous, per-pair game-object work -- the same work this
            // loop already waited on before this change, just now also
            // returning a result instead of firing and forgetting.
            //
            // The promise is heap-allocated behind a shared_ptr, not
            // captured by value/move directly, because SKSE::TaskInterface
            // stores the task in a std::function -- and std::function
            // requires its target be copy-constructible, which
            // std::promise is not. A shared_ptr is cheaply copyable and
            // keeps the promise alive across the hop to the main thread.
            auto ackPromise = std::make_shared<std::promise<std::vector<HydrationAckEntry>>>();
            auto ackFuture = ackPromise->get_future();

            SKSE::GetTaskInterface()->AddTask([pairs, promise = ackPromise] {
                std::vector<HydrationAckEntry> acks;
                acks.reserve(pairs.size());

                // Guard against acting before any save is loaded (e.g. this
                // thread's first 8s tick can land at the main menu, well
                // before kDataLoaded's own actor/form singletons are
                // necessarily meaningful in a live-game sense). RE::Main::
                // gameActive is the same "is a save actually running"
                // signal other CommonLibSSE-NG plugins check for this
                // purpose. Cheap, and this is the one write path in the
                // whole plugin -- worth being conservative about when it's
                // allowed to run at all.
                //
                // Nothing in this batch was even attempted when no game is
                // active -- that is a TEMPORARY condition (a save may load
                // moments later), so every pair is reported kRetry rather
                // than silently dropping the ack call entirely. Skipping
                // the ack outright here would leave these pairs stuck
                // "awaiting_ack" on the listener's side until the next poll
                // happens to offer them a genuinely different rank (see
                // listener.py's _HydrationPairState) -- reporting kRetry
                // explicitly is the more honest, self-correcting choice.
                auto* main = RE::Main::GetSingleton();
                if (!main || !main->gameActive) {
                    SKSE::log::trace("ChronicleBridge hydration: no active game -- reporting this poll's pairs as retry");
                    for (const auto& pair : pairs) {
                        acks.push_back({.holderId = pair.holderId, .targetId = pair.targetId,
                                         .outcome = HydrationApplyOutcome::kRetry});
                    }
                } else {
                    for (const auto& pair : pairs) {
                        auto outcome = ApplyHydrationPair(pair);
                        acks.push_back({.holderId = pair.holderId, .targetId = pair.targetId, .outcome = outcome});
                    }
                }

                promise->set_value(std::move(acks));
            });

            auto acks = ackFuture.get();
            PostHydrationAck(config, acks);
        }
    }

}  // namespace ChronicleBridge
