using Mutagen.Bethesda;
using Mutagen.Bethesda.Skyrim;
using Xunit;

namespace ChroniclePatcher.Tests;

/// <summary>
/// Exercises AvoidancePatchBuilder end-to-end against synthetic, in-memory
/// stub masters -- no real Skyrim.esm/HearthFires.esm/USSEP available in
/// this environment (see tools/chronicle-patcher/README.md's verification
/// status). These stub masters are built at the *exact* FormKeys
/// IdentityMap.cs (mirroring ChronicleBridge's IdentityMap.cpp) expects, so
/// this test exercises real FormKey resolution via a real ILinkCache, real
/// override-record creation (Npcs.GetOrAddAsOverride), real record
/// construction (Global/Package), and a real binary write + read-back --
/// everything this patcher does except load actual Bethesda game files.
///
/// Covers the per-PAIR design (see AvoidancePatchBuilder's own doc comment
/// for why): one shared ChronicleAvoidingPair_&lt;a&gt;_&lt;b&gt; global per
/// unordered pair, and two Flee packages per pair (one per direction), each
/// with its target hardcoded to the actual other actor in that pair.
/// </summary>
public class AvoidancePatchBuilderTests
{
    private static (ISkyrimMod skyrim, ISkyrimMod hearthfires, ISkyrimMod ussep) BuildStubMasters(
        IReadOnlyList<NamedCastEntry> namedCast)
    {
        var skyrim = new SkyrimMod(ModKey.FromNameAndExtension("Skyrim.esm"), SkyrimRelease.SkyrimSE);
        var hearthfires = new SkyrimMod(ModKey.FromNameAndExtension("HearthFires.esm"), SkyrimRelease.SkyrimSE);
        var ussep = new SkyrimMod(
            ModKey.FromNameAndExtension("unofficial skyrim special edition patch.esp"),
            SkyrimRelease.SkyrimSE);

        var byPlugin = new Dictionary<string, ISkyrimMod>
        {
            ["Skyrim.esm"] = skyrim,
            ["HearthFires.esm"] = hearthfires,
            ["unofficial skyrim special edition patch.esp"] = ussep,
        };

        foreach (var entry in namedCast)
        {
            var mod = byPlugin[entry.PluginName];
            var formKey = new FormKey(mod.ModKey, entry.LocalFormId);
            var npc = mod.Npcs.AddNew(formKey);
            npc.EditorID = "Stub_" + entry.NpcId;
        }

        return (skyrim, hearthfires, ussep);
    }

    /// <summary>n-choose-2.</summary>
    private static int PairCount(int n) => n * (n - 1) / 2;

