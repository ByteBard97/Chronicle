---
date: 2026-08-27
sources:
  - local CommonLibSSE-NG header/source checkout at
    /home/geoff/projects/skyrim-re-toolkit/type-importer/vendor/CommonLibSSE-NG
    (RE/T/TESObjectREFR.h + .cpp, RE/T/TESDataHandler.h + .cpp)
  - github.com/Styyx1/SurpriseSpawner, src/Events.cpp (public GitHub repo)
    — a real, shipped-style SKSE plugin that spawns enemies/props on
    activate events and toggles `Enable()`/`Disable()` on the triggering
    reference, using the exact same `SKSE::GetTaskInterface()->AddTask()`
    main-thread-hop pattern ChronicleBridge's own pollers already use
  - github.com/HarperZ9/skyrimbridge, src/core/ModelSpawn.cpp (public
    GitHub repo) — a second, independent, "bridge"-named SKSE plugin that
    spawns a dynamic static model reference at runtime relative to the
    player
  - a pre-existing local clone of Mutagen's own source at
    /tmp/claude-1000/.../scratchpad/mutagen-src/Mutagen.Bethesda.Skyrim
    (Records/Major Records/PlacedObject.xml + .cs, Records/Common
    Subrecords/Placement.xml) — read directly for schema ground-truth,
    not taken from documentation prose
  - docs/design/kimi-architecture-delta-audit.md (this report's premise)
  - docs/research/28-vendor-price-hook-address-library-spike.md and
    docs/research/30-crime-witness-prior-art-spike.md (the process
    template this pass follows: read real shipped source, not just
    headers)
  - docs/design/chronicle-bridge-avoidance-mutagen-out.md,
    docs/design/chronicle-bridge-vendor-markup-out.md,
    tools/chronicle-patcher/README.md (the established three-layer
    pattern and the patcher's current authoring scope)
  - chronicle/claims.py (Evidence dataclass, read directly for the real
    field name/shape)
  - adapters/skyrim/ChronicleBridge/src/IdentityMap.cpp (checked for an
    existing home-reference concept; none found)
  - GitHub code search (`gh api search/code`) for `PlaceObjectAtMe` and
    `IsInitiallyDisabled` usage in real C++ SKSE plugins
topic: "Can ChronicleBridge place or move a physical object in the world at runtime for a 'diegetic evidence' slice, and what does it actually cost?"
status: filed
---

# Diegetic Evidence: Object-Placement Spike — Both Mechanisms Are `[BUILD-ON]`, the Real Gap Is Location Data

**Document File ID:** docs/research/31-diegetic-evidence-object-placement-spike.md

## TL;DR

Both candidate mechanisms the task asked about — pre-place-and-toggle and
spawn-at-runtime — are **fully inside CommonLibSSE-NG's already-documented,
`RELOCATION_ID`/vtable-backed API surface**, confirmed by reading the real
`.cpp` implementations (not just header declarations), and **confirmed a
second time by reading two independent real, shipped SKSE plugins that use
exactly these calls** (`Styyx1/SurpriseSpawner`, `HarperZ9/skyrimbridge`).
Unlike vendor-markup (report 26→28) and crime-witness (report 29→30), this
pass found no reverse-engineering trap at all to correct — the header-only
read and the prior-art read agree from the start. Mutagen, independently
verified against its own source, can already author a `PlacedObject`
(`REFR`) record with a base-object link, a world position/rotation
(`Placement.DATA`), and an `InitiallyDisabled` flag — the exact ingredients
report's §1 pre-place-and-toggle option needs. **The real open item this
pass surfaced is not the game-engine mechanism at all — it's that
Chronicle currently has zero location data to bind evidence to.**
`IdentityMap.cpp`/`.cs` carry only each named-cast NPC's own placed-actor
FormID, no home/workplace interior cell, and `chronicle/claims.py`'s
`Evidence` dataclass carries no location field either (only
`belief_id`/`source_id`/`evidence_type`/`strength`/`gamets`) — "near where
an incident happens" is not a slot Chronicle's model currently populates
anywhere. **Verdict: `[BUILD-ON]`** for both engine-side mechanisms, at the
same risk tier as hydration/avoidance's plain-field writes — but scoping a
real slice needs a location-modeling decision first, which this pass
correctly stops short of making.

## Findings

**[F1] [VERIFIED] `RE::TESObjectREFR::Enable()`/`Disable()` are real,
documented, `RELOCATION_ID`/vtable-backed calls — the pre-place-and-toggle
mechanism needs zero reverse-engineering.**

```cpp
// include/RE/T/TESObjectREFR.h
void Enable(bool a_resetInventory);                              // non-virtual
SKYRIM_REL_VR_VIRTUAL void Disable();                             // 89, virtual

// src/RE/T/TESObjectREFR.cpp
void TESObjectREFR::Enable(bool a_resetInventory) {
    using func_t = decltype(&TESObjectREFR::Enable);
    REL::Relocation<func_t> func{ RELOCATION_ID(19373, 19800) };
    return func(this, a_resetInventory);
}
void TESObjectREFR::Disable() {
    REL::RelocateVirtual<decltype(&TESObjectREFR::Disable)>(0x89, 0x8A, this);
}
```

`Enable` resolves via a plain `RELOCATION_ID` (SE 19373 / AE 19800) —
identical idiom to every other already-used relocation in this project's
checkout (e.g. report 28's `VTABLE_BarterMenu`). `Disable` is a documented
virtual at vtable slot `0x89`/`0x8A` (SE/AE), resolved the same
`RelocateVirtual` way this project's own `RE::TESObjectREFR::MoveTo`-
adjacent calls already work. Both are exactly the kind of "plain
documented `RE::` field/call" tier every prior ChronicleBridge slice has
used — not the vtable-swap-on-a-menu tier vendor-markup needed, and not
the raw-trampoline-onto-unnamed-function tier crime-witness's event
hooking needed.

**[F2] [VERIFIED] `RE::TESObjectREFR::PlaceObjectAtMe()` and the
`RE::TESDataHandler::CreateReferenceAtLocation()` it wraps are real,
documented, `RELOCATION_ID`-backed calls — the spawn-at-runtime mechanism
also needs zero reverse-engineering.**

```cpp
// src/RE/T/TESObjectREFR.cpp
NiPointer<TESObjectREFR> TESObjectREFR::PlaceObjectAtMe(TESBoundObject* a_baseToPlace, bool a_forcePersist) const {
    const auto handle = TESDataHandler::GetSingleton()->CreateReferenceAtLocation(
        a_baseToPlace, GetPosition(), GetAngle(), GetParentCell(), GetWorldspace(),
        nullptr, nullptr, ObjectRefHandle(), a_forcePersist, true);
    return handle.get();
}

// include/RE/T/TESDataHandler.h
ObjectRefHandle CreateReferenceAtLocation(TESBoundObject* a_base, const NiPoint3& a_location,
    const NiPoint3& a_rotation, TESObjectCELL* a_targetCell, TESWorldSpace* a_selfWorldSpace,
    TESObjectREFR* a_alreadyCreatedRef, BGSPrimitive* a_primitive,
    const ObjectRefHandle& a_linkedRoomRefHandle, bool a_forcePersist, bool a_arg11);
```

`CreateReferenceAtLocation` itself resolves via its own `RELOCATION_ID` in
`TESDataHandler.cpp` (confirmed by direct grep — same idiom, not shown
again here for brevity). `PlaceObjectAtMe` is literally the Papyrus-native
`PlaceAtMe`'s underlying C++ implementation, callable directly on any
`TESObjectREFR*` (an NPC actor, the player, or any other reference) to
spawn a new reference of an arbitrary base object at that reference's own
position.

**[F3] [VERIFIED, two independent real-world confirmations] Both
mechanisms are used together, in production-style SKSE plugin code, not
just declared in headers.** `Styyx1/SurpriseSpawner`'s `Events.cpp`:

```cpp
auto mimic = a_eventItem->PlaceObjectAtMe(a_enemyToSpawn, false)->AsReference();
...
mimic->MoveTo(a_eventItem);
...
a_eventItem->Disable();
```
and, in a separate branch of the same file:
```cpp
SKSE::GetTaskInterface()->AddTask([=] { a_eventItem->Enable(false); });
```

This is a real, git-hosted plugin that spawns an object/actor at another
reference's position on an activation event, later toggles `Disable()`/
`Enable()` on the original reference, and — notably for this project's own
conventions — routes every actual game-object write through
`SKSE::GetTaskInterface()->AddTask()`, the exact same main-thread task-hop
idiom `HydrationPoller`/`AvoidancePoller`/`VendorPriceHook` already use.
Independently, `HarperZ9/skyrimbridge` (a second, unrelated "bridge"-named
SKSE plugin, structurally the closest analog to ChronicleBridge itself
found in this pass) does the plain spawn case:

```cpp
// src/core/ModelSpawn.cpp
auto ref = player->PlaceObjectAtMe(stat, false);
```

spawning a dynamically-created `TESObjectSTAT` model reference relative to
the player. Two independent authors, two different use cases, same two
calls — this is prior art at the same confidence tier report 30 found for
`fireundubh/LibFire`'s `GetCrimeValue()` read, not a single untested
data point.

**[F4] [VERIFIED, direct schema read] Mutagen can already author the
exact record shape pre-place-and-toggle needs: a placed reference with a
base-object link, an authored world position/rotation, and an
initially-disabled flag.** Read directly from Mutagen's own source
(`Records/Major Records/PlacedObject.xml`/`.cs`, `Records/Common
Subrecords/Placement.xml`), not from documentation:

```xml
<!-- PlacedObject.xml -->
<Object name="PlacedObject" recordType="REFR" baseClass="SkyrimMajorRecord" ...>
  <FormLink name="Base" recordType="NAME"><Interface>IPlaceableObject</Interface></FormLink>
  ...
  <RefDirect name="Placement" refName="Placement" />
</Object>

<!-- Placement.xml -->
<Object name="Placement" objType="Subrecord" recordType="DATA">
  <Fields>
    <P3Float name="Position" />
    <P3Float name="Rotation" />
  </Fields>
</Object>
```

```csharp
// PlacedObject.cs (MajorRecordFlag)
InitiallyDisabled = 0x0000_0800,
```

This is the same class of Mutagen-schema fact this project's own patcher
README already documents finding for `PACK`/`Package`/`GlobalShort`
records (`tools/chronicle-patcher/README.md`'s "Targeting" and "Design
decision" sections) — a real, Loqui-generated, binary-round-trippable
record type, not an inferred capability. A `PlacedObject` authored this
way is exactly a Skyrim ACHR/REFR-equivalent placed reference: give it a
`Base` FormLink to a `MISC`/`WEAP`/`STAT` record, a `Placement.Position`/
`Rotation`, and the `InitiallyDisabled` flag, and it is byte-for-byte the
same kind of record CK-authored "quest prop starts hidden, script/global
reveals it" content already uses in vanilla and modded Skyrim — this
pass did not find a specific third-party mod's source doing this exact
CK-adjacent pattern (unlike F3's runtime-spawn confirmation), so treat
"Mutagen can author the record" as independently schema-verified but not
yet corroborated by a second real mod's use of it the way F1–F3 are.

**[F5] [NEW GAP, not a mechanism risk] The engine-side mechanism is solved;
Chronicle's own data model has no location concept to bind evidence to.**
Two separate checks in this pass came back empty:

- `adapters/skyrim/ChronicleBridge/src/IdentityMap.cpp`'s `kNamedCast`
  table carries `(pluginName, localFormId, chronicleNpcId)` for each
  NPC's own placed *actor* reference — nothing about a home, workplace, or
  any other interior/exterior cell tied to that NPC. There is no existing
  "NPC's home reference" concept anywhere in this project's C++ or C#
  identity tables to bind evidence content to for free.
- `chronicle/claims.py`'s `Evidence` dataclass (the record the task's
  brief pointed at) is: `id, belief_id, evidence_type, source_id,
  predecessor_belief_id, gamets, strength`. **The field is named
  `strength`, not `evidentiary_strength`** (the audit doc's paraphrase) —
  a float on a per-*belief* record (what one NPC believes, grounded via
  `evidence_type: "witnessed" | "reported"`), not a per-*claim* or
  per-*canonical-event* record. It carries no location field of any kind.
  `source_id` names who the evidence came from, not where it physically
  is.

This means "place an object near where an incident happens" is not
something Chronicle can resolve today from existing fixture/identity data
— it would require deciding and adding new state (e.g., a per-canonical-
event location, or a per-NPC home-cell table mirroring `IdentityMap`'s own
conventions) before any authoring or C++ work could target a real place.
Binding evidence to "the NPC's own placed actor reference's current
position" (using `HydrationPoller`'s existing `Actor*` resolution and
`GetPosition()`, already read in F2's `PlaceObjectAtMe` signature) is a
plausible cheap substitute that needs zero new location data — it reads
"near this named-cast NPC, wherever they currently are" rather than "at
the scene of the incident," a smaller and more honest claim.

## Recommendation

**Both engine mechanisms: `[BUILD-ON]`, same risk tier as hydration/
avoidance's plain-field writes and vendor-markup's post-report-28
vtable-swap — no reverse-engineering, no address hunt, confirmed twice
over (headers + real shipped plugins).** Concretely:

1. **Prefer spawn-at-runtime (`PlaceObjectAtMe`) over pre-place-and-toggle
   for a first cut, reversing the task's own stated cheapness ordering.**
   Pre-place-and-toggle needs new Mutagen-authored content (F4) *and* a
   new FormID-lookup table on the C++ side (mirroring
   `AvoidanceGlobals.cpp`'s pattern) *and* a resolved world/cell position
   at authoring time — which per F5 Chronicle cannot currently supply.
   Spawn-at-runtime needs no new Mutagen content at all: call
   `npcActor->PlaceObjectAtMe(evidenceBaseObject, true)` on the already-
   resolved `Actor*` `HydrationPoller`'s `ResolveLiveNpc` chain already
   produces, using the actor's own live position as the location. This
   inverts vendor-markup/avoidance's usual "Mutagen does the heavy
   lifting" shape, but only because F5's real gap (no location data) makes
   the usual shape not cheaper here.
2. **Scope the simplest real "evidence object" as a single pre-authored
   `MISC` or `WEAP` item** (a bloodied dagger, a torn note — reusing an
   existing vanilla base object needs no new Mutagen record at all;
   authoring one new `MISC`/`WEAP` base record is a small, already-
   demonstrated Mutagen capability, well inside what the patcher's current
   `GlobalShort`/`Package`/NPC-override authoring already proves out).
   Skip decal/`BGSDecalGroup` content for a first cut — F4 verified
   `PlacedObject` schema support for a base object generally, but decal
   placement/spawning was not separately verified in this pass and adds
   an unconfirmed dimension for no clear first-cut benefit over a plain
   item drop.
3. **Do not schedule pre-place-and-toggle until a location-modeling
   decision is made.** It is not blocked by any engine-side unknown (F1,
   F4) — it is blocked by a Chronicle-side data-model question (what
   "where an incident happens" even means) that this research pass
   correctly did not answer, per the task's own scope. That decision
   belongs in a design-prep pass, not this one.
4. **Follow the established three-layer split exactly once the location
   question is settled**: Python (`chronicle/`) computes which evidence
   should exist and (new) where; a Mutagen step authors any new base
   objects (not placed references, if recommendation 1 is followed); C++
   calls `PlaceObjectAtMe`/`Enable`/`Disable` on the already-resolved
   `Actor*`. This reuses `HydrationPoller`'s existing NPC-resolution chain
   verbatim — no new resolution mechanism needed.

## Caveats

- **F4's `PlacedObject`/`InitiallyDisabled` schema read is independently
  verified against Mutagen's own source, but not corroborated by a second
  real mod's use of the exact pattern the way F1–F3 are** — this pass
  found strong runtime-spawn prior art (F3) but did not find a
  CK/Mutagen-authored "quest prop starts hidden, toggled by global" example
  in the wild to read start-to-finish. If pre-place-and-toggle is picked
  up later, spend a short pass finding one (the way report 30 found
  `Skyrim-Crime-Extensions`) before assuming the whole chain (base object
  → placement → cell resolution → `InitiallyDisabled` → runtime toggle)
  behaves as expected in-game.
- **Placing a new `PlacedObject` in a specific *exterior* worldspace
  location requires resolving which grid-block `TESObjectCELL` covers that
  coordinate** — this pass verified Mutagen can author position/rotation
  data on a `PlacedObject`, but did not verify the mechanics of choosing
  or creating the correct exterior cell block for an arbitrary Whiterun
  coordinate. Binding evidence to an NPC's own actor position (this
  report's recommendation 1) or to an existing interior cell sidesteps
  this entirely; only a "fixed outdoor spot" design would need it solved.
- **No live-game verification of any kind in this pass** — F1–F3's
  confidence rests on real header/`.cpp`/shipped-plugin-source reads, the
  same evidentiary standard reports 28/30 used before their own
  live-verification caveats. Whether a Mutagen-authored `PlacedObject`
  with `InitiallyDisabled` actually behaves correctly once
  `Enable()`/`Disable()`d from C++, and whether `PlaceObjectAtMe`'s
  dynamically-created reference persists correctly across a save/reload,
  are real open questions a short in-game smoke test would settle, not
  addressed here.
- This pass did not touch `chronicle/`, `adapters/skyrim/ChronicleBridge/`,
  `tools/chronicle-patcher/`, or `docs/decisions/`, and did not create a
  design-prep doc, per this task's own scope (research-and-file only).
