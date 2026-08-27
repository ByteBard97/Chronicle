# Design prep — avoidance's game-side half, via Mutagen-authored content

**Status (2026-08-26): both halves built and independently verified,
neither run against real game data yet.** `tools/chronicle-patcher/`
(Mutagen console app) and `adapters/skyrim/ChronicleBridge/src/
AvoidancePoller.{h,cpp}`/`AvoidanceGlobals.{h,cpp}` (C++ consumer) are
both committed. **A real design change from this doc's original §2
plan, found while building the C++ half**: no safe native
`SetLinkedRef`-equivalent exists on `RE::TESObjectREFR` (verified
against the real CommonLibSSE-NG 3.6.0 headers) — the "one shared
package + runtime-resolved linked-ref target" plan below is **not
viable** and was not built. The actual, working design is per-**pair**
content instead: one `TESGlobal` (`ChronicleAvoidingPair_<a>_<b>`,
sorted) and two Flee packages with hardcoded targets
(`ChronicleAvoidance_<owner>_from_<target>`) per named-cast pair (all
171 pairs generated), gated by that pair's shared global. See
`AvoidancePoller.h`'s header comment for the full finding and
`tools/chronicle-patcher/src/AvoidancePatchBuilder.cs`'s doc-comment for
the corrected authoring design. Both sides' naming/canonicalization were
independently verified to match.

**Status (2026-08-27): the "someone needs to run it" step above is
done, and it surfaced a real bug beyond the note's own expectations.**
A real Skyrim 1.6.1170 + HearthFires.esm + USSEP data set now exists in
`~/Games/ChronicleDev/` (the minimal MO2 dev instance built this
session), so the patcher was run for real. Two findings, not one:
(1) every `IdentityMap.cpp`/`.cs` FormID is a placed-reference (ACHR)
FormID, correct for the C++ runtime side but not directly resolvable
as the `NPC_` base record the patcher needs to attach Flee packages to
— fixed in `AvoidancePatchBuilder.cs` by resolving the ACHR first and
following its `.Base` link, not by mutating the shared table; (2) 5 of
the 19 named-cast entries (`amren`, `braith`, `lars_battle_born`,
`idolaf_battle_born`, `lillith_maiden_loom`) were attributed to the
wrong origin plugin (`HearthFires.esm`/USSEP instead of their real
`Skyrim.esm`) — a bug that would have silently broken runtime identity
resolution for those 5 actors too, not just the patcher. Both fixed in
`IdentityMap.cpp` and its `.cs` mirror. The corrected run succeeded in
full: 171/171 pairs, 342 packages, 19 NPC overrides. `AvoidanceGlobals.
cpp`'s 4 illustrative pairs now carry the real FormIDs from that run
(`out/chronicle-globals.json`) instead of `0x000000` placeholders.
Still not load-ordered in an actual running game — that verification,
like every other ChronicleBridge write path, remains pending.

Original design proposal follows, unchanged except where noted above.
Written
immediately after `docs/research/24-programmatic-esp-authoring.md`
retracted `chronicle-bridge-avoidance-out.md` §2b's "needs Creation Kit
GUI access" conclusion. This doc turns that research finding into a
concrete build plan for avoidance's C++/game-side half — the one piece
every ChronicleBridge slice's Python side has been waiting on since
avoidance-out.md was written.

Local environment note: the .NET 8 SDK is now installed at `~/.dotnet` on
this Linux dev machine (user-local install, no sudo, fully reversible —
`rm -rf ~/.dotnet`). Mutagen is cross-platform .NET, so **the record-
authoring half of this slice does not need the Windows build machine at
all** — only ChronicleBridge's C++ half still does (same as every other
slice).

## 0. What this closes

Rule 18 (`chronicle/driver.py`) already computes, every tick, which named-
cast NPC pairs should be avoiding each other. `chronicle/avoidance.py`'s
`is_avoiding()` and `GET /whiterun/avoidance` already expose that state.
The only missing piece, per `chronicle-bridge-avoidance-out.md` §2b/§2c,
is a game-side consumer: something that actually makes an NPC visibly
avoid another NPC in Skyrim. §2c already established the two ingredients
needed (an authored `PACK` with a gating `CTDA`, and C++ that flips the
gate and calls `RE::Actor::EvaluatePackage`) — this doc designs both.

## 1. Authoring plan (Mutagen, C#, headless, runs on this Linux machine)

**One reusable package, not 19 per-NPC packages.** A single `PACK` record,
`ChronicleAvoidance`, with:
- **Target**: a package alias resolved via `SetLinkedRef` at runtime
  (Bethesda's own "linked reference" alias-fill mechanism — the same
  mechanism vanilla follower/marriage packages use for a runtime-
  determined target). The package itself never names a specific NPC;
  C++ decides the target per-application.
- **Condition** (`CTDA`, gates the whole package): `GetLinkedRef ==
  <the target alias>` is already implied by using a linked-ref target,
  so the actual gating condition only needs to answer "is this NPC
  currently *in* avoidance mode at all" — a per-NPC global variable,
  `ChronicleAvoiding_<NpcId>` (19 globals, one per named-cast NPC,
  boolean 0/1), checked via `ConditionGlobal` (confirmed real and
  Mutagen-typed, research doc F2). This keeps the package itself generic
  (one `PACK` record, one condition shape) while letting each NPC's
  avoidance state toggle independently.
