#include "SyncHandshakeCore.h"

// See SyncHandshakeCore.h's header comment for what this file is and is
// not: the pure half of what the spec calls SyncHandshake.h/.cpp. No
// SKSE::, no I/O, no globals -- every function here is a plain
// (state, event) -> (state, effects) transformation.

namespace ChronicleBridge {

    // ------------------------------------------------------------------
    // §3: manifest byte layout.
    // ------------------------------------------------------------------

    bool ManifestEquals(const Manifest& a, const Manifest& b) {
        return std::memcmp(&a, &b, sizeof(Manifest)) == 0;
    }

    std::array<std::uint8_t, kManifestWireSize> ManifestToBytes(const Manifest& m) {
        std::array<std::uint8_t, kManifestWireSize> out{};
        std::size_t off = 0;

        auto putU32 = [&](std::uint32_t v) {
            for (int i = 0; i < 4; ++i) {
                out[off++] = static_cast<std::uint8_t>((v >> (8 * i)) & 0xFFu);
            }
        };
        auto putU64 = [&](std::uint64_t v) {
            for (int i = 0; i < 8; ++i) {
                out[off++] = static_cast<std::uint8_t>((v >> (8 * i)) & 0xFFu);
            }
        };

        putU32(m.magic);
        for (int i = 0; i < 16; ++i) {
            out[off++] = m.save_uuid[i];
        }
        putU64(m.generation);
        putU64(m.parent_generation);
        putU64(m.head_seq);

        // gamets's IEEE-754 bit pattern, moved with memcpy (never a union or
        // reinterpret_cast -- that would be undefined behavior).
        std::uint64_t gametsBits = 0;
        std::memcpy(&gametsBits, &m.gamets, sizeof(gametsBits));
        putU64(gametsBits);

        // wall_ts's two's-complement bit pattern (C++20 mandates two's
        // complement for signed integers, so this static_cast is exact).
        putU64(static_cast<std::uint64_t>(m.wall_ts));

        putU64(m.char_name_hash);

        return out;
    }

    bool ManifestFromBytes(const std::array<std::uint8_t, kManifestWireSize>& bytes, Manifest* out) {
        std::size_t off = 0;

        auto getU32 = [&]() -> std::uint32_t {
            std::uint32_t v = 0;
            for (int i = 0; i < 4; ++i) {
                v |= static_cast<std::uint32_t>(bytes[off++]) << (8 * i);
            }
            return v;
        };
        auto getU64 = [&]() -> std::uint64_t {
            std::uint64_t v = 0;
            for (int i = 0; i < 8; ++i) {
                v |= static_cast<std::uint64_t>(bytes[off++]) << (8 * i);
            }
            return v;
        };

        const std::uint32_t magic = getU32();
        if (magic != kManifestMagic) {
            return false;
        }

        Manifest m;
        m.magic = magic;
        for (int i = 0; i < 16; ++i) {
            m.save_uuid[i] = bytes[off++];
        }
        m.generation = getU64();
        m.parent_generation = getU64();
        m.head_seq = getU64();

        const std::uint64_t gametsBits = getU64();
        std::memcpy(&m.gamets, &gametsBits, sizeof(m.gamets));

        m.wall_ts = static_cast<std::int64_t>(getU64());
        m.char_name_hash = getU64();

        *out = m;
        return true;
    }

    namespace {

        // Spec §3's full Load-time gate: "reject the record unless
        // GetNextRecordInfo's length == sizeof(Manifest) (68), the leading
        // 4 bytes match the sentinel, a_version is recognized, AND
        // ReadRecordData's own return value also equals 68." All four are
        // ANDed; ManifestFromBytes covers the magic check, the other three
        // are checked here first (short-circuiting before we even look at
        // the bytes, matching the spec's "fall through ... on any
        // mismatch").
        bool ValidateAndParseManifest(const LoadRecordInfo& record, Manifest* out) {
            if (!record.recordFound) {
                return false;
            }
            if (record.declaredLength != kManifestWireSize) {
                return false;
            }
            if (record.version != kManifestRecordVersion) {
                return false;
            }
            if (record.actualReadLength != kManifestWireSize) {
                return false;
            }
            return ManifestFromBytes(record.rawBytes, out);
        }

    }  // namespace

    // ------------------------------------------------------------------
    // Transitions.
    // ------------------------------------------------------------------

