#include "SyncHandshake.h"

#include <algorithm>
#include <array>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <deque>
#include <filesystem>
#include <format>
#include <fstream>
#include <mutex>
#include <optional>
#include <random>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

// ---------------------------------------------------------------------
// THE ONE CORRECTNESS INVARIANT THIS FILE EXISTS TO PROTECT (verified
// against skse64's real engine source, Hooks_SaveLoad.cpp -- see the
// sync-wiring plan's design decision 2): kSaveGame fires from
// OnSkseMessage BEFORE the actual save begins -- there is no open co-save
// stream at that point. WriteRecord CANNOT be called from
// HandleSaveGameMessage (the kSaveGame messaging case below); it would
// silently return false and the manifest would never be written, with no
// error. The ONLY place this file calls WriteRecord is the anonymous
// namespace's OnGameSave function, registered via
// SerializationInterface::SetSaveCallback -- the one context with an
// actually-open co-save record target. HandleSaveGameMessage runs the pure
// OnSaveGame transition and STASHES the resulting manifest into
// g_pendingSaveManifest (guarded by the SAME mutex as g_syncState, so the
// stash-then-consume pair shares one atomic snapshot -- spec D5: "the same
// atomic read, sampled once," never two separate reads that can skew under
// a concurrent mutation ACK landing in between). Do not "fix" this by
// moving WriteRecord into HandleSaveGameMessage -- that is the exact bug
// this split exists to prevent.
// ---------------------------------------------------------------------

namespace ChronicleBridge::SyncHandshake {

    namespace {

        // 'TMNL' -- the record type inside the 'CHRN'-scoped co-save
        // section (design doc §1: WriteRecord('TMNL', version=1, ...)).
        // Written as a raw multichar literal, matching the design doc's own
        // plugin.cpp snippet and this codebase's other FourCC constants --
        // deliberately NOT hand-computed to hex here, since eyeballing that
        // arithmetic is exactly what produced two real byte-order/value
        // bugs elsewhere in this spec (see SyncHandshakeCore.h's magic
        // sentinel comment).
        constexpr std::uint32_t kSyncManifestRecordType = 'TMNL';

        // ---------------------------------------------------------------
        // Shared state. g_syncStateMutex guards BOTH g_syncState AND
        // g_pendingSaveManifest -- see this file's header comment for why
        // the two share one mutex (the kSaveGame-stash / SetSaveCallback-
        // consume handoff needs one atomic snapshot, not two independently-
        // locked reads).
        // ---------------------------------------------------------------
        std::mutex g_syncStateMutex;
        ChronicleBridge::SyncState g_syncState;
        std::optional<ChronicleBridge::Manifest> g_pendingSaveManifest;

        // ---------------------------------------------------------------
        // The sync-sender thread's own work queue. Carries the raw
        // SyncSideEffect variant -- only ever pushed here for the six
        // effect kinds decision 2's dispatch table routes to this thread
        // (SendHello, SendMutation, SpillMutationToFile, RotateSpillFile,
        // ScheduleHelloRetryBackoff, CancelScheduledHelloRetry); every
        // other effect kind is handled locally by DispatchEffects and never
        // reaches this queue.
        // ---------------------------------------------------------------
        std::mutex g_senderQueueMutex;
        std::condition_variable g_senderQueueReady;
        std::deque<ChronicleBridge::SyncSideEffect> g_senderQueue;

        void EnqueueSenderWork(ChronicleBridge::SyncSideEffect effect) {
            {
                std::lock_guard lock(g_senderQueueMutex);
                g_senderQueue.push_back(std::move(effect));
            }
            g_senderQueueReady.notify_one();
        }

