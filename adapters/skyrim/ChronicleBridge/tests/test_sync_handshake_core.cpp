// Plain C++ test main for SyncHandshakeCore.h/.cpp -- the pure sync-
// handshake state machine (docs/design/chronicle-bridge-sync-handshake-out.md
// §5's hard requirement: this component must be unit-testable without SKSE,
// since the project has no C++ test harness and the live-game path is
// separately blocked, see that doc's §7).
//
// No test framework dependency on purpose -- this whole exercise is about
// proving the state machine is testable with nothing but a stock compiler,
// so pulling in gtest/Catch2 (unavailable in this environment, and not
// something ChronicleBridge's existing vcpkg manifest provides) would
// undercut the point. See this directory's README/compile command at the
// bottom of this file's companion report for how to build and run this.

#include "../src/SyncHandshakeCore.h"
#include "../src/SyncHelloResponseParser.h"

#include <cstdio>
#include <cstring>
#include <string>

using namespace ChronicleBridge;

namespace {

    int g_checks = 0;
    int g_failures = 0;

    void Fail(const char* file, int line, const char* expr) {
        ++g_failures;
        std::fprintf(stderr, "  CHECK FAILED at %s:%d: %s\n", file, line, expr);
    }

#define CHECK(cond)                          \
    do {                                      \
        ++g_checks;                           \
        if (!(cond)) Fail(__FILE__, __LINE__, #cond); \
    } while (0)

#define RUN(fn)                                          \
    do {                                                  \
        std::fprintf(stderr, "-- %s\n", #fn);              \
        fn();                                              \
    } while (0)

    std::string HexEncode(const std::array<std::uint8_t, kManifestWireSize>& bytes) {
        static const char* kHex = "0123456789abcdef";
        std::string out;
        out.reserve(bytes.size() * 2);
        for (std::uint8_t b : bytes) {
            out.push_back(kHex[(b >> 4) & 0xF]);
            out.push_back(kHex[b & 0xF]);
        }
        return out;
    }

    template <typename T>
    int CountEffectsOfType(const SyncSideEffects& effects) {
        int n = 0;
        for (const auto& e : effects) {
            if (std::holds_alternative<T>(e)) ++n;
        }
        return n;
    }

    Manifest MakeManifest(std::uint64_t generation, std::uint64_t parentGeneration, std::uint64_t headSeq, double gamets,
                           std::int64_t wallTsMs, std::uint64_t charNameHash,
                           const std::array<std::uint8_t, 16>& uuid) {
        Manifest m;
        m.generation = generation;
        m.parent_generation = parentGeneration;
        m.head_seq = headSeq;
        m.gamets = gamets;
        m.wall_ts = wallTsMs;
        m.char_name_hash = charNameHash;
        for (int i = 0; i < 16; ++i) m.save_uuid[i] = uuid[i];
        return m;
    }

    LoadRecordInfo MakeValidLoadRecord(const Manifest& m) {
        LoadRecordInfo r;
        r.recordFound = true;
        r.declaredLength = kManifestWireSize;
        r.version = kManifestRecordVersion;
        r.rawBytes = ManifestToBytes(m);
        r.actualReadLength = kManifestWireSize;
        return r;
    }

    // ------------------------------------------------------------------
    // 1. Golden fixture round trip (spec §3) -- must match byte-for-byte
    //    against the SAME field values the Python-side agent is checking.
    // ------------------------------------------------------------------
    void Test_GoldenFixtureRoundTrip() {
        const std::array<std::uint8_t, 16> uuid = {
            0x01, 0x23, 0x45, 0x67, 0x89, 0xab, 0xcd, 0xef,
            0x01, 0x23, 0x45, 0x67, 0x89, 0xab, 0xcd, 0xef,
        };
        const Manifest m = MakeManifest(/*generation=*/0, /*parentGeneration=*/0, /*headSeq=*/42, /*gamets=*/123.5,
                                         /*wallTsMs=*/1735689600123, /*charNameHash=*/0xdeadbeefcafebabeULL, uuid);

        const std::string kExpectedHex =
            "435248430123456789abcdef0123456789abcdef000000000000000000000000000000002a0000"
            "00000000000000000000e05e407b7c291f94010000bebafecaefbeadde";

        const auto encoded = ManifestToBytes(m);
        const std::string gotHex = HexEncode(encoded);
        if (gotHex != kExpectedHex) {
            std::fprintf(stderr, "  golden fixture mismatch:\n    expected: %s\n    got:      %s\n",
                         kExpectedHex.c_str(), gotHex.c_str());
        }
        CHECK(gotHex == kExpectedHex);

        // The packed struct's raw memory image must ALSO equal the explicit
        // LE encoding -- this is the unstated property the future
        // WriteRecord(&manifest, sizeof(manifest)) glue call depends on.
        std::array<std::uint8_t, kManifestWireSize> viaMemcpy{};
        std::memcpy(viaMemcpy.data(), &m, sizeof(m));
        CHECK(viaMemcpy == encoded);

        // Parse back to the same field values.
        Manifest parsed;
        CHECK(ManifestFromBytes(encoded, &parsed));
        CHECK(ManifestEquals(parsed, m));
        CHECK(parsed.generation == 0);
        CHECK(parsed.parent_generation == 0);
        CHECK(parsed.head_seq == 42);
        CHECK(parsed.gamets == 123.5);
        CHECK(parsed.wall_ts == 1735689600123);
        CHECK(parsed.char_name_hash == 0xdeadbeefcafebabeULL);
    }

    // ------------------------------------------------------------------
    // 2. hello_seq staleness discard (spec §4.2, quickload-quickload race).
    // ------------------------------------------------------------------
    void Test_HelloSeqStalenessDiscard() {
        SyncState s;
        s = OnPreLoadGame(s).state;
        s = OnLoadCallback(s, MakeValidLoadRecord(Manifest{})).state;
        auto r1 = OnPostLoadGame(s);  // HELLO A, hello_seq = 1
        s = r1.state;
        CHECK(s.helloSeq == 1);
        CHECK(CountEffectsOfType<SendHello>(r1.effects) == 1);

        // Player quickloads again before A answers.
        s = OnPreLoadGame(s).state;
        s = OnLoadCallback(s, MakeValidLoadRecord(Manifest{})).state;
        auto r2 = OnPostLoadGame(s);  // HELLO B, hello_seq = 2
        s = r2.state;
        CHECK(s.helloSeq == 2);
        CHECK(s.isLoading == true);
        CHECK(s.decision == SyncDecision::kUnknown);
        CHECK(s.epochId == 0);

        // A's late response arrives, echoing the now-stale hello_seq = 1.
        HelloResponse stale;
        stale.helloSeq = 1;
        stale.decision = SyncDecision::kContinue;
        stale.actionable = true;
        stale.epochId = 999;
        auto rStale = OnHelloResponse(s, stale);

        // Must be discarded entirely: no state change at all.
        CHECK(rStale.state.isLoading == true);
        CHECK(rStale.state.decision == SyncDecision::kUnknown);
        CHECK(rStale.state.epochId == 0);
        CHECK(rStale.state.helloSeq == 2);
        CHECK(CountEffectsOfType<SendMutation>(rStale.effects) == 0);

        // B's real response arrives, matching.
        HelloResponse fresh;
        fresh.helloSeq = 2;
        fresh.decision = SyncDecision::kContinue;
        fresh.actionable = true;
        fresh.epochId = 5;
        auto rFresh = OnHelloResponse(s, fresh);

        CHECK(rFresh.state.isLoading == false);
        CHECK(rFresh.state.decision == SyncDecision::kContinue);
        CHECK(rFresh.state.epochId == 5);
    }

    // ------------------------------------------------------------------
    // 3. Full CONTINUE happy path.
    // ------------------------------------------------------------------
    void Test_ContinueHappyPath() {
        SyncState s;
        s = OnPreLoadGame(s).state;

        const std::array<std::uint8_t, 16> uuid = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16};
        Manifest loaded = MakeManifest(0, 0, /*headSeq=*/10, 100.0, 1000, 0xAA, uuid);
        s = OnLoadCallback(s, MakeValidLoadRecord(loaded)).state;
        CHECK(s.manifestPresent == true);
        CHECK(s.currentManifest.head_seq == 10);

        auto rPost = OnPostLoadGame(s);
        s = rPost.state;
        CHECK(s.helloSeq == 1);

        HelloResponse resp;
        resp.helloSeq = 1;
        resp.decision = SyncDecision::kContinue;
        resp.actionable = true;
        resp.epochId = 5;
        auto rResp = OnHelloResponse(s, resp);
        s = rResp.state;
        CHECK(s.isLoading == false);
        CHECK(s.decision == SyncDecision::kContinue);
        CHECK(s.actionable == true);
        CHECK(s.epochId == 5);
        CHECK(s.currentManifest.head_seq == 10);  // untouched by the response itself

        MutationEvent ev;
        ev.seq = 11;
        ev.gamets = 101.0;
        ev.wallTs = 1100;
        ev.eventPayload = "npc_died";
        auto rMut = OnMutationReady(s, ev);
        s = rMut.state;
        CHECK(CountEffectsOfType<SendMutation>(rMut.effects) == 1);
        CHECK(CountEffectsOfType<BufferMutationLocally>(rMut.effects) == 0);
        CHECK(s.outboundRing.empty());

        MutationCommitInfo commit{11, 101.0, 1100};
        s = OnMutationAccepted(s, commit).state;
        CHECK(s.currentManifest.head_seq == 11);
        CHECK(s.currentManifest.gamets == 101.0);
        CHECK(s.currentManifest.wall_ts == 1100);

        auto rSave = OnSaveGame(s);
        CHECK(CountEffectsOfType<WriteCoSaveRecord>(rSave.effects) == 1);
        for (const auto& e : rSave.effects) {
            if (auto* w = std::get_if<WriteCoSaveRecord>(&e)) {
                CHECK(w->manifest.head_seq == 11);
            }
        }
    }

    // ------------------------------------------------------------------
    // 4. DEGRADED timeout -> buffer -> reconnect -> replay.
    // ------------------------------------------------------------------
    void Test_DegradedTimeoutBufferReconnectReplay() {
        SyncState s;
        s = OnPreLoadGame(s).state;
        Manifest loaded = MakeManifest(0, 0, 5, 50.0, 500, 0xBB, {});
        s = OnLoadCallback(s, MakeValidLoadRecord(loaded)).state;
        s = OnPostLoadGame(s).state;  // hello_seq = 1
        CHECK(s.helloSeq == 1);

        auto rTimeout = OnHelloTimeout(s, 1);
        s = rTimeout.state;
        CHECK(s.isLoading == false);
        CHECK(s.decision == SyncDecision::kDegraded);
        CHECK(s.actionable == false);
        CHECK(s.helloRetryScheduled == true);
        bool sawSchedule = false;
        for (const auto& e : rTimeout.effects) {
            if (auto* sc = std::get_if<ScheduleHelloRetryBackoff>(&e)) {
                sawSchedule = true;
                CHECK(sc->helloSeq == 2);
            }
        }
        CHECK(sawSchedule);

        MutationEvent e1{6, 60.0, 600, "a"};
        MutationEvent e2{7, 70.0, 700, "b"};
        auto rm1 = OnMutationReady(s, e1);
        s = rm1.state;
        CHECK(CountEffectsOfType<BufferMutationLocally>(rm1.effects) == 1);
        CHECK(CountEffectsOfType<SendMutation>(rm1.effects) == 0);
        auto rm2 = OnMutationReady(s, e2);
        s = rm2.state;
        CHECK(s.outboundRing.size() == 2);

        auto rFire = OnHelloBackoffFire(s);
        s = rFire.state;
        CHECK(s.helloRetryScheduled == false);
        CHECK(s.helloSeq == 2);
        CHECK(CountEffectsOfType<SendHello>(rFire.effects) == 1);

        HelloResponse resp;
        resp.helloSeq = 2;
        resp.decision = SyncDecision::kContinue;
        resp.actionable = true;
        resp.epochId = 8;
        auto rResp = OnHelloResponse(s, resp);
        s = rResp.state;
        CHECK(s.isLoading == false);
        CHECK(s.decision == SyncDecision::kContinue);
        CHECK(s.epochId == 8);
        CHECK(s.outboundRing.empty());

        // Replayed oldest-first, both under the newly-resolved epoch.
        std::vector<std::uint64_t> replayedSeqs;
        for (const auto& e : rResp.effects) {
            if (auto* sm = std::get_if<SendMutation>(&e)) {
                replayedSeqs.push_back(sm->seq);
                CHECK(sm->epochId == 8);
            }
        }
        CHECK(replayedSeqs.size() == 2);
        if (replayedSeqs.size() == 2) {
            CHECK(replayedSeqs[0] == 6);
            CHECK(replayedSeqs[1] == 7);
        }
    }

    // ------------------------------------------------------------------
    // 5. actionable:false handled identically to DEGRADED (spec §4/§4.5).
    // ------------------------------------------------------------------
    void Test_ActionableFalseHandledLikeDegraded() {
        SyncState s;
        s = OnPreLoadGame(s).state;
        s = OnLoadCallback(s, MakeValidLoadRecord(Manifest{})).state;
        s = OnPostLoadGame(s).state;
        CHECK(s.helloSeq == 1);

        HelloResponse resp;
        resp.helloSeq = 1;
        resp.decision = SyncDecision::kFork;  // decided, not actionable (spec §4)
        resp.actionable = false;
        resp.epochId = 3;
        s = OnHelloResponse(s, resp).state;
        CHECK(s.isLoading == false);
        CHECK(s.decision == SyncDecision::kFork);
        CHECK(s.actionable == false);
        CHECK(DecisionRequiresBuffering(s.decision, s.actionable) == true);

        MutationEvent ev{1, 1.0, 100, "x"};
        auto rMut = OnMutationReady(s, ev);
        CHECK(CountEffectsOfType<SendMutation>(rMut.effects) == 0);
        CHECK(CountEffectsOfType<BufferMutationLocally>(rMut.effects) == 1);
        CHECK(rMut.state.outboundRing.size() == 1);
    }

    // ------------------------------------------------------------------
    // 6. Revert mid-load drops queued state and requests spill rotation.
    // ------------------------------------------------------------------
    void Test_RevertMidLoadDropsQueueAndRotatesSpill() {
        SyncState s;
        s = OnPreLoadGame(s).state;
        Manifest loaded = MakeManifest(2, 1, 20, 200.0, 2000, 0xCC, {});
        s = OnLoadCallback(s, MakeValidLoadRecord(loaded)).state;
        CHECK(s.manifestPresent == true);

        // A mutation gets generated before HELLO ever resolves -- buffered.
        MutationEvent ev{21, 210.0, 2100, "pre-hello"};
        s = OnMutationReady(s, ev).state;
        CHECK(s.outboundRing.size() == 1);

        const bool wasLoading = s.isLoading;
        CHECK(wasLoading == true);

        auto rRevert = OnGameRevert(s);
        s = rRevert.state;

        CHECK(s.outboundRing.empty());
        CHECK(s.epochId == 0);
        CHECK(s.manifestPresent == false);
        CHECK(s.decision == SyncDecision::kUnknown);
        CHECK(ManifestEquals(s.currentManifest, Manifest{}));
        CHECK(CountEffectsOfType<RotateSpillFile>(rRevert.effects) == 1);

        // D3: g_isLoading is left exactly as it was, not forced.
        CHECK(s.isLoading == wasLoading);
    }

    // Revert on quit-to-main-menu with NO subsequent load (D3): isLoading
    // was already false, and Revert must not flip it true.
    void Test_RevertWithNoSubsequentLoadLeavesIsLoadingFalse() {
        SyncState s;  // clean/default -- as if nothing is currently loading
        CHECK(s.isLoading == false);
        auto r = OnGameRevert(s);
        CHECK(r.state.isLoading == false);
        CHECK(CountEffectsOfType<RotateSpillFile>(r.effects) == 1);
    }

    // Regression test for the extra hello_seq bump inside OnGameRevert
    // (beyond what spec §4.2's text literally lists): a HELLO in flight at
    // Revert time, with no subsequent load ever bumping hello_seq again,
    // must NOT be accepted when it answers late.
    void Test_RevertInvalidatesInFlightHello() {
        SyncState s;
        s = OnPostLoadGame(s).state;  // HELLO fired, hello_seq = 1
        CHECK(s.helloSeq == 1);

        s = OnGameRevert(s).state;
        CHECK(s.helloSeq == 2);  // bumped even though no new load started
        CHECK(s.epochId == 0);

        HelloResponse lateResp;
        lateResp.helloSeq = 1;  // the pre-Revert HELLO's id
        lateResp.decision = SyncDecision::kContinue;
        lateResp.actionable = true;
        lateResp.epochId = 999;
        auto r = OnHelloResponse(s, lateResp);

        CHECK(r.state.epochId == 0);  // unchanged -- discarded as stale
        CHECK(r.state.decision == SyncDecision::kUnknown);
    }

    // A scheduled DEGRADED backoff retry is actually cancelled -- not just
    // silently ignored later -- by the next kPreLoadGame, and the
    // cancellation is observable both as the flag flipping AND as the
    // CancelScheduledHelloRetry effect actually being emitted. Then prove
    // the cancellation matters: the straggling retry, if it fires anyway
    // (a timer the glue layer failed to actually cancel), must produce NO
    // SendHello.
    void Test_PreLoadGameCancelsScheduledHelloRetry() {
        SyncState s;
        s = OnPostLoadGame(s).state;       // hello_seq = 1
        s = OnHelloTimeout(s, 1).state;    // DEGRADED, helloRetryScheduled = true
        CHECK(s.helloRetryScheduled == true);

        auto r = OnPreLoadGame(s);
        CHECK(r.state.helloRetryScheduled == false);
        CHECK(CountEffectsOfType<CancelScheduledHelloRetry>(r.effects) == 1);

        // The straggler fires anyway (glue-layer timer raced the cancel) --
        // must be a no-op, not a second HELLO.
        auto rStraggler = OnHelloBackoffFire(r.state);
        CHECK(CountEffectsOfType<SendHello>(rStraggler.effects) == 0);
        CHECK(rStraggler.state.helloSeq == r.state.helloSeq);
    }

    // Same race, but Revert is what cancels it (spec §4.2's "cancel it on
    // kPreLoadGame/Revert").
    void Test_RevertCancelsScheduledHelloRetry() {
        SyncState s;
        s = OnPostLoadGame(s).state;
        s = OnHelloTimeout(s, 1).state;
        CHECK(s.helloRetryScheduled == true);

        auto r = OnGameRevert(s);
        CHECK(r.state.helloRetryScheduled == false);
        CHECK(CountEffectsOfType<CancelScheduledHelloRetry>(r.effects) == 1);

        auto rStraggler = OnHelloBackoffFire(r.state);
        CHECK(CountEffectsOfType<SendHello>(rStraggler.effects) == 0);
        CHECK(rStraggler.state.helloSeq == r.state.helloSeq);
    }

    // ------------------------------------------------------------------
    // OnMutationSendFailed -- the third httplib::Result outcome (spec §2)
    // that neither OnMutationAccepted nor OnMutationRejected covers.
    // ------------------------------------------------------------------
    void Test_MutationSendFailedBuffersAndSchedulesRetry() {
        SyncState s;
        s.decision = SyncDecision::kContinue;
        s.actionable = true;
        s.epochId = 5;
        CHECK(s.helloRetryScheduled == false);

        MutationEvent ev{20, 200.0, 2000, "connection-lost"};
        auto r = OnMutationSendFailed(s, ev);

        // The event is buffered, never dropped.
        CHECK(r.state.outboundRing.size() == 1);
        CHECK(r.state.outboundRing.front().seq == 20);
        CHECK(CountEffectsOfType<BufferMutationLocally>(r.effects) == 1);

        // Self-assigned DEGRADED, matching the timeout path's semantics.
        CHECK(r.state.decision == SyncDecision::kDegraded);
        CHECK(r.state.actionable == false);
        CHECK(r.state.helloRetryScheduled == true);
        CHECK(CountEffectsOfType<ScheduleHelloRetryBackoff>(r.effects) == 1);

        // A second failure while a retry is already pending doesn't
        // schedule a duplicate one.
        MutationEvent ev2{21, 210.0, 2100, "still-down"};
        auto r2 = OnMutationSendFailed(r.state, ev2);
        CHECK(r2.state.outboundRing.size() == 2);
        CHECK(CountEffectsOfType<ScheduleHelloRetryBackoff>(r2.effects) == 0);
    }

    // ------------------------------------------------------------------
    // 7. Extra coverage beyond the minimum list.
    // ------------------------------------------------------------------

    // Save during DEGRADED writes the last ACKed seq, not the highest
    // generated/buffered-but-unconfirmed one (spec §4.4's whole point).
    void Test_SaveDuringDegradedWritesLastAckedSeq() {
        SyncState s;
        s.currentManifest.head_seq = 10;
        s.decision = SyncDecision::kDegraded;
        s.actionable = false;
        s.isLoading = false;

        for (std::uint64_t seq : {11ULL, 12ULL, 13ULL}) {
            MutationEvent ev{seq, static_cast<double>(seq), static_cast<std::int64_t>(seq) * 100, "x"};
            s = OnMutationReady(s, ev).state;
        }
        CHECK(s.outboundRing.size() == 3);
        CHECK(s.currentManifest.head_seq == 10);  // still the last ACKed value

        auto rSave = OnSaveGame(s);
        for (const auto& e : rSave.effects) {
            if (auto* w = std::get_if<WriteCoSaveRecord>(&e)) {
                CHECK(w->manifest.head_seq == 10);
            }
        }
    }

    // Non-null replay_from_seq must never itself produce a SendMutation --
    // that's server-side bookkeeping the shim doesn't act on (guards the
    // exact inversion spec §4.4 says v1 got backwards).
    void Test_ReplayFromSeqProducesNoSendMutation() {
        SyncState s;
        s = OnPostLoadGame(s).state;  // hello_seq = 1, empty ring
        CHECK(s.outboundRing.empty());

        HelloResponse resp;
        resp.helloSeq = 1;
        resp.decision = SyncDecision::kContinue;
        resp.actionable = true;
        resp.epochId = 1;
        resp.replayFromSeq = 42;
        auto r = OnHelloResponse(s, resp);

        CHECK(CountEffectsOfType<SendMutation>(r.effects) == 0);
        CHECK(CountEffectsOfType<LogInfo>(r.effects) == 1);
    }

    // Load-validation table: each of the four §3 checks failing
    // individually (plus "no record at all") -> manifestPresent=false and
    // the manifest is left at defaults, never partially populated.
    void Test_LoadValidationTable() {
        const std::array<std::uint8_t, 16> uuid = {9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9};
        Manifest valid = MakeManifest(1, 0, 77, 7.0, 700, 0xDD, uuid);

        auto checkRejected = [](const LoadRecordInfo& rec, const char* label) {
            // Seed DIRTY state first -- a fresh SyncState already has
            // manifestPresent=false and currentManifest==Manifest{}, which
            // would make this assertion pass even if OnLoadCallback did
            // nothing at all. Seeding non-default values makes "rejected"
            // an actual reset, not a no-op that happens to look right.
            SyncState s;
            s.manifestPresent = true;
            s.currentManifest.head_seq = 55;
            s.currentManifest.generation = 3;
            auto r = OnLoadCallback(s, rec);
            if (r.state.manifestPresent != false) {
                std::fprintf(stderr, "  [%s] expected manifestPresent=false\n", label);
            }
            CHECK(r.state.manifestPresent == false);
            CHECK(ManifestEquals(r.state.currentManifest, Manifest{}));
        };

        {  // no record found at all
            LoadRecordInfo rec;
            rec.recordFound = false;
            checkRejected(rec, "no record found");
        }
        {  // declared length mismatch
            LoadRecordInfo rec = MakeValidLoadRecord(valid);
            rec.declaredLength = 60;
            checkRejected(rec, "declaredLength != 68");
        }
        {  // magic mismatch
            LoadRecordInfo rec = MakeValidLoadRecord(valid);
            rec.rawBytes[0] ^= 0xFF;
            checkRejected(rec, "bad magic");
        }
        {  // unrecognized version
            LoadRecordInfo rec = MakeValidLoadRecord(valid);
            rec.version = 2;
            checkRejected(rec, "unrecognized version");
        }
        {  // truncated actual read
            LoadRecordInfo rec = MakeValidLoadRecord(valid);
            rec.actualReadLength = 67;
            checkRejected(rec, "actualReadLength != 68");
        }
        {  // sanity: the same record, unmutated, IS accepted
            SyncState s;
            auto r = OnLoadCallback(s, MakeValidLoadRecord(valid));
            CHECK(r.state.manifestPresent == true);
            CHECK(ManifestEquals(r.state.currentManifest, valid));
        }
    }

    // Regression coverage for the 2026-09-03 live crash: kPostLoadGame's
    // `data` is the packed value itself, never a pointer to dereference.
    // `data`'s numeric value can only ever legitimately be 0 or 1 (skse64's
    // own bool-as-pointer-slot convention), but this checks a few more
    // bit patterns anyway precisely because the whole point of this bug was
    // "someone's plausible-looking assumption about the encoding was
    // wrong" -- don't repeat that by only testing the one shape expected.
    void Test_DecodePostLoadSuccessFlag() {
        CHECK(DecodePostLoadSuccessFlag(reinterpret_cast<void*>(std::uintptr_t{1}), 1) == true);
        CHECK(DecodePostLoadSuccessFlag(reinterpret_cast<void*>(std::uintptr_t{0}), 1) == false);
        CHECK(DecodePostLoadSuccessFlag(nullptr, 1) == false);
        // Never treat a pointer-sized nonzero value's low byte alone as
        // proof of "true" beyond what dataLen==1 actually promises, but
        // also never crash trying to read through it as an address.
        CHECK(DecodePostLoadSuccessFlag(reinterpret_cast<void*>(std::uintptr_t{0x100}), 1) == false);
        CHECK(DecodePostLoadSuccessFlag(reinterpret_cast<void*>(std::uintptr_t{0x101}), 1) == true);
        // Wrong dataLen: an SKSE build that changed this convention must
        // not be silently treated as success.
        CHECK(DecodePostLoadSuccessFlag(reinterpret_cast<void*>(std::uintptr_t{1}), 0) == false);
        CHECK(DecodePostLoadSuccessFlag(reinterpret_cast<void*>(std::uintptr_t{1}), 4) == false);
    }

    // Mechanical single-writer discipline: every transition EXCEPT
    // OnHelloResponse (epochId) and OnMutationAccepted (head_seq) must
    // leave both fields untouched. OnLoadCallback and OnNewGame are
    // deliberately excluded (see this file's header / SyncHandshakeCore.h
    // comments) -- they perform a hydration-from-disk and a hardcoded
    // fresh-playthrough reset respectively, not a live "advance", and are
    // covered by their own dedicated tests below instead.
    void Test_SingleWriterDisciplineMechanical() {
        auto seed = []() {
            SyncState s;
            s.epochId = 7;
            s.currentManifest.head_seq = 99;
            return s;
        };
        auto assertUnchanged = [](const SyncState& s, const char* label) {
            if (s.epochId != 7 || s.currentManifest.head_seq != 99) {
                std::fprintf(stderr, "  [%s] epochId=%llu head_seq=%llu (expected 7/99)\n", label,
                             static_cast<unsigned long long>(s.epochId),
                             static_cast<unsigned long long>(s.currentManifest.head_seq));
            }
            CHECK(s.epochId == 7);
            CHECK(s.currentManifest.head_seq == 99);
        };

        assertUnchanged(OnPreLoadGame(seed()).state, "OnPreLoadGame");
        assertUnchanged(OnPostLoadGame(seed()).state, "OnPostLoadGame");
        assertUnchanged(OnSaveGame(seed()).state, "OnSaveGame");

        {
            SyncState s = seed();
            s.decision = SyncDecision::kContinue;
            s.actionable = true;
            s.isLoading = false;
            MutationEvent ev{1, 1.0, 100, "x"};
            assertUnchanged(OnMutationReady(s, ev).state, "OnMutationReady (send path)");
        }
        {
            SyncState s = seed();
            s.decision = SyncDecision::kDegraded;
            MutationEvent ev{1, 1.0, 100, "x"};
            assertUnchanged(OnMutationReady(s, ev).state, "OnMutationReady (buffer path)");
        }
        {
            SyncState s = seed();
            s.helloSeq = 3;
            assertUnchanged(OnHelloTimeout(s, 3).state, "OnHelloTimeout (matching)");
        }
        {
            SyncState s = seed();
            assertUnchanged(OnMutationRejected(s, 7, 99).state, "OnMutationRejected");
        }
        {
            SyncState s = seed();
            MutationEvent ev{1, 1.0, 100, "x"};
            assertUnchanged(OnMutationSendFailed(s, ev).state, "OnMutationSendFailed");
        }
        {
            SyncState s = seed();
            s.helloRetryScheduled = true;
            assertUnchanged(OnHelloBackoffFire(s).state, "OnHelloBackoffFire (fires)");
        }
        {
            SyncState s = seed();
            s.helloRetryScheduled = false;
            assertUnchanged(OnHelloBackoffFire(s).state, "OnHelloBackoffFire (no-op)");
        }
    }

    // OnLoadCallback is a faithful hydration from disk, not an independent
    // advance: feeding it a record whose OWN head_seq happens to be 99
    // reproduces 99 (it doesn't invent or skip it); epochId is never
    // touched (the manifest carries no epoch_id field at all).
    void Test_LoadCallbackIsHydrationNotAdvance() {
        SyncState s;
        s.epochId = 7;
        Manifest onDisk;
        onDisk.head_seq = 99;
        auto r = OnLoadCallback(s, MakeValidLoadRecord(onDisk));
        CHECK(r.state.epochId == 7);
        CHECK(r.state.currentManifest.head_seq == 99);
        CHECK(r.state.manifestPresent == true);
    }

    // format_version cross-agent contract fix: the Python-side /whiterun/
    // sync/hello handler requires format_version in the HELLO body to
    // construct chronicle.sync.Manifest -- omitting it 400s. This proves
    // the value a successful Load validated against actually reaches the
    // SendHello side effect a future glue layer would serialize, and that
    // a rejected/absent manifest still reports a defined, non-garbage
    // value rather than leaving the field meaningless.
    void Test_FormatVersionReachesSendHello() {
        // Valid manifest: OnLoadCallback observed kManifestRecordVersion,
        // OnPostLoadGame's SendHello must carry exactly that.
        {
            SyncState s;
            Manifest onDisk;
            onDisk.head_seq = 5;
            s = OnLoadCallback(s, MakeValidLoadRecord(onDisk)).state;
            CHECK(s.currentFormatVersion == kManifestRecordVersion);

            auto r = OnPostLoadGame(s);
            bool found = false;
            for (const auto& e : r.effects) {
                if (auto* h = std::get_if<SendHello>(&e)) {
                    CHECK(h->manifestPresent == true);
                    CHECK(h->formatVersion == kManifestRecordVersion);
                    found = true;
                }
            }
            CHECK(found);
        }

        // Rejected manifest (a_version mismatch, spec §3's four-way gate):
        // manifestPresent must be false AND formatVersion must still be a
        // defined value (kManifestRecordVersion, this build's own current
        // version -- there is no co-save value to report), not left at
        // whatever stale value happened to be in state beforehand.
        {
            SyncState s;
            s.currentFormatVersion = 99;  // deliberately wrong, to prove OnLoadCallback resets it
            LoadRecordInfo badVersion = MakeValidLoadRecord(Manifest{});
            badVersion.version = kManifestRecordVersion + 1;  // unrecognized -- spec §3's version gate

            auto loaded = OnLoadCallback(s, badVersion);
            CHECK(loaded.state.manifestPresent == false);
            CHECK(loaded.state.currentFormatVersion == kManifestRecordVersion);

            auto r = OnPostLoadGame(loaded.state);
            bool found = false;
            for (const auto& e : r.effects) {
                if (auto* h = std::get_if<SendHello>(&e)) {
                    CHECK(h->manifestPresent == false);
                    CHECK(h->formatVersion == kManifestRecordVersion);
                    found = true;
                }
            }
            CHECK(found);
        }

        // OnNewGame and OnGameRevert must also leave a defined value, not
        // a stale carry-over from before the reset.
        {
            SyncState s;
            s.currentFormatVersion = 99;
            std::array<std::uint8_t, 16> uuid = {2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2};
            auto r = OnNewGame(s, uuid);
            CHECK(r.state.currentFormatVersion == kManifestRecordVersion);
            for (const auto& e : r.effects) {
                if (auto* h = std::get_if<SendHello>(&e)) {
                    CHECK(h->formatVersion == kManifestRecordVersion);
                }
            }
        }
        {
            SyncState s;
            s.currentFormatVersion = 99;
            auto r = OnGameRevert(s);
            CHECK(r.state.currentFormatVersion == kManifestRecordVersion);
        }
    }

    // OnNewGame forcibly resets head_seq/generation/parent_generation to 0
    // regardless of whatever was previously in state -- a brand-new
    // playthrough has no prior history (this is the opposite invariant
    // from the "unchanged" set above, and deliberately so).
    void Test_NewGameForciblyResetsManifest() {
        SyncState s;
        s.currentManifest.head_seq = 99;
        s.currentManifest.generation = 5;
        s.epochId = 7;

        std::array<std::uint8_t, 16> uuid = {1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1};
        auto r = OnNewGame(s, uuid);

        CHECK(r.state.currentManifest.head_seq == 0);
        CHECK(r.state.currentManifest.generation == 0);
        CHECK(r.state.currentManifest.parent_generation == 0);
        CHECK(r.state.manifestPresent == true);
        CHECK(r.state.isLoading == true);
        CHECK(CountEffectsOfType<SendHello>(r.effects) == 1);
        for (int i = 0; i < 16; ++i) {
            CHECK(r.state.currentManifest.save_uuid[i] == uuid[i]);
        }
    }

    // 409 rejection: below threshold just logs and drops; crossing the
    // threshold re-fires HELLO and resets the counter.
    void Test_MutationRejected409ThresholdRefiresHello() {
        SyncState s;
        s.helloSeq = 1;
        s.manifestPresent = true;

        auto r1 = OnMutationRejected(s, 1, 100);
        s = r1.state;
        CHECK(s.mutation409Count == 1);
        CHECK(CountEffectsOfType<SendHello>(r1.effects) == 0);

        auto r2 = OnMutationRejected(s, 1, 101);
        s = r2.state;
        CHECK(s.mutation409Count == 2);
        CHECK(CountEffectsOfType<SendHello>(r2.effects) == 0);

        auto r3 = OnMutationRejected(s, 1, 102);  // crosses kMutation409ReHelloThreshold (3)
        s = r3.state;
        CHECK(s.mutation409Count == 0);
        CHECK(s.helloSeq == 2);
        CHECK(CountEffectsOfType<SendHello>(r3.effects) == 1);
    }

    // Ring overflow spills the OLDEST entry to file, keeping the newest N
    // in memory (so file-then-ring replay order stays coherent).
    void Test_RingOverflowSpillsOldest() {
        SyncState s;
        s.decision = SyncDecision::kDegraded;  // force buffering

        for (std::uint64_t seq = 0; seq < kOutboundRingCapacity; ++seq) {
            MutationEvent ev{seq, 0.0, 0, "x"};
            s = OnMutationReady(s, ev).state;
        }
        CHECK(s.outboundRing.size() == kOutboundRingCapacity);
        CHECK(s.outboundRing.front().seq == 0);

        MutationEvent overflow{kOutboundRingCapacity, 0.0, 0, "overflow"};
        auto r = OnMutationReady(s, overflow);
        s = r.state;

        CHECK(s.outboundRing.size() == kOutboundRingCapacity);
        CHECK(s.outboundRing.front().seq == 1);              // oldest (0) evicted
        CHECK(s.outboundRing.back().seq == kOutboundRingCapacity);  // newest arrival kept

        bool sawSpill = false;
        for (const auto& e : r.effects) {
            if (auto* sp = std::get_if<SpillMutationToFile>(&e)) {
                sawSpill = true;
                CHECK(sp->seq == 0);  // the oldest, not the new arrival
            }
        }
        CHECK(sawSpill);
    }

    // ------------------------------------------------------------------
    // HELLO *response* parser tests (SyncHelloResponseParser.h/.cpp) --
    // the one genuinely new hand-rolled component the glue layer needed
    // that could still be factored to be SKSE-independent (the sync-wiring
    // plan's own Verification section names this explicitly: "the HELLO
    // response parser ... is the riskiest untestable-in-game piece of this
    // lane, and nothing currently exercises it").
    // ------------------------------------------------------------------

    void Test_HelloResponseParser_WellFormed() {
        const std::string body =
            R"({"decision":"CONTINUE","actionable":true,"epoch_id":7,)"
            R"("replay_from_seq":42,"confirm_required":false,"hello_seq":3})";
        auto parsed = ParseSyncHelloResponseJson(body);
        CHECK(parsed.has_value());
        CHECK(parsed->decision == SyncDecision::kContinue);
        CHECK(parsed->actionable == true);
        CHECK(parsed->epochId == 7);
        CHECK(parsed->replayFromSeq.has_value());
        CHECK(*parsed->replayFromSeq == 42);
        CHECK(parsed->confirmRequired == false);
        CHECK(parsed->helloSeq == 3);
    }

    void Test_HelloResponseParser_ReplayFromSeqNull() {
        const std::string body =
            R"({"decision":"NEW_TIMELINE","actionable":true,"epoch_id":1,)"
            R"("replay_from_seq":null,"confirm_required":false,"hello_seq":1})";
        auto parsed = ParseSyncHelloResponseJson(body);
        CHECK(parsed.has_value());
        CHECK(parsed->decision == SyncDecision::kNewTimeline);
        CHECK(!parsed->replayFromSeq.has_value());
    }

    void Test_HelloResponseParser_EachRecognizedDecision() {
        struct Case {
            const char* wire;
            SyncDecision expected;
        };
        const Case cases[] = {
            {"CONTINUE", SyncDecision::kContinue},   {"FORK", SyncDecision::kFork},
            {"ADOPT", SyncDecision::kAdopt},         {"NEW_TIMELINE", SyncDecision::kNewTimeline},
            {"LEGACY_IMPORT", SyncDecision::kLegacyImport}, {"DEGRADED", SyncDecision::kDegraded},
        };
        for (const auto& c : cases) {
            const std::string body = std::string(R"({"decision":")") + c.wire +
                                      R"(","actionable":false,"epoch_id":0,)"
                                      R"("replay_from_seq":null,"confirm_required":false,"hello_seq":0})";
            auto parsed = ParseSyncHelloResponseJson(body);
            CHECK(parsed.has_value());
            if (parsed) {
                CHECK(parsed->decision == c.expected);
            }
        }
    }