    SyncTransitionResult OnPreLoadGame(SyncState state) {
        state.isLoading = true;

        SyncSideEffects effects;
        if (state.helloRetryScheduled) {
            state.helloRetryScheduled = false;
            effects.push_back(CancelScheduledHelloRetry{});
        }
        return {state, effects};
    }

    SyncTransitionResult OnLoadCallback(SyncState state, const LoadRecordInfo& record) {
        Manifest parsed;
        if (ValidateAndParseManifest(record, &parsed)) {
            state.manifestPresent = true;
            state.currentManifest = parsed;
            // record.version already passed ValidateAndParseManifest's own
            // == kManifestRecordVersion check, so this is currently always
            // that same constant -- stored from the observed value rather
            // than hardcoded so a future loosening of that check (e.g. to
            // let the *service* decide LEGACY_IMPORT on a too-new version,
            // instead of gating client-side) doesn't silently start lying
            // about which version was actually read.
            state.currentFormatVersion = record.version;
        } else {
            // Never a partially-populated manifest -- any failed check
            // means "no manifest" in full, matching the HELLO body's
            // manifest_present=false case (spec §4.1) and the LEGACY_IMPORT
            // fall-through (spec §3), which is resolve()'s call to make,
            // not this transition's.
            state.manifestPresent = false;
            state.currentManifest = Manifest{};
            state.currentFormatVersion = kManifestRecordVersion;
        }
        // No side effects: kPostLoadGame is what fires HELLO (spec §1), not
        // the Load callback itself. epochId is untouched -- the manifest
        // carries no epoch_id field at all.
        return {state, {}};
    }

    SyncTransitionResult OnPostLoadGame(SyncState state) {
        state.isLoading = true;
        state.helloSeq += 1;

        SyncSideEffects effects;
        effects.push_back(
            SendHello{state.manifestPresent, state.currentManifest, state.helloSeq, state.currentFormatVersion});
        return {state, effects};
    }

    SyncTransitionResult OnHelloResponse(SyncState state, const HelloResponse& response) {
        SyncSideEffects effects;

        if (response.helloSeq != state.helloSeq) {
            // Spec §4.2: discard a stale response outright -- no state
            // change of any kind, including isLoading/decision/actionable.
            effects.push_back(LogWarning{"stale HELLO response discarded (hello_seq mismatch)"});
            return {state, effects};
        }

        state.isLoading = false;
        state.decision = response.decision;
        state.actionable = response.actionable;
        state.epochId = response.epochId;  // the single write site for epochId (spec §2/§4.4)

        if (response.confirmRequired) {
            // Spec §4.6: notification only, never a blocking dialog. Exact
            // copy is a UX decision outside this spec.
            effects.push_back(NotifyPlayerNonModal{"a save conflict was detected"});
        }

        if (response.replayFromSeq.has_value()) {
            // Spec §4.4: this is service-side bookkeeping the shim does NOT
            // act on (v1's replay-direction bug, now guarded against by
            // simply never generating a SendMutation from this value).
            effects.push_back(LogInfo{"service reports committed head_seq ahead of the manifest's -- "
                                       "server-side bookkeeping only, shim takes no action"});
        }

        if (DecisionRequiresBuffering(state.decision, state.actionable)) {
            effects.push_back(LogWarning{
                "HELLO resolved to a non-actionable or DEGRADED decision -- continuing to buffer outbound mutations"});
        } else {
            // Reconnect / first successful resolution: replay anything
            // queued while unresolved, oldest first (spec §4.5).
            for (const auto& q : state.outboundRing) {
                effects.push_back(SendMutation{state.epochId, state.currentManifest, q.seq, q.gamets, q.wallTs, q.eventPayload});
            }
            state.outboundRing.clear();
            state.mutation409Count = 0;
        }

        return {state, effects};
    }

    SyncTransitionResult OnHelloTimeout(SyncState state, std::uint64_t timedOutHelloSeq) {
        if (timedOutHelloSeq != state.helloSeq) {
            // A timeout for a load/HELLO this state has already moved past
            // (a new kPreLoadGame/kPostLoadGame/Revert already bumped
            // hello_seq) -- ignore it entirely.
            return {state, {LogWarning{"stale HELLO timeout ignored (hello_seq mismatch)"}}};
        }

        state.isLoading = false;
        state.decision = SyncDecision::kDegraded;
        state.actionable = false;
        state.helloRetryScheduled = true;

        SyncSideEffects effects;
        effects.push_back(LogWarning{"HELLO timed out -- proceeding DEGRADED, buffering outbound mutations"});
        effects.push_back(ScheduleHelloRetryBackoff{state.helloSeq + 1});
        return {state, effects};
    }

