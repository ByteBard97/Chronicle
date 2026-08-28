#include "Config.h"

#include <Windows.h>

#include <filesystem>

namespace ChronicleBridge {

    namespace {

        // The ini lives next to this DLL (Data/SKSE/Plugins/ChronicleBridge.ini,
        // same folder CommonLibSSE-NG drops the plugin into) -- resolved from
        // this function's own address rather than assumed, since the mod
        // manager decides the actual install path.
        std::filesystem::path IniPath() {
            HMODULE self = nullptr;
            GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                                reinterpret_cast<LPCSTR>(&IniPath), &self);

            char modulePath[MAX_PATH]{};
            GetModuleFileNameA(self, modulePath, MAX_PATH);

            return std::filesystem::path(modulePath).parent_path() / "ChronicleBridge.ini";
        }

        constexpr auto kSection = "General";

        // Deliberately NOT spdlog::level::from_str: that returns level::off
        // for anything it doesn't recognize, so a typo like "infi" would
        // silence the log entirely -- the exact opposite of what this key
        // exists for. Unknown values fall back to info and say so.
        spdlog::level::level_enum ParseLogLevel(std::string_view name) {
            if (name == "trace") return spdlog::level::trace;
            if (name == "debug") return spdlog::level::debug;
            if (name == "info") return spdlog::level::info;
            if (name == "warn") return spdlog::level::warn;
            if (name == "error") return spdlog::level::err;
            SKSE::log::warn("ChronicleBridge.ini: unrecognized LogLevel '{}' -- using info", std::string(name));
            return spdlog::level::info;
        }

        // The canonical spelling of whatever ParseLogLevel settled on, for
        // the "ini loaded" line -- echoing the raw ini string back would lie
        // about the effective level whenever the value was unrecognized.
        const char* LogLevelName(spdlog::level::level_enum level) {
            switch (level) {
                case spdlog::level::trace: return "trace";
                case spdlog::level::debug: return "debug";
                case spdlog::level::warn: return "warn";
                case spdlog::level::err: return "error";
                default: return "info";
            }
        }

    }  // namespace

    BridgeConfig LoadConfigFromIni() {
        BridgeConfig bridge{};
        OutboundConfig& config = bridge.outbound;

        const auto iniPath = IniPath();
        if (!std::filesystem::exists(iniPath)) {
            SKSE::log::info("ChronicleBridge.ini not found at {} -- using defaults (host={}, port={}, logLevel=info)",
                             iniPath.string(), config.host, config.port);
            return bridge;
        }
        const auto iniPathStr = iniPath.string();

        char hostBuf[256]{};
        GetPrivateProfileStringA(kSection, "Host", config.host.c_str(), hostBuf, sizeof(hostBuf), iniPathStr.c_str());
        config.host = hostBuf;

        config.port = static_cast<int>(GetPrivateProfileIntA(kSection, "Port", config.port, iniPathStr.c_str()));

        char secretBuf[256]{};
        auto secretLen = GetPrivateProfileStringA(kSection, "SharedSecret", "", secretBuf, sizeof(secretBuf),
                                                    iniPathStr.c_str());
        if (secretLen > 0) {
            config.sharedSecret = std::string(secretBuf);
        }

        char logLevelBuf[32]{};
        GetPrivateProfileStringA(kSection, "LogLevel", "info", logLevelBuf, sizeof(logLevelBuf), iniPathStr.c_str());
        bridge.logLevel = ParseLogLevel(logLevelBuf);

        SKSE::log::info("ChronicleBridge.ini loaded from {} -- host={}, port={}, sharedSecret={}, logLevel={}",
                         iniPathStr, config.host, config.port, config.sharedSecret ? "set" : "unset",
                         LogLevelName(bridge.logLevel));
        return bridge;
    }

}  // namespace ChronicleBridge
