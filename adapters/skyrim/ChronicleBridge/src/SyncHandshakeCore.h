#pragma once

// Design doc (docs/design/chronicle-bridge-sync-handshake-out.md) §5's hard
// requirement: the save/reload sync-handshake state machine MUST be a pure
// transition function -- (current state, event) -> (new state, side
// effects) -- with no SKSE:: types and no I/O in its signature, in its own
// translation unit. This project has no C++ test harness today and the
// live-game path is separately blocked (spec §7), so this file is the ONLY
// piece of the sync-handshake feature that gets test coverage before the
// glue layer ships.
//
// Naming: the spec's §5 file layout names a single `SyncHandshake.h/.cpp`
// that "owns g_isLoading, epoch_id, hello_seq, ... the manifest struct,
// SerializationInterface registration, and the state machine" -- then says
// in the very next paragraph that this splits into "the pure state machine
// ... and thin SKSE glue ... that calls into it." This file IS that pure
// half. It is deliberately named `SyncHandshakeCore`, not `SyncHandshake`,
// so the future glue translation unit (SerializationInterface registration,
// the actual ReadRecordData/WriteRecord calls, the actual httplib call --
// all explicitly out of scope here) can claim `SyncHandshake.h/.cpp` without
// a collision, while still sharing the spec's name as a recognizable prefix.
//
// Everything below is plain C++ (std::uint8_t/uint64_t/double/int64_t, STL
// containers) -- no SKSE:: types anywhere in this header, on purpose: that's
// what makes it compilable and unit-testable with a stock g++/clang++ on any
// machine, no SKSE SDK or Windows toolchain required. See
// tests/test_sync_handshake_core.cpp for the compile/run command.
//
// Style/structure note: header-comment density and struct-with-inline-
// rationale conventions here follow DeathEventSink.h/OutboundClient.h in
// this same directory.
//
// Build follow-up (deliberately not done here -- see
// tests/Makefile's own header comment for why): SyncHandshakeCore.cpp is
// NOT yet listed in ../CMakeLists.txt's add_commonlibsse_plugin(SOURCES ...)
// -- correct while nothing calls it, but a required one-line addition once
// the glue layer (SyncHandshake.h/.cpp) lands, or the pure core silently
// won't be in the shipped DLL.
//
// Judgment call, worth flagging explicitly: a HELLO RESPONSE carrying
// decision=DEGRADED (one of resolve()'s six possible outputs per spec §4,
// distinct from the shim self-assigning DEGRADED on a timeout) goes down
// OnHelloResponse's buffering branch and does NOT schedule a retry the way
// OnHelloTimeout/OnMutationSendFailed do -- spec §4.5 only mandates
// retry-on-timeout text-for-text, so this is a defensible reading, but it
// means a service-returned DEGRADED buffers outbound mutations
// indefinitely (until something else, e.g. the next kPostLoadGame/kNewGame,
// fires a fresh HELLO) rather than being treated as transient. Flagged, not
// fixed, since the spec doesn't clearly call for one behavior over the
// other here.

#include <array>
#include <cstdint>
#include <cstring>
#include <optional>
#include <string>
#include <type_traits>
#include <variant>
#include <vector>

namespace ChronicleBridge {

    // ------------------------------------------------------------------
    // §3: the manifest -- co-save binary layout and byte-exact wire shape.
    // ------------------------------------------------------------------

    // 'CHRC' -- the mandatory 4-byte magic sentinel prefixed to the co-save
    // record (spec §3). Distinct from the 'CHRN' SetUniqueID and 'TMNL'
    // record-type FourCCs (those live in the glue layer, not here) --
    // defends against a SetUniqueID collision landing a different plugin's
    // same-length record in this Load callback.
    inline constexpr std::uint32_t kManifestMagic = 0x43485243u;

