#include "AvoidanceGlobals.h"

#include <algorithm>
#include <array>

namespace ChronicleBridge {

    namespace {

        struct AvoidancePairEntry {
            std::string_view npcA;  // always the lexicographically smaller of the pair.
            std::string_view npcB;
            std::string_view pluginName;
            std::uint32_t localFormId;
        };

        // 2026-08-27: real FormIDs, filled in from tools/chronicle-patcher/
        // out/chronicle-globals.json after a real run of the patcher against
        // Skyrim.esm + HearthFires.esm + USSEP succeeded (171/171 pairs
        // resolved -- see tools/chronicle-patcher/src/IdentityMap.cs's and
        // AvoidancePatchBuilder.cs's 2026-08-27 fixes; this file's own
        // IdentityMap.cpp was NOT changed -- its original plugin attributions
        // were already correct, see its 2026-08-27 note). `pluginName`
        // confirmed to match the patcher's actual output filename.
        //
        // Entries are illustrative, not exhaustive -- see AvoidanceGlobals.h.
        // Every npcA/npcB here is drawn from IdentityMap.cpp's kNamedCast
        // table (a pair not in THAT table can never resolve to a live actor
        // anyway, so this table is only ever consulted for named-cast
        // pairs -- see AvoidancePoller.cpp's resolution order). Expanding
        // this to the full 171-pair set the patcher now generates is future
        // work, not done here.
        constexpr std::array<AvoidancePairEntry, 4> kAvoidancePairGlobals{{
            {"nazeem", "ysolda", "ChroniclePatcher.esp", 0x000818},
            {"carlotta_valentia", "saffir", "ChroniclePatcher.esp", 0x000869},
            {"amren", "brenuin", "ChroniclePatcher.esp", 0x0008d8},
            {"fralia_gray_mane", "idolaf_battle_born", "ChroniclePatcher.esp", 0x000848},
        }};

    }  // namespace

    std::optional<FormRef> ResolveAvoidancePairGlobal(std::string_view npcA, std::string_view npcB) {
        // Canonicalize the same way listener.py's _avoidance_pairs does
        // (tuple(sorted((a, b)))) before comparing against the table, so a
        // pair named in either order still finds its entry.
        auto a = npcA, b = npcB;
        if (b < a) std::swap(a, b);

        for (const auto& entry : kAvoidancePairGlobals) {
            if (entry.npcA == a && entry.npcB == b) {
                return FormRef{.pluginName = std::string{entry.pluginName}, .localFormId = entry.localFormId};
            }
        }
        return std::nullopt;
    }

}  // namespace ChronicleBridge
