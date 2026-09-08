#include "EvidencePoller.h"

#include <chrono>
#include <future>
#include <set>
#include <thread>
#include <utility>

#include "IdentityMap.h"

namespace ChronicleBridge {

    namespace {

        // Process-lifetime dedupe against the listener's own documented
        // restart behavior (adapters/skyrim/listener/listener.py's
        // _EvidenceEntryState docstring: its "applied" status is in-memory
        // only and does NOT survive a listener restart -- an already-spawned
        // entry reverts to "not-yet-offered" and gets re-offered as if new).
        // Without this, a routine Python-side listener restart -- the game
        // process itself keeps running the whole time -- would make
        // ApplyEvidenceEntry spawn a second, permanent duplicate of every
        // evidence object already in the world. See
        // docs/design/mod-conflict-mitigation-plan.md §4 for the full
        // finding. Keyed on (holderId, beliefId), the same dedupe key the
        // wire protocol itself already uses (OutboundClient.h's
        // EvidenceAckEntry comment). Deliberately process-lifetime only, not
        // persisted across a full game restart -- a `forcePersist=true`
        // object surviving a save/reload means the listener's own database
        // (not this cache) is the actual source of truth across saves; this
        // cache only needs to survive a listener restart *within* a running
        // game session, which it does.
        std::set<std::pair<std::string, std::string>> g_alreadySpawnedEvidence;

        // Same cadence rationale as HydrationPoller.cpp/AvoidancePoller.cpp's
        // kPollInterval: evidence reveals are occasional discrete state (a
        // belief's decayed confidence crossing a threshold), not a ~1Hz
        // telemetry stream, and the listener's own dedupe/awaiting-ack cache
        // means a poll with nothing new is a cheap no-op response. Reusing
        // the identical 8s interval rather than inventing a second,
        // arbitrarily-different tunable for a protocol this structurally
        // similar to the other three poll/ack slices.
        constexpr auto kPollInterval = std::chrono::seconds(8);

        // REAL EVIDENCE BASE OBJECT -- design doc §5 step 2's "pick/author a
        // real evidence object" is done. This is now real authored content,
        // not a placeholder: a brand-new MISC record, EditorID
        // ChronicleEvidenceObject, authored by
        // tools/chronicle-patcher/src/EvidenceItemPatchBuilder.cs into
        // ChroniclePatcher.esp (the same output plugin
        // AvoidanceGlobals.cpp's real FormIDs come from). A new record was
        // authored rather than reusing an existing vanilla FormID (report
        // 31 recommendation 2's literal "single pre-authored MISC or WEAP
        // item" wording would allow either) specifically to avoid the risk
        // of blind-picking a vanilla record that turns out to be unique,
        // quest-critical, or carries an attached script -- every field on
        // this record is explicit and known because this project's own
        // patcher set every one of them. It is not an invisible/
        // default-cube object in-game: its Model is a real vanilla clutter
        // path, `Clutter\BloodyRags\BloodyRags.nif` (copied as a plain
        // string, the same model vanilla Skyrim.esm's own BloodyRags01 MISC
        // record uses -- confirmed via a real Mutagen read against
        // Skyrim.esm to be non-unique/non-quest/unscripted, and a
        // thematically better fit for "evidence of something happened
        // here" than the superseded Gold001 placeholder), not a reference
        // to that vanilla record itself. FormID 0x000a01 confirmed by
        // running the patcher against a real Skyrim.esm + HearthFires.esm +
        // USSEP load order and reading the resulting ChroniclePatcher.esp
        // back with Mutagen (same verification technique
        // AvoidanceGlobals.cpp's 171-pair run used) -- not guessed.
        //
        // *** THIS FORMID IS ALLOCATION-ORDER-DEPENDENT, NOT FIXED ***:
        // tools/chronicle-patcher/src/Program.cs authors the evidence item
        // (EvidenceItemPatchBuilder) AFTER AvoidancePatchBuilder has already
        // claimed 3 new FormIDs per resolved named-cast pair (1 global + 2
        // packages) -- so this value is `0x800 + 3 * pairCount` (0x800 is
        // Mutagen's first new-ESP FormID; today's 19-NPC roster resolves to
        // 171 pairs, 513 prior records, landing here at 0xa01). If
        // IdentityMap.cpp's/IdentityMap.cs's named-cast roster ever grows or
        // shrinks, THIS VALUE SHIFTS -- re-run the patcher and re-read
        // out/chronicle-evidence.json (the regeneration source for this
        // constant, mirroring out/chronicle-globals.json's role for
        // AvoidanceGlobals.cpp's table) before trusting it again. Same
        // "hardcoded from a real run, re-verify if the roster changes"
        // posture AvoidanceGlobals.cpp's own table already carries.
        //
        // ResolveLiveActor's LookupForm below still fails safe (returns
        // nullptr -> ApplyEvidenceEntry reports kRetry forever) if this
        // FormID is ever stale, so a bad value here still cannot crash or
        // corrupt anything, it just silently never spawns.
        constexpr std::string_view kEvidencePluginName = "ChroniclePatcher.esp";
        constexpr std::uint32_t kEvidenceLocalFormId = 0x000a01;