    // WriteRecord('TMNL', a_version, ...)'s a_version -- the glue layer's
    // job to pass, but the pure core needs the same constant to recognize a
    // valid record during Load validation (see ValidateAndParseManifest).
    inline constexpr std::uint32_t kManifestRecordVersion = 1u;

    inline constexpr std::size_t kManifestWireSize = 68;

    // Field order matches spec §3's table exactly, with the magic sentinel
    // prefixed as that section specifies. #pragma pack(push, 1) is
    // mandatory, not stylistic: under natural alignment the first uint64_t
    // would land at offset 20 (not 8-aligned) -- v1 of this spec eyeballed
    // the byte count instead of asserting it and got 56 instead of 64
    // (missed the magic entirely: 68). Don't repeat that; the static_assert
    // below is what actually catches it.
#pragma pack(push, 1)
    struct Manifest {
        std::uint32_t magic = kManifestMagic;
        std::uint8_t  save_uuid[16] = {};        // UUIDv4, generated once per playthrough on kNewGame
        std::uint64_t generation = 0;             // ADR-0004's fork counter
        std::uint64_t parent_generation = 0;      // 0 sentinel == root generation. Converted to Python
                                                   // None at the HTTP boundary (spec §3) -- NEVER here;
                                                   // this field's raw wire value is always the sentinel.
        std::uint64_t head_seq = 0;               // last DURABLY-COMMITTED event sequence (spec §4.4) --
                                                   // written only by OnMutationAccepted below, or reset by
                                                   // OnGameRevert/OnNewGame. Never advanced speculatively.
        double        gamets = 0.0;               // bitemporal valid time (ADR-0004)
        std::int64_t  wall_ts = 0;                // bitemporal transaction time (ADR-0004), Unix MS.
                                                   // chronicle.events.Event.wall_ts is Unix SECONDS as a
                                                   // float -- the ms->s conversion happens at the HTTP
                                                   // boundary (spec §3), NEVER here or in the co-save.
        std::uint64_t char_name_hash = 0;         // display/debug only, never a lookup key
    };
#pragma pack(pop)

    static_assert(sizeof(Manifest) == kManifestWireSize,
                  "Manifest must be exactly 68 bytes (magic 4 + save_uuid 16 + 6*8) -- "
                  "spec doc §3; v1 of this spec miscounted this as 56, then 60.");
    static_assert(std::is_trivially_copyable_v<Manifest>,
                  "Manifest must be safe to copy as raw bytes -- that's the whole point of "
                  "the real WriteRecord(&manifest, sizeof(manifest)) / ReadRecordData call "
                  "the future glue layer will make.");

    // Field-by-field equality (memcmp is safe: pack(1) means no padding
    // bytes to worry about, and Manifest is trivially copyable).
    bool ManifestEquals(const Manifest& a, const Manifest& b);

    // Explicit little-endian encode/decode. Deliberately NOT relying solely
    // on "the packed struct's memory image already IS the wire format" (true
    // on this x86-64 target, and the real glue layer's WriteRecord call will
    // in fact lean on exactly that) -- this codebase's golden fixture (spec
    // §3) is also being byte-matched by an independently-written Python
    // agent, so the encoder needs to be provably endian-correct on its own
    // terms, not "correct because this box happens to be little-endian."
    // gamets's bit pattern is moved with std::memcpy into a uint64_t, never
    // a union or reinterpret_cast, to stay within defined behavior.
    std::array<std::uint8_t, kManifestWireSize> ManifestToBytes(const Manifest& m);

    // Returns false (leaving *out untouched) if the leading 4 bytes don't
    // match kManifestMagic. Does NOT check length/version/record-context --
    // those are SKSE-Load-callback-specific checks the caller performs
    // first; see ValidateAndParseManifest, which is the full §3 Load-time
    // gate this function is one piece of.
    bool ManifestFromBytes(const std::array<std::uint8_t, kManifestWireSize>& bytes, Manifest* out);

