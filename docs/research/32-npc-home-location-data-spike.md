---
date: 2026-08-27
sources:
  - local CommonLibSSE-NG header checkout at
    /home/geoff/projects/skyrim-re-toolkit/type-importer/vendor/CommonLibSSE-NG
    (include/RE/T/TESPackage.h, include/RE/P/PackageLocation.h,
    include/RE/B/BGSLocation.h, include/RE/T/TESNPC.h) -- same checkout
    report 26/28/31 already cite
  - a pre-existing local clone of Mutagen's own source at
    /tmp/claude-1000/.../scratchpad/mutagen-src/Mutagen.Bethesda.Skyrim
    (Records/Major Records/Package.xml, Npc.xml, Location.xml, Records/
    Common Subrecords/LocationTargetRadius.xml) -- read directly for
    schema ground-truth, same clone report 31 used
  - a from-scratch standalone .NET 8 console app (not committed --
    scratchpad only), built against the real, already-restored
    Mutagen.Bethesda.Skyrim 23.4.0 NuGet package (the exact version
    tools/chronicle-patcher/src/ChroniclePatcher.csproj pins), run against
    the real Data folder at
    "~/Games/ChronicleDev/Stock Game/Data" (Skyrim.esm, Update.esm,
    Dawnguard.esm, HearthFires.esm, Dragonborn.esm loaded read-only,
    nothing written back) -- directly dumped Ysolda's, Amren's, and
    Braith's real `Package` (PACK) records and their `PackageDataLocation`
    subrecords, the same "read real records, don't guess" technique
    reports 27/28/30/31 all used
  - System.Reflection introspection of the actual installed
    Mutagen.Bethesda.Skyrim.dll (23.4.0) to resolve a schema-naming
    mismatch between the local mutagen-src git checkout (a newer/different
    version) and the pinned NuGet package this project actually builds
    against -- confirmed the two are NOT the same version and documented
    the real, installed property names
  - adapters/skyrim/ChronicleBridge/src/IdentityMap.cpp (kNamedCast table,
    checked again for a location field; still none)
  - adapters/skyrim/ChronicleBridge/src/EvidencePoller.cpp (read in full;
    confirms report 31's recommended live-position proxy is already
    shipped, not just recommended)
  - docs/research/31-diegetic-evidence-object-placement-spike.md (this
    report's premise and F5's gap)
  - chronicle/claims.py (Evidence dataclass, re-checked for a location
    field; still none)
topic: "What real NPC home/workplace location data does Skyrim already have, and how cheaply can Chronicle/ChronicleBridge get at it -- closing report 31's F5 gap?"
status: filed
---

# NPC Home-Location Data Spike: Real, Statically Readable, and Not Worth Building Yet

**Document File ID:** docs/research/32-npc-home-location-data-spike.md

## TL;DR

Skyrim's AI-package system genuinely does carry per-NPC home/workplace
location data, and a real, from-scratch Mutagen program in this pass
**successfully read it directly out of the real `Skyrim.esm`/
`HearthFires.esm` data** for 2 of the 3 requested named-cast NPCs: Amren's
and Braith's own `WhiterunAmrenHomePackage`/`WhiterunBraithHomePackage`
records each carry a `PackageDataLocation` subrecord whose target is a
plain `LocationCell` FormLink resolving to the real `WhiterunAmrensHouse`
cell record -- a fully static, no-game-logic read. Ysolda's case is the
honest complication: she has no explicit "home package" at all, only a
`DefaultSandboxHomeowner` package using the `LocationFallback`/
"near editor location" indirection, which per CommonLibSSE-NG's own
`BGSLocation::uniqueNPCs` (`LCUN`) field is resolved via a *separate*
reverse-index (which `Location` record claims this NPC as a unique actor)
rather than a direct link -- a real, header-documented mechanism, but one
this pass's own tooling hit real friction reproducing statically (see F4).
Meanwhile, `EvidencePoller.cpp` is not hypothetical -- it is **already
shipped**, already spawning evidence objects at an NPC's live
`GetPosition()`, working identically for all 19 named-cast NPCs regardless
of whether they have a resolvable home package. **Verdict: the underlying
data is `[BUILD-ON]`-tier where it exists at all (a real static Mutagen
read, no reverse-engineering), but authoring/tracking a real home-location
model for Chronicle is NOT WORTH PURSUING right now** -- the coverage is
uneven (2/3 sampled NPCs have a clean answer, 1/3 doesn't), the payoff
duplicates what EvidencePoller.cpp's live-position fallback already does
uniformly, and no roadmap item currently needs "the scene of a specific
incident" as opposed to "near this NPC."

## Findings

**[F1] [VERIFIED] `TESNPC` itself has zero home/location fields --
confirmed by reading the real header a second time, at every candidate
name.** `RE/T/TESNPC.h`'s member list (skills, class, combat style, race,
outfits, faction, head parts, tint, relationships -- every field from
offset `0x190` to `0x268`) contains nothing resembling a home marker, a
workplace cell, or a location FormLink. `RE/T/TESPackage.h`'s
`PACKAGE_DATA` (`AIDT`-equivalent read via Mutagen's own `AIData`
subrecord, independently confirmed identical: `Aggression`, `Confidence`,
`EnergyLevel`, `Responsibility`, `Mood`, `Assistance`, `Warn`,
`WarnOrAttack`, `Attack` -- no location field either) closes off the other
obvious candidate. **Any home/workplace concept in Skyrim lives on the AI
*package* system, never on the NPC or its AI-data block directly** -- this
sharpens report 31's F5, which only checked `IdentityMap.cpp`/
`chronicle/claims.py` and correctly found nothing there, but didn't yet
check whether the *engine* has the concept anywhere to read from.

