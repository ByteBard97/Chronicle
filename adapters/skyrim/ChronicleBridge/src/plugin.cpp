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
#include <mutex>
#include <thread>

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

}  // namespace

SKSEPluginLoad(const SKSE::LoadInterface* skse) {
    SKSE::Init(skse);
    SetupLog();

    SKSE::log::info(
        "ChronicleBridge loaded -- spatial streamer slice only (see docs/design/chronicle-bridge-spatial-streamer.md)");

    // TODO once the Chronicle host's actual LAN IP is known: read host, port,
    // and sharedSecret from an INI file (SKSE plugins conventionally ship a
    // Data/SKSE/Plugins/ChronicleBridge.ini) rather than hardcoding
    // OutboundConfig's defaults -- the default 127.0.0.1 only works if
    // Chronicle runs on the same machine, which won't be true once Skyrim
    // runs on its own Windows box, and sharedSecret must match whatever the
    // listener was started with (--shared-secret, adapters/skyrim/listener/
    // listener.py) or every POST gets rejected with 401.
    ChronicleBridge::OutboundConfig config{};

    std::thread(TimerThreadLoop).detach();
    std::thread(SenderThreadLoop, config).detach();

    return true;
}