    SyncTransitionResult OnHelloBackoffFire(SyncState state) {
        if (!state.helloRetryScheduled) {
            // Cancelled by a later kPreLoadGame/Revert (spec §4.2) -- a
            // straggling timer callback firing anyway is a no-op. This is
            // exactly the guard that keeps a stale retry from landing
            // mid-new-load.
            return {state, {}};
        }

        state.helloRetryScheduled = false;
        state.helloSeq += 1;

        SyncSideEffects effects;
        effects.push_back(
            SendHello{state.manifestPresent, state.currentManifest, state.helloSeq, state.currentFormatVersion});
        return {state, effects};
    }

    SyncTransitionResult OnNewGame(SyncState state, const std::array<std::uint8_t, 16>& newSaveUuid) {
        state.isLoading = true;

        // A brand-new playthrough has no prior history: generation,
        // parent_generation, and head_seq all start at 0 by construction.
        // This is a hardcoded reset, not an "advance" driven by live
        // traffic -- see SyncState::currentManifest's field comment.
        Manifest m;
        for (int i = 0; i < 16; ++i) {
            m.save_uuid[i] = newSaveUuid[i];
        }
        state.currentManifest = m;
        state.manifestPresent = true;  // a real, freshly-minted manifest, even though nothing loaded from disk
        state.currentFormatVersion = kManifestRecordVersion;  // written at this build's own current version

        state.helloSeq += 1;

        SyncSideEffects effects;
        effects.push_back(SendHello{true, state.currentManifest, state.helloSeq, state.currentFormatVersion});
        return {state, effects};
    }

    SyncTransitionResult OnSaveGame(SyncState state) {
        // D5: head_seq/gamets/wall_ts here are exactly whatever
        // OnMutationAccepted last wrote -- one field, read once here, never
        // re-derived from a second, possibly-skewed source.
        SyncSideEffects effects;
        effects.push_back(WriteCoSaveRecord{state.currentManifest});
        return {state, effects};
    }

    SyncTransitionResult OnMutationReady(SyncState state, const MutationEvent& event) {
        SyncSideEffects effects;

        // D1: this IS the drain gate for the sync slice -- gated on
        // isLoading/actionable, not per-sink.
        if (state.isLoading || DecisionRequiresBuffering(state.decision, state.actionable)) {
            if (state.outboundRing.size() >= kOutboundRingCapacity) {
                const QueuedMutation oldest = state.outboundRing.front();
                state.outboundRing.erase(state.outboundRing.begin());
                effects.push_back(SpillMutationToFile{oldest.seq, oldest.gamets, oldest.wallTs, oldest.eventPayload});
            }
            state.outboundRing.push_back(QueuedMutation{event.seq, event.gamets, event.wallTs, event.eventPayload});
            effects.push_back(BufferMutationLocally{event.seq, event.gamets, event.wallTs, event.eventPayload});
        } else {
            effects.push_back(
                SendMutation{state.epochId, state.currentManifest, event.seq, event.gamets, event.wallTs, event.eventPayload});
        }

        return {state, effects};
    }

    SyncTransitionResult OnMutationAccepted(SyncState state, const MutationCommitInfo& info) {
        // The one transition (besides the hydration/reset cases documented
        // on SyncState::currentManifest) allowed to advance head_seq --
        // and seq/gamets/wall_ts are written together here from a single
        // echoed source, which is what makes D5's "same atomic read"
        // requirement true by construction (see MutationCommitInfo's
        // comment).
        state.currentManifest.head_seq = info.seq;
        state.currentManifest.gamets = info.gamets;
        state.currentManifest.wall_ts = info.wallTs;
        return {state, {}};
    }