    // ------------------------------------------------------------------
    // §4: the six-way resolve() decision, as the shim sees it.
    // ------------------------------------------------------------------

    enum class SyncDecision : std::uint8_t {
        kUnknown,       // no HELLO has resolved yet this session (initial construction, or just after Revert)
        kContinue,
        kFork,          // decided by resolve(), NOT actionable in v1 (spec §4) -- server also says actionable=false
        kAdopt,         // decided by resolve(), NOT actionable in v1
        kNewTimeline,
        kLegacyImport,  // decided by resolve(), NOT actionable in v1
        kDegraded,      // resolve() itself can return this, AND the shim self-assigns it on a HELLO timeout (§4.5)
    };

    // Spec §4/§4.5, verbatim rule: "actionable: false is handled identically
    // to DEGRADED for outbound buffering purposes." kUnknown (nothing
    // resolved yet) is folded in here too -- there is nothing safe to send
    // before the first HELLO resolves either.
    constexpr bool DecisionRequiresBuffering(SyncDecision decision, bool actionable) {
        return !actionable || decision == SyncDecision::kDegraded || decision == SyncDecision::kUnknown;
    }

    // ------------------------------------------------------------------
    // Side effects -- plain data describing what the (not-yet-written) SKSE
    // glue layer should DO. Never performed by this file. Host/port/path/
    // shared-secret are OutboundClient::OutboundConfig's job, not carried
    // here -- these are the logical payloads only.
    // ------------------------------------------------------------------

    struct SendHello {
        bool manifestPresent = false;   // HELLO body's manifest_present (spec §4.1)
        Manifest manifest;               // meaningful only if manifestPresent
        std::uint64_t helloSeq = 0;      // spec §4.2's fencing value; echoed back in the response

        // The HELLO body's format_version field (the co-save record's
        // validated a_version, i.e. Manifest.format_version on the Python
        // side) -- NOT one of the 68-byte Manifest struct's seven fields
        // (spec §3: it's a WriteRecord/a_version parameter, not a struct
        // field), but the glue layer still needs it in hand to build the
        // real JSON body, since chronicle.sync.Manifest.format_version is
        // mandatory on the service side. Always kManifestRecordVersion when
        // manifestPresent is true, given ValidateAndParseManifest currently
        // only ever accepts that exact version (see SyncState::
        // currentFormatVersion's comment for the manifestPresent=false
        // case).
        std::uint32_t formatVersion = kManifestRecordVersion;
    };

    struct SendMutation {
        std::uint64_t epochId = 0;
        Manifest manifest;                // identifies the branch (save_uuid/generation) for the mutation body
        std::uint64_t seq = 0;
        double gamets = 0.0;
        std::int64_t wallTs = 0;
        std::string eventPayload;         // opaque -- the actual event JSON shape is the glue layer's job
    };

    struct WriteCoSaveRecord {
        Manifest manifest;                 // exactly what WriteRecord('TMNL', kManifestRecordVersion, ...) should persist
    };

    struct BufferMutationLocally {
        std::uint64_t seq = 0;
        double gamets = 0.0;
        std::int64_t wallTs = 0;
        std::string eventPayload;
    };

    // The oldest ring entry, evicted to make room (spec §4.5's "spilling to
    // a local file if the ring fills"). Eviction is always oldest-first so
    // replay order stays coherent across the two storage tiers: the file
    // holds the oldest overflow, the in-memory ring holds the newest N: a
    // correct full replay is "file contents, then the ring" (file replay is
    // the glue layer's own job -- this pure core never reads its own spill
    // file back).
    struct SpillMutationToFile {
        std::uint64_t seq = 0;
        double gamets = 0.0;
        std::int64_t wallTs = 0;
        std::string eventPayload;
    };

    // Revert's unconditional spill-file rotation/delete (spec §4.5/§5) --
    // "not just the in-memory ring." Emitted every time OnGameRevert runs,
    // whether or not a spill file actually exists; rotating a nonexistent
    // file is expected to be a cheap no-op for the glue layer.
    struct RotateSpillFile {};

