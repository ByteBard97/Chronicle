---
date: 2026-08-27
sources:
  - adapters/skyrim/listener/whiterun-positions.json (read in full --
    the actual live-captured snapshot this pass evaluates)
  - adapters/skyrim/ChronicleBridge/src/SpatialStreamer.h + .cpp (read in
    full -- the code that produced whiterun-positions.json; confirms what
    it does and does not capture)
  - adapters/skyrim/ChronicleBridge/src/IdentityMap.cpp (kNamedCast
    table, cross-checked name-for-name against whiterun-positions.json)
  - adapters/skyrim/ChronicleBridge/src/EvidencePoller.cpp (read in full
    -- the already-shipped runtime-spawn implementation and its own
    save-growth caveat comment, this pass's baseline to compare against)
  - docs/research/31-diegetic-evidence-object-placement-spike.md and
    docs/research/32-npc-home-location-data-spike.md (this report's
    premise; re-read for their exact Mutagen/cell-resolution and
    save-bloat framing, not just their conclusions)
  - local CommonLibSSE-NG header/source checkout at
    /home/geoff/projects/skyrim-re-toolkit/type-importer/vendor/CommonLibSSE-NG
    (RE/T/TESObjectREFR.h + .cpp for `IsPersistent`/`RecordFlags::kPersistent`;
    same checkout reports 31/32 cite)
  - docs/research/00-index.md's merged [BUILD-ON] list, entry (12): the
    already-established `floor(gameX/4096)` WhiterunWorld exterior-cell
    coordinate math this pass reuses rather than re-deriving
  - web research (search-engine-extracted, direct fetch blocked by
    403s -- see Caveats): en.uesp.net/wiki/Skyrim_Mod:Save_File_Format
    and its REFR_Changeform sub-page (formID-prefix-0xFF "created form"
    handling), and a gamesas.com community thread on PlaceAtMe/savegame
    bloat, for corroboration of the Enable/Disable-vs-PlaceObjectAtMe
    save-growth claim
topic: "Could a pre-place-and-toggle evidence scheme use whiterun-positions.json's already-captured live coordinates directly, sidestepping report 32's AI-package reverse-index dead end -- and would it actually buy anything over the already-shipped PlaceObjectAtMe approach?"
status: filed
---

# Evidence Pre-Place-and-Toggle from Snapshot Coordinates: A Real, Better-Founded Version of the Idea Report 32 Rejected -- Still Not Worth Building Yet

**Document File ID:** docs/research/33-evidence-preplace-toggle-snapshot-coordinates.md

## TL;DR

`adapters/skyrim/listener/whiterun-positions.json` is a real, live-captured
snapshot (from `SpatialStreamer.cpp`'s telemetry, not the AI-package
system report 32 investigated) that covers **all 19 of 19** named-cast NPCs
with world-space X/Y -- strictly better coverage than report 32's 2-of-3
package-based sample, and it sidesteps that report's `BGSLocation::
uniqueNPCs` reverse-index dead end entirely. This pass also found and
**verified against real engine mechanics** the concrete benefit the task
asked about: `TESObjectREFR::Enable()`/`Disable()` toggling an
already-authored reference updates that reference's own single, bounded
save-file `ChangeForm` slot, while `PlaceObjectAtMe(..., true)` (the
shipped mechanism) creates a brand-new `0xFF`-prefixed "created form"
record in the save **on every single call**, permanently, confirmed by
`EvidencePoller.cpp`'s own comment and corroborated by Bethesda's
documented save-format convention (created-reference FormIDs get
distinct, permanent handling, not a routine `ChangeForm` update).
Pre-place-and-toggle also gets evidence **retraction for free**
(`Disable()`), something report 31 flagged the shipped mechanism as
explicitly lacking ("no retraction, ever"). Both benefits are real, not
hand-waved. But two new, equally real costs land at the same time: (1) the
snapshot is frozen at one arbitrary moment against NPCs Skyrim's own AI
packages move on a schedule (report 32's own F3 proved Amren/Ysolda/Braith
keep real, distinct hourly packages) -- so a marker anchored to a snapshot
position is neither "always exactly right" (the live approach) nor
"a stable, legible landmark" (report 32's rejected home-cell approach), it
is a fixed point with no narrative meaning, sometimes close to the NPC and
sometimes not; and (2) the snapshot has **no Z coordinate at all** --
confirmed by reading `SpatialStreamer.cpp`'s own capture code, which reads
a full 3-D `GetPosition()` and explicitly keeps only `.x`/`.y` -- a real,
if small, gap that has to be closed before any object could be placed
without floating or clipping through the ground. **Verdict: still not
worth building now**, but for a different, more specific reason than
report 32's: the save-growth benefit this pass verified is real but
unmeasured (no evidence yet that Chronicle's actual evidence-spawn volume
over a real save's life produces observable bloat), while the staleness
and new-authoring costs are certain and immediate. This should be
revisited if either (a) a real playtest shows the shipped mechanism
producing an uncomfortably large or ergonomically bad number of permanent
save entries, or (b) Chronicle ships toward long-running real player
saves rather than short test sessions.

## Findings

**[F1] [VERIFIED] `whiterun-positions.json` covers all 19 of 19 named-cast
NPCs, not a subset -- strictly better coverage than report 32's
package-based sample.** The file's `npcs` array has 29 entries; 19 of them
are named individuals matching `IdentityMap.cpp`'s `kNamedCast` table
name-for-name (Idolaf Battle-Born, Saffir, Carlotta Valentia, Amren,
Adrianne Avenicci, Lars Battle-Born, Braith, Fralia Gray-Mane, Nazeem,
Lillith Maiden-Loom, Brenuin, Ysolda, Anoriath, Lucia, Heimskr, Sigurd,
Olava the Feeble, Danica Pure-Spring, Olfina Gray-Mane); the remaining 10
are 6 generic "Whiterun Guard" entries and 1 "Cow", none of which are
`holderId`-addressable by `EvidencePoller.cpp` anyway (`ResolveChronicleNpcId`
only resolves `kNamedCast` entries). Ysolda -- report 32's specific
unresolved case, the one whose home package needed the
`BGSLocation::uniqueNPCs` reverse-index this project's own from-scratch
Mutagen tooling could not get working against the pinned 23.4.0 package --
has a perfectly ordinary entry here: `{"id": "ysolda", "name": "Ysolda",
"x": 25059.27, "y": -7450.68}`, already resolved through the same
`ResolveNamedCast` path `IdentityMap.cpp` uses elsewhere. This confirms
the premise: live position telemetry does not route through the
AI-package system at all, so it has none of report 32's version-sensitive,
uneven-coverage friction.

**[F2] [VERIFIED] The coordinate format is Skyrim world-space X/Y, matching
`RE::TESObjectREFR::GetPosition()`'s own coordinate space -- but there is
no Z, and this is a real capture-side gap, not a display artifact.**
`SpatialStreamer.cpp` reads a genuinely 3-D position and discards a third
of it:

```cpp
const RE::NiPoint3 pos = actorPtr->GetPosition();
out.push_back(NpcPosition{.id = std::move(id), .name = std::move(name), .x = pos.x, .y = pos.y});
```

`RE::NiPoint3` (`GetPosition()`'s return type) carries `x`, `y`, *and*
`z` -- `SpatialStreamer.h`'s own `NpcPosition` struct only declares `float
x; float y;`, so `pos.z` is read off the engine and then thrown away
before it ever reaches `whiterun-positions.json`. This is not a limitation
of the engine or the telemetry channel -- it is one field missing from one
struct and one line dropping it. Closing it (add `float z;`, populate it,
re-run the capture) is a small, mechanical change, not new research. It
is real work that has not been done, though: today's file cannot place an
object at a correct height without it -- Mutagen's `Placement.DATA`
subrecord (`P3Float name="Position"`, per report 31's F4) is a full 3-D
position field, and an authored `PlacedObject` given only X/Y (Z defaulted
to 0 or copied from some unrelated reference) would very likely spawn
underground or floating, depending on Whiterun's local terrain height at
that point -- exactly the failure mode the task's brief anticipated.

**[F3] [VERIFIED, re-reading report 31's own text] Mutagen's schema can
author position data fine; the real remaining friction is resolving which
exterior `TESObjectCELL` a given world coordinate falls in -- and this
project already has that formula from unrelated prior work, so the gap is
smaller than report 32's package reverse-index, not the same size.**
Report 31's own caveats section says this plainly and this pass confirms
it is still true: "Placing a new `PlacedObject` in a specific *exterior*
worldspace location requires resolving which grid-block `TESObjectCELL`
covers that coordinate -- this pass verified Mutagen can author
position/rotation data on a `PlacedObject`, but did not verify the
mechanics of choosing or creating the correct exterior cell block for an
arbitrary Whiterun coordinate." That is a real, structurally similar
"need a second piece of information Mutagen alone won't hand you" gap --
the same *shape* of problem report 32 hit with `BGSLocation::uniqueNPCs`.
The difference is that this project has **already solved the specific
computation** elsewhere: `docs/research/00-index.md`'s merged
`[BUILD-ON]` list (entry 12, "Dashboard map backdrop"/"Dashboard frontend
prior art") already states `WhiterunWorld` exterior cell math is
`floor(gameX/4096)` (and the analogous Y division), calibrated and
"exact for Skyrim's linear projection" for this project's own map
tooling. Applying that formula to, e.g., Ysolda's `x=25059.27,
y=-7450.68` gives a grid cell coordinate directly, which Mutagen can then
resolve to the real `CELL` FormKey the same `LinkCache.TryResolve` way
report 32's own tooling already resolved `WhiterunAmrensHouse`. This is
arithmetic plus one lookup this project has already proven works, not an
unreproduced reverse-index -- a real gap, but a **solved-elsewhere** one,
not a repeat of report 32's dead end. It has not actually been wired into
`tools/chronicle-patcher/`, so treat it as "known how, not yet done,"
consistent with this pass's spike-not-implementation scope.

**[F4] [VERIFIED against real engine mechanics and corroborated by
Bethesda's documented save-format convention] `Enable()`/`Disable()`
toggling a pre-authored reference is a bounded, single-slot save-file cost;
`PlaceObjectAtMe(..., true)` is an unbounded, permanently-growing cost --
this is the real, concrete, distinct benefit the task asked to verify, not
an assumption.** Three independent pieces of evidence converge:

1. **`EvidencePoller.cpp`'s own comment already states the cost, in this
   project's own words**, written when `a_forcePersist=true` was chosen:
   "a forced-persistent reference is never garbage collected, so every
   successful spawn is a small permanent addition to the save file for
   the lifetime of that save, compounding with [the] 'no retraction,
   ever' limitation." This is not this pass's inference -- it is the
   shipped code's own documented tradeoff, restated here because the task
   specifically asked to verify it rather than assume it.
2. **`RE::TESObjectREFR::IsPersistent()` (`TESObjectREFR.cpp`, read
   directly) resolves via `RecordFlags::kPersistent` on the reference's
   own form flags** -- a real, non-virtual, header-documented field
   (`TESForm.h`'s `RecordFlags` enum, same checkout reports 31/32 cite).
   A reference authored by Mutagen already exists as a fixed FormID in
   `ChroniclePatcher.esp`; toggling its `Enable()`/`Disable()` state
   changes that *one, already-allocated* FormID's runtime state. A
   dynamically spawned reference (`PlaceObjectAtMe`) has no FormID at all
   until the engine allocates one at spawn time.
3. **Bethesda's own save-format convention (corroborated via web search
   of `en.uesp.net/wiki/Skyrim_Mod:Save_File_Format` and its
   `REFR_Changeform` sub-page, and independently discussed in a gamesas.com
   community thread on `PlaceAtMe` savegame bloat) treats
   dynamically-created references as a structurally distinct case**: a
   changeform whose FormID is `>= 0xFF000000` is a "created" form and
   receives its own permanent handling in the save's created-object
   table, distinct from an ordinary `ChangeForm` update to a form that
   already exists in a loaded plugin. In plain terms: toggling
   `Enable()`/`Disable()` on a Mutagen-authored reference updates that
   reference's *existing* `ChangeForm` entry every time it is toggled --
   the entry count does not grow no matter how many times it flips.
   Calling `PlaceObjectAtMe(..., true)` allocates a **new** `0xFF`-prefixed
   FormID and a new permanent created-form table entry **on every call**
   -- N evidence events across a save's life means N such entries, forever,
   matching this project's own `EvidencePoller.cpp` comment exactly.

   This claim's confidence should be stated honestly: the UESP save-format
   pages themselves returned HTTP 403 to direct fetch in this pass (see
   Caveats), so the corroboration here rests on search-engine-extracted
   quotes from those pages plus a community forum thread, not a
   first-hand read of the wiki's full prose the way reports 28/30/31/32
   read their primary sources. The engine-side half of the claim
   (`RecordFlags::kPersistent`, `IsPersistent()`) *is* a first-hand header
   read at the same confidence tier as those reports.

4. **Pre-place-and-toggle also buys retraction for free**, a second real
   benefit distinct from save-growth: `Disable()` on a pre-placed
   reference removes it from the player's visible world exactly as
   cleanly as `Enable()` added it, with no new save-format cost either
   way (still the same one bounded `ChangeForm` slot). Report 31 named
   "no retraction, ever" as an accepted, unaddressed limitation of the
   shipped `PlaceObjectAtMe` design; a toggle-based design does not carry
   that limitation at all. This is worth stating plainly because it is
   not the tradeoff the task asked about (save growth) but it is real and
   it would matter if Chronicle ever wants an evidence item to disappear
   when the belief it grounds decays back below threshold.

**[F5] [REASONED, not hand-waved either direction] Snapshot staleness is
a real cost to this specific feature's purpose, distinct from both
alternatives -- neither as good as live position nor as good as report
32's rejected home-cell idea.** Report 32's own F3 already proved Skyrim's
named-cast NPCs keep genuine, distinct hourly AI packages (Amren's home
package at hour 19, Ysolda's market/patrol/inn packages at hours 8/16/20).
A coordinate frozen at whenever `whiterun-positions.json` happened to be
captured (this file's `wall_ts` corresponds to 2026-08-24) is not tied to
any of that schedule -- it is wherever that NPC happened to be standing at
one arbitrary moment, which could be mid-patrol, at a market stall, or
anywhere else in Whiterun's exterior. Compare the three options
concretely:

- **Live spawn (shipped today):** always exactly where the NPC currently
  is, by construction. Best possible discoverability relative to the NPC.
- **Report 32's rejected home-cell idea:** fixed, but at a place with real
  narrative meaning ("their house") -- legible even when the NPC isn't
  there, because the player can reason "this is where they live."
- **Snapshot coordinate (this report's subject):** fixed, but at a place
  with *no* narrative meaning -- just wherever they were standing once.
  It is worse than the home-cell idea for exactly the reason it is
  cheaper to obtain: it required no interpretation of *why* that spot
  matters, so a player has no way to reason about it either.

This is a real cost, not a rhetorical one, but it should not be overstated
into a dealbreaker: Whiterun's playable exterior is small (a walled town,
not an open region), so even an off-schedule snapshot position is very
likely still somewhere a player exploring Whiterun would pass by. The
honest framing is "diegetically weaker than either alternative, but not
necessarily broken for casual discoverability in a town this size" --
this pass did not attempt to quantify "how far can an NPC's position drift
across a full day" against Whiterun's actual map dimensions, which would
be needed to turn this from a reasoned judgment into a measured one.

## Recommendation

**Verdict: not worth building now.** The reasoning is different from, and
more specific than, report 32's -- report 32 rejected pre-place-and-toggle
because the location data itself was hard to get uniformly; this pass
shows that objection dissolves for snapshot coordinates (F1: full 19/19
coverage, no reverse-index needed). The real reasons to hold off are:

1. **F4's save-growth benefit is real but currently unmeasured, while
   F2/F5's costs are certain and immediate.** No pass (this one or
   report 31/32) has shown that Chronicle's actual evidence-spawn *volume*
   over a real save's realistic playtime produces observable bloat,
   corruption risk, or even a noticeable file-size delta -- `EvidencePoller.cpp`'s
   own comment names the cost honestly but does not quantify it, and this
   pass did not run a live save long enough to measure it either. Meanwhile,
   building the snapshot-based alternative today means paying, immediately
   and for certain: a Z-capture code change (F2), a new exterior-cell
   FormKey resolution step wired into the patcher (F3), a new Mutagen
   authoring pass and a new C++ FormID lookup table mirroring
   `AvoidanceGlobals.cpp`'s pattern, a design decision on how many markers
   to pre-author per NPC (see point 3 below), and a real, reasoned
   discoverability regression (F5) versus the live approach players get
   for free today. Paying a certain cost now to avert an unmeasured future
   cost is not a good trade without more evidence that the future cost is
   real at Chronicle's actual scale.
2. **The already-shipped mechanism is not blocked or broken -- it works
   uniformly for all 19 NPCs today**, with a known, named, accepted
   limitation (unbounded save growth, no retraction) rather than an
   unknown one. Nothing in this pass found a reason that limitation is
   urgent right now.
3. **If pursued later, a minimal version is genuinely small** (comparable
   in scope to `AvoidancePoller.cpp`'s existing 171-pair pattern, not a
   new architectural layer): (a) add `float z` to `SpatialStreamer.h`'s
   `NpcPosition` and populate it from `GetPosition().z`, re-capture
   `whiterun-positions.json`; (b) a new
   `EvidenceMarkerPatchBuilder.cs` in `tools/chronicle-patcher/`,
   authoring one `PlacedObject` per named-cast NPC at its captured X/Y/Z,
   resolving the exterior `CELL` FormKey via the `floor(coord/4096)` math
   already established for this project's dashboard tooling (F3), flagged
   `InitiallyDisabled`; (c) a new `EvidenceMarkerGlobals.cpp` FormID table,
   structurally identical to `AvoidanceGlobals.cpp`'s existing table; (d)
   an `EvidencePoller.cpp` code path that resolves a holder's pre-placed
   marker and calls `Enable()`/`Disable()` instead of (or alongside)
   `PlaceObjectAtMe`. **The open design question this sketch does not
   answer**, and would need answering first, is how many markers to
   pre-author per NPC: one marker per NPC only supports one
   currently-active evidence item at a time (losing the shipped
   mechanism's per-event granularity, where multiple simultaneous beliefs
   about the same NPC can each get their own separate physical object);
   N markers per NPC fixes that at the cost of authoring N times as much
   content and picking N in advance without knowing how many simultaneous
   evidence items any given NPC will realistically accumulate.
4. **Concrete trigger conditions to revisit, rather than leaving this
   open-ended:** (a) a live playtest surfaces an actually-large or
   ergonomically bad number of permanent `PlaceObjectAtMe` spawns in a
   real save (turning F4's currently-theoretical cost into a measured
   one), or (b) Chronicle's own roadmap shifts from short test sessions
   toward long-running real player saves, where save-file health becomes
   a real player-facing concern rather than a development-time one.

## Caveats

- **F4's save-format corroboration (the `0xFF`-prefix "created form"
  convention) rests on search-engine-extracted quotes, not a first-hand
  page read** -- `en.uesp.net/wiki/Skyrim_Mod:Save_File_Format` and its
  `REFR_Changeform` sub-page, and `ck.uesp.net/wiki/Persistence_(Creation_Kit)`,
  all returned HTTP 403 to direct fetch in this pass (both the desktop and
  mobile UESP hosts, and an archive.org mirror was also unavailable in
  this environment). The engine-side half of F4 (`RecordFlags::kPersistent`,
  `TESObjectREFR::IsPersistent()`) is a first-hand header/`.cpp` read at
  the same confidence tier reports 28/30/31/32 use; the save-file-format
  half is one tier weaker -- real and specific, but not verified by
  reading the primary source directly the way this project's convention
  otherwise requires. A future pass that can reach UESP directly (or has
  a local mirror) should confirm the `REFR_Changeform` page's exact prose
  before treating this as fully closed.
- **F3's cell-resolution path is reasoned from an existing formula, not
  re-verified against this specific dataset.** This pass did not actually
  run Mutagen against any of the 19 snapshot coordinates to confirm the
  `floor(coord/4096)` math resolves to a real, loadable `CELL` FormKey for
  each one -- it reused report 00-index's already-established figure from
  unrelated dashboard-map work and reasoned by analogy. A future pass
  picking this up should do that resolution for real before assuming it
  is friction-free for all 19 points, particularly near Whiterun's
  worldspace edges if any snapshot coordinate falls close to a cell
  boundary.
- **F5's "Whiterun is small enough that staleness may not matter much" is
  a reasoned judgment, not a measurement.** No pass has compared an NPC's
  observed daily position drift against Whiterun's actual exterior
  dimensions to produce a real discoverability estimate.
- **No live-game verification of any kind in this pass**, consistent with
  every source-reading-tier report in this series (28/30/31/32). Whether
  a Mutagen-authored, `InitiallyDisabled` `PlacedObject` at one of these
  19 specific coordinates actually renders correctly once `Enable()`'d
  from C++ remains exactly the open item report 31's own caveats already
  named for pre-place-and-toggle in general.
- This pass did not touch `chronicle/`, `adapters/skyrim/ChronicleBridge/`,
  `tools/chronicle-patcher/`, or `docs/decisions/`, and did not create a
  design-prep doc, per this task's own scope (research-and-file only).