        // Dispatches one transition's worth of effects to their correct
        // destination (the sync-wiring plan's design decision 2's
        // per-effect table), never under g_syncStateMutex (the caller has
        // already unlocked by the time this runs -- see every Handle*
        // function below). WriteCoSaveRecord is deliberately NOT handled
        // here at all -- see this file's header comment; it should be
        // structurally unreachable through this function.
        void DispatchEffects(const ChronicleBridge::SyncSideEffects& effects) {
            for (const auto& effect : effects) {
                std::visit(
                    [&](auto&& e) {
                        using T = std::decay_t<decltype(e)>;
                        if constexpr (std::is_same_v<T, ChronicleBridge::SendHello> ||
                                      std::is_same_v<T, ChronicleBridge::SendMutation> ||
                                      std::is_same_v<T, ChronicleBridge::SpillMutationToFile> ||
                                      std::is_same_v<T, ChronicleBridge::RotateSpillFile> ||
                                      std::is_same_v<T, ChronicleBridge::ScheduleHelloRetryBackoff> ||
                                      std::is_same_v<T, ChronicleBridge::CancelScheduledHelloRetry>) {
                            // Network I/O and file I/O both go to the
                            // sync-sender thread -- never dispatched inline,
                            // regardless of which thread this function is
                            // called from (decision 2: OnMutationReady can
                            // be called from a main-thread sink, and
                            // OnGameRevert runs under SKSE's global
                            // g_loadGameLock -- inline file I/O in either
                            // context is a real never-block violation).
                            EnqueueSenderWork(e);
                        } else if constexpr (std::is_same_v<T, ChronicleBridge::LogWarning>) {
                            SKSE::log::warn("ChronicleBridge sync: {}", e.message);
                        } else if constexpr (std::is_same_v<T, ChronicleBridge::LogInfo>) {
                            SKSE::log::info("ChronicleBridge sync: {}", e.message);
                        } else if constexpr (std::is_same_v<T, ChronicleBridge::NotifyPlayerNonModal>) {
                            // §4.6: notification-only in v1, no blocking
                            // dialog, no in-game UI hook exists yet for
                            // this -- logged so it's at least visible in
                            // ChronicleBridge.log until a real rendering
                            // mechanism is designed (an explicitly deferred
                            // UX decision, per the spec).
                            SKSE::log::info("ChronicleBridge sync (player notice): {}", e.message);
                        } else if constexpr (std::is_same_v<T, ChronicleBridge::BufferMutationLocally>) {
                            // Cheap, non-blocking, informational -- the
                            // plan's per-effect table doesn't name this one
                            // explicitly, but it's the same "dispatch
                            // locally, wherever the transition ran" shape
                            // as Log*/NotifyPlayerNonModal (the actual
                            // ring-buffer write already happened inside the
                            // pure transition's returned state; this effect
                            // is purely a "note: this got buffered" signal).
                            SKSE::log::info("ChronicleBridge sync: mutation seq={} buffered locally (outbound ring)",
                                             e.seq);
                        } else if constexpr (std::is_same_v<T, ChronicleBridge::WriteCoSaveRecord>) {
                            // Structurally unreachable: WriteCoSaveRecord is
                            // only ever produced by OnSaveGame, and every
                            // call site of OnSaveGame in this file
                            // (HandleSaveGameMessage) intercepts that effect
                            // BEFORE calling DispatchEffects -- see this
                            // file's header comment. Logged loudly, not
                            // silently ignored, if this invariant is ever
                            // violated by a future edit.
                            SKSE::log::error(
                                "ChronicleBridge sync: WriteCoSaveRecord effect reached the generic dispatcher -- "
                                "this should be unreachable; the manifest was NOT written this call");
                        }
                    },
                    effect);
            }
        }

        // UUIDv4, seeded from std::random_device -- explicitly not
        // deterministic (decision 7: "don't let a test convenience -- a
        // fixed seed -- leak into shipped code").
        std::array<std::uint8_t, 16> GenerateUuidV4() {
            std::random_device rd;
            std::mt19937_64 rng(rd());
            std::uniform_int_distribution<std::uint32_t> byteDist(0, 255);

            std::array<std::uint8_t, 16> bytes{};
            for (auto& b : bytes) {
                b = static_cast<std::uint8_t>(byteDist(rng));
            }
            bytes[6] = static_cast<std::uint8_t>((bytes[6] & 0x0Fu) | 0x40u);  // version 4
            bytes[8] = static_cast<std::uint8_t>((bytes[8] & 0x3Fu) | 0x80u);  // variant 10
            return bytes;
        }