    struct ScheduleHelloRetryBackoff {
        std::uint64_t helloSeq = 0;   // the hello_seq the eventual retry attempt will use once it fires
    };

    // Cancels a previously-scheduled backoff retry (spec §4.2: "cancel it on
    // kPreLoadGame/Revert ... rather than allowed to fire mid-new-load").
    struct CancelScheduledHelloRetry {};

    struct LogWarning { std::string message; };
    struct LogInfo { std::string message; };

    // §4.6: confirm_required is notification-only in v1 -- no blocking
    // dialog, no "decline" branch (nothing has been specified for one to
    // do). Exact copy is a UX decision outside this spec.
    struct NotifyPlayerNonModal { std::string message; };

    using SyncSideEffect = std::variant<
        SendHello,
        SendMutation,
        WriteCoSaveRecord,
        BufferMutationLocally,
        SpillMutationToFile,
        RotateSpillFile,
        ScheduleHelloRetryBackoff,
        CancelScheduledHelloRetry,
        LogWarning,
        LogInfo,
        NotifyPlayerNonModal>;

    using SyncSideEffects = std::vector<SyncSideEffect>;

    // ------------------------------------------------------------------
    // State.
    // ------------------------------------------------------------------

    // spec §4.5: "bounded ring buffer" -- no capacity value is given by the
    // spec itself (§8b's open-questions list is about the HELLO timeout and
    // the large-jump threshold, not this). Picked here as a judgment call;
    // trivially tunable later, nothing else in this file depends on the
    // exact value.
    inline constexpr std::size_t kOutboundRingCapacity = 64;

    // spec §4.1's "small threshold in a short window" for re-firing HELLO
    // after repeated 409s -- the "short window" clause needs a time source
    // this pure core deliberately doesn't have (no OnMutationRejected
    // parameter carries a clock reading); implemented here as a plain
    // counter, reset whenever a HELLO is (re-)fired. Judgment call --
    // documented, not silently dropped; a real time window is easy to layer
    // on top in the glue layer later if 8b's open questions get resolved.
    inline constexpr std::uint32_t kMutation409ReHelloThreshold = 3;

    struct QueuedMutation {
        std::uint64_t seq = 0;
        double gamets = 0.0;
        std::int64_t wallTs = 0;
        std::string eventPayload;
    };

    struct SyncState {
        // g_isLoading -- true only inside a kPreLoadGame..HELLO-resolved-or-
        // timeout window (spec §4.1 "g_isLoading clears anyway after a
        // bounded timeout", §4.5). Deliberately NOT forced true by
        // OnGameRevert (see that transition's comment) -- D3: Revert also
        // fires on quit-to-main-menu with no subsequent load.
        bool isLoading = false;

        // spec §4.2: bumped on EVERY HELLO send -- OnPostLoadGame,
        // OnNewGame, a fired backoff retry (OnHelloBackoffFire), a 409-
        // threshold re-fire (OnMutationRejected), AND OnGameRevert (see
        // that transition's comment for why Revert needs this too, beyond
        // what §4.2's text literally lists).
        std::uint64_t helloSeq = 0;

        // DEGRADED backoff-retry scheduling flag -- cancelled (and this set
        // false) on OnPreLoadGame/OnGameRevert per §4.2/§4.5.
        bool helloRetryScheduled = false;

        SyncDecision decision = SyncDecision::kUnknown;
        bool actionable = false;

        // Written ONLY by OnHelloResponse (the single-writer discipline
        // spec §2/§4.4 calls for -- this is the one field only a real
        // network response may set), or reset to 0 by OnGameRevert/
        // OnNewGame/construction. No other transition below writes this.
        std::uint64_t epochId = 0;

