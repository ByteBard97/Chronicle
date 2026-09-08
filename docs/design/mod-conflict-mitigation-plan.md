# Mod-conflict mitigation plan for ChronicleBridge's four write paths

**MAJOR CORRECTION (2026-09-05, third review pass): the SkyPatcher recommendation in §1 is invalidated —
read "§1 corrected assessment" before acting on anything below that references SkyPatcher.** All three external
research tools recommended distributing avoidance's Flee packages via a SkyPatcher directive named
`packageListAdd`. Direct inspection of SkyPatcher's actual source (`Zzyxz/SkyPatcher` on GitHub — verified
against a real installed copy of the compiled DLL already present on this machine, not just the source) shows
its complete NPC-patching directive table has no package-list mechanism at all: `keywordsToAdd`, `factionsToAdd`,
`perksToAdd`, `spellsToAdd`, `objectsToAdd`, `shoutsToAdd` all exist; nothing for AI packages. The one `aipackages`
string found in the compiled binary turned out to be a `TEMPLATE_USE_FLAG` bit (whether an NPC inherits its
packages from a template NPC) — an unrelated mechanism, not a way to add a new package. `packageListAdd` does not
exist anywhere in SkyPatcher's source; it was never real. Action items 2 and 4 below (which depend on it) are dead
ends as written. See "§1 corrected assessment" for the real remaining options.

**Status (2026-09-05): synthesis complete, reviewed three times (advisor+Kimi together, then a second independent
Kimi pass, then this SkyPatcher correction from direct source verification), and real code changes now exist for
two of the four subsystems (§3 `HydrationPoller`, §4 `EvidencePoller`) — both verified to compile clean (full
rebuild, zero errors, on the real Windows build machine) and the existing unit suite still passes. AI-package
distribution (§1) is now decided in principle (Quest Alias injection, confirmed Mutagen-authorable without
Papyrus) but not yet implemented — it's gated on live-verifying the current avoidance design first, per this
project's own freeze doctrine. Vendor-price (§2) is unaffected and still just needs one live-game test.** The second Kimi pass ran against a version of this document that
predated the first review's ordering/freeze-doctrine/adoption-data fixes, so most of its critique had already been
addressed by the time it landed — those points aren't repeated here. It did surface two things the first pass
missed, both folded in below: a sharper, corrected read of the evidence-boundedness question (bounded per belief,
not per NPC — but a separate, listener-restart duplicate-spawn risk compounds it), and direct confirmation (a grep,
not an inference) that Chronicle's patcher authors zero quest records today, strengthening the
`OnStoryRelationshipChange` cost warning from "unverified" to "confirmed absent." This document consolidates ten external research reports (three tools
— Gemini, Kimi, Claude — each answering four prompts) plus two internal consultations (Kimi + `advisor` on the
dependency question, then a second Kimi + `advisor` pass reviewing this document itself against its own sources)
into a single mitigation plan. Every claim below was cross-checked against Chronicle's actual source
(`adapters/skyrim/ChronicleBridge/src/`) and existing design docs before being accepted — several external claims
were rejected or corrected in the process, and the review pass caught one real internal contradiction (the original
action-item ordering) plus several claims this document had stated more confidently than the source reports
actually support; those corrections are called out inline throughout, not just here.

Source material: `docs/research/mod-conflict-external-reviews-2026-09/` (the ten raw reports, plus an index
explaining what each one contributes and its sourcing quality). Original prompts:
`notes/mod-conflict-research-prompts-2026-09-05.md`.

## Scope

ChronicleBridge writes into live game state through four paths, all currently scoped to the same 19 named Whiterun
NPCs (Ysolda, Idolaf Battle-Born, Saffir, Carlotta Valentia, Amren, Adrianne Avenicci, Lars Battle-Born, Braith,
Fralia Gray-Mane, Nazeem, Lillith Maiden-Loom, Brenuin, Anoriath, Lucia, Heimskr, Sigurd, Olava the Feeble, Danica
Pure-Spring, Olfina Gray-Mane):

1. **AI package / schedule override** (`AvoidancePoller.cpp`, `tools/chronicle-patcher/`) — a headless Mutagen
   patcher directly overrides the `AIPackages` list on these 19 NPCs' base `NPC_` records with new Flee packages,
   gated by per-pair `TESGlobal`s the C++ plugin flips at runtime (`Actor::EvaluatePackage` forces reevaluation).
2. **Native vendor-price hook** (`VendorPriceHook.cpp`) — overwrites a vtable slot in `RE::BarterMenu`
   (`PostCreate`) to intercept the ActionScript `UpdateItemCardInfo` callback and multiply displayed item prices by
   a player-directed markup.
3. **Relationship-rank writes** (`HydrationPoller.cpp`) — writes vanilla relationship rank
   (Confidant/Ally/Lover/Friend/Rival/Foe) for the 19 NPCs at runtime, driven by simulated grudges/rumors.
4. **Persistent object spawning** (`EvidencePoller.cpp`) — calls `PlaceObjectAtMe(evidenceObject, true)`
   (`forcePersist=true`) at a believer NPC's live position.

Two other ChronicleBridge components were explicitly out of scope for this research (passive multi-subscriber SKSE
event sinks and a read-only position poller — essentially zero conflict risk).

---

## 1. AI package / schedule override

