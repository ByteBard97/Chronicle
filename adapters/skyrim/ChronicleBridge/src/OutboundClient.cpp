#include "OutboundClient.h"

#include <httplib.h>

#include <cctype>
#include <cmath>
#include <format>
#include <sstream>

namespace ChronicleBridge {

    namespace {

        // Full JSON string escaping (RFC 8259 §7) -- deliberately not pulling
        // in a JSON library for a 3-field payload (see this file's header
        // comment and the design doc's dependency-minimalism note), but this
        // must still produce spec-conformant output: a raw, unescaped control
        // character (< 0x20) inside a JSON string is not valid JSON. A
        // hand-rolled writer that only escapes `"`/`\` and lets control
        // characters through is a real parser/validator differential --
        // Python's own stdlib `json.loads` tolerates plenty a strict decoder
        // won't, and pydantic-core (what the listener actually validates
        // against, per PositionSnapshot.model_validate_json) does not. Every
        // id this plugin actually produces today (a Chronicle npc_id, or
        // "<plugin>:<hex>") happens not to contain one, but a plugin filename
        // is not a value this code should trust to stay that way.
        std::string EscapeJsonString(std::string_view s) {
            std::string out;
            out.reserve(s.size() + 2);
            for (unsigned char c : s) {
                switch (c) {
                    case '"':
                        out += "\\\"";
                        break;
                    case '\\':
                        out += "\\\\";
                        break;
                    case '\b':
                        out += "\\b";
                        break;
                    case '\f':
                        out += "\\f";
                        break;
                    case '\n':
                        out += "\\n";
                        break;
                    case '\r':
                        out += "\\r";
                        break;
                    case '\t':
                        out += "\\t";
                        break;
                    default:
                        if (c < 0x20) {
                            out += std::format("\\u{:04x}", static_cast<unsigned>(c));
                        } else {
                            out += static_cast<char>(c);
                        }
                }
            }
            return out;
        }

        // JSON has no token for NaN/Infinity (RFC 8259 §6 defines `number`
        // strictly as decimal digits) -- `std::format("{}", ...)` would
        // happily emit the literal text `nan`/`inf`/`-inf`, which is not
        // valid JSON at all. This is the other half of the same
        // parser/validator-differential class as the string-escaping fix
        // above: CPython's `json.loads` non-conformantly accepts bare
        // `NaN`/`Infinity`/`-Infinity` by default, but pydantic-core (the
        // listener's actual parser) does not, so a non-finite value here
        // would make every subsequent snapshot silently fail validation
        // until the game state producing it changed. Emit `0` instead --
        // wrong is a broken position for one tick, not a payload the
        // listener rejects wholesale.
        double SanitizeFinite(double value) { return std::isfinite(value) ? value : 0.0; }

        // Matches adapters/skyrim/contracts/chronicle-bridge.openapi.yaml's
        // PositionSnapshot schema exactly -- field-for-field, same order isn't
        // required by JSON but kept matching the spec for readability.
        std::string BuildPositionSnapshotJson(double wallTimestamp, const std::vector<NpcPosition>& npcs) {
            std::ostringstream body;
            body << std::format(R"({{"wall_ts":{},"npcs":[)", SanitizeFinite(wallTimestamp));
            for (std::size_t i = 0; i < npcs.size(); ++i) {
                if (i > 0) body << ',';
                body << std::format(R"({{"id":"{}","name":"{}","x":{},"y":{}}})", EscapeJsonString(npcs[i].id),
                                     EscapeJsonString(npcs[i].name), SanitizeFinite(npcs[i].x),
                                     SanitizeFinite(npcs[i].y));
            }
            body << "]}";
            return body.str();
        }

