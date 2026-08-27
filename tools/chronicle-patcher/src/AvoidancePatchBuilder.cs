using Mutagen.Bethesda;
using Mutagen.Bethesda.Skyrim;

namespace ChroniclePatcher;

/// <summary>
/// Failure resolving one named-cast NPC's FormKey against the supplied link
/// cache -- means the (pluginName, localFormId) pair in IdentityMap doesn't
/// resolve in the load order the patcher was pointed at.
/// </summary>
public sealed record NpcResolutionFailure(string NpcId, string PluginName, uint LocalFormId);

/// <summary>
/// One authored avoidance pair: the shared gating global, and the two
/// flee packages (one per direction) that global controls.
/// </summary>
public sealed record AvoidancePairPatchResult(
    string NpcA,
    string NpcB,
    FormKey GlobalFormKey,
    FormKey PackageAFleesBFormKey,
    FormKey PackageBFleesAFormKey);

/// <summary>
/// Builds the ChronicleAvoidance content into an output SkyrimMod, given a
/// link cache that can resolve the named-cast NPCs' FormKeys (normally built
/// from the real Skyrim/HearthFires/USSEP masters, but for tests any link
/// cache -- including one built purely from in-memory stub mods -- works
/// identically, since this class never touches disk itself).
///
/// *** DESIGN CHANGE, SUPERSEDING THE ORIGINAL PER-NPC + LINKED-REF SHAPE
/// THIS CLASS USED TO IMPLEMENT ***: this class originally authored one
/// `ChronicleAvoiding_&lt;npcId&gt;` global and one `ChronicleAvoidance_&lt;npcId&gt;`
/// package per NPC, with the package's Flee target left as an unset
/// "linked reference" (`PackageTargetReference` with no `Reference` set) --
/// on the assumption that ChronicleBridge's C++ side would call
/// `RE::TESObjectREFR::SetLinkedRef` (or equivalent) at runtime to point
/// that linked ref at whichever NPC this NPC should currently flee.
///
/// That assumption did not survive contact with the real CommonLibSSE-NG
/// headers. `adapters/skyrim/ChronicleBridge/src/AvoidancePoller.h`'s
/// header comment documents the finding in full: `RE::TESObjectREFR`
/// exposes only `GetLinkedRef` (a getter); there is no safe, documented
/// CommonLibSSE-NG API to set a linked reference at runtime. ChronicleBridge
/// therefore implemented the design doc's own named fallback instead: one
/// `TESGlobal` PER PAIR of named-cast NPCs (not per NPC), and the flee
/// TARGET is decided at content-AUTHORING time (here, by this class), not
/// at runtime. See `AvoidanceGlobals.h`/`.cpp` and `AvoidancePoller.h`'s
/// header comments for the full C++-side reasoning; this class implements
/// the Mutagen half of that same corrected design:
///
/// - One `GlobalShort`, `ChronicleAvoidingPair_&lt;a&gt;_&lt;b&gt;`, per
///   unordered pair of named-cast NPCs (`a`/`b` sorted ordinally --
///   the same canonicalization `AvoidanceGlobals.cpp`'s
///   `ResolveAvoidancePairGlobal` and `listener.py`'s `_avoidance_pairs`/
///   `_apply_avoidance_ack` both use: `if (b &lt; a) swap(a, b)` /
///   `tuple(sorted((a, b)))`). This is the EXACT name
///   `AvoidanceGlobals.cpp`'s `ResolveAvoidancePairGlobal` looks up, and
///   this patcher's output mod is named `ChroniclePatcher.esp` (see
///   `Program.cs`), matching that file's `pluginName` expectation too.
/// - TWO `Package` (PACK) records per pair, one per direction ("A flees B"
///   and "B flees A"), both gated by the SAME shared per-pair global
///   (avoidance is mutual: when the pair's global flips to 1, both actors
///   flee each other simultaneously). Each package's Flee target is
///   HARDCODED to the actual other actor in that specific pair -- decided
///   here, at authoring time, precisely because no runtime target-
///   resolution mechanism exists. "A flees B" is attached to A's own
///   `Packages` list; "B flees A" to B's.
/// - Which pairs: rule 18 can put any two named-cast NPCs into avoidance,
///   not a fixed set, so there is no principled way to pick a small
///   "correct" subset ahead of time. With 19 named-cast NPCs that's
///   19-choose-2 = 171 pairs; this is well within the scale Mutagen/
///   Synthesis patchers routinely author (thousands of generated records
///   is common), so this builder generates content for ALL resolvable
///   pairs by default, not an illustrative subset -- see `Build`'s doc
///   comment for the resulting record counts.
///
/// Targeting mechanism: `PackageTargetSpecificReference` (the schema's
/// dedicated "specific reference" target type) requires a
/// `FormLink&lt;ILinkedReferenceGetter&gt;`, which only placed-reference
/// records (ACHR/REFR) implement -- NOT `NPC_` base records, which is what
/// this builder attaches Flee packages to (resolved by following each
/// named-cast NPC's ACHR `.Base` link -- see `Build`'s resolution loop and
/// 2026-08-27's IdentityMap.cs doc-comment update: `IdentityMap`'s FormKeys
/// are themselves ACHR FormIDs, not NPC_ ones). This builder
/// therefore reuses `PackageTargetReference` instead (the schema's
/// generically-typed "linked reference" target variant, positionally the
/// 4th `APackageTarget` subclass -- see the previous version of this file's
/// README section for how that positional mapping was confirmed by
/// reflection against the installed Mutagen.Bethesda.Skyrim 23.4.0
/// assembly). Its `Reference` property is a broadly-typed
/// `FormLink&lt;ISkyrimMajorRecordGetter&gt;` with no interface constraint
/// tying it to placed references specifically, so setting it directly to
/// the target NPC's `NPC_` FormKey is mechanically valid in Mutagen's
/// schema and has been confirmed (in this task's own scratch verification)
/// to survive a real binary write + `CreateFromBinaryOverlay` read-back
/// intact. Whether the game engine itself accepts an `NPC_` FormID (rather
/// than a placed ACHR/REFR) in this slot the same way it accepts a real
/// linked reference is NOT verified here -- no Creation Kit, no live game,
/// same "compiled, not live-tested" posture the rest of this tool and
/// ChronicleBridge's C++ side both carry (see this tool's README).
/// </summary>
public static class AvoidancePatchBuilder
{
    public const string PackageEditorIdPrefix = "ChronicleAvoidance_";
    public const string GlobalEditorIdPrefix = "ChronicleAvoidingPair_";