**Verdict: real, confirmed, and precedented — migrate off the current design.** All three tools independently
confirm this is a textbook "last plugin in load order wins" record conflict, and name the same dominant offender:
**AI Overhaul SSE** (36,103 endorsements), which edits the exact same `NPC_`/`AIPackages` field on a large majority
of the 19 (Idolaf, Amren, Adrianne, Nazeem, Lillith, Lucia, Danica, Ysolda, Sigurd, Brenuin, Heimskr, Anoriath,
Lars, Saffir are all independently named across the reports, cross-referenced against AI Overhaul's own changelog
by Claude's report). **Immersive Citizens – AI Overhaul** is a *different* conflict class — it injects packages via
quest reference-aliases, which outrank base-record packages at the engine's evaluation-stack level, so it is
invisible to xEdit/merge-patch tooling entirely and unfixable by any record-level patch. **Cutting Room Floor** has
a small, real, patchable overlap (Nazeem, Lillith). **Populated Cities Towns Villages** and **JK's Whiterun** are
both confirmed clean at the record level (new/independent NPCs, or navmesh/geometry-only edits respectively) —
their only risk is pathing/clipping, not a record conflict.

~~**Recommendation: distribute the Flee packages via SkyPatcher's runtime package-list addition instead of a
Mutagen base-record override.** SkyPatcher lets a package be added to an NPC's runtime package stack via a plain
`.ini` file targeting a FormID, without touching the base `NPC_` record — no ESP override, no last-plugin-wins
collision with AI Overhaul or CRF. It's a near-standard fixture in modern Skyrim modlists (already used by AI
Overhaul's own compatibility ecosystem to escape this exact problem class), and the same Mutagen pipeline that
generates the current 342 packages/19 overrides can emit SkyPatcher `.ini`s instead with a comparatively small
change.~~ **Superseded — SkyPatcher has no package-list mechanism at all, see "§1 corrected assessment" below for
the three real remaining options.** Left struck through rather than deleted so the corrections immediately below
(still accurate as *critiques of the original external reports*, just no longer pointing at a live recommendation)
keep their context.

**Corrections to the source reports, verified against Chronicle's own code (historical — the recommendation these
were correcting no longer stands, but the individual corrections were real and are preserved for the record):**
- **SkyPatcher does not eliminate Chronicle's ESP.** The patcher still needs to *author* the 342 new Flee `PACK`
  records and 171 `TESGlobal`s somewhere — SkyPatcher distributes existing records *by FormID*, it doesn't create
  them. Chronicle still ships a plugin; it just stops *overriding the 19 `NPC_` records*, which is the actual
  source of the conflict. Don't describe the fix as "no ESP" — describe it as "no record override."
- **SkyPatcher likely does not fix the Immersive Citizens conflict, but this is an assertion, not a verified
  fact, and this document should not have stated it as one.** The claim is that IC's quest-alias packages outrank
  base-record packages regardless of whether Chronicle's package arrives via a direct override or a SkyPatcher
  addition, because both are still base-record-tier in the engine's evaluation stack. Neither source report actually
  verified SkyPatcher's runtime injection priority against the engine's package-evaluation hierarchy — it's
  plausible a runtime-injected package sits at a different priority tier than a plain base-record one, in which case
  SkyPatcher could partially mitigate the IC conflict too. This claim currently does real argumentative work (it's
  the sole justification for action item 5 below) while being held to a looser evidentiary bar than the
  `packageListAdd` directive-name caveat directly below it — both should be verified with the same rigor before
  either is trusted. IC is one of the most-installed AI mods in the ecosystem regardless, and needs its own
  mitigation path evaluated either way: either package-priority tuning, or IC's own documented exclusion-faction
  opt-out mechanism (unverified against IC's actual implementation — flagged as an open item below).
- **`packageListAdd` as an exact SkyPatcher directive name has not been verified against SkyPatcher's own
  documentation** — every report's citation for it traces back to secondary sources (other mods' patch notes,
  forum threads), not SkyPatcher's own docs. Verify before committing to the exact `.ini` syntax.
- **"AI Overhaul's own compatibility ecosystem" is imprecise** — the SkyPatcher-based AI Overhaul patch (Nexus mod
  138722) is a third-party community patch, not something AI Overhaul's own author ships. Doesn't change the
  conclusion (it's still real, widely-adopted evidence SkyPatcher is the community's chosen escape route from this
  conflict class), just a citation-precision fix.
- **SkyPatcher targeting will hit Chronicle's own known `IdentityMap` divergence and must be checked against it
  before generating anything.** `IdentityMap.cpp` (the C++ runtime side) attributes 5 of the 19 NPCs (Amren, Braith,
  Lars Battle-Born, Idolaf Battle-Born, Lillith Maiden-Loom) to whichever plugin *currently wins the override chain*
  for their placed reference (HearthFires.esm/USSEP) — deliberately different from `IdentityMap.cs` (the Mutagen
  patcher side), which keys the same 5 NPCs by *originating master* (Skyrim.esm), since Mutagen's `FormKey`
  resolution works that way. Both are correct for their own purpose (`chronicle-bridge-avoidance-mutagen-out.md`
  documents why they're allowed to diverge), but this divergence already caused one false-alarm "fix" that had to be
  reverted once. SkyPatcher filters by plugin+FormID, so before generating any `.ini`, confirm which of the two
  conventions its filter actually expects — the same verification rigor as the `packageListAdd` name above.
- **SkyPatcher's "ecosystem-load-bearing, low bus-factor risk" framing (used again in §5 below to justify the hard
  dependency) currently rests entirely on the source reports' assertion, not verified adoption data.** Worth an
  actual check (Nexus endorsement/download counts, or how many of the mods already cited in this document — AI
  Overhaul's own patch ecosystem, DPF/DPF-consumers — depend on it) before treating this as settled, since it's the
  load-bearing premise behind the whole hard-dependency recommendation.

### §1 corrected assessment (2026-09-05): SkyPatcher is not viable, here are the real remaining options

Confirmed by reading `Zzyxz/SkyPatcher`'s actual source (`npc.cpp`'s full directive table, `gh api
repos/Zzyxz/SkyPatcher/contents/npc.cpp`) — not secondhand citation. SkyPatcher can add keywords, factions, perks,
spells, and inventory objects to an NPC at runtime without touching its base record, but it has no equivalent for
AI packages. This rules out the whole "adopt SkyPatcher, hard-depend on it" thread from the earlier Kimi/advisor
dependency consultation for this specific subsystem — that consultation's *reasoning* (prefer an existing
maintained framework over reimplementing something risky natively, when a real conflict is guaranteed) still
holds, it just has no target to apply to here. The real options, none of which were fully vetted in this
synthesis:

1. **Quest Alias injection at high priority**, mirroring how Immersive Citizens itself avoids this conflict class
   (Gemini's original report, "Architectural Alternative A"). A quest with 19 reference aliases (one per named NPC)
   and packages conditioned on Chronicle's existing globals, authored at a priority that beats both AI Overhaul's
   base-record packages and (if high enough) IC's own alias packages. This can likely be authored entirely via
   Mutagen — quest/alias/package records with global-gated conditions don't obviously require a Papyrus script,
   since Chronicle's mechanism is already "flip a global, call `EvaluatePackage`," the same pattern IC's own
   condition-gated aliases use — but this needs verification against Mutagen's actual quest/alias-authoring
   surface before treating it as confirmed cheap. If it does turn out to need Papyrus, it has the same new-
   mechanism-class cost flagged for `OnStoryRelationshipChange` in §3.
2. **Native runtime package override.** Verified (2026-09-05) directly against PapyrusUtil's own source
   (`eeveelo/PapyrusUtil`, an LE-era fork — SE/AE currency not confirmed): `ActorUtil::AddPackageOverride` is real
   and shipped, backed by a `Packages` manager (`PackageData.cpp`) that stores per-actor override packages keyed by
   priority/flags. But it depends on `skse64_common/BranchTrampoline.h` and `xbyak` — a genuine engine-level detour
   hook into the package-evaluation routine, not a call into an already-exposed public engine API. `RE::ExtraPackage`
   (confirmed a real class, `CommonLibSSE`'s `include/RE/E/ExtraPackage.h`) is read-side extra-data on an actor
   reference (tracks an in-progress package's runtime state), not itself a push-an-override API. So this option is
   confirmed buildable and precedented — PapyrusUtil is a hugely popular, actively-maintained mod plenty of other
   systems already depend on for exactly this — but it's real reverse-engineering-adjacent C++ work (a detour hook,
   not a quick wrapper), and it's still open whether Chronicle should reimplement this logic itself or actually take
   PapyrusUtil as a dependency and drive its already-shipped mechanism (PapyrusUtil is already present in
   Chronicle's own SimpleSkyrim test modlist, for what that's worth on the dependency-appetite question from §5).
3. **Stay with the current direct base-record override, and become a normal, patchable citizen of the AI-mod
   ecosystem instead of trying to architect the conflict away.** Add the `Actors.AIPackages` Wrye Bash tag to
   Chronicle's plugin so Wrye Bash users get an automatic merge instead of a silent drop; publish a documented
   load-order rule and/or a pre-built merge patch for AI Overhaul SSE and Cutting Room Floor specifically (the two
   confirmed real record-level clashes), mirroring the AI Overhaul Official Patch Hub's own established pattern.
   This doesn't fix the Immersive Citizens runtime-priority conflict (nothing but options 1/2 does), but it's the
   cheapest option, requires no new mechanism, and matches how most of the AI-mod ecosystem already handles this
   exact problem class for each other.

**Decided via socratic-debate (2026-09-05): sequence, don't pick one option exclusively — and the deciding fact is
now resolved.** Full debate transcript folded into this document's history; verdict: (1) live-verify the current
avoidance slice first, no architecture change of any kind until then — non-negotiable per this project's own freeze
doctrine (action item 8 already captured this). (2) Confirm whether Mutagen can author a static quest + 19
reference aliases + condition-gated packages without any Papyrus (option 1's whole cost case hinged on this one
fact). **Resolved (2026-09-05), same day, by reading Mutagen's actual Skyrim record definitions directly
(`gh api repos/Mutagen-Modding/Mutagen/contents/...`, not secondhand): confirmed Papyrus-free.**
`Quest.Flag.StartGameEnabled` auto-starts the quest with no script trigger; `Quest.Priority` is a plain settable
byte; `QuestAlias.ForcedReference` points an alias directly at one of the 19 NPCs' placed references (a
"forced reference" alias resolves immediately at quest-start, unlike a conditional/location alias — no runtime
fill logic needed); `QuestAlias.PackageData` and `QuestAlias.Conditions` are exactly the package-list-plus-
global-gate shape Chronicle's current `AvoidancePoller`/`AvoidanceGlobals` mechanism already uses. Every piece
Option 1 needs is a plain, headlessly-authorable record field — nothing requires Papyrus. (3) Given this,
**Option 1 (Quest Alias injection) is the path to pursue**, after live verification succeeds — it uniquely fixes
both the AI Overhaul and Immersive Citizens conflicts at once, converging on Immersive Citizens' own proven
architecture, for no more authoring cost than the current base-record approach. Option 3 (stay-and-patch) is no
longer the likely fallback path given this finding, though it remains available if Quest Alias implementation
uncovers a real blocker Mutagen's record schema doesn't show (e.g. an engine-side quirk with 19 aliases on one
quest, unverified in this pass). Option 2 (native override) stays a low-priority fallback only if Immersive
Citizens compatibility becomes a demonstrated frequent complaint after Option 1 ships.

---

## 2. Native vendor-price hook

**Verdict: low external-mod collision risk, but a real, still-open internal correctness question.** Kimi's survey
found almost no popular mod natively hooks `BarterMenu` for price computation — mainstream economy mods (Trade and
Barter, Trade Routes, Economics of Skyrim) all work through perks/GMSTs/Papyrus. `VendorPriceHook.cpp` already does
correct call-through chaining (`g_origPostCreate(a_this)` is called unconditionally before Chronicle's own logic
runs), so the "destructive vtable overwrite" failure mode both Gemini's and Claude's reports warn about generically
does not apply to the current implementation.

The real open question is one Chronicle's own code already flags, independently rediscovered by two of the three
external reports: **does the price markup Chronicle installs (via the Scaleform `UpdateItemCardInfo` callback)
actually change the gold amount exchanged at transaction time, or only the displayed number?** Skyrim's BarterMenu
UI and its transaction engine are architecturally separate systems; a display-only markup would let a player see one
price and get charged another. `VendorPriceHook.cpp`'s own comment (line ~141) already calls this "UNVERIFIED
against a live save," and `docs/research/28-vendor-price-hook-address-library-spike.md` flagged the identical
question when this was designed. Claude's report independently identified `JerryYOJ/DynamicPrices-SKSE` (Dynamic
Prices Framework, "DPF") — the same mod report 28 already used as the reference for the current callback pattern —
as a mature framework that solves this generically via a multiplier-callback registry.