    void Test_HelloResponseParser_UnrecognizedDecisionFails() {
        const std::string body =
            R"({"decision":"UNKNOWN","actionable":false,"epoch_id":0,)"
            R"("replay_from_seq":null,"confirm_required":false,"hello_seq":0})";
        auto parsed = ParseSyncHelloResponseJson(body);
        CHECK(!parsed.has_value());  // must fail loudly, never silently accept.

        const std::string bodyGarbage =
            R"({"decision":"totally-not-a-decision","actionable":false,"epoch_id":0,)"
            R"("replay_from_seq":null,"confirm_required":false,"hello_seq":0})";
        CHECK(!ParseSyncHelloResponseJson(bodyGarbage).has_value());
    }

    void Test_HelloResponseParser_MissingFieldFails() {
        // Missing hello_seq entirely.
        const std::string missingHelloSeq =
            R"({"decision":"CONTINUE","actionable":true,"epoch_id":7,)"
            R"("replay_from_seq":null,"confirm_required":false})";
        CHECK(!ParseSyncHelloResponseJson(missingHelloSeq).has_value());

        // Missing decision entirely.
        const std::string missingDecision =
            R"({"actionable":true,"epoch_id":7,"replay_from_seq":null,)"
            R"("confirm_required":false,"hello_seq":1})";
        CHECK(!ParseSyncHelloResponseJson(missingDecision).has_value());

        // Missing replay_from_seq entirely (not even a null literal) --
        // must fail, not silently treat "absent" as "null".
        const std::string missingReplayFromSeq =
            R"({"decision":"CONTINUE","actionable":true,"epoch_id":7,)"
            R"("confirm_required":false,"hello_seq":1})";
        CHECK(!ParseSyncHelloResponseJson(missingReplayFromSeq).has_value());
    }

