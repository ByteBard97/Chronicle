# chronicle-patcher

A headless C# console app that authors `ChroniclePatcher.esp` -- the
game-content half of avoidance's game-side consumer, per
`docs/design/chronicle-bridge-avoidance-mutagen-out.md` §1. Uses
[Mutagen](https://github.com/Mutagen-Modding/Mutagen)
(`Mutagen.Bethesda.Skyrim`, MIT-licensed, cross-platform .NET) to create new
Skyrim game records directly -- no Creation Kit, no GUI, no Windows required
for this half (see `docs/research/24-programmatic-esp-authoring.md`).

## What it authors

*** DESIGN CHANGE FROM AN EARLIER VERSION OF THIS TOOL ***: this patcher
originally authored a per-NPC design (one global + one package per NPC,
with the package's Flee target left as an unset "linked reference" that
ChronicleBridge's C++ side would supposedly point at the right actor via
`SetLinkedRef` at runtime). That assumption did not survive contact with
the real CommonLibSSE-NG headers: `RE::TESObjectREFR` exposes no safe
setter for a linked reference (see
`adapters/skyrim/ChronicleBridge/src/AvoidancePoller.h`'s header comment
for the full finding). ChronicleBridge's C++ side implemented the design
doc's own named fallback instead -- **per-PAIR globals, target decided at
authoring time, not at runtime** -- and this patcher was rewritten to
match, so the two halves actually interoperate. See
`AvoidancePatchBuilder`'s own doc comment for the full before/after
reasoning.

For every unordered pair of the named-cast NPCs in
`adapters/skyrim/ChronicleBridge/src/IdentityMap.cpp`'s `kNamedCast` table
(mirrored verbatim in `src/IdentityMap.cs` -- keep the two in sync if that
table ever changes) that both resolve against the supplied load order:

- One `GlobalShort` record, `ChronicleAvoidingPair_<a>_<b>` (`a`/`b` = the
  pair's two NPC ids, sorted ordinally -- the exact name and canonicalization
  `AvoidanceGlobals.cpp`'s `ResolveAvoidancePairGlobal` and `listener.py`'s
  `_avoidance_pairs`/`_apply_avoidance_ack` both expect), a 0/1 flag
  ChronicleBridge's C++ side flips at runtime. Shared by both directions'
  packages below, since avoidance is mutual.
- Two `Package` (PACK) records per pair, `ChronicleAvoidance_<a>_from_<b>`
  and `ChronicleAvoidance_<b>_from_<a>`, each gated by that SAME shared
  global and using the vanilla `Flee` procedure with its target HARDCODED
  to the actual other actor in the pair (no runtime target resolution --
  see "Targeting" below).
- One NPC override per NPC (not per pair) for that NPC's `NPC_` record,
  with every pair it participates in contributing one Flee package to the
  front of its `Packages` list (higher priority; inert whenever that
  pair's gating global is 0, so it never disturbs existing schedules).

It also writes `out/chronicle-globals.json`, a `(npcA, npcB) pair -> global/
package editor ID -> local FormID` map for the output mod -- closing the
design doc's open question about how ChronicleBridge would find each
global's FormID once that C++ half exists (not written under
`adapters/skyrim/ChronicleBridge/` -- that tree is a different agent's
scope; wire it in from there when that side is built). Its shape matches
exactly what `AvoidanceGlobals.cpp`'s illustrative lookup table needs
filled in with real FormIDs.

## Scale: all 171 pairs, not a fixed subset

Rule 18 can put *any* two named-cast NPCs into avoidance -- there is no
fixed set of pairs to special-case. With 19 named-cast NPCs that is
19-choose-2 = **171 pairs** (342 packages, 171 globals, plus 19 NPC
overrides). This patcher generates content for every resolvable pair by
default, rather than an illustrative subset: authoring hundreds of
mechanically-identical generated records is exactly the scale Mutagen/
Synthesis patchers are built for, and the full-roster round-trip test
(`Build_FullNamedCast_RoundTripsThroughBinaryWrite`) exercises all 171
pairs through a real binary write + read-back without issue. (Contrast
this with `AvoidanceGlobals.cpp`'s own lookup table, which *is*
illustrative/non-exhaustive by necessity -- it can only list pairs this
patcher has actually generated FormIDs for, and today that's a placeholder
handful pending a real load-order run of this tool.)

## Design decision: per-pair packages, not one shared PACK

The design doc's §1 originally asked for "one reusable PACK." That
doesn't survive contact with Mutagen's actual `Condition` schema: a
`Package`'s `Conditions` list is one list, shared by every NPC the package
is ever attached to -- it cannot encode "check *this specific* pair's
global" differently depending on which NPC currently has the package
active. This patcher instead generates one `Package` variant per
(owner, target) direction, identical in every field except which global
its one condition checks and which NPC its Flee procedure targets --
a nested loop over resolved pairs (`AvoidancePatchBuilder.Build`), not
hand-authored records.

## Targeting: PackageTargetReference, populated at authoring time

Mutagen's schema has a dedicated "specific reference" target type,
`PackageTargetSpecificReference`, but its `Reference` property is typed
`FormLink<ILinkedReferenceGetter>` -- an interface only placed-reference
records (ACHR/REFR) implement. `IdentityMap`'s named-cast FormKeys all
resolve to `NPC_` base records, not placed references, and this project
tracks no ACHR FormKeys for them. So this patcher reuses
`PackageTargetReference` instead -- confirmed by reflection against the
actual installed `Mutagen.Bethesda.Skyrim` 23.4.0 assembly to be the
positionally-4th `APackageTarget` subclass (`APackageTarget.Type`/
`Package.TargetDataType` enumerate `SpecificReference, ObjectID,
ObjectType, LinkedReference, RefAlias, Unknown, Self` in that order; this
assembly generates 7 concrete `PackageTarget*` subclasses in the same
order). Its `Reference` property is broadly typed
`FormLink<ISkyrimMajorRecordGetter>`, with no interface constraint tying
it to placed references specifically -- so, unlike the superseded design
(which left `Reference` unset for C++ to fill in via `SetLinkedRef` at
runtime), this patcher sets it DIRECTLY to the target NPC's `NPC_` FormKey
at authoring time. Confirmed (via a scratch reflection/round-trip check
during this rewrite, and by the test suite's own
`Build_FullNamedCast_RoundTripsThroughBinaryWrite`) to survive a real
binary write + `CreateFromBinaryOverlay` read-back intact. Whether the
game engine accepts an `NPC_` FormID (rather than a placed ACHR/REFR) in
this slot the same way it accepts a genuine linked reference is **not**
verified here -- no Creation Kit, no live game.

## Honestly unverified

The task brief explicitly allows naming a gap plainly instead of guessing
past it; this is that gap (unchanged from the superseded per-NPC design).
`PackageBranch.BranchType`/`ProcedureType` are raw strings ("Flee" is used
here, matching the vanilla procedure-type name), and `DataInputIndices`
wires a branch to an index into the package's `Data` dictionary, which is
where the target lives (`Data[0]`). **This shape is real and matches
Mutagen's `Package.xml` schema exactly**, but whether `"Flee"` is the
precise literal string the engine expects and whether index `0` is the
correct target-input slot for that procedure could not be checked against
a known-good CK- or xEdit-authored Flee package in this environment (no
Creation Kit, no such reference file available). If this turns out wrong,
the fix is narrowly scoped to `AvoidancePatchBuilder.BuildPackage` --
everything else (globals, conditions, NPC overrides, the loop structure)
does not depend on getting this exactly right.

## Building and running

Requires the .NET 8 SDK (`~/.dotnet` on this dev machine; add it to `PATH`
or call `~/.dotnet/dotnet` directly).

```
dotnet build ChroniclePatcher.sln -c Release
dotnet test tests/ChroniclePatcher.Tests.csproj
```

To actually author the `.esp` against a real Skyrim install, point it at
the `Data` folder containing `Skyrim.esm`, `HearthFires.esm`, and
`unofficial skyrim special edition patch.esp`:

```
dotnet run --project src -c Release -- \
  --data-path "/path/to/Steam/steamapps/common/Skyrim Special Edition/Data"
```

Output lands in `tools/chronicle-patcher/out/ChroniclePatcher.esp` (plus
`out/chronicle-globals.json`) by default -- `--output <dir>` overrides
this. The default is resolved from this tool's own directory (via
`ChroniclePatcher.sln`'s location), not the process's current working
directory, so it lands in the same place (and stays covered by the
`tools/chronicle-patcher/out/` gitignore entry) no matter where you run
`dotnet run` from.
If any of the 19 named-cast NPCs can't be resolved against `--data-path`
(wrong load order, missing plugin, a FormID that doesn't actually exist --
see `src/IdentityMap.cs`'s doc comment about a few surprising plugin
attributions inherited verbatim from `IdentityMap.cpp` that are flagged but
not fixed here), the patcher **fails loud**: it prints every unresolved
NPC and refuses to write any output file at all, rather than authoring a
partial/broken mod.

### Why `.esp`, not `.esl`

`AvoidancePoller` (a ChronicleBridge C++ slice, already built --see
`adapters/skyrim/ChronicleBridge/src/AvoidanceGlobals.h`/`.cpp`) needs to
look up each pair's global FormID by `(pluginName, localFormId)` -- the
same scheme `IdentityMap.cpp` already uses for NPCs. ESL-flagged plugins
use a compressed `0xFE`-prefixed FormID layout at runtime that would make
that lookup table more fragile to generate and reason about for no real
benefit here (this mod's record count -- 171 globals, 342 packages, 19 NPC
overrides -- is still nowhere near the reason ESL flagging usually exists,
avoiding burning a full plugin slot). Plain `.esp`, plain local FormIDs.

### Output is not committed

Same posture as ChronicleBridge's own build output (its `.dll` is never
committed -- see `adapters/skyrim/ChronicleBridge/README.md`'s "Building"
section, which documents a build step and an env-var-driven copy into a
mod manager's folder instead). `tools/chronicle-patcher/**/bin/`,
`**/obj/`, and `tools/chronicle-patcher/out/` are all gitignored. Run this
patcher as a documented one-time (or re-run-on-change) step against your
own load order; there is nothing here to check in.

## Verification status

**Compiles cleanly and passes unit tests written and run in this
environment -- has never been run against a real Skyrim install, because
none exists here.** Specifically:

- `dotnet build ChroniclePatcher.sln -c Release` -- succeeds, 0
  warnings/errors.
- `dotnet test tests/ChroniclePatcher.Tests.csproj` -- 3/3 tests pass,
  including a full round trip: build synthetic in-memory stub masters at
  the exact FormKeys `IdentityMap.cpp` expects (no real `Skyrim.esm`
  involved), resolve all 19 named-cast NPCs through a real `ILinkCache`,
  author all 171 pairs' globals/packages plus all 19 NPC overrides, write
  the result to a real binary `.esp` file on disk, then read it back with
  `SkyrimMod.CreateFromBinaryOverlay` and re-assert every record --
  including each package's hardcoded Flee target -- survived intact.
- **Never run against a real `Skyrim.esm`/`HearthFires.esm`/USSEP, and
  never loaded in an actual game.** This is the same "compiled, not
  live-tested" posture every ChronicleBridge C++ slice uses (see that
  project's own README) -- exercising real record construction, real
  FormKey resolution, and a real binary write/read-back is a stronger
  claim than "it compiles," but it is still not the same claim as "the
  game accepts this file and the NPC actually flees." That check needs
  someone with a real Skyrim install and load order to run this against
  their own `Data` folder and confirm in-game.
