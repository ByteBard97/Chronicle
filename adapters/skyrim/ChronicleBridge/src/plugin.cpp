// ChronicleBridge -- entry point. First slice only (docs/design/
// chronicle-bridge-spatial-streamer.md): sample WhiterunWorld's outdoor
// actors at ~1Hz, push each snapshot out to the Chronicle host. No event
// sinks, no hydration, no save/reload sync yet -- those are real future
// slices, not this one.
//
// Threading shape (deliberately NOT "sleep inside a main-thread task"):
// research/22's own recommendation is a periodic task that enumerates
// actors, then "pushes spatial state vectors to the network QUEUE" --
// i.e. sampling and sending are two different concerns on two different
// threads, because RE::ProcessLists access needs the main game thread
// (SKSE::GetTaskInterface()'s whole purpose), but the outbound HTTP POST
// (OutboundClient.cpp's own 1s connect/write/read timeouts) must never run
// on that thread -- a slow or unreachable listener would otherwise stall
// the game every single sample. So: a dedicated timer thread drives the
// ~1Hz cadence and only ever touches a mutex-guarded "latest snapshot"
// slot; a dedicated sender thread blocks on that slot and does the actual
// network I/O; the main thread is only ever asked to do the actual
// RE::ProcessLists enumeration, which research/22 measured at <50
// microseconds -- negligible even on the main thread.

#include <spdlog/sinks/basic_file_sink.h>

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <deque>
#include <mutex>
#include <thread>

#include "AvoidancePoller.h"
#include "BarterMenuSink.h"
#include "Config.h"
#include "DeathEventSink.h"
#include "EvidencePoller.h"
#include "HydrationPoller.h"
#include "OutboundClient.h"
#include "SpatialStreamer.h"
#include "SyncHandshake.h"
#include "VendorMarkupCache.h"
#include "VendorPriceHook.h"

namespace {

    void SetupLog() {
        auto logsFolder = SKSE::log::log_directory();
        if (!logsFolder) {
            SKSE::stl::report_and_fail("SKSE log_directory not provided, logs disabled.");
            return;
        }
        auto pluginName = SKSE::PluginDeclaration::GetSingleton()->GetName();
        auto logFilePath = *logsFolder / std::format("{}.log", pluginName);
        auto fileLoggerPtr = std::make_shared<spdlog::sinks::basic_file_sink_mt>(logFilePath.string(), true);
        auto loggerPtr = std::make_shared<spdlog::logger>("log", std::move(fileLoggerPtr));
        spdlog::set_default_logger(std::move(loggerPtr));
        spdlog::set_level(spdlog::level::info);
        spdlog::flush_on(spdlog::level::info);
    }

    struct PendingSnapshot {
        double wallTimestamp = 0.0;
        std::vector<ChronicleBridge::NpcPosition> npcs;
        bool ready = false;
    };

    std::mutex g_snapshotMutex;
    std::condition_variable g_snapshotReady;
    PendingSnapshot g_latestSnapshot;

    // Runs forever on its own thread: every ~1s, hop onto the main thread
    // just long enough to enumerate actors (main-thread-only API, but
    // research/22-verified as microseconds of work), then hand the result
    // to the sender thread and go back to sleeping. Never itself touches
    // the network.
    void TimerThreadLoop() {
        while (true) {
            std::this_thread::sleep_for(std::chrono::seconds(1));

            SKSE::GetTaskInterface()->AddTask([] {
                auto npcs = ChronicleBridge::SampleWhiterunExteriorPositions();
                const double wallTs =
                    std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();

                std::lock_guard lock(g_snapshotMutex);
                g_latestSnapshot = PendingSnapshot{.wallTimestamp = wallTs, .npcs = std::move(npcs), .ready = true};
                g_snapshotReady.notify_one();
            });
        }
    }

    // Runs forever on its own thread: blocks until the timer thread hands it
    // a fresh snapshot, then does the (potentially slow) outbound POST --
    // entirely off the main thread, so a slow/unreachable listener never
    // costs a single dropped frame.
    void SenderThreadLoop(ChronicleBridge::OutboundConfig config) {
        while (true) {
            PendingSnapshot snapshot;
            {
                std::unique_lock lock(g_snapshotMutex);
                g_snapshotReady.wait(lock, [] { return g_latestSnapshot.ready; });
                snapshot = std::move(g_latestSnapshot);
                g_latestSnapshot = PendingSnapshot{};
            }
            if (!snapshot.npcs.empty()) {
                ChronicleBridge::PostPositionSnapshot(config, snapshot.wallTimestamp, snapshot.npcs);
            }
        }
    }