    SyncTransitionResult OnMutationRejected(SyncState state, std::uint64_t epochAtSend, std::uint64_t seq) {
        SyncSideEffects effects;

        state.mutation409Count += 1;
        effects.push_back(LogWarning{"mutation seq=" + std::to_string(seq) + " rejected (409) under epoch=" +
                                      std::to_string(epochAtSend) + " -- dropped, belongs to a superseded epoch"});

        if (state.mutation409Count >= kMutation409ReHelloThreshold) {
            state.mutation409Count = 0;
            state.helloSeq += 1;
            effects.push_back(LogWarning{"409 threshold exceeded -- re-firing HELLO, possible epoch desync"});
            effects.push_back(SendHello{state.manifestPresent, state.currentManifest, state.helloSeq});
        }

        return {state, effects};
    }

    SyncTransitionResult OnMutationSendFailed(SyncState state, const MutationEvent& event) {
        // Spec §2: the synchronous httplib::Result on a mutation POST has
        // exactly three outcomes -- 2xx (OnMutationAccepted), 409
        // (OnMutationRejected), and this one (connection refused, timeout,
        // or a 5xx), which neither §4.1 nor §4.4's text walks through.
        // Judgment call: treat it like a HELLO timeout rather than
        // dropping the event -- buffer it through the SAME ring/spill path
        // OnMutationReady's buffering branch uses (never lost), self-assign
        // DEGRADED, and schedule a HELLO retry if one isn't already
        // pending. Without this transition a mid-session service outage
        // would silently drop every subsequent mutation with no buffering
        // and no DEGRADED signal -- strictly worse than either named
        // outcome.
        SyncSideEffects effects;

        if (state.outboundRing.size() >= kOutboundRingCapacity) {
            const QueuedMutation oldest = state.outboundRing.front();
            state.outboundRing.erase(state.outboundRing.begin());
            effects.push_back(SpillMutationToFile{oldest.seq, oldest.gamets, oldest.wallTs, oldest.eventPayload});
        }
        state.outboundRing.push_back(QueuedMutation{event.seq, event.gamets, event.wallTs, event.eventPayload});
        effects.push_back(BufferMutationLocally{event.seq, event.gamets, event.wallTs, event.eventPayload});

        state.decision = SyncDecision::kDegraded;
        state.actionable = false;

        if (!state.helloRetryScheduled) {
            state.helloRetryScheduled = true;
            effects.push_back(
                LogWarning{"mutation send failed (connection/timeout/5xx) -- proceeding DEGRADED, scheduling HELLO retry"});
            effects.push_back(ScheduleHelloRetryBackoff{state.helloSeq + 1});
        } else {
            effects.push_back(LogWarning{"mutation send failed (connection/timeout/5xx) -- already DEGRADED with a retry pending"});
        }

        return {state, effects};
    }

    SyncTransitionResult OnGameRevert(SyncState state) {
        SyncSideEffects effects;

        // Deliberately NOT touching isLoading -- see the field's comment
        // and this function's declaration comment in the header: forcing
        // it true would latch the drain gate shut on the quit-to-main-menu-
        // with-no-subsequent-load case (D3).

        if (state.helloRetryScheduled) {
            state.helloRetryScheduled = false;
            effects.push_back(CancelScheduledHelloRetry{});
        }

        // Bump hello_seq here too, beyond what spec §4.2's text literally
        // lists (kPostLoadGame/kNewGame). Rationale: if a HELLO is in
        // flight when Revert fires and NO subsequent load ever starts
        // (quit to main menu, D3), nothing else would ever bump hello_seq
        // again -- so that in-flight response, arriving late, would still
        // match state.helloSeq and be wrongly accepted, reintroducing
        // exactly the stale-epoch race §4.2 exists to close, one edge case
        // (Revert-with-no-following-load) its own worked example doesn't
        // walk through. Judgment call; see
        // test_sync_handshake_core.cpp's dedicated regression test.
        state.helloSeq += 1;

        state.decision = SyncDecision::kUnknown;
        state.actionable = false;
        state.epochId = 0;
        state.manifestPresent = false;
        state.currentManifest = Manifest{};
        state.currentFormatVersion = kManifestRecordVersion;
        state.mutation409Count = 0;
        state.outboundRing.clear();

        // Unconditional -- spec §4.5/§5: "Revert must also delete/rotate
        // the spill file, not just the in-memory ring." Rotating a
        // nonexistent file is expected to be a cheap no-op for the glue
        // layer, so no "was there actually a spill file" check belongs
        // here.
        effects.push_back(RotateSpillFile{});

        return {state, effects};
    }

}  // namespace ChronicleBridge
