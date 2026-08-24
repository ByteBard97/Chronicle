#include "OutboundClient.h"

#include <httplib.h>

#include <format>
#include <sstream>

namespace ChronicleBridge {

    namespace {

        // Minimal JSON string escaping -- deliberately not pulling in a JSON
        // library for a 3-field payload (see this file's header comment and
        // the design doc's dependency-minimalism note). Every id this plugin
        // actually produces (a Chronicle npc_id, or "<plugin>:<hex>") is
        // already JSON-safe, but escaping defensively costs nothing and
        // avoids a malformed-payload footgun if a plugin filename ever
        // contains a quote or backslash.
        std::string EscapeJsonString(std::string_view s) {
            std::string out;
            out.reserve(s.size() + 2);
            for (char c : s) {
                switch (c) {
                    case '"':
                        out += "\\\"";
                        break;
                    case '\\':
                        out += "\\\\";
                        break;
                    default:
                        out += c;
                }
            }
            return out;
        }

        // Matches adapters/skyrim/contracts/chronicle-bridge.openapi.yaml's
        // PositionSnapshot schema exactly -- field-for-field, same order isn't
        // required by JSON but kept matching the spec for readability.
        std::string BuildPositionSnapshotJson(double wallTimestamp, const std::vector<NpcPosition>& npcs) {
            std::ostringstream body;
            body << std::format(R"({{"wall_ts":{},"npcs":[)", wallTimestamp);
            for (std::size_t i = 0; i < npcs.size(); ++i) {
                if (i > 0) body << ',';
                body << std::format(R"({{"id":"{}","x":{},"y":{}}})", EscapeJsonString(npcs[i].id), npcs[i].x, npcs[i].y);
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
        auto result = client.Post(config.path, body, "application/json");

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