        // Where the sync-sender thread spills overflowed/buffered mutations
        // and rotates them away on Revert (spec §4.5's "spilling to a local
        // file if the ring fills," §4.5/§5's "Revert must also
        // delete/rotate the spill file"). Alongside ChronicleBridge.log,
        // not a second config-driven path -- there's nothing here for an
        // ini to usefully override.
        //
        // NAMED GAP, not fixed here: nothing in this file ever reads this
        // file back and replays it (SyncHandshakeCore.h's own
        // SpillMutationToFile comment: "file replay is the glue layer's own
        // job -- this pure core never reads its own spill file back").
        // Unreachable today -- SubmitMutation has no current caller (see
        // this file's own header comment / SyncHandshake.h), so nothing
        // ever actually spills in practice -- but a real future mutation
        // producer will need this replay path built before spilling can be
        // trusted as anything more than a ring-overflow safety valve.
        std::filesystem::path SpillFilePath() {
            auto logsFolder = SKSE::log::log_directory();
            if (!logsFolder) {
                return {};
            }
            return *logsFolder / "ChronicleBridge.sync-spill.jsonl";
        }

        // Runs ONLY on the sync-sender thread (called from SenderThreadLoop
        // below) -- file I/O, never the main thread (D2's fix).
        void HandleSpillMutationToFile(const ChronicleBridge::SpillMutationToFile& spill) {
            auto path = SpillFilePath();
            if (path.empty()) {
                SKSE::log::warn("ChronicleBridge sync: cannot spill mutation seq={} to disk -- no log directory available",
                                 spill.seq);
                return;
            }
            std::ofstream out(path, std::ios::app);
            if (!out) {
                SKSE::log::warn("ChronicleBridge sync: failed to open spill file {} for mutation seq={}", path.string(),
                                 spill.seq);
                return;
            }
            // One JSON object per line (JSONL) -- eventPayload embedded
            // verbatim as already-serialized JSON text, matching
            // OutboundClient.cpp's BuildSyncMutationRequestJson convention
            // for the same field (see that function's own comment).
            out << std::format(R"({{"seq":{},"gamets":{},"wall_ts":{},"event":{}}})", spill.seq, spill.gamets,
                                spill.wallTs, spill.eventPayload)
                << '\n';
        }

        // Runs ONLY on the sync-sender thread. Rotating a nonexistent file
        // is expected to be a cheap no-op (SyncHandshakeCore.h's
        // RotateSpillFile comment) -- the error_code overload is used
        // specifically so a missing file never throws or logs.
        void HandleRotateSpillFile() {
            auto path = SpillFilePath();
            if (path.empty()) return;
            std::error_code ec;
            std::filesystem::remove(path, ec);
        }