**Recommendation (per the Kimi + advisor consultation below): stay native, do not adopt DPF as a dependency.**
Chronicle's hook already *is* DPF's pattern (report 28 copied it). "Does DPF move real gold" and "does Chronicle's
hook move real gold" are the same question about the same mechanism — adopting DPF would not skip the verification
step, it would add a dependency on top of still owing it. The fix is a single live-game test, not a framework
migration: open a barter menu with a marked-up named-cast vendor, note item price and gold, complete the purchase,
recheck gold. This test needs no save/reload, so it is unblocked by the `load` no-op bug.

**Correction, caught reviewing this document (2026-09-05): the "Chronicle is the only mod marking up these
vendors' prices" premise above is overstated.** Claude's BarterMenu report (prompt 2) identifies a *second* native
framework this document initially failed to carry forward: shazdeh2's **Dynamic Pricing Framework** (Nexus #167487,
a distinct project from JerryYOJ's "Dynamic Prices Framework"/DPF above, despite the near-identical name), with real
downstream consumers — Gilded Road (#169528) and Immersive Merchants (#156053) — that rewrite displayed barter
prices by keyword/condition and plausibly apply to some of the same 19 vendors (Adrianne, Anoriath, Carlotta are
named as candidates). Combined with Trade and Barter's own price tiers (below), the "low collision risk, no
stacking problem" framing is shakier than stated — the recommendation to stay native still holds (§ below), but the
rationale should say "the residual composition risk is a documented, testable set of specific mods" rather than
implying no other mod touches these prices at all. **Also dropped from this synthesis and worth restoring as a
pre-release check**: Claude's report separately flags Inventory Interface Information Injector ("I4") as a
near-universal load-order fixture hooking the *same* item-list-update machinery Chronicle's hook is adjacent to,
with documented CTDs when hook order or runtime offsets are wrong — worth including in whatever pre-release
compatibility test pass this plan eventually calls for, alongside DPF/DPF-consumers and Trade and Barter.

**Separately flagged, not yet resolved:** Kimi's research also found that **Trade and Barter** already ships
relationship-rank-based price tiers via perks — meaning the vendor-markup feature overlaps *functionally* with a
popular incumbent regardless of how it's implemented. Worth a design conversation about whether this slice earns
its keep independent of the hooking-mechanism question — **see action item 1 below, which now gates the barter
verification test on answering this first, not after.**

---

## 3. Relationship-rank writes

**Verdict: no true race condition against any popular mod as installed by default — the dominant real exposure is
vanilla itself, not other mods.** RDO, Immersive Speechcraft, Amorous Adventures, and the follower frameworks (NFF,
AFT, EFF) are either pure readers of the field or maintain their own parallel disposition value; RDO in particular
is pure upside, since it will surface Chronicle's simulated grudges through its own dialogue conditions with zero
integration work. The real exposures, all confirmed across multiple reports:

- **Vanilla's own favor/quest/marriage system writes rank absolutely** ("=1", "=-1" in UESP's notation — an
  unconditional overwrite) for at least six of the 19: Ysolda, Amren, Carlotta, Danica, Lars, and Braith
  (this specific enumeration is sourced only to Kimi's report, not independently cross-checked against UESP
  directly in this synthesis — worth a quick verification pass since it's the concrete evidence behind the whole
  "vanilla itself is the dominant writer" claim). A
  continuously-resyncing Chronicle will silently erase the reward from completing e.g. "Bullying Braith" or Amren's
  sword-recovery favor, with **zero other mods installed**.
- **Ysolda is a vanilla marriage candidate.** Chronicle could demote a player's own wife to Enemy with no mod
  involved at all — this is a policy/exclusion problem, not a compatibility one.
- **One genuine, but conditional, periodic-writer conflict**: "Follower Dismissal – Immersive Relationship System"
  syncs its own value into vanilla rank every 24 in-game hours, but only for NPCs the player has explicitly
  registered as followers — narrow and opt-in, not a general risk.

**New mechanism, not previously known to Chronicle: `OnStoryRelationshipChange`.** This Story Manager event fires
whenever relationship rank changes for any reason — console, quest, another mod — carrying both actors and the
old/new values. This lets Chronicle detect external writes reactively instead of blindly overwriting on every sync
tick. **Real architectural cost, not just an implementation detail: this is a Papyrus quest-script event, requiring
an authored quest attached to a Story Manager SM Event Node — and confirmed, not just suspected, that Chronicle has
none of this today.** A direct grep of `tools/chronicle-patcher/src/` for any quest (`QUST`) authoring turns up
nothing — the patcher currently generates only `PACK`/`TESGlobal` records, zero quests. So `OnStoryRelationshipChange`
is a genuinely new mechanism class for this project, not a small addition, and the project's standing architecture
otherwise keeps game-side logic in C++/native records specifically to avoid Papyrus's own limitations (see the
earlier "port to C++" discussion this project has already had). Before committing to this mechanism, check whether
CommonLibSSE-NG exposes a native relationship-change sink or hook instead of the Story Manager path — if not, this
recommendation needs its Papyrus/quest-authoring cost priced in explicitly against that backdrop, not discovered
during implementation. Separately, the listening quest (if built) must have "Shares Event" checked on the Story
Manager node, or Chronicle risks suppressing (or being suppressed by) another mod's own relationship-change quest.

