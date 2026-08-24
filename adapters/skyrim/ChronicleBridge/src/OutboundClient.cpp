#include "OutboundClient.h"

#include <httplib.h>

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
                body << std::format(R"({{"id":"{}","x":{},"y":{}}})", EscapeJsonString(npcs[i].id),
                                     SanitizeFinite(npcs[i].x), SanitizeFinite(npcs[i].y));
            }
            body << "]}";
            return body.str();
        }

    }  // namespace

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