        // HELLO body's manifest_present (spec §4.1): false = no co-save
        // record found (pre-feature save, or the pairing was lost), OR
        // Revert just ran and nothing has loaded/started since.
        bool manifestPresent = false;

        // currentManifest.head_seq/gamets/wall_ts ARE the "committed" state
        // (spec §4.4: ACK is commit, full stop -- no separate volatile
        // buffer exists to track). Written by: OnLoadCallback (a faithful
        // hydration from disk, not a live advance), OnNewGame/OnGameRevert
        // (a hardcoded reset to defaults), and OnMutationAccepted (the ONE
        // transition allowed to advance head_seq/gamets/wall_ts based on
        // live traffic -- see that transition's comment). No other
        // transition writes into this struct.
        Manifest currentManifest;

        // The format_version that validated alongside currentManifest --
        // mirrors currentManifest's own write sites exactly (OnLoadCallback
        // on success writes the observed, validated record.version; every
        // reset site -- construction, OnNewGame, OnGameRevert, and
        // OnLoadCallback's own failure branch -- writes kManifestRecordVersion,
        // this build's own current version, since there is no co-save value
        // to report once manifestPresent is false. Not stored in Manifest
        // itself (spec §3: format_version is an a_version/WriteRecord
        // parameter, not one of the struct's seven fields) but a real SKSE
        // glue layer needs this value in hand to build the actual HELLO
        // JSON body, since chronicle.sync.Manifest.format_version is
        // mandatory on the service side -- found missing during Python-side
        // integration, added here to close that gap.
        std::uint32_t currentFormatVersion = kManifestRecordVersion;

        // §4.1 shim-side 409 handling -- see kMutation409ReHelloThreshold.
        std::uint32_t mutation409Count = 0;

        // Newest kOutboundRingCapacity buffered-but-not-yet-sent mutations,
        // oldest first. Overflow evicts the front (oldest) via
        // SpillMutationToFile. Cleared on successful HELLO resolution
        // (replayed first, oldest to newest) and on OnGameRevert (dropped,
        // per §4.5/§5 -- "anything still queued was never committed").
        std::vector<QueuedMutation> outboundRing;
    };

    // ------------------------------------------------------------------
    // Events (transition inputs).
    // ------------------------------------------------------------------

    // What the SKSE Load callback observed, translated to plain data. The
    // four-way validation this feeds (declared length == 68, magic ==
    // kManifestMagic, version == kManifestRecordVersion, actual-read length
    // == 68) is spec §3's exact rule: "reject the record unless ... AND
    // ReadRecordData's own return value also equals 68" -- checking only
    // GetNextRecordInfo's reported length and not the actual bytes read is
    // an easy way to silently accept a truncated read, which is why both
    // lengths are separate fields here rather than one.
    struct LoadRecordInfo {
        bool recordFound = false;                                    // OpenRecord/GetNextRecordInfo found anything at all
        std::uint32_t declaredLength = 0;                             // GetNextRecordInfo's reported length
        std::uint32_t version = 0;                                    // GetNextRecordInfo's reported a_version
        std::array<std::uint8_t, kManifestWireSize> rawBytes{};       // meaningful only if declaredLength == 68
        std::uint32_t actualReadLength = 0;                           // ReadRecordData's own return value
    };

    // The /whiterun/sync/hello response, already decoded to plain types --
    // JSON parsing of the wire response is glue-layer work (out of scope
    // here, see this file's header comment).
    struct HelloResponse {
        std::uint64_t helloSeq = 0;                       // echoes the request's hello_seq -- the §4.2 staleness key
        SyncDecision decision = SyncDecision::kUnknown;
        bool actionable = false;
        std::uint64_t epochId = 0;
        std::optional<std::uint64_t> replayFromSeq;        // §4.4: service-side bookkeeping ONLY -- the shim never acts on this
        bool confirmRequired = false;
    };