**Architectural correction, found while implementing (2026-09-05): `HydrationPoller.cpp` never calls
`Actor.SetRelationshipRank` at all.** Every source report (and the first draft of this section) analyzed the
Papyrus-level `SetRelationshipRank`/`GetRelationshipRank`/`OnStoryRelationshipChange` trio. Chronicle's actual C++
write goes straight to `RE::BGSRelationship::GetRelationship(npc1, npc2)->level` — a different, native record type
CommonLibSSE-NG exposes directly (`SetRelationshipRank` isn't in CommonLibSSE-NG's headers at all; it's Papyrus-VM-
only, confirmed by its absence from `Actor.h`'s search results). This is the *architecturally correct* choice for a
native plugin (no VM round-trip), not a bug — and independently confirmed to be the same underlying data the
Papyrus-visible rank represents: a real third-party plugin (`tetherball88/Relations-Finder`) computes "relationship
rank" via the identical `4 - level.underlying()` mapping Chronicle's own `LevelForRank()` does in reverse, both
reading/writing the same `BGSRelationship.level` field. So the overall analysis above stands (RDO/dialogue/etc. do
read the same underlying value), but **`OnStoryRelationshipChange` firing for Chronicle's own writes is now in
real doubt**, not just an unpriced cost: that Story Manager event is plausibly tied to the specific internal engine
function `SetRelationshipRank` calls, not to the `BGSRelationship.level` field's mere mutation — Chronicle's write
bypasses that function entirely. This doesn't prevent Chronicle from *listening* for genuine external writes (those
likely do go through the normal path and would still fire the event), but it means the event can't be assumed to
reflect Chronicle's own loopback, and building the listener before confirming this would be exactly the kind of
unverified-assumption risk this document's SkyPatcher correction already burned a research pass on once.

**Implemented (2026-09-05), the parts that don't depend on resolving the above**: `HydrationPoller.cpp` now (a)
debounces — skips the write entirely if `relationship->level` already equals the computed target, avoiding needless
`AddChange` churn; (b) hard-excludes any pair where either resolved actor is `IsPlayerTeammate()` (an active
follower, regardless of which recruitment framework put them there) or where the relationship is already at
`kLover` (protects an existing spouse without needing a specific, unverified marriage-faction FormID). Both are
narrow, defensive checks that never fire for Chronicle's more common NPC↔NPC grudge pairs.

**Recommendation, revised — what's left, not a compatibility patch (there is no ESP to patch against):**
1. ~~Register an `OnStoryRelationshipChange` listener~~ — **deferred, not implemented.** First confirm whether this
   event actually fires for writes that bypass `SetRelationshipRank`'s own internal call path (a research task, not
   a live-game task) before building a Papyrus/quest-authoring surface this project doesn't have yet on a foundation
   that might not even receive the signal it's built to detect.
2. ~~Debounce writes~~ — **done**, see above.
3. ~~Hard-exclude spouses and active followers~~ — **done**, see above.
4. On detecting an external change (once/if item 1 is resolved and built), apply a cooldown before reasserting
   rather than reasserting immediately — immediate reassertion is exactly what produces flapping if another system
   does the same. Still applicable whenever item 1 is picked back up.

---

## 4. Persistent object spawning (evidence)

**Verdict: the live-position spawn design is structurally validated, not a mistake — the real issues are lifecycle
and coherence, both fixable without changing the core approach.** Kimi's report found that vanilla itself relocates
two of the 19 (Olfina Gray-Mane to Dragonsreach, Ysolda into a shop) depending on playthrough events, and
live-position spawning handles both correctly *by construction* — direct evidence the design choice was right, not
a liability. This directly contradicts Gemini's report, whose headline recommendation (abandon live-position
spawning for hand-authored, pre-placed disabled references) is **the same tradeoff Chronicle's own
`docs/research/33-evidence-preplace-toggle-snapshot-coordinates.md` already evaluated and rejected** — pre-placed
markers go stale as soon as a schedule-overhaul mod moves an NPC, and there's an unresolved Z-coordinate/exterior-
cell-FormKey gap for authoring them by hand. Do not re-litigate that decision on this report's authority alone.

Three concrete, independently-fixable problems remain, confirmed across all three tools:

- **Placement coherence, not correctness.** Immersive Citizens routinely relocates NPCs into narratively
  incoherent contexts (fleeing to a random hideout, sheltering from rain, rambling into the wilderness); evidence
  will spawn in the technically-correct-but-narratively-strange place. Fix: gate spawning on NPC context (not
  fleeing, not away from home location), not on position correction.
- **Placement staleness after fast-travel/sleep.** Immersive Citizens' own FAQ documents that NPC positions don't
  update during these windows. A poll read immediately after either could place a *permanent* object at a stale
  coordinate. Fix: require position stability across two poll cycles before spawning.
