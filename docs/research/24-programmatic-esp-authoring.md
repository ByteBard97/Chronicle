---
date: 2026-08-26
sources:
  - web research session (this pass) — xEdit/TES5Edit scripting docs and
    prior-art scripts, UESP Mod File Format wiki, ck-cmd repository,
    Mutagen-Modding/Mutagen source (fetched directly from GitHub), local
    CommonLibSSE-NG header checkout at
    /home/geoff/projects/skyrim-re-toolkit/type-importer/vendor/CommonLibSSE-NG
topic: "verifying/refuting chronicle-bridge-avoidance-out.md §2b's claim that authoring an AI Package + Condition requires the Creation Kit's interactive GUI"
status: filed
---

# Programmatic .esp Authoring: Can an AI Package + Condition Be Created Without the CK GUI?

**Document File ID:** docs/research/24-programmatic-esp-authoring.md
**Date:** 2026-08-26

## TL;DR

`chronicle-bridge-avoidance-out.md` §2b's "needs the Creation Kit GUI, out
of reach from headless/SSH" conclusion was **not researched and is
wrong**. A mature, actively-maintained, fully headless path exists today:
**Mutagen** (`Mutagen-Modding/Mutagen`, C#/.NET), the library underlying
the Synthesis patcher ecosystem, ships a complete code-generated typed
schema for Skyrim's `Package` record (`PACK`, mapping `PKDT`/`PSDT`,
`Conditions`, `CombatStyle`, `OwnerQuest`, procedure tree) and for
`Condition` (`CTDA`) — including a dedicated `ConditionGlobal` type and
hundreds of typed per-function condition-data classes
(`GetActorValueConditionData`, etc.). This is new-record creation, not
record editing, driven entirely by a C# console app — no GUI, no Bethesda
tool, fully reachable over SSH once .NET is installed. **xEdit's Pascal
scripting engine can also create new records** (`Add()` against a group
container, not just against an existing record) and can be driven
non-interactively from the command line via `-autoload`/`-autoexit`, but
prior-art xEdit scripts found here demonstrate only *editing* existing
records, not synthesizing whole new `PACK`+`CTDA` graphs — it's a weaker,
less-attested version of the same capability Mutagen already provides
cleanly. The Creation Kit itself has **no** headless content-authoring
mode — its command-line switches (`-GenerateLips`, `-ExportDialogue`,
`-OptimizeMasterFile`, `-GenerateSEQ`, etc.) are narrow fixed-purpose
batch utilities, none of which create arbitrary new records. Hand-writing
raw `PACK`/`CTDA` binary from a from-scratch script (no library at all)
is theoretically supported by the public UESP file-format spec but is
pure reinvention of what Mutagen already does robustly — not recommended.
A partial no-new-content path also exists: CommonLibSSE-NG's real
`RE::Actor::PutCreatedPackage(TESPackage*, ...)` (virtual index `0xDF`)
lets C++ force an arbitrary `TESPackage*` onto an actor at runtime, and
the engine has a native `kFlee`/`kAvoidPlayer` procedure-type — but there
is no built-in "avoid this specific other NPC" procedure, so this path
still needs either an authored package (back to Mutagen) or a
nontrivial from-scratch in-memory `TESPackage` construction that
reimplements what the CK's package compiler normally does. **Decisive
recommendation: use Mutagen, headlessly, from the build/CI machine — do
not touch xEdit scripting, hand-rolled binary authoring, or attempt to
reach the CK GUI over SSH.**

## Findings

**[F1] Mutagen creates brand-new records, not just edits them, and is
built for headless/CI use.** `Mutagen-Modding/Mutagen`'s README describes
it as "*a library for analyzing, creating, and manipulating Bethesda mods
written in .NET*" with strongly-typed C# classes generated per record
type. This is not a documentation claim taken on faith — fetching the
actual source confirms it. `Mutagen.Bethesda.Skyrim/Records/Major
Records/Package.xml` (Loqui code-generation schema, `objType="Record"
recordType="PACK"`) defines the full `Package` record: `PKDT`
(flags/type/interrupt/speed), `PSDT` (schedule), a `RefList
name="Conditions" refName="Condition"` (the CTDA list), `CombatStyle`
(`CNAM` form link), `OwnerQuest` (`QNAM` form link), `PackageTemplate`,
and a `ProcedureTree`. The generated `Package_Generated.cs` exposes this
as `public ExtendedList<Condition> Conditions` on the object — an
ordinary C# collection a script appends `new Condition{...}` to. Because
Mutagen is a plain .NET console library (used this way throughout the
Synthesis patcher ecosystem, e.g. the AI Overhaul Synthesis patcher which
itself forwards/merges AI package and faction data across mods), the
entire authoring step is `dotnet run` on a build machine — reachable over
SSH with no display, no Bethesda binary, no Wine/Proton GUI session.