        // Runs ONLY on the sync-sender thread: performs the actual blocking
        // HELLO POST, then applies decision 6's three-way result mapping.
        void HandleSendHello(const ChronicleBridge::OutboundConfig& config, const ChronicleBridge::SendHello& hello) {
            auto result = ChronicleBridge::PostSyncHello(config, hello);

            bool skipRetryBackoff = false;
            ChronicleBridge::SyncSideEffects effects;
            {
                std::lock_guard lock(g_syncStateMutex);
                ChronicleBridge::SyncTransitionResult transition;
                switch (result.outcome) {
                    case ChronicleBridge::SyncHelloTransportOutcome::kOk:
                        transition = ChronicleBridge::OnHelloResponse(g_syncState, *result.response);
                        break;
                    case ChronicleBridge::SyncHelloTransportOutcome::kTransportFailure:
                    case ChronicleBridge::SyncHelloTransportOutcome::kUnparseableBody:
                        transition = ChronicleBridge::OnHelloTimeout(g_syncState, hello.helloSeq);
                        break;
                    case ChronicleBridge::SyncHelloTransportOutcome::kHttpErrorStatus:
                        transition = ChronicleBridge::OnHelloTimeout(g_syncState, hello.helloSeq);
                        // Decision 6: a received HTTP error status is a
                        // THIRD case, distinct from a transport
                        // failure/timeout -- 401/403 (misconfigured shared
                        // secret) must not retry forever silently, unlike a
                        // generic transient failure.
                        if (result.httpStatus == 401 || result.httpStatus == 403) {
                            skipRetryBackoff = true;
                        }
                        break;
                }
                g_syncState = transition.state;
                effects = std::move(transition.effects);
            }

            if (result.outcome == ChronicleBridge::SyncHelloTransportOutcome::kHttpErrorStatus) {
                SKSE::log::warn("ChronicleBridge sync: HELLO returned HTTP status {}{}", result.httpStatus,
                                 skipRetryBackoff
                                     ? " -- NOT scheduling a retry (likely a misconfigured shared secret)"
                                     : " -- proceeding DEGRADED");
            }

            if (skipRetryBackoff) {
                // OnHelloTimeout's own state already set
                // helloRetryScheduled=true regardless of why it fired --
                // dropping ONLY the ScheduleHelloRetryBackoff effect (never
                // actually arming the sender thread's backoff timer) is
                // what keeps 401/403 from retrying. helloRetryScheduled
                // simply sits inert until the next kPreLoadGame/Revert,
                // whose CancelScheduledHelloRetry effect is a harmless no-op
                // on this thread since nothing was actually scheduled here.
                effects.erase(std::remove_if(effects.begin(), effects.end(),
                                              [](const ChronicleBridge::SyncSideEffect& e) {
                                                  return std::holds_alternative<ChronicleBridge::ScheduleHelloRetryBackoff>(e);
                                              }),
                              effects.end());
            }

            DispatchEffects(effects);
        }

        // Runs ONLY on the sync-sender thread: performs the actual blocking
        // mutation POST, then maps its raw status to the correct one of
        // OnMutationAccepted/OnMutationRejected/OnMutationSendFailed
        // (SyncHandshakeCore.h's own documented three-way split of a
        // synchronous httplib::Result: 2xx, 409, or "connection refused,
        // timeout, or a 5xx").
        void HandleSendMutation(const ChronicleBridge::OutboundConfig& config, const ChronicleBridge::SendMutation& mutation) {
            const int status = ChronicleBridge::PostSyncMutation(config, mutation);

            ChronicleBridge::SyncSideEffects effects;
            {
                std::lock_guard lock(g_syncStateMutex);
                ChronicleBridge::SyncTransitionResult transition;
                if (status >= 200 && status < 300) {
                    transition = ChronicleBridge::OnMutationAccepted(
                        g_syncState, ChronicleBridge::MutationCommitInfo{mutation.seq, mutation.gamets, mutation.wallTs});
                } else if (status == 409) {
                    transition = ChronicleBridge::OnMutationRejected(g_syncState, mutation.epochId, mutation.seq);
                } else {
                    transition = ChronicleBridge::OnMutationSendFailed(
                        g_syncState,
                        ChronicleBridge::MutationEvent{mutation.seq, mutation.gamets, mutation.wallTs, mutation.eventPayload});
                }
                g_syncState = transition.state;
                effects = std::move(transition.effects);
            }
            DispatchEffects(effects);
        }