- **Procedure**: `kFlee` (confirmed present in `PACKAGE_PROCEDURE_TYPE`,
  research doc F7) targeting the linked ref, generic distance/duration
  fields left at sane defaults (the exact tuning is cosmetic, not
  load-bearing — first cut doesn't need playtesting-derived precision,
  same "placeholder, not a number to obsess over" posture as
  `vendor_markup.py`'s `MARKUP_CEILING`).
- **High priority in the AIPackages list**: for each of the 19 named-cast
  NPCs' `NPC_` records, prepend `ChronicleAvoidance` to `AIPackages`
  (`Npc.AIPackages` field, confirmed Mutagen-typed in research doc F3) —
  vanilla package-stack ordering means an earlier entry only actually
  runs when its condition passes, so this is additive and never disturbs
  existing schedules/packages when the gating global is 0.

**Why one shared package instead of 19 distinct ones:** the alternative
(a bespoke package per named-cast NPC, hardcoding the OTHER 18 as
possible targets) is combinatorially worse for zero benefit — the
linked-ref mechanism already solves "which specific other NPC" without
authoring per-pair content. Confirm this shared-package approach at
implementation time against a working xEdit/CK example of a linked-ref
Flee package if one is easy to find; if the linked-ref alias-fill
mechanism turns out not to apply cleanly to a non-quest, non-aliased
generic actor package, the fallback is a `GetIsID`-conditioned package
that checks a *pair* of globals (one holding a FormID reference via
`ConditionGlobal` doesn't directly support that — would need per-pair
booleans, 19×18 in the worst case, which is why linked-ref is strongly
preferred and should be tried first).

**New artifact**: a new top-level directory, `tools/chronicle-patcher/`
(a small C# console project, `dotnet new console`, referencing the
`Mutagen.Bethesda.Skyrim` NuGet package), producing
`ChroniclePatcher.esp` — checked into the repo as a build output next to
its generator, the same "generated but committed" posture the project
doesn't otherwise use elsewhere, flagged here as a real open question:
confirm with a quick check of `.gitignore`/repo convention at
implementation time whether generated binary game assets are ever
committed in this repo, or whether the patcher should instead run as a
documented one-time step against the owner's own load order (more likely
correct, given ChronicleBridge's own `.dll` is never committed either).

## 2. C++ half: `AvoidancePoller.h/.cpp`

Mirrors `HydrationPoller.h/.cpp`'s shape exactly (same file, same
`OutboundConfig`-taking thread-loop pattern, same main-thread task hop
via `SKSE::GetTaskInterface()->AddTask()` for the actual game-object
writes):

- `GET /whiterun/avoidance` (already implemented, listener-side) returns
  named-cast pairs whose avoidance state changed, symmetric
  (`{npc_a, npc_b, avoiding}`).
- For each pair: resolve both NPCs via `IdentityMap::ResolveChronicleNpcId`
  → `TESDataHandler::LookupForm<Actor>` (same resolution chain
  `HydrationPoller.cpp` already established — reuse it, don't
  reimplement).
- If `avoiding == true`: call the (to-be-added) native equivalent of
  `SetLinkedRef` on each actor pointing at the other (symmetric — both
  directions, since rule 18's avoidance is mutual), set both
  `ChronicleAvoiding_<npc>` globals to `1` via `RE::TESGlobal::value`
  (need to confirm exact global-lookup-by-editor-ID API at
  implementation time — likely `RE::TESDataHandler::LookupForm<RE::
  TESGlobal>()` by form ID, same pattern as `LookupForm<Actor>`, needs
  the global's FormID recorded somewhere ChronicleBridge can read it,
  e.g. a small generated header from the same Mutagen patcher run, or a
  hardcoded table mirroring `IdentityMap.cpp`'s own pattern), then call
  `actor->EvaluatePackage(true, true)` on both.
- If `avoiding == false`: set both globals back to `0`, call
  `EvaluatePackage` again to let each actor fall back to its normal
  package stack.
- Ack outcomes: `applied` (both actors resolved, both writes attempted)
  / `retry` (either actor unresolvable or no active game) — matches
  avoidance's existing two-outcome ack contract exactly, no protocol
  change needed on the listener side.

**Real open question, name honestly rather than guess:** whether
`RE::TESObjectREFR::SetLinkedRef` (the Papyrus-native's underlying
virtual) is directly callable the way `BGSRelationship::GetRelationship`
was for hydration — needs the same header-verification-over-SSH pass
`HydrationPoller`'s design got before assuming its API surface. Do not
skip that verification step; it is exactly the kind of assumption that
was wrong for hydration's ack protocol only after ready to compile.

## 3. Non-goals for this first cut

- Per-severity flee distance/duration tuning — a fixed, reasonable
  default is fine, same posture as every other placeholder constant in
  this codebase.
- Committing the generated `.esp` to the repo as a tracked binary, unless
  a quick look at repo convention says otherwise (§1).
- Any change to `chronicle/avoidance.py`, rule 18, or the listener's
  `/whiterun/avoidance` protocol — this is purely a new C++ consumer of
  an already-shipped, already-tested read path.
- In-game verification — stays exactly as scoped in
  `docs/design/chronicle-bridge-verification-runbook.md` (compiled, not
  live-tested, until someone with a real game session confirms it).

## 4. Build order

1. `tools/chronicle-patcher/` — Mutagen console app, run locally (this
   Linux machine now has a working `dotnet` toolchain), producing the
   package/condition/global records and the 19 NPC `AIPackages` edits.
2. `AvoidancePoller.h/.cpp` on the Windows build machine, following
   `HydrationPoller`'s exact pattern, verified with a real header check
   for `SetLinkedRef` before assuming the API shape, then a full clean
   rebuild over SSH (same discipline every prior C++ slice used).
3. Wire into `plugin.cpp` alongside the other three pollers.