**[F2] `Condition`/CTDA is a first-class, richly typed Mutagen object,
including a global-variable condition type.** Listing
`Mutagen.Bethesda.Skyrim/Records/Common Subrecords/` turned up
`Condition.cs`, `Condition.xml`, `ConditionData.cs`, `ConditionFloat.cs`,
and — directly answering the avoidance doc's specific need — a dedicated
`ConditionGlobal.cs`/`ConditionGlobal_Generated.cs` type for a condition
that reads a global variable. The same directory holds hundreds of other
generated `*ConditionData.cs` files (`GetActorValueConditionData`,
`GetActorCrimePlayerEnemyConditionData`, `GetActorAggroRadiusViolatedConditionData`,
etc.) — i.e. Mutagen has already mapped essentially every CTDA function
index Bethesda shipped to a typed C# class. A quest-alias-value condition
follows the identical pattern (an alias-scoped `GetValue`-style condition
data class referencing a `Quest`/alias form link) since Mutagen's code
generator covers the same CTDA function table CK exposes. Authoring "if
`GlobalXYZ == 1` then run this package" from a script is therefore a
matter of instantiating `new Package{...}` with `Conditions = [new
Condition{Data = new ConditionGlobal{ComparisonValue = ..., Global =
globalFormLink}}]` and saving the mod — no GUI step anywhere in that
pipeline.

**[F3] Package-to-Actor/faction linking is also just field assignment in
Mutagen, no CK step.** The vanilla mechanism for putting a package on an
actor is the `Npc.AIPackages`/`Race.AIPackages`/`Faction`-level
"Ranked"/"Unranked" package list fields on the corresponding record types
— these are ordinary `FormLink` lists that Mutagen exposes with the same
typed-record pattern documented for `Package` in F1. Editing an existing
`NPC_`/`FACT` record's package list to reference the newly created
`Package` FormKey is strictly simpler than creating the `PACK` record
itself (it's editing, the well-attested and uncontroversial half of
xEdit/Mutagen capability), so no further verification was needed here —
if F1/F2 hold, this step is not a risk.

