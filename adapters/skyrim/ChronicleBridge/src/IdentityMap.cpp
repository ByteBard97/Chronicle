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

        // Filled in only from FormIDs actually observed at runtime (the
        // plugin's own NpcPosition.name field, cross-referenced against
        // Chronicle's fixture npc_ids in
        // chronicle/fixtures/whiterun_relationships.py) -- never guessed
        // from memory, per this comment's original reasoning: a wrong
        // hardcoded hex value would silently resolve to the wrong NPC,
        // worse than the generic fallback catching it honestly.
        //
        // "ysolda" observed 2026-08-24 in a live Whiterun exterior snapshot
        // (Skyrim.esm:01a69a -> name "Ysolda").
        //
        // jarl_balgruuf/irileth/proventus/hulda are not yet in this table --
        // they spend most of their time indoors (Dragonsreach, the Bannered
        // Mare) and hadn't appeared in an *outdoor* snapshot as of this
        // pass; add them the same way once one of them is observed outside.
        // whiterun_guard_1 is deliberately never added this way: Whiterun's
        // guards are multiple interchangeable generic actors sharing the
        // same display name, so no single observed FormID is "the" guard
        // any more than another -- picking one would be exactly the kind of
        // guess this table exists to avoid. Leave guards on the generic
        // fallback.
        constexpr std::array<NamedCastEntry, 1> kNamedCast{{
            {"Skyrim.esm", 0x01a69a, "ysolda"},
        }};

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