- **Save-mass lifecycle.** `forcePersist=true` objects are never cleaned up by any automatic engine mechanism
  (confirmed against the CK/UESP `PlaceAtMe` wiki page, Bethesda's own Cell Reset documentation, and the Unofficial
  Patch's own history of fixing exactly this bloat class for dropped weapons/ash piles). Fix: default to
  non-persistent spawns, track created refIDs in `EvidencePoller`, and call `MarkForDelete()` on stale/collected
  evidence rather than accumulating forever.

**Two new edge cases, not previously flagged, both easy fixes:**
- **Dead/killable NPCs.** Several of the 19 can die in a normal playthrough (Amren, Carlotta, Anoriath, Nazeem).
  `PlaceObjectAtMe` on a cleaned-up corpse reference will fail or misplace the object — `EvidencePoller` needs a
  null/3D-loaded check before spawning.
- **Physics-hookup workaround exists and is documented.** Freshly `PlaceAtMe`'d objects aren't hooked into physics
  events until the cell reloads (if the base form doesn't already exist in that cell) — the standard CK-documented
  workaround is `Disable()` then `Enable()` plus a small Z-offset, addressing the (weakly-sourced) Havok-ejection
  concern one report raised.

**Sizing check, refined during a second review pass (2026-09-05) — evidence generation IS bounded per belief, but
a separate, already-documented gap means it can still duplicate.** The oft-cited Skyrim reference-handle cap
(2²⁰ ≈ 1,048,576 active handles) is real, but one report did the actual arithmetic Chronicle needs: 19 objects —
even a few hundred — is trivially negligible against that ceiling, so the cap itself isn't the near-term concern.
This synthesis's first pass read `chronicle/diegetic_evidence.py` and concluded evidence generation was unbounded
per NPC; a second review pass went further and read `adapters/skyrim/listener/listener.py`'s
`_EvidenceEntryState` (~line 810), which corrects that: evidence is explicitly designed as **"a one-shot reveal
with no re-offer on decay"** — once an entry is `applied`, it is never re-offered even if the belief's confidence
later drops and rises again. So the true growth source isn't repeated re-triggering of the same belief, it's one
permanent object per distinct `(holder_id, belief_id)` pair that ever crosses threshold over the whole
playthrough — bounded by how many distinct beliefs ever qualify, not unbounded re-spawning.

**However, `listener.py`'s own docstring names a real, already-acknowledged gap that directly threatens
`EvidencePoller`: this state is in-memory only and does not survive a listener restart, and a restart forgets an
already-`applied` entry entirely** — "even though this cut's own within-process contract says `applied` is
otherwise permanent." Concretely: restart the Python listener process after evidence has already been spawned for
some belief, and that belief's entry reverts to "not-yet-offered," which the next poll will offer again — meaning
**`EvidencePoller` would spawn a second, duplicate persistent object for evidence that already exists in the
world**, with no correction on the Python side (this is documented as a known limitation there, not something to
fix in `chronicle/` or `listener.py` — the fix has to live game-side). This directly reinforces, and sharpens, the
existing `forcePersist=true`/no-cleanup concern below: `EvidencePoller.cpp`'s own comment (line ~139) already
called it "not verified against a real save's long-run size/behavior," but the new finding shows the risk isn't
just about the volume of first-time spawns from the original synthesis — it's that duplicate spawns from listener
restarts compound the same lifecycle problem from a second angle. The action item below (track refIDs, dedupe,
explicit cleanup) is the fix for both angles simultaneously, since a refID-keyed dedup on the C++ side is exactly
what would also make a listener restart's re-offer a no-op instead of a duplicate spawn.

**Implemented (2026-09-05), the dedup half of the fix**: `EvidencePoller.cpp` now keeps a process-lifetime
`(holderId, beliefId)` set and skips spawning (reporting `kApplied` again instead) for any pair already recorded as
spawned this session — closing the concrete listener-restart-duplicate bug found above. Also added: a dead-actor
check (`Actor::IsDead()`) before spawning, since several of the 19 NPCs can die mid-playthrough and calling
`PlaceObjectAtMe` on/near a corpse was an unhandled edge case. **Deliberately NOT changed**: `forcePersist` is still
`true`. Dropping it would not, by itself, fix anything — a non-persistent `PlaceAtMe` reference is *also* not
auto-cleaned by an ordinary cell reset (confirmed against the CK wiki's own documentation) — so the real fix for
genuinely unbounded save growth across a very long playthrough is a protocol-level retraction/expiry signal (neither
side of the wire protocol has one today), which is a separate, larger design task, not something safe to bolt on
as a quick fix in this pass. Position-stability gating (defer spawn until an NPC's position is stable across two
poll cycles) and NPC-context gating (don't spawn while fleeing/away from home) are also not yet implemented —
both need `EvidenceEntry`/the listener protocol to carry enough state to check, which the current wire shape may or
may not already support; unverified in this pass.

---

## 5. The dependency question: SkyPatcher and DPF

**Note added 2026-09-05: the SkyPatcher half of this section is now moot as a concrete recommendation** — there is
no SkyPatcher package-distribution mechanism to hard-depend on (see "§1 corrected assessment"). The *reasoning*
below (prefer a maintained framework over reimplementing something risky natively, when conflict is guaranteed)
remains sound and should be re-applied once §1's three options are evaluated — option 1 (Quest Alias) and option 2
(native override) are the two that would actually need this kind of dependency-vs-native judgment call; option 3
doesn't. The DPF (vendor-price) conclusion below is unaffected by this and still stands on its own.

Raised because sections 1 and 2 both point at adopting a third-party native framework, which sits in tension with
Chronicle's own stated distribution philosophy (minimize what a non-technical end user has to install, motivated by
the earlier Python-sidecar-avoidance discussion). Consulted both Kimi (`kimi_think`) and `advisor` independently on
this specific tradeoff; both converged on the same split, for compatible but distinct reasons.

**Recommendation: split the policy — hard-depend on SkyPatcher, stay native on the vendor-price hook. Reject
"detect-and-fall-back" for both.**

- **SkyPatcher (AI packages): adopt as a hard dependency.** This isn't a risk-adjusted tradeoff — the AI Overhaul
  conflict is *guaranteed*, not probabilistic, for a large fraction of Chronicle's actual user base, and the native
  alternative (reimplementing runtime package-stack injection from scratch, e.g. a hand-rolled
  `RE::ExtraPackage`-style override) is a real reverse-engineering project with its own crash-risk blast radius, for
  a solo team, to replicate something a maintained framework already does via an `.ini` file. SkyPatcher's bus-factor
  risk is low: it's load-bearing for a large slice of the modern modlist ecosystem, so if an AE update breaks it,
  fix pressure comes from thousands of modlists, not from Chronicle alone. The "avoid Python-sidecar-style
  distribution complexity" principle was about fragile multi-process setups a non-technical user can't debug — a
  single, extremely common, actively-maintained required SKSE plugin is not in that category.
- **Dynamic Prices Framework (vendor price): do not adopt.** Chronicle already has a correctly-chaining hook with
  low external collision risk, and (per section 2) DPF's whole value proposition — composing multiple mods' price
  multipliers — solves a problem Chronicle doesn't have, since it's the only mod marking up these particular
  vendors' prices. The actual open risk (display-vs-transaction correctness) is not resolved by adopting DPF; DPF's
  own hook uses the identical mechanism Chronicle's does, so the same verification would still be owed, plus a new
  dependency with a smaller bus factor (one author, one flagship consumer) than the risk it would nominally reduce.
- **No detect-and-fallback for either.** This doesn't halve risk, it doubles the test matrix — every behavior would
  have two implementations, each exercised by an unknown fraction of the user base, and the fallback path is the one
  that bit-rots because the team's own testing (and most engaged users) will tend to have the framework installed.
  A missing required mod should fail loud (a startup check + clear log/message), not spawn a second permanently-
  maintained implementation.

**The asymmetry driving the split**, per both consultations independently: a missing required dependency fails
*loudly and immediately* (detectable, messageable) — that argues for depending on frameworks when the alternative is
subtle, silent, per-user correctness risk (the AI-package case). But it cuts the other way when Chronicle already
owns a working, low-risk implementation and the framework doesn't actually retire the remaining risk (the
vendor-price case) — there, a dependency just adds recurring coordination cost (version compatibility, SE/AE lag)
to avoid a one-time verification cost that has to be paid either way.

---

## Consolidated action items, ordered so nothing gates something ranked before it

_Re-ordered after review (2026-09-05): the first draft of this list ranked the barter test first as "cheapest," but
also separately said the vendor-markup viability question should be answered "before investing further" in that
same test — both `advisor` and Kimi independently caught this as a real ordering contradiction. Cheap-decision
questions that gate a live-game test now come first._

1. **Decide whether the vendor-markup feature earns its keep at all**, given Trade and Barter's existing
   relationship-based price tiers and (per the correction above) shazdeh2's Dynamic Pricing Framework's existing
   consumer ecosystem covering some of the same vendors. This is a design conversation, not research — answer it
   before spending a live-game session on item 3 below, since a "no" makes that session unnecessary.
2. **Read `chronicle/diegetic_evidence.py` and `EvidencePoller.cpp` to confirm the evidence-boundedness finding
   above is complete** (done in this synthesis pass, but re-check before implementation: is there any dedup/cap
   logic elsewhere in the C++ poller not visible in the excerpt reviewed here?). Cheaper than any live-game item,
   gates how aggressive item 7's cleanup policy needs to be.
3. **Barter transaction verification (live-game, no save/reload needed)** — only after item 1 says yes. Open a
   barter menu with a marked-up named-cast vendor, note price and gold, complete a purchase, recheck gold. Answers
   section 2's open question definitively and is unblocked by the `load` bug.
4. **Resolved (2026-09-05): Mutagen's quest/reference-alias/package-authoring API confirmed Papyrus-free — proceed
   with Option 1 (Quest Alias) once action item 8's live-verification gate clears.** SkyPatcher is off the table
   entirely (confirmed, not just suspected). The `IdentityMap.cpp`/`IdentityMap.cs` divergence (§1's corrections)
   still applies to Option 1's implementation, since it still needs to resolve "which plugin owns this NPC's
   FormID" correctly when authoring each `ForcedReference`.
5. **Resolved (2026-09-05), then independently re-confirmed the same day directly against IC's real `.esp`
   (v0.4.1a, "Full Legendary" build — the owner downloaded it and handed it over; opened with the new
   `tools/esp-dump/` utility, built for exactly this).** Both the exclusion mechanism and the priority-conflict
   shape are now hard facts, not inference from an author's FAQ or secondhand research:
   - `NPCO_ExclusionFaction` is real: FormKey `237FB4:Immersive Citizens - AI Overhaul.esp`, confirmed by direct
     read, matching the FAQ exactly.
   - **The actual quest and priority Chronicle's Quest Alias (Option 1) needs to beat**: `NPCO_AIWhiterunNPCs`
     (`20A698:Immersive Citizens - AI Overhaul.esp`), **Priority 20**. Not a guess — read directly off the record.
     Chronicle's own Quest Alias needs a priority above 20 to win the evaluation-stack fight for any NPC both
     mods touch.
   - **Only 14 of Chronicle's 19 named NPCs are actually inside this quest's alias list at all**: Carlotta
     Valentia, Danica Pure-Spring, Fralia Gray-Mane, Heimskr, Idolaf Battle-Born, Lars Battle-Born, Lillith
     Maiden-Loom, Lucia, Nazeem, Olava the Feeble, Olfina Gray-Mane, Saffir, Sigurd, Ysolda. **Amren, Adrianne
     Avenicci, Braith, Brenuin, and Anoriath are not in it at all** — those five appear elsewhere in IC's `.esp`
     only as participants in vanilla `Skyrim.esm` ambient dialogue-scene quests IC lightly patches (no
     `PackageData`, no schedule involvement), not in `NPCO_AIWhiterunNPCs`. **For those five, there is no IC
     priority conflict to solve at all, under any of §1's options** — this narrows the real problem from "19 NPCs
     vs. IC" to "14 NPCs vs. IC," a smaller and more precisely scoped fix than anything in this document assumed
     before this read.
   - This also resolves the coexistence-vs-exclusion tradeoff raised earlier in conversation with a real number to
     design against: Quest Alias coexistence (Option 1, priority > 20) is now a fully specified, checkable target
     for those 14 NPCs, not a vague "tune it high enough" aspiration.

   Adding all 19 to `NPCO_ExclusionFaction` remains available as the cheaper, blunter fallback (still a smaller,
   more surgical edit than the current `AIPackages` override, still orthogonal to whichever of §1's options ships)
   — but it's no longer the only concretely-actionable path; Option 1 coexistence is now equally concrete for the
   14 NPCs that actually need it.
   Residual, smaller risk carried over from the AI-package analysis above: faction membership is still a base-record
   field, so it's still theoretically subject to a last-plugin-wins collision if another mod also edits factions on
   the same NPC — but faction merging is one of Wrye Bash's most mature, reliable bash tags (`Actors.Factions`),
   unlike `AIPackages`, so the risk class here is much lower.
6. **`HydrationPoller`'s write policy — partially done (2026-09-05).** Debounce, and spouse/follower exclusion:
   **implemented**, see §3. Still open: whether CommonLibSSE-NG exposes a native relationship-change sink, and
   whether `OnStoryRelationshipChange` even fires for a write that bypasses `SetRelationshipRank`'s own internal
   call path (a new, sharper open question found while implementing — see §3's architectural correction) —
   resolve this before building any listener at all, not just before choosing which mechanism to use.
7. **`EvidencePoller`'s lifecycle — partially done (2026-09-05).** Dedup against listener-restart duplicates, and a
   dead-actor check: **implemented**, see §4. Still open, deliberately not attempted in this pass: dropping
   `forcePersist` doesn't help without a protocol-level retraction signal neither side has yet (a larger design
   task), and position-stability/NPC-context spawn gating needs the wire protocol checked for whether it already
   carries enough state to gate on.
8. **Decide explicitly whether migrating avoidance's package-delivery mechanism (to whichever of §1's three options
   is chosen) should happen before or after this slice's game-side half is verified live even once.** `docs/design/
   chronicle-bridge-avoidance-mutagen-out.md` states the current 342-package/19-override build has never been
   load-ordered in an actual running game — and `GOALS.md`'s standing owner decision explicitly freezes new
   architecture work on infrastructure that hasn't been proven live (the same reasoning behind freezing ADR-0011).
   There's a real argument for migrating first (why verify a design already slated for replacement?), but this
   document should not leave that tension implicit — decide and record which side wins before starting the
   migration itself.

## Open questions

**Resolved this session (2026-09-05), left here for the record:**
- ~~IC's exclusion-faction opt-out mechanism~~ — confirmed real and named (`NPCO_ExclusionFaction`), quoted
  directly from the author's own FAQ. See action item 5.
- ~~Which of §1's options to pursue~~ — resolved via socratic-debate: sequence live-verification first, then
  Option 1 (Quest Alias), confirmed Mutagen-authorable without Papyrus. SkyPatcher (a fourth, since-invalidated
  option) is confirmed not viable at all.
- ~~Whether Mutagen can author a Quest Alias + package + condition setup without new Papyrus~~ — confirmed yes,
  directly from Mutagen's own Skyrim record definitions (`Quest.Flag.StartGameEnabled`, `Quest.Priority`,
  `QuestAlias.ForcedReference`, `QuestAlias.PackageData`, `QuestAlias.Conditions` all exist and are plain
  settable fields).
- ~~Whether CommonLibSSE-NG exposes a native relationship-change sink~~ — confirmed absent (`BGSRelationship.h`
  has no event/sink type at all). The only path to detect external rank writes is the Story Manager event,
  whose applicability to Chronicle's own writes is still the one real remaining question below.
- ~~IC's exact quest/priority for the 19 NPCs, and whether all 19 are even in scope~~ — resolved by direct read of
  IC's real `.esp` (v0.4.1a): the quest is `NPCO_AIWhiterunNPCs`, priority 20, and it only actually covers 14 of
  the 19 (Amren, Adrianne Avenicci, Braith, Brenuin, Anoriath are outside its alias list entirely). See action
  item 5.

**Still genuinely open:**
- Whether `OnStoryRelationshipChange` fires for a write that bypasses `Actor.SetRelationshipRank`'s own internal
  call path (Chronicle writes `BGSRelationship.level` directly) — this is now the key blocker for action item 6's
  deferred listener work, not a native-sink-vs-Papyrus cost question anymore (that part's resolved: no native sink
  exists, so Papyrus is the only path *if* built at all). The "Shares Event" SM-node requirement is also still
  unverified against an actual authored quest (none exist yet to check it against).
- For option 2 (native override, now a low-priority fallback): whether CommonLibSSE-NG exposes a public
  push-an-override API beyond `RE::ExtraPackage` (confirmed read-side only) — PapyrusUtil's real
  `ActorUtil::AddPackageOverride` implementation is confirmed to work via a genuine engine detour hook, not a
  public API call, so this option's cost is now a known quantity rather than speculative, but no longer the
  likely path given Option 1's resolution.
- Whether the specific NPC-favor enumeration in §3 (Ysolda, Amren, Carlotta, Danica, Lars, Braith) holds up against
  a direct UESP check — still sourced only to Kimi's report, not independently verified in this synthesis.