**[F4] xEdit's Pascal scripting engine can create new records (not just
edit them), and can run non-interactively, but no prior-art script doing
a full PACK+CTDA synthesis was found.** `xEdit`'s documented `Add(aeContainer,
asNameOrSignature, abSilent)` function creates "a child element with the
name-or-signature" and, per the xEdit scripting docs and community
threads, this same `Add()` call directed at a *group* container (rather
than an existing record) is the documented technique for inserting whole
new records — this is distinct from, and stronger than, the "add a
subrecord to an already-selected record" pattern shown in the
`TES5Edit/xEditScripts` "Add New Records.pas" template script (which only
adds an `MESG` element to a pre-existing record and is explicitly a
beginner template, not evidence of full record synthesis). Separately,
xEdit's command-line switches `-quickautoclean`/`-autoload`/`-autoexit`
(and a documented `-script:` batch mode) are real and let xEdit run one
operation and exit without an interactive session, which is the piece of
this claim that most directly answers "reachable over SSH." No
public example of a modder generating an entire new `PACK` record
plus new `CTDA` conditions from an xEdit script was found in this pass —
xEdit is capable in principle, but Mutagen is the tool the community
actually uses for wholesale new-record generation (that's the whole
premise of the Synthesis patcher ecosystem), and it is far better
documented for this exact task. Treat xEdit scripting as a fallback, not
the primary path.

**[F5] The Skyrim plugin file format is publicly and precisely
documented, so hand-written binary is possible in principle but is
reinventing Mutagen.** UESP's `Skyrim_Mod:Mod_File_Format/PACK` and
`.../CTDA_Field` pages document the subrecord layout precisely enough
(field names, byte offsets/types, the `<Reference>.<Function>(Param1,
Param2) <Operator> <Value>` condition-statement model) that a from-scratch
Python/C script could in theory emit valid `PACK`/`CTDA` bytes with zero
Bethesda tooling. This is real and citable, but it buys nothing over
Mutagen: Mutagen's generated code *is* an implementation of this exact
spec, already tested against the live Synthesis ecosystem, with
compression/masters/form-ID handling solved. Hand-rolling binary records
is the correct fallback only if Mutagen were somehow unavailable
(licensing, platform) — not the case here (MIT-licensed, cross-platform
.NET).

**[F6] The Creation Kit itself has no headless content-authoring mode —
this half of the avoidance doc's premise is confirmed correct.**
Documented CK command-line switches
(`-OptimizeMasterFile`, `-BuildShaderList`, `-ExportDialogue`,
`-GenerateLips:ESMName.ESM`, `-ExportFaceGenData`, `-TagifyMasterfile`,
`-ExportText`, `-CompileTextExport`, `-DelocalizeMasterfile`,
`-GenerateSEQ:PluginName.esp`) are all narrow, fixed-purpose batch
utilities for specific asset pipelines (lip sync, dialogue/text export,
master optimization, SEQ file generation) — none of them create or edit
arbitrary new records like Packages or Conditions. `ck-cmd`
(`aerisarn/ck-cmd`), the one CK-adjacent command-line tool found, is
scoped entirely to FBX→NIF mesh conversion and has nothing to do with
record editing. So: the CK GUI genuinely cannot be scripted/batched for
this task, and there is no separate CK-side automation surface for it
either — but this is moot, since F1–F3 show the task doesn't need the CK
at all.

**[F7] A no-new-content, pure-C++-runtime path exists but doesn't cover
"avoid a specific NPC" out of the box.** The local CommonLibSSE-NG header
checkout
(`/home/geoff/projects/skyrim-re-toolkit/type-importer/vendor/CommonLibSSE-NG/include/RE/A/Actor.h`)
confirms `RE::Actor::EvaluatePackage(bool, bool)` (already known from the
avoidance doc) plus a real virtual `PutCreatedPackage(TESPackage*
a_package, bool a_tempPackage, bool a_createdPackage, bool
a_allowFromFurniture)` at vtable index `0xDF` — this lets native C++ push
an arbitrary `TESPackage*` onto an actor's package stack at runtime,
bypassing the actor's authored package list entirely. `TESPackage.h`'s
`PACKAGE_PROCEDURE_TYPE` enum confirms the engine has native `kFlee = 22`
and `kAvoidPlayer = 31` procedure kinds. However, `kAvoidPlayer` is
hardcoded to the player specifically, and there is no
`kAvoidActor`/generic-target flee procedure type in the enum — so forcing
avoidance of an arbitrary *other NPC* via a vanilla, already-existing
package is not directly available. The two remaining sub-options are (a)
point `PutCreatedPackage` at a *newly authored* `TESPackage` created via
Mutagen (F1) and loaded normally — the clean, recommended combination — or
(b) hand-construct a `TESPackage` object purely in C++ memory (never
touching an .esp) and pass that pointer to `PutCreatedPackage` — feasible
in principle since the class is a plain `TESForm`-derived C++ object, but
this means manually populating the procedure-tree/condition/target-data
structures the CK's package compiler normally produces, which is
undocumented beyond header field layouts and is meaningfully more R&D
risk than just generating a `PACK` record with Mutagen and loading it as
a plugin. Not recommended as the first attempt.

## Recommendation

**Fully-programmatic (no-GUI) AI Package + Condition authoring is
realistic, low-risk, and should be attempted — the original "needs CK
GUI, out of reach" conclusion in `chronicle-bridge-avoidance-out.md` §2b
was an unresearched assumption and is incorrect.** The concrete path:
write a small Mutagen (C#/.NET, MIT-licensed) console program that (1)
creates a new `Package` record with a `Conditions` list containing a
`ConditionGlobal` (or an alias/quest-value condition, generated the same
way) referencing a global variable Chronicle's own SKSE plugin/Papyrus
side flips, (2) sets whatever procedure/target data the avoidance
behavior needs on that package, (3) edits the target NPC's or faction's
`AIPackages` list to reference it, and (4) saves the result as
Chronicle's own `.esp`. This runs as an ordinary `dotnet` process,
entirely headless, entirely reachable over SSH, with no Bethesda tool
involved at any step. Do not pursue xEdit Pascal scripting (real
capability, but weaker prior art and worse documentation for this
specific "synthesize a brand-new PACK+CTDA graph" task than Mutagen), do
not hand-roll binary `PACK`/`CTDA` bytes from the UESP spec (correct in
principle, pure reinvention of Mutagen in practice), and do not spend any
effort trying to reach the Creation Kit's interactive GUI over SSH/remote
desktop — it has no headless content-authoring surface, so that avenue is
correctly ruled out, it just isn't the *only* avenue, which is the part
the earlier doc got wrong. The `PutCreatedPackage`/`TESPackage*`
runtime-override path (F7) is worth keeping in mind as a potential
alternative *if* a Mutagen-authored package proves awkward to route
through Papyrus/SKSE glue, but it should be a second attempt, not the
first, since it requires either the same authored package as its target
or nontrivial from-scratch native construction.

## Caveats

- This pass verified Mutagen's *schema and code-generation coverage* by
  reading the actual generated C# and Loqui XML source from GitHub; it
  did not build and run a Mutagen program end-to-end against a live
  Skyrim SE install, so packaging/load-order/runtime-load specifics
  (does the game engine accept a Mutagen-authored `.esp` identically to
  a CK-authored one — it should, since Mutagen round-trips real Bethesda
  masters routinely in the Synthesis ecosystem, but this project has not
  independently confirmed it) remain an implementation-time check, not a
  research gap.
- The exact CTDA function index needed for "actor A avoids actor B
  specifically" (as opposed to the generic conditions surveyed) was not
  hunted down function-by-function; Mutagen's `Common Subrecords`
  directory make it clear the full function table is covered, but which
  named class corresponds to which specific avoidance-relevant function
  should be confirmed at implementation time via that directory listing
  or the CK's own Condition Function list.
- F7's `PutCreatedPackage` signature and the `PACKAGE_PROCEDURE_TYPE`
  enum come from CommonLibSSE-NG headers (reverse-engineered, not an
  official Bethesda source) — reliable as far as CommonLibSSE-NG's own
  track record goes, same trust level as the already-cited
  `EvaluatePackage()` finding in the original avoidance doc.
