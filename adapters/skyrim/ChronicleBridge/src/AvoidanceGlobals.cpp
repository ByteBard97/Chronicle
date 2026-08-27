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

        // TODO: fill in real FormIDs once tools/chronicle-patcher/'s
        // ChroniclePatcher.esp is generated and load-ordered (see this
        // file's header comment). `pluginName` is a placeholder guess
        // ("ChroniclePatcher.esp", matching the design doc §1's named
        // output file) -- confirm it against whatever the patcher actually
        // emits once it exists.
        //
        // Entries are illustrative, not exhaustive -- see AvoidanceGlobals.h.
        // Every npcA/npcB here is drawn from IdentityMap.cpp's kNamedCast
        // table (a pair not in THAT table can never resolve to a live actor
        // anyway, so this table is only ever consulted for named-cast
        // pairs -- see AvoidancePoller.cpp's resolution order).
        constexpr std::array<AvoidancePairEntry, 4> kAvoidancePairGlobals{{
            {"nazeem", "ysolda", "ChroniclePatcher.esp", 0x000000},
            {"carlotta_valentia", "saffir", "ChroniclePatcher.esp", 0x000000},
            {"amren", "brenuin", "ChroniclePatcher.esp", 0x000000},
            {"fralia_gray_mane", "idolaf_battle_born", "ChroniclePatcher.esp", 0x000000},
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