    // Death events are rare/discrete (design doc §3's instruction: not a
    // 1Hz stream, so the full periodic-snapshot machinery above is
    // overkill) -- a small thread-safe queue plus one dedicated sender
    // thread is the smallest correct thing that still keeps the POST off
    // the main thread. DeathEventHandler::ProcessEvent (main thread) pushes
    // into g_pendingEvents; this loop blocks on the condvar and drains it
    // one event at a time.
    std::mutex g_eventQueueMutex;
    std::condition_variable g_eventQueueReady;
    std::deque<ChronicleBridge::PendingGameEvent> g_pendingEvents;

    void EventSenderThreadLoop(ChronicleBridge::OutboundConfig config) {
        while (true) {
            ChronicleBridge::PendingGameEvent event;
            {
                std::unique_lock lock(g_eventQueueMutex);
                g_eventQueueReady.wait(lock, [] { return !g_pendingEvents.empty(); });
                event = std::move(g_pendingEvents.front());
                g_pendingEvents.pop_front();
            }
            ChronicleBridge::PostGameEvent(config, event);
        }
    }

    // Invoked synchronously on the main thread from DeathEventHandler::
    // ProcessEvent -- must stay fast (just a lock + push), never do network
    // I/O itself (EventSenderThreadLoop's job).
    void EnqueueDeathEvent(ChronicleBridge::PendingGameEvent event) {
        {
            std::lock_guard lock(g_eventQueueMutex);
            g_pendingEvents.push_back(std::move(event));
        }
        g_eventQueueReady.notify_one();
    }

    // Fifth slice (BarterMenuSink.h, docs/research/26-vendor-price-markup-
    // hook.md's detection half): barter-menu opens against a named-cast
    // vendor are rare/discrete, same shape as death events -- a small
    // thread-safe queue plus one dedicated sender thread keeps the log line
    // (and this slice's optional read-only markup GET) off the main thread,
    // exactly like EnqueueDeathEvent/EventSenderThreadLoop above.
    std::mutex g_barterQueueMutex;
    std::condition_variable g_barterQueueReady;
    std::deque<ChronicleBridge::PendingBarterOpen> g_pendingBarterOpens;

    // No longer takes an OutboundConfig -- since VendorMarkupCache.h became
    // the one caller of FetchVendorMarkupPairs, this loop no longer does
    // any network I/O of its own (it only reads VendorMarkupCache's
    // in-process map), so it has nothing left to need a host/port/secret
    // for.
    void BarterMenuSenderThreadLoop() {
        while (true) {
            ChronicleBridge::PendingBarterOpen open;
            {
                std::unique_lock lock(g_barterQueueMutex);
                g_barterQueueReady.wait(lock, [] { return !g_pendingBarterOpens.empty(); });
                open = std::move(g_pendingBarterOpens.front());
                g_pendingBarterOpens.pop_front();
            }

            // This log line now reads VendorMarkupCache instead of calling
            // FetchVendorMarkupPairs a second time -- VendorMarkupCache.h's
            // own header comment explains why: listener.py's GET
            // /whiterun/vendor-markup is a DELTA feed (a pair is only
            // returned once until it changes again or its awaiting-ack
            // entry expires), so a second independent poller here would
            // race VendorMarkupCachePollerThreadLoop for the same deltas
            // and starve whichever one lost. Reading the shared cache
            // instead reports the exact multiplier PostCreate would apply
            // (or "no entry"), never a stale/racy second read.
            auto multiplier = ChronicleBridge::GetPlayerMarkupMultiplier(open.npcId);

            if (multiplier) {
                SKSE::log::info(
                    "ChronicleBridge barter: named-cast vendor '{}' opened BarterMenu -- {:.2f}x player-directed "
                    "markup is cached for this vendor (VendorPriceHook.cpp applies this at PostCreate)",
                    open.npcId, *multiplier);
            } else {
                SKSE::log::info(
                    "ChronicleBridge barter: named-cast vendor '{}' opened BarterMenu (no player-directed "
                    "vendor-markup entry cached for this vendor)",
                    open.npcId);
            }
        }
    }

    // Invoked synchronously on the main thread from BarterMenuHandler::
    // ProcessEvent -- must stay fast (just a lock + push), never do network
    // I/O itself (BarterMenuSenderThreadLoop's job), same discipline as
    // EnqueueDeathEvent above.
    void EnqueueBarterOpen(ChronicleBridge::PendingBarterOpen open) {
        {
            std::lock_guard lock(g_barterQueueMutex);
            g_pendingBarterOpens.push_back(std::move(open));
        }
        g_barterQueueReady.notify_one();
    }