    // One generated event ready to go out -- this IS the D1 "drain" gate's
    // input: the transition below decides send-now vs. buffer based on
    // current isLoading/decision/actionable, so callers don't need to gate
    // per-sink themselves.
    struct MutationEvent {
        std::uint64_t seq = 0;
        double gamets = 0.0;
        std::int64_t wallTs = 0;
        std::string eventPayload;
    };

    // What actually got committed, per a mutation POST's 2xx response.
    // Deliberately just an ECHO of what OnMutationReady already sent for
    // this seq (see MutationEvent above) -- not a second, independent read
    // of live game state. That's what makes D5's "same atomic read, sampled
    // once" requirement true by construction here: there is only ever one
    // place (whatever built the original MutationEvent) that samples
    // gamets/wall_ts for a given seq.
    struct MutationCommitInfo {
        std::uint64_t seq = 0;
        double gamets = 0.0;
        std::int64_t wallTs = 0;
    };

    // ------------------------------------------------------------------
    // The transition function itself.
    // ------------------------------------------------------------------

    struct SyncTransitionResult {
        SyncState state;
        SyncSideEffects effects;
    };

    // Fires on SKSE::MessagingInterface kPreLoadGame. Marks a load as
    // starting and cancels any in-flight DEGRADED backoff retry (spec
    // §4.2) so it can't land mid-new-load.
    SyncTransitionResult OnPreLoadGame(SyncState state);

    // Fires from the SerializationInterface Load callback (NOT a messaging
    // event -- spec §1). Validates and, if valid, parses the manifest; on
    // ANY validation failure, treats this as "no manifest" (manifestPresent
    // = false, currentManifest left at defaults) -- the spec's LEGACY_IMPORT
    // fall-through is a server-side resolve() decision, not something this
    // transition decides itself. Does NOT fire HELLO (see OnPostLoadGame)
    // and does NOT touch epochId (the manifest carries no epoch_id field).
    SyncTransitionResult OnLoadCallback(SyncState state, const LoadRecordInfo& record);

    // Fires on kPostLoadGame -- the engine has finished loading; THIS is
    // where HELLO actually fires (spec §1: never from inside the Load
    // callback itself). Bumps hello_seq and emits SendHello.
    SyncTransitionResult OnPostLoadGame(SyncState state);

    // Fires when the sender thread gets a HELLO response. Discards (no
    // state change at all) if response.helloSeq doesn't match the current
    // hello_seq (spec §4.2's fencing). Otherwise this is the single writer
    // of epochId, and -- if the resolved decision no longer requires
    // buffering -- replays anything queued in outboundRing, oldest first,
    // then clears it.
    SyncTransitionResult OnHelloResponse(SyncState state, const HelloResponse& response);

    // Fires when the sender thread's blocking HELLO POST times out with no
    // response (spec §2: the httplib call itself blocks up to the HELLO
    // timeout; there is no separate scheduled-timer side effect for this).
    // Discards (no state change) if timedOutHelloSeq doesn't match the
    // current hello_seq. Otherwise self-assigns DEGRADED and schedules a
    // backoff retry.
    SyncTransitionResult OnHelloTimeout(SyncState state, std::uint64_t timedOutHelloSeq);

    // Fires when a previously-scheduled DEGRADED backoff retry actually
    // fires. No-ops (empty effects, unchanged state) if
    // helloRetryScheduled is already false -- i.e. it was cancelled by a
    // later kPreLoadGame/Revert (spec §4.2's "cancel it ... rather than
    // allowed to fire mid-new-load") and this is a straggling timer call.
    SyncTransitionResult OnHelloBackoffFire(SyncState state);