        // Runs ONLY on the sync-sender thread, when a previously-scheduled
        // DEGRADED backoff retry's deadline actually elapses with nothing
        // else in the queue (see SenderThreadLoop below).
        void FireHelloBackoff() {
            ChronicleBridge::SyncSideEffects effects;
            {
                std::lock_guard lock(g_syncStateMutex);
                auto result = ChronicleBridge::OnHelloBackoffFire(g_syncState);
                g_syncState = result.state;
                effects = std::move(result.effects);
            }
            DispatchEffects(effects);
        }

        // ---------------------------------------------------------------
        // SerializationInterface callback registrants -- SKSE-facing,
        // matching SKSE::SerializationInterface::EventCallback's exact
        // signature (void(SerializationInterface*)). Kept file-local
        // (anonymous namespace) rather than exposed via SyncHandshake.h:
        // nothing outside this file ever needs to call these directly: SKSE
        // itself is the only caller, via the function pointers registered
        // in RegisterSerializationCallbacks below.
        // ---------------------------------------------------------------

        // SetLoadCallback registrant -- fires on the main thread during
        // SKSE's load sequence, NOT a messaging event (spec §1). This is
        // where ReadRecordData actually runs.
        void OnGameLoad(SKSE::SerializationInterface* intfc) {
            ChronicleBridge::LoadRecordInfo record;

            std::uint32_t type = 0, version = 0, length = 0;
            while (intfc->GetNextRecordInfo(type, version, length)) {
                if (type == kSyncManifestRecordType) {
                    record.recordFound = true;
                    record.declaredLength = length;
                    record.version = version;
                    if (length == ChronicleBridge::kManifestWireSize) {
                        record.actualReadLength =
                            intfc->ReadRecordData(record.rawBytes.data(), static_cast<std::uint32_t>(record.rawBytes.size()));
                    } else {
                        // Drain anyway -- an unexpected length must not
                        // desync GetNextRecordInfo's iteration for whatever
                        // record (if any) follows under this plugin's own
                        // 'CHRN' scope.
                        std::vector<std::uint8_t> discard(length);
                        record.actualReadLength = intfc->ReadRecordData(discard.data(), length);
                    }
                    break;  // 'TMNL' is the only record type this plugin ever writes under 'CHRN'.
                }
                // Unknown record type under our own uid -- defensive; drain
                // and keep scanning. Should never actually trigger today.
                std::vector<std::uint8_t> discard(length);
                intfc->ReadRecordData(discard.data(), length);
            }

            std::lock_guard lock(g_syncStateMutex);
            auto result = ChronicleBridge::OnLoadCallback(g_syncState, record);
            g_syncState = result.state;
            // OnLoadCallback never emits effects (verified directly against
            // SyncHandshakeCore.cpp) -- nothing to dispatch.
        }

        // SetSaveCallback registrant -- THE ONLY PLACE THIS FEATURE CALLS
        // WriteRecord. See this file's header comment for the full
        // invariant this protects. Locks g_syncStateMutex (the SAME mutex
        // HandleSaveGameMessage used to stash g_pendingSaveManifest) across
        // the write itself: WriteRecord is a leaf call into SKSE's
        // in-memory co-save stream, cannot re-enter plugin code, and no
        // other plugin lock is ever acquired under g_syncStateMutex, so
        // this is safe. Nothing but the WriteRecord call itself happens
        // UNDER the lock, per the sync-wiring plan's constraint -- but that
        // constraint is about what runs while the mutex is held, not about
        // discarding the outcome. This feature's live-verification path is
        // separately blocked, so a silently-dropped or silently-failed
        // manifest write here would be undebuggable from anywhere but this
        // log -- both failure branches (no stash at all, and WriteRecord
        // itself returning false) are logged AFTER the lock is released.
        void OnGameSave(SKSE::SerializationInterface* intfc) {
            bool hadStash = false;
            bool wrote = false;
            {
                std::lock_guard lock(g_syncStateMutex);
                if (g_pendingSaveManifest) {
                    hadStash = true;
                    wrote = intfc->WriteRecord(kSyncManifestRecordType, ChronicleBridge::kManifestRecordVersion,
                                                *g_pendingSaveManifest);
                    g_pendingSaveManifest.reset();
                }
            }
            if (!hadStash) {
                // kSaveGame's messaging case never ran before this fired
                // (or already consumed it) -- a human debugging a missing
                // manifest should be able to see this in the log rather
                // than infer it from silence.
                SKSE::log::warn(
                    "ChronicleBridge sync: SetSaveCallback fired with no stashed manifest -- kSaveGame's messaging "
                    "case may not have run first; the sync manifest will NOT be written this save");
            } else if (!wrote) {
                SKSE::log::warn("ChronicleBridge sync: WriteRecord('TMNL') returned false -- the sync manifest was "
                                 "NOT written this save");
            }
        }