    public sealed record BuildOutcome(
        IReadOnlyList<AvoidancePairPatchResult> Applied,
        IReadOnlyList<NpcResolutionFailure> Failures);

    /// <summary>
    /// Resolves all named-cast NPCs against <paramref name="linkCache"/> and,
    /// only if every one resolves, authors one shared global plus two flee
    /// packages for EVERY unordered pair (n-choose-2 pairs for n named-cast
    /// NPCs -- 171 for the real 19-NPC roster) into <paramref name="outputMod"/>.
    /// Fails loud: if any NPC doesn't resolve, nothing is written to
    /// <paramref name="outputMod"/> and the returned outcome's Failures list
    /// is non-empty -- callers (Program.cs) must check this and refuse to
    /// write an output file.
    /// </summary>
    public static BuildOutcome Build(ISkyrimMod outputMod, ILinkCache linkCache)
    {
        return Build(outputMod, linkCache, IdentityMap.NamedCast);
    }

    /// <summary>
    /// Same as <see cref="Build(ISkyrimMod, ILinkCache)"/> but takes an
    /// explicit named-cast list -- the overload tests use, so they can point
    /// at a small synthetic roster instead of the real 19.
    /// </summary>
    public static BuildOutcome Build(
        ISkyrimMod outputMod,
        ILinkCache linkCache,
        IReadOnlyList<NamedCastEntry> namedCast)
    {
        var resolved = new List<(NamedCastEntry Entry, INpcGetter Npc)>();
        var failures = new List<NpcResolutionFailure>();

        foreach (var entry in namedCast)
        {
            // IdentityMap's FormKeys are placed-reference (ACHR) FormIDs, not
            // NPC_ base-record FormIDs -- correct for the C++ runtime side,
            // which resolves identity off the live RE::Actor* (itself a
            // placed reference). Verified against a real Skyrim.esm +
            // HearthFires.esm + USSEP load order: every one of the 19
            // named-cast FormKeys resolves as IPlacedNpcGetter (ACHR), not
            // INpcGetter (NPC_). This patcher, unlike the C++ side, needs the
            // actual NPC_ base record to attach Flee packages to, so it
            // resolves the ACHR first and follows its Base link (a
            // FormLinkNullable<INpcGetter>, confirmed to exist and resolve
            // cleanly on the installed Mutagen.Bethesda.Skyrim 23.4.0
            // assembly) to get there.
            var formKey = new FormKey(ModKey.FromNameAndExtension(entry.PluginName), entry.LocalFormId);
            if (linkCache.TryResolve<IPlacedNpcGetter>(formKey, out var placedNpc)
                && placedNpc.Base.TryResolve(linkCache, out var npcGetter))
            {
                resolved.Add((entry, npcGetter));
            }
            else
            {
                failures.Add(new NpcResolutionFailure(entry.NpcId, entry.PluginName, entry.LocalFormId));
            }
        }

        if (failures.Count > 0)
        {
            // Fail loud: don't half-author the mod. Nothing gets written to
            // outputMod, and Program.cs must not write a file when Failures
            // is non-empty.
            return new BuildOutcome(Array.Empty<AvoidancePairPatchResult>(), failures);
        }

        // NPC overrides are created lazily, once per NPC (not once per pair
        // it participates in), so an NPC that's in N-1 pairs still gets
        // exactly one override with N-1 packages prepended to its list.
        var overridesByNpcId = new Dictionary<string, INpc>();

        INpc GetOrAddOverride(NamedCastEntry entry, INpcGetter masterNpc)
        {
            if (!overridesByNpcId.TryGetValue(entry.NpcId, out var npcOverride))
            {
                npcOverride = outputMod.Npcs.GetOrAddAsOverride(masterNpc);
                overridesByNpcId[entry.NpcId] = npcOverride;
            }
            return npcOverride;
        }

        var results = new List<AvoidancePairPatchResult>();

        for (var i = 0; i < resolved.Count; i++)
        {
            for (var j = i + 1; j < resolved.Count; j++)
            {
                var (entryI, npcI) = resolved[i];
                var (entryJ, npcJ) = resolved[j];

                // Canonicalize ordinally the same way AvoidanceGlobals.cpp's
                // `if (b < a) swap(a, b)` and listener.py's
                // `tuple(sorted((a, b)))` do, so all three sides agree on
                // which NPC is "a" and which is "b" for a given pair.
                var (entryA, npcA, entryB, npcB) = string.CompareOrdinal(entryI.NpcId, entryJ.NpcId) <= 0
                    ? (entryI, npcI, entryJ, npcJ)
                    : (entryJ, npcJ, entryI, npcI);

                var global = BuildPairGlobal(outputMod, entryA.NpcId, entryB.NpcId);

                var packageAFleesB = BuildPackage(outputMod, entryA.NpcId, entryB.NpcId, global, npcB.FormKey);
                var overrideA = GetOrAddOverride(entryA, npcA);
                overrideA.Packages.Insert(0, new FormLink<IPackageGetter>(packageAFleesB.FormKey));

                var packageBFleesA = BuildPackage(outputMod, entryB.NpcId, entryA.NpcId, global, npcA.FormKey);
                var overrideB = GetOrAddOverride(entryB, npcB);
                overrideB.Packages.Insert(0, new FormLink<IPackageGetter>(packageBFleesA.FormKey));

                results.Add(new AvoidancePairPatchResult(
                    entryA.NpcId,
                    entryB.NpcId,
                    global.FormKey,
                    packageAFleesB.FormKey,
                    packageBFleesA.FormKey));
            }
        }

        return new BuildOutcome(results, Array.Empty<NpcResolutionFailure>());
    }