        // Matches chronicle-bridge.openapi.yaml's GameEvent schema exactly.
        // `event_type` is always the literal "npc_died" -- this slice has
        // no other event kind (design doc §2). Optional fields
        // (killer_id/location_id) serialize as JSON null, not an omitted
        // key, matching the schema's `type: [string, "null"]`.
        std::string BuildGameEventJson(const PendingGameEvent& event) {
            std::ostringstream body;
            body << std::format(
                R"({{"event_type":"npc_died","gamets":{},"wall_ts":{},"npc_id":"{}","cause":"{}","killer_id":)",
                SanitizeFinite(event.gamets), SanitizeFinite(event.wallTs), EscapeJsonString(event.npcId),
                EscapeJsonString(event.cause));
            if (event.killerId) {
                body << std::format(R"("{}")", EscapeJsonString(*event.killerId));
            } else {
                body << "null";
            }
            body << ",\"location_id\":";
            if (event.locationId) {
                body << std::format(R"("{}")", EscapeJsonString(*event.locationId));
            } else {
                body << "null";
            }
            body << "}";
            return body.str();
        }

        // Hand-rolled parser for exactly one known, narrow shape: a JSON
        // array of flat 3-field objects, `[{"holder_id":"...",
        // "target_id":"...","relationship_rank":-2}, ...]` -- the listener's
        // GET /whiterun/hydration response (adapters/skyrim/listener/
        // listener.py's _hydration_pairs). Same reasoning as
        // EscapeJsonString above: this file deliberately has no JSON
        // library for a payload this small. This is NOT a general JSON
        // parser -- it has no recursion, no nesting support, no support for
        // any shape other than this exact one, and it is not meant to grow
        // into one. If the response shape ever changes, this function
        // should be rewritten for the new shape, not generalized.
        //
        // Tolerates the two things std::format-based emission on the Python
        // side can actually produce for these three fields: string values
        // with `\"`/`\\` escapes (mirrors EscapeJsonString's own escape
        // set -- holder_id/target_id are Chronicle npc_ids, never expected
        // to contain more exotic control characters, but handled anyway
        // since escaping is cheap), and plain (possibly negative) integers
        // for relationship_rank. Any object that doesn't parse cleanly is
        // skipped, not fatal -- one malformed entry must not lose every
        // other pair in the same response.
        std::optional<std::string> ParseJsonStringField(std::string_view body, std::size_t& pos, std::string_view key) {
            auto keyPos = body.find(std::format(R"("{}")", key), pos);
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

        std::optional<int> ParseJsonIntField(std::string_view body, std::size_t& pos, std::string_view key) {
            auto keyPos = body.find(std::format(R"("{}")", key), pos);
            if (keyPos == std::string_view::npos) return std::nullopt;
            auto colon = body.find(':', keyPos);
            if (colon == std::string_view::npos) return std::nullopt;

            std::size_t i = colon + 1;
            while (i < body.size() && (body[i] == ' ' || body[i] == '\t')) ++i;
            std::size_t start = i;
            if (i < body.size() && body[i] == '-') ++i;
            while (i < body.size() && std::isdigit(static_cast<unsigned char>(body[i]))) ++i;
            if (i == start) return std::nullopt;

            try {
                int value = std::stoi(std::string(body.substr(start, i - start)));
                pos = i;
                return value;
            } catch (...) {
                return std::nullopt;
            }
        }

        std::vector<HydrationPair> ParseHydrationPairsJson(std::string_view body) {
            std::vector<HydrationPair> out;
            std::size_t pos = 0;
            while (true) {
                auto objStart = body.find('{', pos);
                if (objStart == std::string_view::npos) break;
                auto objEnd = body.find('}', objStart);
                if (objEnd == std::string_view::npos) break;

                std::size_t fieldPos = objStart;
                auto holderId = ParseJsonStringField(body, fieldPos, "holder_id");
                fieldPos = objStart;
                auto targetId = ParseJsonStringField(body, fieldPos, "target_id");
                fieldPos = objStart;
                auto rank = ParseJsonIntField(body, fieldPos, "relationship_rank");

                if (holderId && targetId && rank) {
                    out.push_back(HydrationPair{.holderId = *holderId, .targetId = *targetId, .relationshipRank = *rank});
                } else {
                    SKSE::log::warn("ChronicleBridge: skipping unparseable hydration pair object");
                }

                pos = objEnd + 1;
            }
            return out;
        }

    }  // namespace