**[F2] [VERIFIED] `TESPackage::packLoc` (`RE::PackageLocation`) is a real,
documented, non-virtual field carrying exactly the location-type
enumeration a home/workplace read would need**, and Mutagen's own schema
mirrors it field-for-field:

```cpp
// RE/T/TESPackage.h
PackageLocation* packLoc; // 38

// RE/P/PackageLocation.h
enum class Type {
    kNone = -1, kNearReference = 0, kInCell = 1, kNearPackageStartLocation = 2,
    kNearEditorLocation = 3, kObjectID = 4, kObjectType = 5,
    kNearLinkedReference = 6, kAtPackagelocation = 7, kAlias_Reference = 8,
    kAlias_Location = 9, kNearSelf = 12,
};
union Data { TESForm* object; ObjectRefHandle refHandle; };
```

```xml
<!-- Mutagen: Common Subrecords/LocationTargetRadius.xml -->
<Object name="LocationTargetRadius" objType="Subrecord">
  <Fields>
    <RefDirect name="Target" refName="ALocationTarget" .../>
    <UInt32 name="Radius" />
  </Fields>
</Object>
<Object name="LocationCell" baseClass="ALocationTarget" objType="Subrecord">
  <Fields><FormLink name="Link" refName="Cell" /></Fields>
</Object>
<Object name="LocationTarget" baseClass="ALocationTarget" objType="Subrecord">
  <Fields><FormLink name="Link"><Interface>IPlaced</Interface></FormLink></Fields>
</Object>
<Object name="LocationFallback" baseClass="ALocationTarget" objType="Subrecord">
  <Fields>
    <Enum name="Type" enumName="LocationTargetRadius.LocationType" byteLength="4" />
    <Int32 name="Data" />
  </Fields>
</Object>
```

`RE::`'s `kInCell`/`kNearReference`/`kNearEditorLocation` map 1:1 onto
Mutagen's `LocationCell`/`LocationTarget`/`LocationFallback` variants --
the two independently-sourced schemas (a C++ header checkout and a C#
Loqui schema, maintained by different open-source projects) agree exactly,
the same cross-confirmation pattern report 31's F1-F4 used.

**[F3] [VERIFIED, real-data proof-of-concept] Two of the three sampled
named-cast NPCs have a plain, statically-readable home-location package --
no game logic, no reverse-engineering, a direct field read.** A from-
scratch Mutagen console app (built against the exact
`Mutagen.Bethesda.Skyrim` 23.4.0 package `tools/chronicle-patcher/` itself
pins) loaded the real `Skyrim.esm`+`HearthFires.esm` from
`~/Games/ChronicleDev/Stock Game/Data` and printed every package on
Amren's, Braith's, and Ysolda's real NPC records. Amren's real output:

```
[Packages] Package WhiterunAmrenHomePackage (02C901:Skyrim.esm) type=Package schedHour=19
    -> LOCATION target type=LocationCell radius=0
       Cell: WhiterunAmrensHouse (0165AB:Skyrim.esm)
```

Braith's real output (she shares the same house):

```
[Packages] Package WhiterunBraithHomePackage (02C903:Skyrim.esm) type=Package schedHour=-1
    -> LOCATION target type=LocationCell radius=0
       Cell: WhiterunAmrensHouse (0165AB:Skyrim.esm)
[Packages] Package WhiterunBraithSleep21x12 (10F979:Skyrim.esm) type=Package schedHour=21
    -> LOCATION target type=LocationCell radius=0
       Cell: WhiterunAmrensHouse (0165AB:Skyrim.esm)
```

