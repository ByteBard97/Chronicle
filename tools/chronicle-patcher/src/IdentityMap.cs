namespace ChroniclePatcher;

/// <summary>
/// One named-cast NPC entry. Values here MUST match
/// adapters/skyrim/ChronicleBridge/src/IdentityMap.cpp's kNamedCast table
/// exactly -- the C++ side resolves the same (pluginName, localFormId) pair
/// to the same NpcId string, and this patcher's globals/packages are keyed
/// by NpcId so the two sides agree on what "ChronicleAvoiding_<NpcId>"
/// refers to.
/// </summary>
public readonly record struct NamedCastEntry(string NpcId, string PluginName, uint LocalFormId);

public static class IdentityMap
{
    /// <summary>
    /// Mirrors adapters/skyrim/ChronicleBridge/src/IdentityMap.cpp's kNamedCast
    /// array (same order, same 19 entries) -- EXCEPT for the plugin field on
    /// 5 entries, which intentionally differs. See below.
    ///
    /// NOTE (2026-08-27, corrected same day): a first pass "fixed" amren,
    /// idolaf_battle_born, lars_battle_born, braith, and lillith_maiden_loom
    /// to Skyrim.esm on BOTH sides, reasoning that IdentityMap.cpp's
    /// HearthFires.esm/USSEP attributions were wrong. A live-capture
    /// cross-check (adapters/skyrim/listener/whiterun-positions.json)
    /// disproved that for the .cpp side: IdentityMap.cpp's original
    /// attributions exactly match what ChronicleBridge's own
    /// TESForm::GetFile(0) call observes at runtime, because that call
    /// returns whichever plugin currently WINS the override chain for a
    /// record (HearthFires.esm overrides Amren/Braith/Lars's placed refs;
    /// USSEP overrides Idolaf's/Lillith's) -- a different, override-
    /// sensitive identity than a record's static originating master.
    /// IdentityMap.cpp was reverted to its original attributions for these
    /// 5 entries; do not "fix" it to match this file again.
    ///
    /// THIS file legitimately needs Skyrim.esm instead: Mutagen's FormKey
    /// resolution is keyed by originating master regardless of override
    /// chain, so a FormKey built from HearthFires.esm/USSEP for these 5
    /// simply fails to resolve (confirmed: 0/19 pairs resolved before this
    /// fix, 171/171 after). The two tables' plugin fields are correct to
    /// diverge on exactly these 5 rows -- this is not a sync bug.
    /// </summary>
    public static readonly IReadOnlyList<NamedCastEntry> NamedCast = new[]
    {
        new NamedCastEntry("ysolda", "Skyrim.esm", 0x01a69a),
        new NamedCastEntry("idolaf_battle_born", "Skyrim.esm", 0x01a689),
        new NamedCastEntry("saffir", "Skyrim.esm", 0x01a66c),
        new NamedCastEntry("carlotta_valentia", "Skyrim.esm", 0x01a675),
        new NamedCastEntry("amren", "Skyrim.esm", 0x01a66a),
        new NamedCastEntry("adrianne_avenicci", "Skyrim.esm", 0x01a67c),
        new NamedCastEntry("lars_battle_born", "Skyrim.esm", 0x01a68c),
        new NamedCastEntry("braith", "Skyrim.esm", 0x01a66b),
        new NamedCastEntry("fralia_gray_mane", "Skyrim.esm", 0x01a684),
        new NamedCastEntry("nazeem", "Skyrim.esm", 0x01a6a4),
        new NamedCastEntry("lillith_maiden_loom", "Skyrim.esm", 0x10e2b6),
        new NamedCastEntry("brenuin", "Skyrim.esm", 0x02c90f),
        new NamedCastEntry("anoriath", "Skyrim.esm", 0x01a680),
        new NamedCastEntry("lucia", "HearthFires.esm", 0x003f5e),
        new NamedCastEntry("heimskr", "Skyrim.esm", 0x01a682),
        new NamedCastEntry("sigurd", "Skyrim.esm", 0x0cdd73),
        new NamedCastEntry("olava_the_feeble", "Skyrim.esm", 0x01a699),
        new NamedCastEntry("danica_pure_spring", "Skyrim.esm", 0x01a69f),
        new NamedCastEntry("olfina_gray_mane", "Skyrim.esm", 0x01a685),
    };
}