    void OnSkseMessage(SKSE::MessagingInterface::Message* message) {
        // research/22's documented registration lifecycle: registering the
        // event sink before kDataLoaded risks null singletons (master files
        // not yet loaded). Design doc §2. BarterMenuSink's RE::UI-based
        // registration follows the identical lifecycle rule -- see
        // BarterMenuSink.h's own header comment.
        if (message->type == SKSE::MessagingInterface::kDataLoaded) {
            ChronicleBridge::RegisterDeathEventSink(EnqueueDeathEvent);
            ChronicleBridge::RegisterBarterMenuSink(EnqueueBarterOpen);
            // Sixth slice (VendorPriceHook.h): the RE::VTABLE_BarterMenu[0]
            // PostCreate vtable-slot swap is a process-global vtable
            // pointer write. Installed here, at kDataLoaded, alongside the
            // other event-sink registrations, rather than earlier in
            // SKSEPluginLoad -- no BarterMenu instance can possibly be
            // constructed before a save is loaded, so kDataLoaded is
            // already early enough, and this keeps every RE:: singleton
            // this plugin touches subject to the same one registration
            // lifecycle rule (research/22's own documented rule, restated
            // in BarterMenuSink.h's header comment) instead of carving out
            // an earlier, separately-reasoned-about exception for this one
            // hook.
            ChronicleBridge::InstallVendorPriceHook();
        } else if (message->type == SKSE::MessagingInterface::kPreLoadGame) {
            // Eighth slice (docs/design/chronicle-bridge-sync-handshake-out.md):
            // the save/reload sync handshake. Cancels any in-flight DEGRADED
            // backoff retry so it can't land mid-new-load (spec §4.2).
            ChronicleBridge::SyncHandshake::HandlePreLoadGame();
        } else if (message->type == SKSE::MessagingInterface::kPostLoadGame) {
            // The sync-wiring plan's design decision 3 (corrects ADR-0005's
            // "kPostLoadGame(success=true)" text -- the real
            // SKSE::MessagingInterface::Message struct has no named success
            // field): skse64's own engine source (Hooks_SaveLoad.cpp) still
            // passes the load's bool result as `data` with `dataLen == 1`.
            // Do NOT fire HELLO on a failed load -- that would HELLO a
            // timeline against a world that never actually loaded, exactly
            // the wrong-branch event the handshake exists to prevent.
            //
            // `data` is NOT a pointer to a bool -- see
            // SyncHandshakeCore::DecodePostLoadSuccessFlag's own comment.
            // An earlier version of this line dereferenced `data` directly
            // and crashed on every real successful load (confirmed live,
            // 2026-09-03). Decoding is pulled into that pure, unit-tested
            // function rather than repeated inline here.
            if (ChronicleBridge::DecodePostLoadSuccessFlag(message->data, message->dataLen)) {
                ChronicleBridge::SyncHandshake::HandlePostLoadGame();
            } else {
                SKSE::log::warn(
                    "ChronicleBridge: kPostLoadGame reported a failed load (or carried no success flag) -- sync "
                    "HELLO will NOT fire for this load");
            }
        } else if (message->type == SKSE::MessagingInterface::kSaveGame) {
            // Transition-and-stash ONLY -- decision 2: kSaveGame fires
            // before the actual save begins (no open co-save stream yet),
            // so WriteRecord cannot be called here. See SyncHandshake.cpp's
            // header comment for the full split; the real write happens in
            // the SetSaveCallback registrant, wired up below in
            // SKSEPluginLoad via RegisterSerializationCallbacks.
            ChronicleBridge::SyncHandshake::HandleSaveGameMessage();
        } else if (message->type == SKSE::MessagingInterface::kNewGame) {
            ChronicleBridge::SyncHandshake::HandleNewGame();
        }
        // kDeleteGame is deliberately NOT forwarded here --
        // SyncHandshakeCore.h's own header comment explains why: deleting a
        // save file on disk has no bearing on the CURRENTLY LOADED
        // session's sync state. Pure SKSE plumbing, not a sync-handshake
        // transition.
    }

}  // namespace

