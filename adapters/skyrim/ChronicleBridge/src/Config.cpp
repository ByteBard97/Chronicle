#include "Config.h"

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

    }  // namespace

    OutboundConfig LoadConfigFromIni() {
        OutboundConfig config{};

        const auto iniPath = IniPath();
        if (!std::filesystem::exists(iniPath)) {
            SKSE::log::info("ChronicleBridge.ini not found at {} -- using defaults (host={}, port={})",
                             iniPath.string(), config.host, config.port);
            return config;
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

        SKSE::log::info("ChronicleBridge.ini loaded from {} -- host={}, port={}, sharedSecret={}", iniPathStr,
                         config.host, config.port, config.sharedSecret ? "set" : "unset");
        return config;
    }

}  // namespace ChronicleBridge