    void Test_HelloResponseParser_MalformedFieldFails() {
        // actionable is a string, not a bool literal.
        const std::string badActionable =
            R"({"decision":"CONTINUE","actionable":"true","epoch_id":7,)"
            R"("replay_from_seq":null,"confirm_required":false,"hello_seq":1})";
        CHECK(!ParseSyncHelloResponseJson(badActionable).has_value());

        // epoch_id is not numeric.
        const std::string badEpochId =
            R"({"decision":"CONTINUE","actionable":true,"epoch_id":"not-a-number",)"
            R"("replay_from_seq":null,"confirm_required":false,"hello_seq":1})";
        CHECK(!ParseSyncHelloResponseJson(badEpochId).has_value());

        // replay_from_seq is neither null nor a number.
        const std::string badReplayFromSeq =
            R"({"decision":"CONTINUE","actionable":true,"epoch_id":7,)"
            R"("replay_from_seq":"soon","confirm_required":false,"hello_seq":1})";
        CHECK(!ParseSyncHelloResponseJson(badReplayFromSeq).has_value());
    }

}  // namespace

int main() {
    RUN(Test_GoldenFixtureRoundTrip);
    RUN(Test_HelloSeqStalenessDiscard);
    RUN(Test_ContinueHappyPath);
    RUN(Test_DegradedTimeoutBufferReconnectReplay);
    RUN(Test_ActionableFalseHandledLikeDegraded);
    RUN(Test_RevertMidLoadDropsQueueAndRotatesSpill);
    RUN(Test_RevertWithNoSubsequentLoadLeavesIsLoadingFalse);
    RUN(Test_RevertInvalidatesInFlightHello);
    RUN(Test_PreLoadGameCancelsScheduledHelloRetry);
    RUN(Test_RevertCancelsScheduledHelloRetry);
    RUN(Test_MutationSendFailedBuffersAndSchedulesRetry);
    RUN(Test_SaveDuringDegradedWritesLastAckedSeq);
    RUN(Test_ReplayFromSeqProducesNoSendMutation);
    RUN(Test_LoadValidationTable);
    RUN(Test_DecodePostLoadSuccessFlag);
    RUN(Test_SingleWriterDisciplineMechanical);
    RUN(Test_LoadCallbackIsHydrationNotAdvance);
    RUN(Test_FormatVersionReachesSendHello);
    RUN(Test_NewGameForciblyResetsManifest);
    RUN(Test_MutationRejected409ThresholdRefiresHello);
    RUN(Test_RingOverflowSpillsOldest);
    RUN(Test_HelloResponseParser_WellFormed);
    RUN(Test_HelloResponseParser_ReplayFromSeqNull);
    RUN(Test_HelloResponseParser_EachRecognizedDecision);
    RUN(Test_HelloResponseParser_UnrecognizedDecisionFails);
    RUN(Test_HelloResponseParser_MissingFieldFails);
    RUN(Test_HelloResponseParser_MalformedFieldFails);

    std::fprintf(stderr, "\n%d checks, %d failures\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