SKSEPluginLoad(const SKSE::LoadInterface* skse) {
    SKSE::Init(skse);
    SetupLog();

    SKSE::log::info(
        "ChronicleBridge loaded -- spatial streamer + death-event + hydration-poll + avoidance-poll + "
        "barter-menu-detection + vendor-price-write + diegetic-evidence-poll slices (see "
        "docs/design/chronicle-bridge-spatial-streamer.md, "
        "docs/design/chronicle-bridge-death-extraction.md, docs/design/chronicle-bridge-hydration-out.md, "
        "docs/design/chronicle-bridge-avoidance-mutagen-out.md, "
        "docs/design/chronicle-bridge-vendor-markup-out.md, "
        "docs/research/28-vendor-price-hook-address-library-spike.md, "
        "docs/design/chronicle-bridge-diegetic-evidence-out.md, "
        "docs/research/31-diegetic-evidence-object-placement-spike.md)");

    // Data/SKSE/Plugins/ChronicleBridge.ini overrides host/port/sharedSecret
    // when present (Config.cpp); a fresh install with no ini yet keeps
    // OutboundConfig's 127.0.0.1:8765 defaults, which only work if Chronicle
    // runs on the same machine as the game. sharedSecret must match whatever
    // the listener was started with (--shared-secret, adapters/skyrim/
    // listener/listener.py) or every POST gets rejected with 401.
    ChronicleBridge::BridgeConfig bridgeConfig = ChronicleBridge::LoadConfigFromIni();
    ChronicleBridge::OutboundConfig config = bridgeConfig.outbound;

    // Applied here, not in SetupLog: the logger has to exist before the ini
    // can be read (the read itself logs), so every banner line above stays
    // at the hardcoded info level and only the steady-state diagnostics
    // below obey [General] LogLevel. flush_on(trace) so an unattended
    // harness tailing ChronicleBridge.log sees lines as they happen rather
    // than whenever spdlog's buffer happens to drain -- the whole point of
    // making these levels selectable.
    spdlog::set_level(bridgeConfig.logLevel);
    spdlog::flush_on(spdlog::level::trace);

    std::thread(TimerThreadLoop).detach();
    std::thread(SenderThreadLoop, config).detach();
    std::thread(EventSenderThreadLoop, config).detach();
    // Fifth slice (BarterMenuSink.h): drains barter-menu-open detections and
    // logs the cached vendor-markup multiplier (if any) off the main
    // thread. No config needed -- see BarterMenuSenderThreadLoop's own
    // comment for why.
    std::thread(BarterMenuSenderThreadLoop).detach();
    // Third slice (docs/design/chronicle-bridge-hydration-out.md): polls
    // the listener for pending relationship-rank pushes and applies them to
    // live game objects. Same config (host/port/sharedSecret) as the other
    // two loops -- no second config path. See HydrationPoller.h for why
    // this write path is unverified beyond "it compiles."
    std::thread(ChronicleBridge::HydrationPollerThreadLoop, config).detach();
    // Fourth slice (docs/design/chronicle-bridge-avoidance-mutagen-out.md):
    // polls the listener for changed avoidance pairs and applies them via
    // per-pair TESGlobal writes + EvaluatePackage. Same config as every
    // other loop above. See AvoidancePoller.h for the SetLinkedRef finding
    // that shaped this slice's write path.
    std::thread(ChronicleBridge::AvoidancePollerThreadLoop, config).detach();
    // Sixth slice (VendorMarkupCache.h): polls the listener for
    // player-directed vendor-markup pairs and keeps VendorPriceHook.cpp's
    // in-process multiplier cache current. Same config as every other loop
    // above.
    std::thread(ChronicleBridge::VendorMarkupCachePollerThreadLoop, config).detach();
    // Seventh slice (docs/design/chronicle-bridge-diegetic-evidence-out.md):
    // polls the listener for newly-revealable (holder, belief, claim)
    // evidence entries and spawns a placeholder evidence object at the
    // believer's own live position via PlaceObjectAtMe. Same config as
    // every other loop above. See EvidencePoller.h for the "compiles only,
    // never exercised against a live save" caveat this write path shares
    // with every other ChronicleBridge write.
    std::thread(ChronicleBridge::EvidencePollerThreadLoop, config).detach();
    // Eighth slice (docs/design/chronicle-bridge-sync-handshake-out.md): the
    // dedicated sync-sender thread -- every POST-response-driven sync
    // transition (HELLO/mutation sends, the resulting responses, the
    // DEGRADED backoff-retry wait, and spill-file I/O) runs here, never on
    // the main thread. Same config as every other loop above.
    std::thread(ChronicleBridge::SyncHandshake::SenderThreadLoop, config).detach();

    // SerializationInterface registration (SetUniqueID/SetSaveCallback/
    // SetLoadCallback/SetRevertCallback) -- independent of the messaging
    // bus's kDataLoaded lifecycle rule the RE:: event sinks above follow,
    // so this is registered here rather than deferred to OnSkseMessage.
    ChronicleBridge::SyncHandshake::RegisterSerializationCallbacks();

    // Death-event sink registration is deferred to kDataLoaded (see
    // OnSkseMessage's own comment) -- RegisterListener must be called here,
    // before SKSE::Init returns control, per SKSE's own messaging contract.
    if (auto* messaging = SKSE::GetMessagingInterface()) {
        messaging->RegisterListener(OnSkseMessage);
    } else {
        SKSE::log::error("ChronicleBridge: SKSE::GetMessagingInterface() returned null -- death sink will NOT be registered");
    }

    return true;
}