This is a real `CELL` FormKey (`0165AB:Skyrim.esm`), resolvable the exact
same `LinkCache.TryResolve` way `tools/chronicle-patcher/` already
resolves other records -- editor-ID-named, human-legible
(`WhiterunAmrensHouse`), and requires zero AI-package procedural logic to
interpret: the package's own name (`...HomePackage`) and schedule hour
(19, 21 -- evening/night) corroborate that this is what a person would
call "home" without needing any further inference.

**[F4] [NEW FRICTION, not a blocker but a real limit] Not every NPC has an
explicit home package -- some resolve "home" through a second-order
reverse-index this pass could not fully reproduce with the pinned Mutagen
version.** Ysolda's real package list has no `...HomePackage` entry at
all:

```
[Packages] Package WhiterunYsoldaMarket8x7        schedHour=8  -> LocationTarget (a market stall ref)
[Packages] Package WhiterunYsoldaCarryBasketPatrol16x4 schedHour=16 -> TARGET (no location)
[Packages] Package WhiterunYsoldaBanneredMarePackage20x4 schedHour=20 -> LocationTarget (the Bannered Mare)
[Packages] Package DefaultSleepEditorLoc24x8      schedHour=0  -> LocationFallback radius=2000
[Packages] Package DefaultSandboxHomeowner        schedHour=-1 -> LocationFallback radius=1500
```