    std::vector<HydrationPair> FetchHydrationPairs(const OutboundConfig& config) {
        httplib::Client client(config.host, config.port);
        client.set_connection_timeout(1);
        client.set_write_timeout(1);
        client.set_read_timeout(1);

        httplib::Headers headers;
        if (config.sharedSecret) {
            headers.emplace("X-Chronicle-Bridge-Token", *config.sharedSecret);
        }
        auto result = client.Get(config.hydrationPath, headers);

        if (!result) {
            SKSE::log::warn("ChronicleBridge: GET {}:{}{} failed: {}", config.host, config.port, config.hydrationPath,
                             httplib::to_string(result.error()));
            return {};
        }
        if (result->status < 200 || result->status >= 300) {
            // 503 specifically means "the listener wasn't started with
            // --live-run" (listener.py's own gating convention, matching
            // /whiterun/events) -- an expected, common, non-error steady
            // state for any session not deliberately targeting a live run
            // (design doc §3b: "never default-enabled against a
            // fixture/demo run"). Logging that at warn every ~8s for the
            // life of such a session would be pure noise; trace it instead.
            // Any other non-2xx status is unexpected and stays at warn.
            if (result->status == 503) {
                SKSE::log::trace("ChronicleBridge: GET {}:{}{} returned 503 (no --live-run configured)", config.host,
                                  config.port, config.hydrationPath);
            } else {
                SKSE::log::warn("ChronicleBridge: GET {}:{}{} returned status {}", config.host, config.port,
                                 config.hydrationPath, result->status);
            }
            return {};
        }
        return ParseHydrationPairsJson(result->body);
    }

    bool PostGameEvent(const OutboundConfig& config, const PendingGameEvent& event) {
        httplib::Client client(config.host, config.port);
        client.set_connection_timeout(1);
        client.set_write_timeout(1);
        client.set_read_timeout(1);

        const auto body = BuildGameEventJson(event);
        httplib::Headers headers;
        if (config.sharedSecret) {
            headers.emplace("X-Chronicle-Bridge-Token", *config.sharedSecret);
        }
        auto result = client.Post(config.eventsPath, headers, body, "application/json");

        if (!result) {
            SKSE::log::warn("ChronicleBridge: POST to {}:{}{} failed: {}", config.host, config.port, config.eventsPath,
                             httplib::to_string(result.error()));
            return false;
        }
        if (result->status < 200 || result->status >= 300) {
            SKSE::log::warn("ChronicleBridge: POST to {}:{}{} returned status {}", config.host, config.port,
                             config.eventsPath, result->status);
            return false;
        }
        return true;
    }

    bool PostPositionSnapshot(const OutboundConfig& config, double wallTimestamp, const std::vector<NpcPosition>& npcs) {
        httplib::Client client(config.host, config.port);
        client.set_connection_timeout(1);  // seconds -- never let a slow/unreachable listener stall the sampling task.
        client.set_write_timeout(1);
        client.set_read_timeout(1);

        const auto body = BuildPositionSnapshotJson(wallTimestamp, npcs);
        httplib::Headers headers;
        if (config.sharedSecret) {
            headers.emplace("X-Chronicle-Bridge-Token", *config.sharedSecret);
        }
        auto result = client.Post(config.path, headers, body, "application/json");

        if (!result) {
            SKSE::log::warn("ChronicleBridge: POST to {}:{}{} failed: {}", config.host, config.port, config.path,
                             httplib::to_string(result.error()));
            return false;
        }
        if (result->status < 200 || result->status >= 300) {
            SKSE::log::warn("ChronicleBridge: POST to {}:{}{} returned status {}", config.host, config.port, config.path,
                             result->status);
            return false;
        }
        return true;
    }

}  // namespace ChronicleBridge
