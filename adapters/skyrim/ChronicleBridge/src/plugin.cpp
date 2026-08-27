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

#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <deque>
#include <mutex>
#include <thread>

#include "AvoidancePoller.h"
#include "BarterMenuSink.h"
#include "Config.h"
#include "DeathEventSink.h"
#include "HydrationPoller.h"
#include "OutboundClient.h"
#include "SpatialStreamer.h"

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

    void BarterMenuSenderThreadLoop(ChronicleBridge::OutboundConfig config) {
        while (true) {
            ChronicleBridge::PendingBarterOpen open;
            {
                std::unique_lock lock(g_barterQueueMutex);
                g_barterQueueReady.wait(lock, [] { return !g_pendingBarterOpens.empty(); });
                open = std::move(g_pendingBarterOpens.front());
                g_pendingBarterOpens.pop_front();
            }

            // This slice's whole job is proving detection works (BarterMenuSink.h's
            // header comment) -- no price write, no ack POST. The
            // markup-multiplier GET below is purely informational, using the
            // same GET-only OutboundClient path FetchHydrationPairs/
            // FetchAvoidancePairs already establish. A fetch failure
            // (including the common "listener not started with --live-run"
            // 503) is already logged inside FetchVendorMarkupPairs itself --
            // nothing further to do here beyond noting no entry was found.
            //
            // IMPORTANT: chronicle/vendor_markup.py's (holder_id, target_id)
            // pairs are Grudge state -- both NPC ids, never a player id (no
            // player/dragonborn concept exists anywhere in Chronicle's
            // fixtures or kNamedCast). Matching this vendor as holder_id
            // only tells us this NPC holds a grudge-driven markup entry
            // toward some OTHER NPC -- it says nothing about whether that
            // multiplier is meant to apply to the PLAYER's barter
            // transaction happening right now (an open question this slice
            // deliberately does not resolve, per design doc §1). The log
            // line below is worded to reflect that: it reports the entry,
            // not a claim that it "would apply here."
            auto pairs = ChronicleBridge::FetchVendorMarkupPairs(config);
            auto match = std::find_if(pairs.begin(), pairs.end(), [&](const auto& pair) {
                return pair.holderId == open.npcId;
            });

            if (match != pairs.end()) {
                SKSE::log::info(
                    "ChronicleBridge barter: named-cast vendor '{}' opened BarterMenu -- has a {:.2f}x "
                    "grudge-markup entry toward '{}' (NPC-directed Grudge state; whether/how this should apply to "
                    "a player transaction is unresolved -- read-only, nothing written, see BarterMenuSink.h)",
                    open.npcId, match->markupMultiplier, match->targetId);
            } else {
                SKSE::log::info(
                    "ChronicleBridge barter: named-cast vendor '{}' opened BarterMenu (no vendor-markup entry found "
                    "for this vendor)",
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
        }
    }

}  // namespace

SKSEPluginLoad(const SKSE::LoadInterface* skse) {
    SKSE::Init(skse);
    SetupLog();

    SKSE::log::info(
        "ChronicleBridge loaded -- spatial streamer + death-event + hydration-poll + avoidance-poll + "
        "barter-menu-detection slices (see docs/design/chronicle-bridge-spatial-streamer.md, "
        "docs/design/chronicle-bridge-death-extraction.md, docs/design/chronicle-bridge-hydration-out.md, "
        "docs/design/chronicle-bridge-avoidance-mutagen-out.md, "
        "docs/design/chronicle-bridge-vendor-markup-out.md)");

    // Data/SKSE/Plugins/ChronicleBridge.ini overrides host/port/sharedSecret
    // when present (Config.cpp); a fresh install with no ini yet keeps
    // OutboundConfig's 127.0.0.1:8765 defaults, which only work if Chronicle
    // runs on the same machine as the game. sharedSecret must match whatever
    // the listener was started with (--shared-secret, adapters/skyrim/
    // listener/listener.py) or every POST gets rejected with 401.
    ChronicleBridge::OutboundConfig config = ChronicleBridge::LoadConfigFromIni();

    std::thread(TimerThreadLoop).detach();
    std::thread(SenderThreadLoop, config).detach();
    std::thread(EventSenderThreadLoop, config).detach();
    // Fifth slice (BarterMenuSink.h): drains barter-menu-open detections and
    // does the optional read-only markup-fetch-and-log off the main thread.
    // Same config as every other loop above.
    std::thread(BarterMenuSenderThreadLoop, config).detach();
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
