using System.Text.Json;
using Mutagen.Bethesda;
using Mutagen.Bethesda.Skyrim;

namespace ChroniclePatcher;

/// <summary>
/// Headless Mutagen patcher that authors ChronicleAvoidance content (see
/// docs/design/chronicle-bridge-avoidance-mutagen-out.md §1). Reads real
/// master plugins from a Data folder, never touches the Creation Kit.
///
/// Usage:
///   dotnet run --project src -- --data-path "/path/to/Skyrim Special Edition/Data" [--output <dir>]
///
/// --output defaults to tools/chronicle-patcher/out/ (resolved from this
/// tool's own directory, not the process's cwd -- see ToolRootDir below).
///
/// Requires Skyrim.esm, HearthFires.esm, and
/// "unofficial skyrim special edition patch.esp" to be present in
/// --data-path (the three masters IdentityMap.cpp's kNamedCast table draws
/// its 19 NPCs from).
/// </summary>
public static class Program
{
    public static int Main(string[] args)
    {
        string? dataPath = null;
        string? outputDir = null;

        for (var i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--data-path":
                    dataPath = args[++i];
                    break;
                case "--output":
                    outputDir = args[++i];
                    break;
                default:
                    Console.Error.WriteLine($"Unrecognized argument: {args[i]}");
                    return 2;
            }
        }

        if (dataPath is null)
        {
            Console.Error.WriteLine("Usage: dotnet run --project src -- --data-path <Skyrim Data folder> [--output out]");
            return 2;
        }

        if (!Directory.Exists(dataPath))
        {
            Console.Error.WriteLine($"--data-path does not exist: {dataPath}");
            return 2;
        }

        // Default --output to <this tool's own directory>/out rather than a
        // bare relative "out" (which would land wherever the process's cwd
        // happens to be -- e.g. the repo root if run via `dotnet run
        // --project tools/chronicle-patcher/src` from there -- and the repo
        // root's "out/" is NOT covered by .gitignore's
        // tools/chronicle-patcher/out/ entry). Anchoring on ToolRootDir keeps
        // the default output path stable regardless of cwd, matching the
        // gitignore convention documented in the README.
        outputDir ??= Path.Combine(ToolRootDir(), "out");

        var requiredMasters = new[] { "Skyrim.esm", "HearthFires.esm", "unofficial skyrim special edition patch.esp" };
        var masterMods = new List<ISkyrimModGetter>();
        foreach (var masterName in requiredMasters)
        {
            var path = Path.Combine(dataPath, masterName);
            if (!File.Exists(path))
            {
                Console.Error.WriteLine($"Required master not found: {path}");
                return 1;
            }

            var modKey = ModKey.FromNameAndExtension(masterName);
            var overlay = SkyrimMod.CreateFromBinaryOverlay(new ModPath(modKey, path), SkyrimRelease.SkyrimSE);
            masterMods.Add(overlay);
        }

        var linkCache = masterMods.ToImmutableLinkCache();

        var outputModKey = ModKey.FromNameAndExtension("ChroniclePatcher.esp");
        var outputMod = new SkyrimMod(outputModKey, SkyrimRelease.SkyrimSE);

        var outcome = AvoidancePatchBuilder.Build(outputMod, linkCache);

        if (outcome.Failures.Count > 0)
        {
            Console.Error.WriteLine($"Refusing to write output: {outcome.Failures.Count} of {IdentityMap.NamedCast.Count} named-cast NPCs did not resolve against --data-path:");
            foreach (var failure in outcome.Failures)
            {
                Console.Error.WriteLine($"  {failure.NpcId}: {failure.PluginName}:{failure.LocalFormId:x6} not found");
            }
            return 1;
        }

        Directory.CreateDirectory(outputDir);
        var espPath = Path.Combine(outputDir, outputModKey.FileName);
        outputMod.WriteToBinary(espPath, new BinaryWriteParameters());

        Console.WriteLine($"Wrote {espPath} ({outcome.Applied.Count} avoidance pairs patched).");

        WriteGlobalsMap(outputDir, outcome.Applied);

        return 0;
    }

    /// <summary>
    /// Walks up from the running assembly's directory (normally
    /// .../tools/chronicle-patcher/src/bin/&lt;config&gt;/net8.0/) to find the
    /// tool's own root -- identified by ChroniclePatcher.sln -- so the
    /// default --output path is stable regardless of the process's current
    /// working directory. Falls back to the current directory if the
    /// marker isn't found (e.g. a future publish layout that moves the
    /// .sln), which just reproduces the old cwd-relative behavior rather
    /// than crashing.
    /// </summary>
    private static string ToolRootDir()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (dir.EnumerateFiles("ChroniclePatcher.sln").Any())
            {
                return dir.FullName;
            }
            dir = dir.Parent;
        }

        return Directory.GetCurrentDirectory();
    }

    /// <summary>
    /// Closes the design doc's open question ("the global's FormID recorded
    /// somewhere ChronicleBridge can read it") -- writes (npcA, npcB) pair ->
    /// global editor ID -> local FormID -> plugin name for the *output* mod
    /// (ChroniclePatcher.esp), matching exactly what
    /// AvoidanceGlobals.cpp's ResolveAvoidancePairGlobal table needs filled
    /// in. Written under this tool's own out/ directory, not under
    /// adapters/skyrim/ChronicleBridge/ -- that tree is out of scope for this
    /// task and a parallel agent is working in it.
    /// </summary>
    private static void WriteGlobalsMap(string outputDir, IReadOnlyList<AvoidancePairPatchResult> applied)
    {
        var map = applied.Select(r => new
        {
            npcA = r.NpcA,
            npcB = r.NpcB,
            globalEditorId = AvoidancePatchBuilder.GlobalEditorIdPrefix + r.NpcA + "_" + r.NpcB,
            globalLocalFormId = $"{r.GlobalFormKey.ID:x6}",
            packageAFleesBEditorId = AvoidancePatchBuilder.PackageEditorIdPrefix + r.NpcA + "_from_" + r.NpcB,
            packageAFleesBLocalFormId = $"{r.PackageAFleesBFormKey.ID:x6}",
            packageBFleesAEditorId = AvoidancePatchBuilder.PackageEditorIdPrefix + r.NpcB + "_from_" + r.NpcA,
            packageBFleesALocalFormId = $"{r.PackageBFleesAFormKey.ID:x6}",
            plugin = "ChroniclePatcher.esp",
        });

        var json = JsonSerializer.Serialize(map, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(Path.Combine(outputDir, "chronicle-globals.json"), json);
    }
}
