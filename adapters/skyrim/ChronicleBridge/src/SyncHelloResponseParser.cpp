#include "SyncHelloResponseParser.h"

#include <cctype>
#include <cstdlib>

// See SyncHelloResponseParser.h's header comment for what this file is and
// is not -- the one genuinely new hand-rolled parsing component this lane
// needs, factored out purely so it's testable without the SKSE SDK.
//
// Deliberately does NOT use <format> (unlike OutboundClient.cpp's own
// ParseJson*Field parsers, which this file otherwise mirrors byte-for-byte)
// -- this file must also compile with the plain g++/clang++ the standalone
// tests/ harness uses (this codebase's own g++ 11 test environment has no
// <format> support at all; the real plugin's MSVC/vcpkg toolchain does, but
// this file can't assume it). Plain std::string concatenation instead --
// functionally identical, zero toolchain-version risk.

namespace ChronicleBridge {

    // Byte-for-byte the same narrow parser OutboundClient.cpp's own
    // ParseJsonStringField implements -- see this file's header comment for
    // why it's duplicated rather than shared.
    std::optional<std::string> ParseJsonStringField(std::string_view body, std::size_t& pos, std::string_view key) {
        auto keyPos = body.find(("\"" + std::string(key) + "\""), pos);
        if (keyPos == std::string_view::npos) return std::nullopt;
        auto colon = body.find(':', keyPos);
        if (colon == std::string_view::npos) return std::nullopt;
        auto quoteStart = body.find('"', colon);
        if (quoteStart == std::string_view::npos) return std::nullopt;

        std::string value;
        std::size_t i = quoteStart + 1;
        for (; i < body.size() && body[i] != '"'; ++i) {
            if (body[i] == '\\' && i + 1 < body.size()) {
                ++i;
                switch (body[i]) {
                    case 'n': value += '\n'; break;
                    case 't': value += '\t'; break;
                    case 'r': value += '\r'; break;
                    case '"': value += '"'; break;
                    case '\\': value += '\\'; break;
                    default: value += body[i]; break;
                }
            } else {
                value += body[i];
            }
        }
        if (i >= body.size()) return std::nullopt;  // unterminated string.
        pos = i + 1;
        return value;
    }

    // Byte-for-byte the same narrow parser as OutboundClient.cpp's own
    // ParseJsonBoolField.
    std::optional<bool> ParseJsonBoolField(std::string_view body, std::size_t& pos, std::string_view key) {
        auto keyPos = body.find(("\"" + std::string(key) + "\""), pos);
        if (keyPos == std::string_view::npos) return std::nullopt;
        auto colon = body.find(':', keyPos);
        if (colon == std::string_view::npos) return std::nullopt;

        std::size_t i = colon + 1;
        while (i < body.size() && (body[i] == ' ' || body[i] == '\t')) ++i;
        if (body.compare(i, 4, "true") == 0) {
            pos = i + 4;
            return true;
        }
        if (body.compare(i, 5, "false") == 0) {
            pos = i + 5;
            return false;
        }
        return std::nullopt;
    }

    std::optional<std::uint64_t> ParseJsonUint64Field(std::string_view body, std::size_t& pos, std::string_view key) {
        auto keyPos = body.find(("\"" + std::string(key) + "\""), pos);
        if (keyPos == std::string_view::npos) return std::nullopt;
        auto colon = body.find(':', keyPos);
        if (colon == std::string_view::npos) return std::nullopt;

        std::size_t i = colon + 1;
        while (i < body.size() && (body[i] == ' ' || body[i] == '\t')) ++i;
        std::size_t start = i;
        while (i < body.size() && std::isdigit(static_cast<unsigned char>(body[i]))) ++i;
        if (i == start) return std::nullopt;  // no digits at all -- covers a stray `-` too (uint64 has no sign).

        try {
            std::uint64_t value = std::stoull(std::string(body.substr(start, i - start)));
            pos = i;
            return value;
        } catch (...) {
            return std::nullopt;
        }
    }

    JsonNullableUint64Field ParseJsonNullableUint64Field(std::string_view body, std::size_t& pos, std::string_view key) {
        JsonNullableUint64Field out;

        auto keyPos = body.find(("\"" + std::string(key) + "\""), pos);
        if (keyPos == std::string_view::npos) return out;  // kMissingOrMalformed
        auto colon = body.find(':', keyPos);
        if (colon == std::string_view::npos) return out;

        std::size_t i = colon + 1;
        while (i < body.size() && (body[i] == ' ' || body[i] == '\t')) ++i;

        if (body.compare(i, 4, "null") == 0) {
            out.kind = JsonNullableFieldKind::kNull;
            pos = i + 4;
            return out;
        }

        std::size_t start = i;
        while (i < body.size() && std::isdigit(static_cast<unsigned char>(body[i]))) ++i;
        if (i == start) return out;  // kMissingOrMalformed -- neither `null` nor a digit run.

        try {
            out.value = std::stoull(std::string(body.substr(start, i - start)));
            out.kind = JsonNullableFieldKind::kValue;
            pos = i;
        } catch (...) {
            out.kind = JsonNullableFieldKind::kMissingOrMalformed;
        }
        return out;
    }

    std::optional<SyncDecision> ParseSyncDecisionString(std::string_view value) {
        if (value == "CONTINUE") return SyncDecision::kContinue;
        if (value == "FORK") return SyncDecision::kFork;
        if (value == "ADOPT") return SyncDecision::kAdopt;
        if (value == "NEW_TIMELINE") return SyncDecision::kNewTimeline;
        if (value == "LEGACY_IMPORT") return SyncDecision::kLegacyImport;
        if (value == "DEGRADED") return SyncDecision::kDegraded;
        // Deliberately no case for "UNKNOWN" or anything else -- see this
        // function's header comment.
        return std::nullopt;
    }

    std::optional<HelloResponse> ParseSyncHelloResponseJson(std::string_view body) {
        std::size_t pos = 0;
        auto decisionStr = ParseJsonStringField(body, pos, "decision");
        if (!decisionStr) return std::nullopt;
        auto decision = ParseSyncDecisionString(*decisionStr);
        if (!decision) return std::nullopt;  // unrecognized decision string -- fail loudly, never silently accept.

        pos = 0;
        auto actionable = ParseJsonBoolField(body, pos, "actionable");
        if (!actionable) return std::nullopt;

        pos = 0;
        auto epochId = ParseJsonUint64Field(body, pos, "epoch_id");
        if (!epochId) return std::nullopt;

        pos = 0;
        auto replayFromSeq = ParseJsonNullableUint64Field(body, pos, "replay_from_seq");
        if (replayFromSeq.kind == JsonNullableFieldKind::kMissingOrMalformed) return std::nullopt;

        pos = 0;
        auto confirmRequired = ParseJsonBoolField(body, pos, "confirm_required");
        if (!confirmRequired) return std::nullopt;

        pos = 0;
        auto helloSeq = ParseJsonUint64Field(body, pos, "hello_seq");
        if (!helloSeq) return std::nullopt;

        HelloResponse response;
        response.helloSeq = *helloSeq;
        response.decision = *decision;
        response.actionable = *actionable;
        response.epochId = *epochId;
        response.replayFromSeq = (replayFromSeq.kind == JsonNullableFieldKind::kValue)
                                      ? std::optional<std::uint64_t>(replayFromSeq.value)
                                      : std::nullopt;
        response.confirmRequired = *confirmRequired;
        return response;
    }

}  // namespace ChronicleBridge