    [Fact]
    public void Build_AllNamedCastResolve_AuthorsOnePairGlobalAndTwoPackagesPerPair()
    {
        var namedCast = IdentityMap.NamedCast;
        var (skyrim, hearthfires, ussep) = BuildStubMasters(namedCast);
        var linkCache = new ISkyrimModGetter[] { skyrim, hearthfires, ussep }.ToImmutableLinkCache();

        var outputMod = new SkyrimMod(ModKey.FromNameAndExtension("ChroniclePatcher.esp"), SkyrimRelease.SkyrimSE);

        var outcome = AvoidancePatchBuilder.Build(outputMod, linkCache, namedCast);

        var expectedPairs = PairCount(namedCast.Count);

        Assert.Empty(outcome.Failures);
        Assert.Equal(expectedPairs, outcome.Applied.Count);
        Assert.Equal(expectedPairs, outputMod.Globals.Count);
        Assert.Equal(expectedPairs * 2, outputMod.Packages.Count);
        Assert.Equal(namedCast.Count, outputMod.Npcs.Count);

        // Every pair's two NPCs are always reported sorted ordinally.
        Assert.All(outcome.Applied, r => Assert.True(string.CompareOrdinal(r.NpcA, r.NpcB) < 0));

        // Every unordered pair of named-cast NPCs appears exactly once.
        var seenPairs = outcome.Applied.Select(r => (r.NpcA, r.NpcB)).ToHashSet();
        Assert.Equal(expectedPairs, seenPairs.Count);

        foreach (var result in outcome.Applied)
        {
            var global = outputMod.Globals[result.GlobalFormKey];
            Assert.Equal(AvoidancePatchBuilder.GlobalEditorIdPrefix + result.NpcA + "_" + result.NpcB, global.EditorID);
            Assert.IsType<GlobalShort>(global);
            Assert.Equal((short)0, ((GlobalShort)global).Data);

            var npcAFormKey = outputMod.Npcs.Single(n => n.EditorID == "Stub_" + result.NpcA).FormKey;
            var npcBFormKey = outputMod.Npcs.Single(n => n.EditorID == "Stub_" + result.NpcB).FormKey;

            // A's package: flees B, gated by the shared pair global.
            var packageAFleesB = outputMod.Packages[result.PackageAFleesBFormKey];
            Assert.Equal(
                AvoidancePatchBuilder.PackageEditorIdPrefix + result.NpcA + "_from_" + result.NpcB,
                packageAFleesB.EditorID);
            AssertGatedByGlobal(packageAFleesB, result.GlobalFormKey);
            AssertFleeTargets(packageAFleesB, npcBFormKey);

            // B's package: flees A, gated by the SAME shared pair global
            // (mutual/symmetric avoidance).
            var packageBFleesA = outputMod.Packages[result.PackageBFleesAFormKey];
            Assert.Equal(
                AvoidancePatchBuilder.PackageEditorIdPrefix + result.NpcB + "_from_" + result.NpcA,
                packageBFleesA.EditorID);
            AssertGatedByGlobal(packageBFleesA, result.GlobalFormKey);
            AssertFleeTargets(packageBFleesA, npcAFormKey);

            // A's NPC override carries A-flees-B; B's carries B-flees-A.
            var npcOverrideA = outputMod.Npcs[npcAFormKey];
            Assert.Contains(new FormLink<IPackageGetter>(result.PackageAFleesBFormKey), npcOverrideA.Packages);
            var npcOverrideB = outputMod.Npcs[npcBFormKey];
            Assert.Contains(new FormLink<IPackageGetter>(result.PackageBFleesAFormKey), npcOverrideB.Packages);
        }
    }

    private static void AssertGatedByGlobal(IPackageGetter package, FormKey globalFormKey)
    {
        Assert.Single(package.Conditions);
        var condition = Assert.IsType<ConditionFloat>(package.Conditions[0]);
        Assert.Equal(1f, condition.ComparisonValue);
        Assert.Equal(CompareOperator.EqualTo, condition.CompareOperator);
        var functionData = Assert.IsType<FunctionConditionData>(condition.Data);
        Assert.Equal((ushort)ConditionData.Function.GetGlobalValue, functionData.Function);
        Assert.Equal(globalFormKey, functionData.ParameterOneRecord.FormKey);
    }

    private static void AssertFleeTargets(IPackageGetter package, FormKey expectedTargetFormKey)
    {
        var data = Assert.IsAssignableFrom<IPackageDataTargetGetter>(package.Data[0]);
        var target = Assert.IsAssignableFrom<IPackageTargetReferenceGetter>(data.Target);
        Assert.Equal(expectedTargetFormKey, target.Reference.FormKey);
    }

    [Fact]
    public void Build_UnresolvableNpc_FailsLoudAndWritesNothing()
    {
        var namedCast = new[] { IdentityMap.NamedCast[0], IdentityMap.NamedCast[1] };
        // Empty masters -- nothing resolves.
        var skyrim = new SkyrimMod(ModKey.FromNameAndExtension("Skyrim.esm"), SkyrimRelease.SkyrimSE);
        var linkCache = new ISkyrimModGetter[] { skyrim }.ToImmutableLinkCache();

        var outputMod = new SkyrimMod(ModKey.FromNameAndExtension("ChroniclePatcher.esp"), SkyrimRelease.SkyrimSE);

        var outcome = AvoidancePatchBuilder.Build(outputMod, linkCache, namedCast);

        Assert.Empty(outcome.Applied);
        Assert.Equal(2, outcome.Failures.Count);
        Assert.Contains(outcome.Failures, f => f.NpcId == namedCast[0].NpcId);
        Assert.Contains(outcome.Failures, f => f.NpcId == namedCast[1].NpcId);
        Assert.Empty(outputMod.Globals);
        Assert.Empty(outputMod.Packages);
        Assert.Empty(outputMod.Npcs);
    }

