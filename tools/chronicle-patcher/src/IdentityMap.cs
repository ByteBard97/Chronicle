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
    /// array verbatim (same order, same 19 entries, same plugin/FormID pairs).
    /// Do not edit this table without also updating IdentityMap.cpp -- see
    /// that file's kNamedCast for the source of truth.
    ///
    /// NOTE: 2026-08-27 -- amren, idolaf_battle_born, lars_battle_born,
    /// braith, and lillith_maiden_loom were previously misattributed to
    /// HearthFires.esm/USSEP; verified against a real load order via direct
    /// record dump and corrected to Skyrim.esm (their actual ACHR-owning
    /// master).
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
