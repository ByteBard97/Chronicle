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
        // 18 more entries added 2026-08-26, all read directly from
        // adapters/skyrim/listener/whiterun-positions.json (a single live
        // Whiterun exterior snapshot capturing 28 NPCs), the same
        // observed-at-runtime sourcing this table requires. That snapshot's
        // 6 "Whiterun Guard" entries and its 1 "Cow" entry are excluded for
        // the reasons below (guards) and because a cow is not an NPC.
        // "lucia" uses HearthFires.esm as its origin plugin rather than
        // Skyrim.esm -- that's the plugin actually observed owning the
        // FormID at runtime, not an assumption, and is preserved verbatim.
        //
        // 2026-08-27: amren, braith, lars_battle_born, idolaf_battle_born, and
        // lillith_maiden_loom were previously misattributed to HearthFires.esm
        // or "unofficial skyrim special edition patch.esp" (a runtime
        // observation artifact, not their real originating plugin); verified
        // against a real Skyrim.esm + HearthFires.esm + USSEP load order via
        // direct record dump and corrected to Skyrim.esm.
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
        constexpr std::array<NamedCastEntry, 19> kNamedCast{{
            {"Skyrim.esm", 0x01a69a, "ysolda"},
            {"Skyrim.esm", 0x01a689, "idolaf_battle_born"},
            {"Skyrim.esm", 0x01a66c, "saffir"},
            {"Skyrim.esm", 0x01a675, "carlotta_valentia"},
            {"Skyrim.esm", 0x01a66a, "amren"},
            {"Skyrim.esm", 0x01a67c, "adrianne_avenicci"},
            {"Skyrim.esm", 0x01a68c, "lars_battle_born"},
            {"Skyrim.esm", 0x01a66b, "braith"},
            {"Skyrim.esm", 0x01a684, "fralia_gray_mane"},
            {"Skyrim.esm", 0x01a6a4, "nazeem"},
            {"Skyrim.esm", 0x10e2b6, "lillith_maiden_loom"},
            {"Skyrim.esm", 0x02c90f, "brenuin"},
            {"Skyrim.esm", 0x01a680, "anoriath"},
            {"HearthFires.esm", 0x003f5e, "lucia"},
            {"Skyrim.esm", 0x01a682, "heimskr"},
            {"Skyrim.esm", 0x0cdd73, "sigurd"},
            {"Skyrim.esm", 0x01a699, "olava_the_feeble"},
            {"Skyrim.esm", 0x01a69f, "danica_pure_spring"},
            {"Skyrim.esm", 0x01a685, "olfina_gray_mane"},
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

    std::optional<FormRef> ResolveChronicleNpcId(std::string_view npcId) {
        for (const auto& entry : kNamedCast) {
            if (entry.chronicleNpcId == npcId) {
                return FormRef{.pluginName = std::string{entry.pluginName}, .localFormId = entry.localFormId};
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