        // SetRevertCallback registrant -- fires between kPreLoadGame and
        // the Load callback (and also on quit-to-main-menu with no
        // subsequent load, and never on the very first load after process
        // start -- D3). Also runs inside LoadGame_HookTarget under SKSE's
        // global g_loadGameLock (decision 2) -- RotateSpillFile must be
        // dispatched to the sync-sender thread, never done inline here.
        void OnGameRevert(SKSE::SerializationInterface*) {
            ChronicleBridge::SyncSideEffects effects;
            {
                std::lock_guard lock(g_syncStateMutex);
                auto result = ChronicleBridge::OnGameRevert(g_syncState);
                g_syncState = result.state;
                effects = std::move(result.effects);
                // Nothing left mid-save to actually persist across a
                // revert -- defensive clear, same lock as the stash/consume
                // pair above.
                g_pendingSaveManifest.reset();
            }
            DispatchEffects(effects);
        }

    }  // namespace

    void RegisterSerializationCallbacks() {
        if (auto* serialization = SKSE::GetSerializationInterface()) {
            serialization->SetUniqueID('CHRN');  // 0x4348524E -- design doc §7.1/§8a.
            serialization->SetSaveCallback(OnGameSave);
            serialization->SetLoadCallback(OnGameLoad);
            serialization->SetRevertCallback(OnGameRevert);
        } else {
            SKSE::log::error(
                "ChronicleBridge: SKSE::GetSerializationInterface() returned null -- save/reload sync will NOT function");
        }
    }

    void HandlePreLoadGame() {
        ChronicleBridge::SyncSideEffects effects;
        {
            std::lock_guard lock(g_syncStateMutex);
            auto result = ChronicleBridge::OnPreLoadGame(g_syncState);
            g_syncState = result.state;
            effects = std::move(result.effects);
        }
        DispatchEffects(effects);
    }

    void HandlePostLoadGame() {
        ChronicleBridge::SyncSideEffects effects;
        {
            std::lock_guard lock(g_syncStateMutex);
            auto result = ChronicleBridge::OnPostLoadGame(g_syncState);
            g_syncState = result.state;
            effects = std::move(result.effects);
        }
        DispatchEffects(effects);
    }

    void HandleNewGame() {
        const auto uuid = GenerateUuidV4();
        ChronicleBridge::SyncSideEffects effects;
        {
            std::lock_guard lock(g_syncStateMutex);
            auto result = ChronicleBridge::OnNewGame(g_syncState, uuid);
            g_syncState = result.state;
            effects = std::move(result.effects);
        }
        DispatchEffects(effects);
    }

    void HandleSaveGameMessage() {
        std::lock_guard lock(g_syncStateMutex);
        auto result = ChronicleBridge::OnSaveGame(g_syncState);
        g_syncState = result.state;
        // OnSaveGame's only ever effect is WriteCoSaveRecord (verified
        // directly against SyncHandshakeCore.cpp) -- stash it here, under
        // the same lock OnGameSave (SetSaveCallback) will later use to
        // consume it, so the two share one atomic snapshot (D5). NO
        // WriteRecord call here -- see this file's header comment.
        for (const auto& effect : result.effects) {
            if (auto* rec = std::get_if<ChronicleBridge::WriteCoSaveRecord>(&effect)) {
                g_pendingSaveManifest = rec->manifest;
            }
        }
    }

