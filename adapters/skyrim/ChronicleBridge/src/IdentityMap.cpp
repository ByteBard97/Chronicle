#include "IdentityMap.h"

#include <array>
#include <format>

namespace ChronicleBridge {

    namespace {

        struct NamedCastEntry {
            std::string_view pluginName;
            std::uint32_t localFormId;
            std::string_view chronicleNpcId;
        };

        // NOT YET FILLED IN -- deliberately left empty rather than guessing at
        // FormIDs from memory (a wrong hardcoded hex value would silently
        // resolve to the wrong NPC or to nothing, which is worse than the
        // generic fallback catching them honestly). Fill this in once the
        // plugin can actually run: log every resolved FormRef for a session
        // standing in Whiterun, cross-reference against Chronicle's fixture
        // npc_ids (chronicle/fixtures/whiterun_relationships.py names
        // jarl_balgruuf, proventus, irileth, whiterun_guard_1, hulda,
        // ysolda), and add entries here. Until then every actor resolves via
        // FallbackIdentity() -- correct, just not yet linked to Chronicle's
        // own belief-engine identities.
        constexpr std::array<NamedCastEntry, 0> kNamedCast{};

    }  // namespace

    std::optional<std::string> ResolveNamedCast(const FormRef& ref) {
        for (const auto& entry : kNamedCast) {
            if (entry.pluginName == ref.pluginName && entry.localFormId == ref.localFormId) {
                return std::string{entry.chronicleNpcId};
            }
        }
        return std::nullopt;
    }

    std::string FallbackIdentity(const FormRef& ref) {
        return std::format("{}:{:06x}", ref.pluginName, ref.localFormId);
    }

    std::optional<FormRef> ResolveFormRef(RE::TESForm* form) {
        if (!form) return std::nullopt;

        // TESForm::GetFile(0) is the form's originating plugin; GetLocalFormID()
        // abstracts over the ESL/light-plugin vs. full-plugin FormID bit-layout
        // difference (light plugins use a 12-bit file index + 12-bit local id
        // instead of 8+24) -- verify both calls against the actual
        // CommonLibSSE-NG headers on first build; this is the standard
        // load-order-independent-identity pattern, not exotic, but hasn't been
        // compiled against yet.
        const auto* file = form->GetFile(0);
        if (!file) return std::nullopt;

        return FormRef{
            .pluginName = file->fileName,
            .localFormId = form->GetLocalFormID(),
        };
    }

}  // namespace ChronicleBridge