`DefaultSandboxHomeowner`/`DefaultSleepEditorLoc24x8` use
`kNearEditorLocation` (Mutagen's `LocationFallback`), which per `RE/B/
BGSLocation.h`'s own `uniqueNPCs` field (`BSTArray<UniqueNPCData>`, "LCUN")
resolves via a *location-owns-the-NPC* reverse index, not an NPC-owns-a-
location forward link -- Mutagen's own `Location.xml` confirms the same
shape exists in the file format (`UniqueActorReferencesStatic`/`LCUN`:
`{Actor: Npc, Ref: PlacedNpc, Location: Location}`). **This pass tried to
read that reverse-index directly and hit a real, documented version
mismatch**: the local `mutagen-src` git checkout used for schema reading
in this and report 31 is a *newer* Mutagen version than the
`23.4.0` NuGet package this project's own `ChroniclePatcher.csproj`
actually pins and builds against (confirmed via `System.Reflection` against
the real installed DLL: the 23.4.0 assembly names the equivalent fields
`ActorCellUniques`/`LocationCellUniques`/`ReferenceCellUnique`, an
unrelated-looking, apparently auto-generated naming scheme, not the git
checkout's `UniqueActorReferencesAdded/Static/Removed`). Querying
`LocationCellUniques` in 23.4.0 against the real data returned zero
matches for Ysolda -- **not proof the mechanism is fictional (the header/
schema evidence for it is solid, per F1-F2), but a real, first-hand
demonstration that resolving a "no explicit home package" NPC's location
costs meaningfully more engineering than F3's clean cases**: version-
sensitive schema navigation, a second FormKey hop through whichever
placed-actor reference LCUN actually points at, and (per this pass's
inconclusive result) possibly game-only editor-time data that never made
it into any binary record Mutagen can read at all. This was not chased
further, per this task's own scope (spike, not implementation).

**[F5] [VERIFIED] `EvidencePoller.cpp`'s live-position proxy (report 31's
recommendation) is not a future plan -- it is already shipped, real code,
and covers all 19 named-cast NPCs uniformly regardless of F3/F4's uneven
static coverage.** Read directly:

```cpp
// EvidencePoller.cpp
RE::Actor* believer = ResolveLiveActor(entry.holderId);
...
auto spawned = believer->PlaceObjectAtMe(evidenceObject, true);
```

This resolves through `IdentityMap.cpp`'s existing reverse lookup and
calls the same `PlaceObjectAtMe` report 31's F2 verified, using whatever
position the actor is *actually standing at right now* -- Ysolda at the
market, Amren at home, doesn't matter which. It needs zero location data
of any kind, works identically for the NPC with a clean home package
(Amren) and the one without (Ysolda), and needs no version-sensitive
Mutagen reverse-index work at all. The comment in the file candidly notes
this is "UNVERIFIED against a live save -- compiled only" (an orthogonal,
already-flagged caveat from report 31, not something this pass re-checked)
-- but the *design choice* to use live position rather than a home-cell
model is not a hypothetical to weigh; it is the actual, current,
committed implementation.

## Recommendation

**Building or authoring a real "NPC home/workplace location" data model
for Chronicle is NOT WORTH PURSUING right now.** Reasoning:

1. **The data exists and is real (F1-F3), but coverage is uneven by
   construction, not by this pass's limitation.** Some named-cast NPCs
   (Amren, Braith) have a clean, one-hop static answer. Others (Ysolda --
   and this pass only checked 3 of 19; there is no reason to expect the
   other 16 split any better) require a second-order reverse-index lookup
   that is real per CommonLibSSE-NG's headers (F4) but meaningfully harder
   to implement, and this pass's own attempt to reproduce it against the
   actual pinned Mutagen version came back empty. A home-location model
   built today would need a per-NPC fallback path anyway (some NPCs
   resolve, some don't) -- which is exactly the shape `EvidencePoller.cpp`
   already has today, for free, using live position as the universal case
   rather than the exceptional one.
2. **No roadmap item currently needs "the scene of a specific incident"
   as distinct from "near this NPC."** Report 31 already established that
   `chronicle/claims.py`'s `Evidence` dataclass has no location concept at
   all (belief-scoped, not event-scoped) -- adding a home-location table
   would need a *second*, independent design decision (what "the scene of
   an incident" even means, tracked separately from any NPC's current or
   home position) before it would pay for anything. That decision was
   correctly out of scope for report 31 and remains out of scope here;
   nothing in this pass surfaced a concrete feature that needs it.
3. **The already-shipped alternative is uniformly cheaper and already
   working.** `EvidencePoller.cpp`'s live-position spawn needs no new
   Mutagen authoring, no version-sensitive reverse-index code, no new
   identity table, and treats all 19 named-cast NPCs identically. The
   marginal value of "spawn it at their house instead of wherever they are
   standing" is a flavor improvement (arguably a *worse* one for evidence
   discoverability -- the player is more likely to encounter the NPC in
   person than to go find their house), not a capability unlock.
4. **If a real future need appears** -- e.g., a genuine "incident scene"
   concept independent of any single NPC's position, or a design that
   specifically wants "spawn evidence at the believer's home even when
   they're not there" -- revisit F3's clean case first (it is real,
   cheap, and already proven against real data for at least 2 NPCs) and
   budget real engineering time for F4's reverse-index path before
   assuming full 19-NPC coverage is achievable the same way.

**Classification: real static home-location data is `[BUILD-ON]`-tier
where a plain home package exists (F3, same tier as report 31's plain-
field mechanisms) — but pursuing it as a Chronicle feature right now is a
non-problem, not a gap: `EvidencePoller.cpp`'s existing live-position
proxy is sufficient for the foreseeable roadmap** and should stay the
answer until a concrete design need for scene-independent location data
is identified.

## Caveats

- **Only 3 of 19 named-cast NPCs were sampled** (as the task requested).
  F3's clean 2/3 hit rate is a real, direct-data result, not an estimate,
  but it should not be read as "most named-cast NPCs have a home
  package" -- it's one data point at n=3. A future pass wanting a real
  coverage number would need to run this pass's same dump against all 19.
- **F4's reverse-index dead end is inconclusive, not a refutation.** This
  pass confirmed the *mechanism* is real (header-documented on both the
  CommonLibSSE-NG and Mutagen sides) but did not successfully resolve
  Ysolda's actual home location through it -- possibly a remaining schema-
  navigation mistake in this pass's own scratch code (the 23.4.0
  property names are unusually generic and easy to misuse), possibly a
  genuine limit of what's recoverable outside a live game session. Either
  way, treat "no home found for an NPC without an explicit HomePackage" as
  the honest current state, not as proof no such data exists.
- **The local `mutagen-src` git checkout used for schema reading in this
  report and report 31 is confirmed to be a different (newer) version
  than the `23.4.0` package this project's own `tools/chronicle-patcher/`
  actually builds against.** This did not affect report 31's findings
  (those schema reads matched 23.4.0's real behavior, spot-checked in this
  pass), but F4 shows it *can* matter when a schema's shape changed
  between versions (`UniqueActorReferencesStatic` vs.
  `LocationCellUniques`) -- future passes reading `mutagen-src` for schema
  ground-truth should cross-check against the installed package's actual
  members (e.g., via `System.Reflection`, as done here) before assuming
  the git checkout's field names are what code will actually compile
  against.
- No live-game verification of any kind in this pass, consistent with
  every prior source-reading-tier report in this series.
- This pass did not touch `chronicle/`, `adapters/skyrim/ChronicleBridge/`,
  or `tools/chronicle-patcher/`, and did not create a design-prep doc, per
  this task's own scope (research-and-file only). The standalone .NET
  dump program used to produce F3/F4's real output lives only in this
  session's scratchpad, not in the repo.