    void SubmitMutation(const MutationEvent& event) {
        ChronicleBridge::SyncSideEffects effects;
        {
            std::lock_guard lock(g_syncStateMutex);
            auto result = ChronicleBridge::OnMutationReady(g_syncState, event);
            g_syncState = result.state;
            effects = std::move(result.effects);
        }
        DispatchEffects(effects);
    }

    void SenderThreadLoop(OutboundConfig config) {
        // The DEGRADED backoff-retry deadline, if one is currently
        // scheduled -- implemented as a condvar wait_until on this thread's
        // OWN queue (not a bare sleep), so a CancelScheduledHelloRetry item
        // landing in the queue wakes this thread immediately instead of
        // waiting out a stale deadline (the sync-wiring plan's own
        // instruction; OnHelloBackoffFire's stale-fire no-op already makes
        // a late wake harmless, so this is a responsiveness polish, not a
        // correctness requirement).
        std::optional<std::chrono::steady_clock::time_point> backoffDeadline;

        // Spec §4.5 names a "backoff retry" without pinning an exact
        // interval -- one of §8b's genuinely open tuning questions
        // (alongside the HELLO timeout itself). Picked here as a judgment
        // call; trivially tunable later, nothing else in this file depends
        // on the exact value.
        constexpr auto kHelloRetryBackoffDelay = std::chrono::seconds(10);

        while (true) {
            std::optional<ChronicleBridge::SyncSideEffect> item;
            {
                std::unique_lock lock(g_senderQueueMutex);
                if (backoffDeadline) {
                    g_senderQueueReady.wait_until(lock, *backoffDeadline, [] { return !g_senderQueue.empty(); });
                } else {
                    g_senderQueueReady.wait(lock, [] { return !g_senderQueue.empty(); });
                }

                if (!g_senderQueue.empty()) {
                    item = std::move(g_senderQueue.front());
                    g_senderQueue.pop_front();
                } else if (backoffDeadline && std::chrono::steady_clock::now() >= *backoffDeadline) {
                    backoffDeadline.reset();
                    lock.unlock();
                    FireHelloBackoff();
                    continue;
                } else {
                    continue;  // spurious wake -- loop again.
                }
            }

            std::visit(
                [&](auto&& e) {
                    using T = std::decay_t<decltype(e)>;
                    if constexpr (std::is_same_v<T, ChronicleBridge::SendHello>) {
                        HandleSendHello(config, e);
                    } else if constexpr (std::is_same_v<T, ChronicleBridge::SendMutation>) {
                        HandleSendMutation(config, e);
                    } else if constexpr (std::is_same_v<T, ChronicleBridge::SpillMutationToFile>) {
                        HandleSpillMutationToFile(e);
                    } else if constexpr (std::is_same_v<T, ChronicleBridge::RotateSpillFile>) {
                        HandleRotateSpillFile();
                    } else if constexpr (std::is_same_v<T, ChronicleBridge::ScheduleHelloRetryBackoff>) {
                        backoffDeadline = std::chrono::steady_clock::now() + kHelloRetryBackoffDelay;
                    } else if constexpr (std::is_same_v<T, ChronicleBridge::CancelScheduledHelloRetry>) {
                        backoffDeadline.reset();
                    } else {
                        // LogWarning/LogInfo/NotifyPlayerNonModal/
                        // BufferMutationLocally/WriteCoSaveRecord are never
                        // enqueued here -- EnqueueSenderWork (DispatchEffects
                        // above) only ever pushes the six kinds handled by
                        // the branches above. Unreachable in practice.
                        SKSE::log::error("ChronicleBridge sync sender: unexpected effect type reached the sender queue");
                    }
                },
                *item);
        }
    }

}  // namespace ChronicleBridge::SyncHandshake