    [Fact]
    public void Build_FullNamedCast_RoundTripsThroughBinaryWrite()
    {
        var namedCast = IdentityMap.NamedCast;
        var (skyrim, hearthfires, ussep) = BuildStubMasters(namedCast);
        var linkCache = new ISkyrimModGetter[] { skyrim, hearthfires, ussep }.ToImmutableLinkCache();

        var outputModKey = ModKey.FromNameAndExtension("ChroniclePatcher.esp");
        var outputMod = new SkyrimMod(outputModKey, SkyrimRelease.SkyrimSE);
        var outcome = AvoidancePatchBuilder.Build(outputMod, linkCache, namedCast);
        Assert.Empty(outcome.Failures);

        var expectedPairs = PairCount(namedCast.Count);

        var tempDir = Directory.CreateTempSubdirectory("chronicle-patcher-tests-");
        try
        {
            var path = Path.Combine(tempDir.FullName, outputModKey.FileName);
            outputMod.WriteToBinary(path, new BinaryWriteParameters());

            using var readBack = SkyrimMod.CreateFromBinaryOverlay(new ModPath(outputModKey, path), SkyrimRelease.SkyrimSE);

            Assert.Equal(expectedPairs, readBack.Globals.Count);
            Assert.Equal(expectedPairs * 2, readBack.Packages.Count);
            Assert.Equal(namedCast.Count, readBack.Npcs.Count);

            foreach (var result in outcome.Applied)
            {
                Assert.True(readBack.Globals.TryGetValue(result.GlobalFormKey, out var global));
                Assert.Equal(
                    AvoidancePatchBuilder.GlobalEditorIdPrefix + result.NpcA + "_" + result.NpcB,
                    global!.EditorID);
                var globalShort = Assert.IsAssignableFrom<IGlobalShortGetter>(global);
                Assert.Equal((short)0, globalShort.Data);

                var npcAFormKey = readBack.Npcs.Single(n => n.EditorID == "Stub_" + result.NpcA).FormKey;
                var npcBFormKey = readBack.Npcs.Single(n => n.EditorID == "Stub_" + result.NpcB).FormKey;

                Assert.True(readBack.Packages.TryGetValue(result.PackageAFleesBFormKey, out var packageAFleesB));
                Assert.Equal(
                    AvoidancePatchBuilder.PackageEditorIdPrefix + result.NpcA + "_from_" + result.NpcB,
                    packageAFleesB!.EditorID);
                Assert.Single(packageAFleesB.Conditions);
                AssertPackageSurvivedRoundTrip(packageAFleesB, npcBFormKey);

                Assert.True(readBack.Packages.TryGetValue(result.PackageBFleesAFormKey, out var packageBFleesA));
                Assert.Equal(
                    AvoidancePatchBuilder.PackageEditorIdPrefix + result.NpcB + "_from_" + result.NpcA,
                    packageBFleesA!.EditorID);
                Assert.Single(packageBFleesA.Conditions);
                AssertPackageSurvivedRoundTrip(packageBFleesA, npcAFormKey);

                Assert.True(readBack.Npcs.TryGetValue(npcAFormKey, out var npcA));
                Assert.Contains(
                    npcA!.Packages,
                    p => p.FormKey == result.PackageAFleesBFormKey);

                Assert.True(readBack.Npcs.TryGetValue(npcBFormKey, out var npcB));
                Assert.Contains(
                    npcB!.Packages,
                    p => p.FormKey == result.PackageBFleesAFormKey);
            }
        }
        finally
        {
            tempDir.Delete(recursive: true);
        }
    }

    /// <summary>
    /// The procedure tree / Data dictionary is the part of BuildPackage
    /// flagged as least-verified (README's "Honestly unverified" section) --
    /// assert it actually survives a real binary write + read-back, not
    /// just that the in-memory object looked right before writing. Also
    /// asserts the hardcoded Flee target (this design's whole reason for
    /// existing) survives the round trip intact.
    /// </summary>
    private static void AssertPackageSurvivedRoundTrip(IPackageGetter package, FormKey expectedTargetFormKey)
    {
        Assert.Single(package.ProcedureTree);
        var branch = package.ProcedureTree[0];
        Assert.Equal("Flee", branch.BranchType);
        Assert.Equal("Flee", branch.ProcedureType);
        Assert.Contains((byte)0, branch.DataInputIndices);
        Assert.True(package.Data.ContainsKey(0));
        var target = Assert.IsAssignableFrom<IPackageDataTargetGetter>(package.Data[0]);
        var reference = Assert.IsAssignableFrom<IPackageTargetReferenceGetter>(target.Target);
        Assert.Equal(expectedTargetFormKey, reference.Reference.FormKey);
    }
}
