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
        // 2026-08-27: expanded from the earlier illustrative 4-entry table
        // to the FULL 171-pair set (19-choose-2 named-cast NPCs), generated
        // programmatically by tools/generate-avoidance-globals-table.py from
        // tools/chronicle-patcher/out/chronicle-globals.json -- not
        // hand-typed. Every npcA/npcB here is drawn from IdentityMap.cpp's
        // kNamedCast table (a pair not in THAT table can never resolve to a
        // live actor anyway, so this table is only ever consulted for
        // named-cast pairs -- see AvoidancePoller.cpp's resolution order).
        //
        // *** THIS TABLE IS ROSTER-DEPENDENT, NOT FIXED ***: if
        // IdentityMap.cpp's/IdentityMap.cs's named-cast roster ever grows or
        // shrinks, the pair set (and every FormID in it, per
        // EvidencePoller.cpp's own allocation-order-dependent
        // kEvidenceLocalFormId comment) shifts. Re-run
        // tools/chronicle-patcher/ to regenerate out/chronicle-globals.json,
        // then re-run tools/generate-avoidance-globals-table.py to
        // regenerate this array, before trusting it again. Same "hardcoded
        // from a real run, re-verify if the roster changes" posture as
        // EvidencePoller.cpp's kEvidenceLocalFormId.
        constexpr std::array<AvoidancePairEntry, 171> kAvoidancePairGlobals{{
            {"adrianne_avenicci", "amren", "ChroniclePatcher.esp", 0x0008c6},
            {"adrianne_avenicci", "anoriath", "ChroniclePatcher.esp", 0x000902},
            {"adrianne_avenicci", "braith", "ChroniclePatcher.esp", 0x0008f3},
            {"adrianne_avenicci", "brenuin", "ChroniclePatcher.esp", 0x0008ff},
            {"adrianne_avenicci", "carlotta_valentia", "ChroniclePatcher.esp", 0x00089c},
            {"adrianne_avenicci", "danica_pure_spring", "ChroniclePatcher.esp", 0x000911},
            {"adrianne_avenicci", "fralia_gray_mane", "ChroniclePatcher.esp", 0x0008f6},
            {"adrianne_avenicci", "heimskr", "ChroniclePatcher.esp", 0x000908},
            {"adrianne_avenicci", "idolaf_battle_born", "ChroniclePatcher.esp", 0x00083f},
            {"adrianne_avenicci", "lars_battle_born", "ChroniclePatcher.esp", 0x0008f0},
            {"adrianne_avenicci", "lillith_maiden_loom", "ChroniclePatcher.esp", 0x0008fc},
            {"adrianne_avenicci", "lucia", "ChroniclePatcher.esp", 0x000905},
            {"adrianne_avenicci", "nazeem", "ChroniclePatcher.esp", 0x0008f9},
            {"adrianne_avenicci", "olava_the_feeble", "ChroniclePatcher.esp", 0x00090e},
            {"adrianne_avenicci", "olfina_gray_mane", "ChroniclePatcher.esp", 0x000914},
            {"adrianne_avenicci", "saffir", "ChroniclePatcher.esp", 0x00086f},
            {"adrianne_avenicci", "sigurd", "ChroniclePatcher.esp", 0x00090b},
            {"adrianne_avenicci", "ysolda", "ChroniclePatcher.esp", 0x00080c},
            {"amren", "anoriath", "ChroniclePatcher.esp", 0x0008db},
            {"amren", "braith", "ChroniclePatcher.esp", 0x0008cc},
            {"amren", "brenuin", "ChroniclePatcher.esp", 0x0008d8},
            {"amren", "carlotta_valentia", "ChroniclePatcher.esp", 0x000899},
            {"amren", "danica_pure_spring", "ChroniclePatcher.esp", 0x0008ea},
            {"amren", "fralia_gray_mane", "ChroniclePatcher.esp", 0x0008cf},
            {"amren", "heimskr", "ChroniclePatcher.esp", 0x0008e1},
            {"amren", "idolaf_battle_born", "ChroniclePatcher.esp", 0x00083c},
            {"amren", "lars_battle_born", "ChroniclePatcher.esp", 0x0008c9},
            {"amren", "lillith_maiden_loom", "ChroniclePatcher.esp", 0x0008d5},
            {"amren", "lucia", "ChroniclePatcher.esp", 0x0008de},
            {"amren", "nazeem", "ChroniclePatcher.esp", 0x0008d2},
            {"amren", "olava_the_feeble", "ChroniclePatcher.esp", 0x0008e7},
            {"amren", "olfina_gray_mane", "ChroniclePatcher.esp", 0x0008ed},
            {"amren", "saffir", "ChroniclePatcher.esp", 0x00086c},
            {"amren", "sigurd", "ChroniclePatcher.esp", 0x0008e4},
            {"amren", "ysolda", "ChroniclePatcher.esp", 0x000809},
            {"anoriath", "braith", "ChroniclePatcher.esp", 0x000947},
            {"anoriath", "brenuin", "ChroniclePatcher.esp", 0x0009ad},
            {"anoriath", "carlotta_valentia", "ChroniclePatcher.esp", 0x0008b1},
            {"anoriath", "danica_pure_spring", "ChroniclePatcher.esp", 0x0009ce},
            {"anoriath", "fralia_gray_mane", "ChroniclePatcher.esp", 0x000965},
            {"anoriath", "heimskr", "ChroniclePatcher.esp", 0x0009c5},
            {"anoriath", "idolaf_battle_born", "ChroniclePatcher.esp", 0x000854},
            {"anoriath", "lars_battle_born", "ChroniclePatcher.esp", 0x000926},
            {"anoriath", "lillith_maiden_loom", "ChroniclePatcher.esp", 0x000998},
            {"anoriath", "lucia", "ChroniclePatcher.esp", 0x0009c2},
            {"anoriath", "nazeem", "ChroniclePatcher.esp", 0x000980},
            {"anoriath", "olava_the_feeble", "ChroniclePatcher.esp", 0x0009cb},
            {"anoriath", "olfina_gray_mane", "ChroniclePatcher.esp", 0x0009d1},
            {"anoriath", "saffir", "ChroniclePatcher.esp", 0x000884},
            {"anoriath", "sigurd", "ChroniclePatcher.esp", 0x0009c8},
            {"anoriath", "ysolda", "ChroniclePatcher.esp", 0x000821},
            {"braith", "brenuin", "ChroniclePatcher.esp", 0x000944},
            {"braith", "carlotta_valentia", "ChroniclePatcher.esp", 0x0008a2},
            {"braith", "danica_pure_spring", "ChroniclePatcher.esp", 0x000956},
            {"braith", "fralia_gray_mane", "ChroniclePatcher.esp", 0x00093b},
            {"braith", "heimskr", "ChroniclePatcher.esp", 0x00094d},
            {"braith", "idolaf_battle_born", "ChroniclePatcher.esp", 0x000845},
            {"braith", "lars_battle_born", "ChroniclePatcher.esp", 0x000917},
            {"braith", "lillith_maiden_loom", "ChroniclePatcher.esp", 0x000941},
            {"braith", "lucia", "ChroniclePatcher.esp", 0x00094a},
            {"braith", "nazeem", "ChroniclePatcher.esp", 0x00093e},
            {"braith", "olava_the_feeble", "ChroniclePatcher.esp", 0x000953},
            {"braith", "olfina_gray_mane", "ChroniclePatcher.esp", 0x000959},
            {"braith", "saffir", "ChroniclePatcher.esp", 0x000875},
            {"braith", "sigurd", "ChroniclePatcher.esp", 0x000950},
            {"braith", "ysolda", "ChroniclePatcher.esp", 0x000812},
            {"brenuin", "carlotta_valentia", "ChroniclePatcher.esp", 0x0008ae},
            {"brenuin", "danica_pure_spring", "ChroniclePatcher.esp", 0x0009bc},
            {"brenuin", "fralia_gray_mane", "ChroniclePatcher.esp", 0x000962},
            {"brenuin", "heimskr", "ChroniclePatcher.esp", 0x0009b3},
            {"brenuin", "idolaf_battle_born", "ChroniclePatcher.esp", 0x000851},
            {"brenuin", "lars_battle_born", "ChroniclePatcher.esp", 0x000923},
            {"brenuin", "lillith_maiden_loom", "ChroniclePatcher.esp", 0x000995},
            {"brenuin", "lucia", "ChroniclePatcher.esp", 0x0009b0},
            {"brenuin", "nazeem", "ChroniclePatcher.esp", 0x00097d},
            {"brenuin", "olava_the_feeble", "ChroniclePatcher.esp", 0x0009b9},
            {"brenuin", "olfina_gray_mane", "ChroniclePatcher.esp", 0x0009bf},
            {"brenuin", "saffir", "ChroniclePatcher.esp", 0x000881},
            {"brenuin", "sigurd", "ChroniclePatcher.esp", 0x0009b6},
            {"brenuin", "ysolda", "ChroniclePatcher.esp", 0x00081e},
            {"carlotta_valentia", "danica_pure_spring", "ChroniclePatcher.esp", 0x0008c0},
            {"carlotta_valentia", "fralia_gray_mane", "ChroniclePatcher.esp", 0x0008a5},
            {"carlotta_valentia", "heimskr", "ChroniclePatcher.esp", 0x0008b7},
            {"carlotta_valentia", "idolaf_battle_born", "ChroniclePatcher.esp", 0x000839},
            {"carlotta_valentia", "lars_battle_born", "ChroniclePatcher.esp", 0x00089f},
            {"carlotta_valentia", "lillith_maiden_loom", "ChroniclePatcher.esp", 0x0008ab},
            {"carlotta_valentia", "lucia", "ChroniclePatcher.esp", 0x0008b4},
            {"carlotta_valentia", "nazeem", "ChroniclePatcher.esp", 0x0008a8},
            {"carlotta_valentia", "olava_the_feeble", "ChroniclePatcher.esp", 0x0008bd},
            {"carlotta_valentia", "olfina_gray_mane", "ChroniclePatcher.esp", 0x0008c3},
            {"carlotta_valentia", "saffir", "ChroniclePatcher.esp", 0x000869},
            {"carlotta_valentia", "sigurd", "ChroniclePatcher.esp", 0x0008ba},
            {"carlotta_valentia", "ysolda", "ChroniclePatcher.esp", 0x000806},
            {"danica_pure_spring", "fralia_gray_mane", "ChroniclePatcher.esp", 0x000974},
            {"danica_pure_spring", "heimskr", "ChroniclePatcher.esp", 0x0009e9},
            {"danica_pure_spring", "idolaf_battle_born", "ChroniclePatcher.esp", 0x000863},
            {"danica_pure_spring", "lars_battle_born", "ChroniclePatcher.esp", 0x000935},
            {"danica_pure_spring", "lillith_maiden_loom", "ChroniclePatcher.esp", 0x0009a7},
            {"danica_pure_spring", "lucia", "ChroniclePatcher.esp", 0x0009dd},
            {"danica_pure_spring", "nazeem", "ChroniclePatcher.esp", 0x00098f},
            {"danica_pure_spring", "olava_the_feeble", "ChroniclePatcher.esp", 0x0009f8},
            {"danica_pure_spring", "olfina_gray_mane", "ChroniclePatcher.esp", 0x0009fe},
            {"danica_pure_spring", "saffir", "ChroniclePatcher.esp", 0x000893},
            {"danica_pure_spring", "sigurd", "ChroniclePatcher.esp", 0x0009f2},
            {"danica_pure_spring", "ysolda", "ChroniclePatcher.esp", 0x000830},
            {"fralia_gray_mane", "heimskr", "ChroniclePatcher.esp", 0x00096b},
            {"fralia_gray_mane", "idolaf_battle_born", "ChroniclePatcher.esp", 0x000848},
            {"fralia_gray_mane", "lars_battle_born", "ChroniclePatcher.esp", 0x00091a},
            {"fralia_gray_mane", "lillith_maiden_loom", "ChroniclePatcher.esp", 0x00095f},
            {"fralia_gray_mane", "lucia", "ChroniclePatcher.esp", 0x000968},
            {"fralia_gray_mane", "nazeem", "ChroniclePatcher.esp", 0x00095c},
            {"fralia_gray_mane", "olava_the_feeble", "ChroniclePatcher.esp", 0x000971},
            {"fralia_gray_mane", "olfina_gray_mane", "ChroniclePatcher.esp", 0x000977},
            {"fralia_gray_mane", "saffir", "ChroniclePatcher.esp", 0x000878},
            {"fralia_gray_mane", "sigurd", "ChroniclePatcher.esp", 0x00096e},
            {"fralia_gray_mane", "ysolda", "ChroniclePatcher.esp", 0x000815},
            {"heimskr", "idolaf_battle_born", "ChroniclePatcher.esp", 0x00085a},
            {"heimskr", "lars_battle_born", "ChroniclePatcher.esp", 0x00092c},
            {"heimskr", "lillith_maiden_loom", "ChroniclePatcher.esp", 0x00099e},
            {"heimskr", "lucia", "ChroniclePatcher.esp", 0x0009d4},
            {"heimskr", "nazeem", "ChroniclePatcher.esp", 0x000986},
            {"heimskr", "olava_the_feeble", "ChroniclePatcher.esp", 0x0009e6},
            {"heimskr", "olfina_gray_mane", "ChroniclePatcher.esp", 0x0009ec},
            {"heimskr", "saffir", "ChroniclePatcher.esp", 0x00088a},
            {"heimskr", "sigurd", "ChroniclePatcher.esp", 0x0009e3},
            {"heimskr", "ysolda", "ChroniclePatcher.esp", 0x000827},
            {"idolaf_battle_born", "lars_battle_born", "ChroniclePatcher.esp", 0x000842},
            {"idolaf_battle_born", "lillith_maiden_loom", "ChroniclePatcher.esp", 0x00084e},
            {"idolaf_battle_born", "lucia", "ChroniclePatcher.esp", 0x000857},
            {"idolaf_battle_born", "nazeem", "ChroniclePatcher.esp", 0x00084b},
            {"idolaf_battle_born", "olava_the_feeble", "ChroniclePatcher.esp", 0x000860},
            {"idolaf_battle_born", "olfina_gray_mane", "ChroniclePatcher.esp", 0x000866},
            {"idolaf_battle_born", "saffir", "ChroniclePatcher.esp", 0x000836},
            {"idolaf_battle_born", "sigurd", "ChroniclePatcher.esp", 0x00085d},
            {"idolaf_battle_born", "ysolda", "ChroniclePatcher.esp", 0x000800},
            {"lars_battle_born", "lillith_maiden_loom", "ChroniclePatcher.esp", 0x000920},
            {"lars_battle_born", "lucia", "ChroniclePatcher.esp", 0x000929},
            {"lars_battle_born", "nazeem", "ChroniclePatcher.esp", 0x00091d},
            {"lars_battle_born", "olava_the_feeble", "ChroniclePatcher.esp", 0x000932},
            {"lars_battle_born", "olfina_gray_mane", "ChroniclePatcher.esp", 0x000938},
            {"lars_battle_born", "saffir", "ChroniclePatcher.esp", 0x000872},
            {"lars_battle_born", "sigurd", "ChroniclePatcher.esp", 0x00092f},
            {"lars_battle_born", "ysolda", "ChroniclePatcher.esp", 0x00080f},
            {"lillith_maiden_loom", "lucia", "ChroniclePatcher.esp", 0x00099b},
            {"lillith_maiden_loom", "nazeem", "ChroniclePatcher.esp", 0x00097a},
            {"lillith_maiden_loom", "olava_the_feeble", "ChroniclePatcher.esp", 0x0009a4},
            {"lillith_maiden_loom", "olfina_gray_mane", "ChroniclePatcher.esp", 0x0009aa},
            {"lillith_maiden_loom", "saffir", "ChroniclePatcher.esp", 0x00087e},
            {"lillith_maiden_loom", "sigurd", "ChroniclePatcher.esp", 0x0009a1},
            {"lillith_maiden_loom", "ysolda", "ChroniclePatcher.esp", 0x00081b},
            {"lucia", "nazeem", "ChroniclePatcher.esp", 0x000983},
            {"lucia", "olava_the_feeble", "ChroniclePatcher.esp", 0x0009da},
            {"lucia", "olfina_gray_mane", "ChroniclePatcher.esp", 0x0009e0},
            {"lucia", "saffir", "ChroniclePatcher.esp", 0x000887},
            {"lucia", "sigurd", "ChroniclePatcher.esp", 0x0009d7},
            {"lucia", "ysolda", "ChroniclePatcher.esp", 0x000824},
            {"nazeem", "olava_the_feeble", "ChroniclePatcher.esp", 0x00098c},
            {"nazeem", "olfina_gray_mane", "ChroniclePatcher.esp", 0x000992},
            {"nazeem", "saffir", "ChroniclePatcher.esp", 0x00087b},
            {"nazeem", "sigurd", "ChroniclePatcher.esp", 0x000989},
            {"nazeem", "ysolda", "ChroniclePatcher.esp", 0x000818},
            {"olava_the_feeble", "olfina_gray_mane", "ChroniclePatcher.esp", 0x0009fb},
            {"olava_the_feeble", "saffir", "ChroniclePatcher.esp", 0x000890},
            {"olava_the_feeble", "sigurd", "ChroniclePatcher.esp", 0x0009ef},
            {"olava_the_feeble", "ysolda", "ChroniclePatcher.esp", 0x00082d},
            {"olfina_gray_mane", "saffir", "ChroniclePatcher.esp", 0x000896},
            {"olfina_gray_mane", "sigurd", "ChroniclePatcher.esp", 0x0009f5},
            {"olfina_gray_mane", "ysolda", "ChroniclePatcher.esp", 0x000833},
            {"saffir", "sigurd", "ChroniclePatcher.esp", 0x00088d},
            {"saffir", "ysolda", "ChroniclePatcher.esp", 0x000803},
            {"sigurd", "ysolda", "ChroniclePatcher.esp", 0x00082a},
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