        // Reverse identity resolution: Chronicle npc_id -> live RE::Actor*.
        // Same chain as AvoidancePoller.cpp's ResolveLiveActor -- this slice
        // needs the live Actor* itself (PlaceObjectAtMe is a TESObjectREFR
        // method, and RE::Actor derives from TESObjectREFR), not a TESNPC*
        // base record the way HydrationPoller.cpp's write does.
        RE::Actor* ResolveLiveActor(const std::string& chronicleNpcId) {
            auto ref = ResolveChronicleNpcId(chronicleNpcId);
            if (!ref) {
                SKSE::log::debug("ChronicleBridge evidence: '{}' has no reverse named-cast entry -- skipping",
                                  chronicleNpcId);
                return nullptr;
            }

            auto* dataHandler = RE::TESDataHandler::GetSingleton();
            if (!dataHandler) return nullptr;

            auto* actor = dataHandler->LookupForm<RE::Actor>(ref->localFormId, ref->pluginName);
            if (!actor) {
                SKSE::log::debug(
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
            // Dedupe first, before resolving anything -- if this exact
            // belief already produced a spawn earlier in this process's
            // life, report it applied again without touching the world a
            // second time. See g_alreadySpawnedEvidence's own comment for
            // why this is necessary, not just defensive.
            const auto dedupeKey = std::make_pair(entry.holderId, entry.beliefId);
            if (g_alreadySpawnedEvidence.contains(dedupeKey)) {
                SKSE::log::debug(
                    "ChronicleBridge evidence: '{}''s belief '{}' was already spawned earlier this session -- "
                    "re-offer from a listener restart, reporting applied without spawning again",
                    entry.holderId, entry.beliefId);
                return EvidenceApplyOutcome::kApplied;
            }

            RE::Actor* believer = ResolveLiveActor(entry.holderId);
            if (!believer) return EvidenceApplyOutcome::kRetry;

            // A dead believer's own reference can still resolve via
            // LookupForm (the base record persists even once the actor is a
            // corpse), but PlaceObjectAtMe on a dead/disabled reference is
            // exactly the "several of the 19 can die" edge case flagged in
            // docs/design/mod-conflict-mitigation-plan.md §4 -- fail safe
            // (retry forever, the same as any other unresolved-actor case)
            // rather than spawn evidence on/near a corpse or risk an
            // undefined placement.
            if (believer->IsDead()) {
                SKSE::log::debug(
                    "ChronicleBridge evidence: holder '{}' is dead -- skipping this poll, retrying later",
                    entry.holderId);
                return EvidenceApplyOutcome::kRetry;
            }

            auto* dataHandler = RE::TESDataHandler::GetSingleton();
            if (!dataHandler) return EvidenceApplyOutcome::kRetry;

            auto* evidenceObject =
                dataHandler->LookupForm<RE::TESObjectMISC>(kEvidenceLocalFormId, kEvidencePluginName);
            if (!evidenceObject) {
                SKSE::log::warn(
                    "ChronicleBridge evidence: evidence base object ({}:{:06x}) did not resolve -- "
                    "retrying later (see EvidencePoller.cpp's kEvidenceLocalFormId comment)",
                    kEvidencePluginName, kEvidenceLocalFormId);
                return EvidenceApplyOutcome::kRetry;
            }

            // a_forcePersist = true, KEPT deliberately as of this pass, not
            // reflexively flipped to false: unlike report 31's F3 prior-art
            // examples (Styyx1/SurpriseSpawner, HarperZ9/skyrimbridge), both
            // of which spawn short-lived combat/visual props that are
            // expected to despawn or get cleaned up, this slice's whole
            // point is a physical object that stays in the world for the
            // player to find later -- an evidence object the engine's
            // ordinary reference-cleanup pass silently deleted before the
            // player ever saw it would defeat the entire feature. Per
            // docs/design/mod-conflict-mitigation-plan.md §4 (cross-checked
            // against the CK wiki's own PlaceAtMe documentation): a
            // NON-persistent PlaceAtMe reference is ALSO not auto-cleaned by
            // an ordinary cell reset, so dropping forcePersist here would
            // not, by itself, fix anything -- the actual fix for unbounded
            // save growth is an explicit retraction/expiry signal (call
            // Disable()+MarkForDelete() when a belief's evidence is
            // superseded or collected), which does not exist yet on either
            // side of the wire protocol (design doc §3's "no retraction,
            // ever" is a stated limitation, not an oversight this function
            // alone can fix). g_alreadySpawnedEvidence above closes the one
            // concrete accumulation bug found so far (duplicate spawns from
            // a listener restart); genuine unbounded growth across a very
            // long playthrough is a real, separate, larger design task
            // (protocol-level retraction) tracked in the mitigation plan,
            // not silently solved by this pass.
            auto spawned = believer->PlaceObjectAtMe(evidenceObject, true);
            if (!spawned) {
                SKSE::log::warn(
                    "ChronicleBridge evidence: PlaceObjectAtMe returned null for holder '{}' belief '{}' (claim "
                    "'{}') -- retrying later",
                    entry.holderId, entry.beliefId, entry.claimId);
                return EvidenceApplyOutcome::kRetry;
            }

            g_alreadySpawnedEvidence.insert(dedupeKey);
            SKSE::log::info(
                "ChronicleBridge evidence: spawned evidence object at '{}''s position for belief '{}' "
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
                    SKSE::log::debug("ChronicleBridge evidence: no active game -- reporting this poll's entries as retry");
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