    // Fires on kNewGame. Spec §4.2 (B4's fix): kNewGame sends HELLO too,
    // unconditionally -- resolve()'s NEW_TIMELINE row already handles
    // "service has never seen this save_uuid" correctly, so there's no
    // special-casing here. Resets the manifest to a fresh one carrying the
    // caller-supplied save_uuid (generation/parent_generation/head_seq all
    // start at 0 -- a brand new playthrough has no prior history to carry
    // forward, so this is a hardcoded reset, not an "advance"). UUID
    // generation itself is NOT done here -- true randomness is impure, so
    // the caller (glue layer) generates it and passes it in.
    SyncTransitionResult OnNewGame(SyncState state, const std::array<std::uint8_t, 16>& newSaveUuid);

    // Fires on kSaveGame. Emits exactly the current currentManifest for the
    // glue layer to WriteRecord -- never re-derives head_seq from anything
    // else (D5).
    SyncTransitionResult OnSaveGame(SyncState state);

    // The drain point (D1): one generated mutation event, ready to go out.
    // Sends immediately if !isLoading && the current decision/actionable
    // don't require buffering; otherwise enqueues into outboundRing
    // (evicting+spilling the oldest entry first if the ring is full).
    SyncTransitionResult OnMutationReady(SyncState state, const MutationEvent& event);

    // Fires on a mutation POST's 2xx response -- the commit point (spec
    // §4.4). The ONE transition (besides OnLoadCallback's hydration and
    // OnGameRevert/OnNewGame's resets) allowed to write
    // currentManifest.head_seq/gamets/wall_ts.
    SyncTransitionResult OnMutationAccepted(SyncState state, const MutationCommitInfo& info);

    // Fires on a mutation POST's 409 response. Drops the event (it belongs
    // to an epoch this session has moved past -- spec §4.1), logs, and
    // counts toward kMutation409ReHelloThreshold; crossing it re-fires
    // HELLO (possible epoch desync) rather than looping silently.
    SyncTransitionResult OnMutationRejected(SyncState state, std::uint64_t epochAtSend, std::uint64_t seq);

    // Fires when a mutation POST fails outright -- connection refused,
    // timeout, or a 5xx -- rather than returning 2xx or 409. Spec §2's
    // synchronous httplib::Result has exactly these three outcomes; the
    // spec's §4.1/§4.4 text only walks through the first two. Without this
    // transition a mid-session service outage would silently drop every
    // subsequent mutation with no buffering and no DEGRADED signal, which
    // is worse than either named outcome. Judgment call, documented at the
    // .cpp definition: treated like a HELLO timeout -- the event is
    // buffered (through the same ring/spill path as OnMutationReady's
    // buffering branch, never dropped) and the shim self-assigns DEGRADED
    // with a HELLO retry scheduled, unless one is already pending.
    SyncTransitionResult OnMutationSendFailed(SyncState state, const MutationEvent& event);

    // Fires on the SerializationInterface Revert callback -- "between
    // kPreLoadGame and the Load callback" per spec §5, but ALSO on quit-to-
    // main-menu with no subsequent load, and NEVER on the very first load
    // after process start (D3's correction to v1's reasoning: initial-state
    // cleanliness comes from SyncState's own default member initializers,
    // not from assuming Revert always runs first). Resets
    // decision/actionable/epochId/manifest/currentManifest to defaults,
    // drops outboundRing, and unconditionally requests a spill-file
    // rotation (§4.5: "not just the in-memory ring"). Does NOT force
    // isLoading true/false -- leaves it exactly as it was (see field
    // comment). DOES bump hello_seq -- see the .cpp for why this goes
    // beyond §4.2's literal text.
    SyncTransitionResult OnGameRevert(SyncState state);

    // kDeleteGame (also listed in spec §5's plugin.cpp wiring) is
    // deliberately NOT modeled here: deleting a save file on disk has no
    // bearing on the CURRENTLY LOADED session's sync state -- the manifest
    // already in memory is unaffected, and a future attempt to load the
    // now-deleted save is already handled by OnLoadCallback's
    // record-not-found path. It is pure SKSE-glue plumbing (just don't
    // forward it into any handler here), not a sync-handshake transition.

}  // namespace ChronicleBridge