    /// <summary>
    /// One boolean-ish global per PAIR, "are these two NPCs currently
    /// avoiding each other." Shared by both directions' Flee packages,
    /// since avoidance is symmetric -- flipping this to 1 should make both
    /// actors flee each other at once, not just one of them. Modeled as
    /// GlobalShort (Mutagen's Global record is abstract; GlobalShort/
    /// GlobalInt/GlobalFloat are the concrete subtypes -- Short is the
    /// natural fit for a 0/1 flag, matching how vanilla Skyrim globals
    /// typically model booleans).
    /// </summary>
    private static GlobalShort BuildPairGlobal(ISkyrimMod mod, string npcIdA, string npcIdB)
    {
        // The (ISkyrimMod, editorID) constructor allocates a FormKey against
        // the mod but does NOT self-register into mod.Globals in this
        // Mutagen version (verified empirically: a bare `new GlobalShort(mod,
        // id)` left mod.Globals.Count at 0) -- unlike Package, which does
        // self-register via mod.Packages.AddNew(...). Add() explicitly.
        var global = new GlobalShort(mod, GlobalEditorIdPrefix + npcIdA + "_" + npcIdB)
        {
            Data = 0,
        };
        mod.Globals.Add(global);
        return global;
    }

    /// <summary>
    /// Builds one ChronicleAvoidance_&lt;ownerNpcId&gt;_from_&lt;targetNpcId&gt;
    /// PACK record: <paramref name="ownerNpcId"/> flees
    /// <paramref name="targetFormKey"/> whenever <paramref name="pairGlobal"/>
    /// is 1.
    /// - Conditions: a single GetGlobalValue(&lt;the pair's shared global&gt;) == 1
    ///   check (ConditionFloat wrapping a FunctionConditionData -- verified
    ///   against the installed Mutagen.Bethesda.Skyrim 23.4.0 assembly by
    ///   reflection, not guessed: ConditionData.Function.GetGlobalValue
    ///   exists, and ConditionFloat.ComparisonValue is the plain-float
    ///   comparison target).
    /// - ProcedureTree: one branch of the vanilla "Flee" procedure type.
    /// - Data[0]: a PackageDataTarget wrapping PackageTargetReference, with
    ///   its Reference set DIRECTLY to <paramref name="targetFormKey"/> --
    ///   the pair itself decides the target at authoring time, so (unlike
    ///   the superseded per-NPC design) there is no unset/runtime-resolved
    ///   placeholder here. See this class's own doc comment for why
    ///   PackageTargetReference (not PackageTargetSpecificReference) is the
    ///   variant used, and the caveat on whether the game engine accepts an
    ///   NPC_ FormID (vs. a placed ACHR/REFR) in this slot.
    ///
    /// HONESTLY UNVERIFIED (flagged per the task brief's explicit allowance,
    /// not guessed past this point, and unchanged from the superseded
    /// version of this method): the exact BranchType/ProcedureType string
    /// values ("Flee") and the low-level DataInputIndices-to-Data[0] wiring
    /// that is supposed to tell the Flee procedure "use Data[0] as your
    /// target" could not be checked against a known-good CK/xEdit-authored
    /// example in this environment (no Creation Kit, no existing
    /// Flee-with-a-hardcoded-target package to diff against). The record
    /// *shape* (string procedure/branch types, a Data dictionary keyed by
    /// the indices a branch references, PackageDataTarget/
    /// PackageTargetReference as the target payload) is real and matches
    /// Package.xml's schema exactly, but whether "Flee" is the right literal
    /// string, and whether index 0 is the correct target-input slot for that
    /// procedure, is unverified. See this method's XML doc and the tool's
    /// README for the same caveat.
    /// </summary>
    private static Package BuildPackage(
        ISkyrimMod mod,
        string ownerNpcId,
        string targetNpcId,
        GlobalShort pairGlobal,
        FormKey targetFormKey)
    {
        var package = mod.Packages.AddNew(PackageEditorIdPrefix + ownerNpcId + "_from_" + targetNpcId);

        package.Conditions.Add(new ConditionFloat
        {
            CompareOperator = CompareOperator.EqualTo,
            ComparisonValue = 1f,
            Data = new FunctionConditionData
            {
                Function = (ushort)ConditionData.Function.GetGlobalValue,
                ParameterOneRecord = new FormLink<ISkyrimMajorRecordGetter>(pairGlobal.FormKey),
            },
        });

        package.ProcedureTree.Add(new PackageBranch
        {
            BranchType = "Flee",
            ProcedureType = "Flee",
            Root = new PackageRoot { BranchCount = 1 },
            DataInputIndices = { 0 },
        });

        package.Data[0] = new PackageDataTarget
        {
            Type = PackageDataTarget.Types.SingleRef,
            Target = new PackageTargetReference
            {
                Reference = new FormLink<ISkyrimMajorRecordGetter>(targetFormKey),
            },
        };

        return package;
    }
}
