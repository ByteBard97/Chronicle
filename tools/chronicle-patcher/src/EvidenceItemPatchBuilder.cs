using Mutagen.Bethesda;
using Mutagen.Bethesda.Skyrim;

namespace ChroniclePatcher;

/// <summary>
/// Authors the single, fixed "diegetic evidence" MISC item that
/// ChronicleBridge's EvidencePoller.cpp spawns (via
/// <c>RE::TESObjectREFR::PlaceObjectAtMe</c>) at a believer's live position
/// once a belief's confidence crosses the reveal threshold. See
/// <c>docs/design/chronicle-bridge-diegetic-evidence-out.md</c> §5 and
/// <c>docs/research/31-diegetic-evidence-object-placement-spike.md</c>'s
/// recommendation 2, which scopes the first cut to "a single pre-authored
/// MISC or WEAP item" -- no per-claim-kind variety yet (that remains a
/// deliberate non-goal here, same as avoidance's own "not done here" style
/// callouts elsewhere in this tool).
///
/// *** WHY A NEW AUTHORED RECORD, NOT A REUSED VANILLA FORMID ***:
/// EvidencePoller.cpp's original placeholder hardcoded vanilla Gold001
/// (Skyrim.esm 0x0000000F) purely because it was a reliably-known FormID,
/// explicitly not for thematic fit. Picking a *different*, thematically
/// better vanilla MISC record blind still carries real risk this project
/// has no tooling to rule out here (no Creation Kit, no xEdit conflict
/// check in this pass): a vanilla record could be flagged unique, be
/// quest-critical, carry an attached script, or be referenced by other
/// systems in ways a bare Mutagen field read doesn't surface. Authoring a
/// brand-new record instead sidesteps all of that -- every field on it is
/// explicit and known, because this builder set every one of them.
///
/// To avoid the new record rendering as an invisible/default-cube object
/// in-game, its <see cref="MiscItem.Model"/> reuses a REAL vanilla model
/// path, copied as a plain string (not a FormLink/reference to the vanilla
/// record itself, so there is no dependency on that record's other fields
/// or flags): <c>Clutter\BloodyRags\BloodyRags.nif</c>, the model vanilla
/// Skyrim.esm's own <c>BloodyRags01</c> MISC record (FormKey
/// 0CC84D:Skyrim.esm) uses. Confirmed via a real Mutagen read against this
/// project's actual Skyrim.esm (dumped in this task's own scratch
/// verification, not guessed): EditorID <c>BloodyRags01</c>, MajorFlags 0
/// (not unique/quest-critical), no VirtualMachineAdapter (no attached
/// script), no Destructible entry -- and its model path is exactly the
/// generic "something violent/criminal happened here" clutter prop this
/// feature's use case (evidence of a belief) calls for, better thematic
/// fit than the superseded Gold001 placeholder. Reusing only the model
/// *path string* means this new record has zero structural dependency on
/// that vanilla record ever resolving correctly.
/// </summary>
public static class EvidenceItemPatchBuilder
{
    public const string EditorId = "ChronicleEvidenceObject";

    /// <summary>
    /// Real vanilla clutter model, confirmed against Skyrim.esm to be the
    /// model BloodyRags01 (FormKey 0CC84D:Skyrim.esm, MajorFlags 0, no
    /// script, no destructible) uses. Copied as a plain path string, not a
    /// reference to that record.
    /// </summary>
    public const string ModelPath = @"Clutter\BloodyRags\BloodyRags.nif";

    public sealed record EvidenceItemPatchResult(FormKey FormKey);

    /// <summary>
    /// Authors one <see cref="MiscItem"/> record, editor ID
    /// <see cref="EditorId"/>, named "Chronicle Evidence", with
    /// <see cref="ModelPath"/> as its model so it isn't an invisible/
    /// default-cube object in-game. Unconditional -- unlike
    /// <see cref="AvoidancePatchBuilder"/>, this has no named-cast
    /// resolution dependency, so it always succeeds.
    /// </summary>
    public static EvidenceItemPatchResult Build(ISkyrimMod outputMod)
    {
        var item = outputMod.MiscItems.AddNew(EditorId);
        item.Name = "Chronicle Evidence";
        item.Model = new Model { File = ModelPath };
        item.Value = 0;
        item.Weight = 1f;

        return new EvidenceItemPatchResult(item.FormKey);
    }
}
