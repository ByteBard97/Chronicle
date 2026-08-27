using Mutagen.Bethesda;
using Mutagen.Bethesda.Skyrim;
using Xunit;

namespace ChroniclePatcher.Tests;

/// <summary>
/// Exercises EvidenceItemPatchBuilder end-to-end: real record construction
/// via Mutagen's ISkyrimMod, a real binary write, and a real read-back --
/// the same "prove the round trip, not just the in-memory object" standard
/// AvoidancePatchBuilderTests.cs already holds itself to. Unlike that
/// builder, this one has no named-cast/load-order dependency (see
/// EvidenceItemPatchBuilder's own doc comment: "Unconditional... always
/// succeeds"), so no stub masters or ILinkCache are needed here.
/// </summary>
public class EvidenceItemPatchBuilderTests
{
    [Fact]
    public void Build_ReturnsResultWithFormKeyFromCorrectPlugin()
    {
        var outputModKey = ModKey.FromNameAndExtension("ChroniclePatcher.esp");
        var outputMod = new SkyrimMod(outputModKey, SkyrimRelease.SkyrimSE);

        var result = EvidenceItemPatchBuilder.Build(outputMod);

        Assert.Equal(outputModKey, result.FormKey.ModKey);
    }

    [Fact]
    public void Build_RoundTripsThroughBinaryWrite()
    {
        var outputModKey = ModKey.FromNameAndExtension("ChroniclePatcher.esp");
        var outputMod = new SkyrimMod(outputModKey, SkyrimRelease.SkyrimSE);

        var result = EvidenceItemPatchBuilder.Build(outputMod);

        var tempDir = Directory.CreateTempSubdirectory("chronicle-patcher-evidence-tests-");
        try
        {
            var path = Path.Combine(tempDir.FullName, outputModKey.FileName);
            outputMod.WriteToBinary(path, new BinaryWriteParameters());

            using var readBack = SkyrimMod.CreateFromBinaryOverlay(new ModPath(outputModKey, path), SkyrimRelease.SkyrimSE);

            Assert.True(readBack.MiscItems.TryGetValue(result.FormKey, out var miscItem));
            Assert.Equal(EvidenceItemPatchBuilder.EditorId, miscItem!.EditorID);
            Assert.Equal("Chronicle Evidence", miscItem.Name?.String);
            Assert.Equal(EvidenceItemPatchBuilder.ModelPath, miscItem.Model?.File);
            Assert.Equal(0u, miscItem.Value);
            Assert.Equal(1f, miscItem.Weight);
        }
        finally
        {
            tempDir.Delete(recursive: true);
        }
    }

    [Fact]
    public void Build_IsUnconditional_SucceedsWithNoNamedCastOrLinkCache()
    {
        // EvidenceItemPatchBuilder's own doc comment: "Unlike
        // AvoidancePatchBuilder, this has no named-cast resolution
        // dependency, so it always succeeds." Calling it against a bare,
        // freshly-constructed mod with nothing else authored is the direct
        // test of that claim.
        var outputMod = new SkyrimMod(ModKey.FromNameAndExtension("ChroniclePatcher.esp"), SkyrimRelease.SkyrimSE);

        var exception = Record.Exception(() => EvidenceItemPatchBuilder.Build(outputMod));

        Assert.Null(exception);
    }
}
