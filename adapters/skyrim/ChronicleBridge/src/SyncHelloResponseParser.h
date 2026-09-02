#pragma once

// Pure, SKSE-independent HELLO *response* parser -- factored out of
// OutboundClient.cpp (which needs SKSE/httplib headers via
// OutboundClient.h's own includes, e.g. SpatialStreamer.h's RE::FormID, and
// so can't be included by the plain-g++ standalone tests/ harness) so this
// genuinely new hand-rolled component gets the same test coverage
// SyncHandshakeCore.h/.cpp already gets. The sync-wiring plan's own
// Verification section calls this out explicitly: "the HELLO response
// parser ... is the one genuinely new hand-rolled component in this lane,
// and it's plain string/JSON parsing -- it can and must be unit-tested on
// Linux with no SKSE SDK, using the exact same pattern as the existing
// tests/test_sync_handshake_core.cpp/tests/Makefile harness."
//
// Same "hand-rolled, narrow-purpose parser, not a general JSON library"
// caveat every parser in OutboundClient.cpp already carries (see that
// file's EscapeJsonString comment): this parses exactly one known response
// shape (docs/design/chronicle-bridge-sync-handshake-out.md §4.1) and is
// not meant to grow into a general parser. The string/bool field parsers
// below are deliberately DUPLICATED from OutboundClient.cpp's
// ParseJsonStringField/ParseJsonBoolField rather than shared -- sharing
// would mean OutboundClient.cpp exporting them, which doesn't fix the
// underlying problem (OutboundClient.h transitively pulls in SKSE headers
// either way). Small, narrow, easy-to-eyeball duplication is the price of
// keeping this file genuinely SKSE-free.
//
// Depends only on SyncHandshakeCore.h (also SKSE-independent by
// construction) for the HelloResponse/SyncDecision types this produces.
// OutboundClient.cpp's PostSyncHello is the one real (non-test) caller.

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>

#include "SyncHandshakeCore.h"

namespace ChronicleBridge {

    // Same narrow contract as OutboundClient.cpp's ParseJsonStringField/
    // ParseJsonBoolField -- see this file's header comment for why these are
    // duplicated here rather than shared.
    std::optional<std::string> ParseJsonStringField(std::string_view body, std::size_t& pos, std::string_view key);
    std::optional<bool> ParseJsonBoolField(std::string_view body, std::size_t& pos, std::string_view key);

    // Non-nullable, per-field uint64 parser -- HELLO's epoch_id/hello_seq
    // fields are always present in a well-formed response (only
    // replay_from_seq is nullable; see ParseJsonNullableUint64Field below).
    // No leading-'-' handling, unlike OutboundClient.cpp's ParseJsonIntField
    // -- a uint64 field has no valid negative representation.
    std::optional<std::uint64_t> ParseJsonUint64Field(std::string_view body, std::size_t& pos, std::string_view key);

    enum class JsonNullableFieldKind : std::uint8_t {
        kMissingOrMalformed,  // key not found, or the value is neither `null` nor a parseable non-negative integer
        kNull,                // the JSON literal `null`
        kValue,               // a parsed, present value
    };

    struct JsonNullableUint64Field {
        JsonNullableFieldKind kind = JsonNullableFieldKind::kMissingOrMalformed;
        std::uint64_t value = 0;  // meaningful only when kind == kValue
    };

    // ParseJsonUint64Field's pattern, extended to check for a literal
    // `null` before attempting to parse a number -- the one genuinely new
    // parser primitive this lane needs (spec §4.1's replay_from_seq: <uint64
    // | null>), per the sync-wiring plan's design decision 6.
    JsonNullableUint64Field ParseJsonNullableUint64Field(std::string_view body, std::size_t& pos, std::string_view key);

    // Maps the wire `decision` string to SyncDecision exactly (spec §4.1's
    // six literal values: CONTINUE, FORK, ADOPT, NEW_TIMELINE,
    // LEGACY_IMPORT, DEGRADED). Deliberately does NOT accept "UNKNOWN" or
    // any other string -- kUnknown is a shim-side-only sentinel
    // (SyncState's own initial/reset value), never a value the service is
    // expected to send on the wire. An unrecognized string must fail loudly
    // here (design decision 6: "must also fail-and-log loudly, never
    // silently default to some kUnknown acceptance"), not silently
    // normalize to it.
    std::optional<SyncDecision> ParseSyncDecisionString(std::string_view value);

    // The full /whiterun/sync/hello response, decoded (spec §4.1):
    // {"decision": str, "actionable": bool, "epoch_id": uint64,
    // "replay_from_seq": uint64|null, "confirm_required": bool, "hello_seq":
    // uint64}. Returns std::nullopt on ANY missing/malformed required field,
    // or an unrecognized `decision` string -- see this file's header
    // comment: a HELLO response must fail-and-log loudly at the call site
    // (OutboundClient.cpp's PostSyncHello), never silently accept an
    // unparseable or unrecognized body.
    std::optional<HelloResponse> ParseSyncHelloResponseJson(std::string_view body);

}  // namespace ChronicleBridge
