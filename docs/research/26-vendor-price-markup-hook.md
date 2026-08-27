---
date: 2026-08-26
sources:
  - local CommonLibSSE-NG header/source checkout at
    /home/geoff/projects/skyrim-re-toolkit/type-importer/vendor/CommonLibSSE-NG
    (RE/B/BarterMenu.h, RE/B/BarterMenu.cpp, RE/M/MenuOpenCloseEvent.h,
    RE/B/BGSEntryPoint.h, RE/A/Actor.h, RE/G/GameSettingCollection.h,
    RE/S/Setting.h, RE/T/TESForm.h)
  - docs/research/16-skyrim-economy-mods.md and
    docs/research/18-skyrim-economy-mods-v2.md (already-filed engine-hook
    survey this doc builds on directly, not re-researched)
  - docs/research/24-programmatic-esp-authoring.md (Mutagen precedent,
    reused for the CTDA/perk-authoring alternative considered and rejected
    below)
  - this project's own C++ source
    (adapters/skyrim/ChronicleBridge/src/HydrationPoller.cpp,
    DeathEventSink.h) for the established documented-API-vs-hook risk
    convention
topic: "ChronicleBridge C++ mechanism for grudge-driven vendor price markup at barter-menu-open"
status: filed
---

# Vendor Price-Markup Hook: What ChronicleBridge's C++ Side Would Actually Need

**Document File ID:** docs/research/26-vendor-price-markup-hook.md

## TL;DR

`docs/design/chronicle-bridge-vendor-markup-out.md`'s Python-only half
(`markup_multiplier_for`, the two listener endpoints) is built and
committed; this doc researches the **still-unbuilt C++ half**: how
ChronicleBridge would apply that multiplier to a specific vendor's prices
when the player opens that vendor's barter menu. Two real, header-verified
CommonLibSSE-NG facts settle question 2 cleanly: `RE::BarterMenu` is a
real `IMenu` subclass with a static `GetTargetRefHandle()` that returns
the vendor's `RefHandle` directly (`RE/B/BarterMenu.h`/`.cpp`,
`RELOCATION_ID(519283, 403520)`), and `RE::MenuOpenCloseEvent` (already a
real, header-confirmed event type, `menuName` + `opening` bool) is the
documented way to know when `"BarterMenu"` opens at all — so identifying
"which vendor" at "which moment" is solved with **no reverse-engineering
required**. Question 1's real vanilla formula is `price factor = 3.3 −
1.3 × min(Speechcraft,100)/100`, already cited from UESP in report 16's
caveats, gated at the low end by the real `fBarterBuyMin` game setting
(read via `RE::GameSettingCollection::GetSingleton()->GetSetting
("fBarterBuyMin")->GetFloat()`, a genuinely documented CommonLibSSE-NG
call). Question 3's honest answer is **no** — there is no
`RE::`-exposed, single-field, per-NPC "price multiplier" write analogous
to `BGSRelationship::level` or a `TESGlobal`'s `value`; the real vanilla
mechanism Speech perks use is `RE::BGSEntryPoint::ENTRY_POINTS::
kModBuyPrices`/`kModSellPrices` (values `8`/`60`, confirmed present in
`RE/B/BGSEntryPoint.h`), which is a **Perk record's entry-point
function**, not a runtime-writable field — it requires authored content
(a `.esp`), not a poller write. Question 4's simpler community pattern is
real and already surveyed in report 16/18: **mod 144874 (Dynamic Prices
Framework by JerryYOJ)**, a native SKSE/CommonLibSSE DLL that hooks the
internal price-calculation routine directly and registers a C++ callback
`(Actor* trader, InventoryEntryData*, uint16_t level, GFxValue&,
bool is_buying) -> float multiplier` — the one path that can bypass
`fBarterBuyMin` because it overrides price *after* the vanilla
calculation, and the pattern *The Gilded Road* (1,049-upvote release
thread, the single most enthusiastically received economy mod release in
this project's whole survey) actually ships. **Recommendation: build on
the `BarterMenu`/`MenuOpenCloseEvent` pair (both genuinely documented,
zero risk) to detect "barter opened with vendor X," but the actual price
write itself requires the same category of mechanism mod 144874 uses —
an internal-function detour hook into engine code CommonLibSSE-NG does
not itself expose as a named, addressed function. That is a real step up
in risk from every prior ChronicleBridge slice** (`BGSRelationship::level`,
`TESGlobal::value`, `Actor::EvaluatePackage` were all documented,
directly-callable `RE::` API writes/calls; this is not). Honest
classification: **[RISK — reverse-engineered hook required]**, meaningfully
higher-risk than hydration/avoidance/spatial, and not a same-tier next
build step — treat it as its own scoped R&D spike (find/verify the
function signature via a signature scan or a community-shared offset,
almost certainly via Address Library / SigMaker against the pinned
1.6.1170 binary per ADR-0008) before committing to an implementation
timeline, the same honesty report 24 gave its own `PutCreatedPackage`
from-scratch-construction fallback.

## Findings

**[F1] [VERIFIED] `RE::BarterMenu` is a real, header-confirmed `IMenu`
subclass, and it exposes the vendor's `RefHandle` through a documented
static function — this fully answers "which Actor* is the vendor" with
zero reverse-engineering on ChronicleBridge's own part.**
`RE/B/BarterMenu.h` (local CommonLibSSE-NG checkout) declares:

```cpp
class BarterMenu : public IMenu {
public:
    constexpr static std::string_view MENU_NAME = "BarterMenu";
    [[nodiscard]] static RefHandle GetTargetRefHandle();
    ...
};
```

and `RE/B/BarterMenu.cpp` implements it as:

```cpp
RefHandle BarterMenu::GetTargetRefHandle() {
    REL::Relocation<RefHandle*> handle{ RELOCATION_ID(519283, 403520) };
    return *handle;
}
```

This is exactly the shape of CommonLibSSE-NG's already-vetted
`RELOCATION_ID` pattern this project already trusts elsewhere (it is the
same idiom, not a novel one) — a maintained, versioned address-library
lookup, not a hand-found offset. `RefHandle` resolves to a live
`TESObjectREFR`/`Actor*` via the standard
`RE::TESObjectREFRPtr`/`LookupByHandle` path CommonLibSSE-NG uses
throughout (the same resolution family `SpatialStreamer`/`HydrationPoller`
already use for other actor lookups in this codebase). Calling
`RE::BarterMenu::GetTargetRefHandle()` any time `"BarterMenu"` is open
gives ChronicleBridge the vendor `Actor*` directly — no menu-internal
GFx/UI scraping needed.

**[F2] [VERIFIED] `RE::MenuOpenCloseEvent` is a real, minimal, already
publicly-documented CommonLibSSE-NG event type — the "barter menu opened"
signal question 2 asked about.** `RE/M/MenuOpenCloseEvent.h`:

```cpp
class MenuOpenCloseEvent {
public:
    BSFixedString menuName;  // 00
    bool          opening;   // 08
};
```

Sinking this via `RE::UI::GetSingleton()->AddEventSink<RE::
MenuOpenCloseEvent>(...)` (the standard CommonLibSSE-NG event-sink
registration pattern) and checking `a_event->menuName ==
RE::BarterMenu::MENU_NAME && a_event->opening` is the documented,
idiomatic way to detect the moment to act — structurally identical to
this project's own `DeathEventSink` pattern (`BSTEventSink<RE::
TESDeathEvent>`, already shipped and explicitly commented "a clean
top-level BSTEventSink, no inline hook required"). **This project does
not yet sink `MenuOpenCloseEvent` anywhere** (grep of
`adapters/skyrim/ChronicleBridge/src/` found no existing reference) —
this would be a new, but low-risk, sink, following an already-proven
in-codebase pattern.

**[F3] [VERIFIED] The real vanilla barter-price formula and its floor,
confirmed against two independent sources.** Report 16's own caveats
section already extracted the real UESP-cited formula in plain text (its
source document's original had base64-embedded images instead of text):
`price factor = 3.3 − 1.3 × min(Speechcraft, 100) / 100`, separately
interpolated for buy/sell by the global `fBarterMax`/`fBarterMin` game
settings, i.e. price is driven by the *vendor's* (or in vanilla, the
*player's*) Speechcraft skill and perks, not by any per-item or
per-relationship field. The floor `fBarterBuyMin` (default 1.05, already
cited in the design doc) is a real, currently-loaded `RE::Setting` —
confirmed reachable via `RE::GameSettingCollection::GetSingleton()->
GetSetting("fBarterBuyMin")` (`RE/G/GameSettingCollection.h`,
`GetSetting(const char*)` is a real public method) and read via
`RE::Setting::GetFloat()` (`RE/S/Setting.h`). Two important
consequences: (a) this is a **global** setting, not per-vendor or
per-NPC — writing `Setting::data.f` (a public field on the real struct,
technically writable at runtime) would move the floor for **every**
vendor simultaneously, which is the wrong shape for a single-grudge-holder
markup and is explicitly the reason report 16/18 call this floor
"real" and un-bypassable by anything except a post-calculation hook; (b)
no `RE::` header anywhere in the local checkout exposes the actual
per-transaction price *calculation function* itself by name — it is
internal, unmapped engine code, confirmed by an exhaustive grep of the
header tree for `CalcBarterPrice`/`CalculateBarterPrice`/`GetBarterPrice`/
`PriceMult`, all of which returned nothing.

**[F4] [VERIFIED] The real, shipped, in-engine "Speechcraft perks change
prices" mechanism is `RE::BGSEntryPoint::ENTRY_POINTS::kModBuyPrices`
(8) / `kModSellPrices` (60), a Perk-record entry point — not a runtime
field.** `RE/B/BGSEntryPoint.h` confirms both enum values exist exactly
as vanilla CK documentation describes them (the "Mod Buy/Sell Prices"
entry-point functions every Speech perk that touches prices — Merchant,
Fence, Master Trader — actually uses). This directly answers question 3's
"is there an AV/mechanism vanilla perks already use" — yes, but it is a
**perk entry-point function attached to a `Perk` record with `CTDA`
conditions**, i.e. authored `.esp` content (report 24's Mutagen path
would create it), not a field ChronicleBridge's C++ can poke at runtime
the way `BGSRelationship::level` or a `TESGlobal`'s `value` can. Vanilla's
own per-vendor conditioning for this mechanism (e.g. the "Fence" perk's
faction-gated markdown) works by attaching a `CTDA` condition (typically
`GetInFaction`/`GetIsID`-style) evaluated with the *vendor* as the
condition's subject reference at price-calc time — real and
CK-documented, but it means one authored condition per targetable NPC (or
a faction-membership proxy), not an arbitrary per-relationship-pair
runtime write. This mechanism does not scale to "any of hundreds of
named-cast NPCs, decided fresh every poll by a continuously-recomputed
Python multiplier" the way the other three ChronicleBridge slices'
runtime writes do — it is authoring-time, not poll-time.

**[F5] [BUILD-ON] The real "simpler, already-proven mod pattern" for
"make one specific vendor's prices worse" is the native price-calc hook,
already surveyed in this project's own report 16/18, not a
faction/perk trick.** Report 16: mod 144874 (Dynamic Prices Framework,
JerryYOJ) is "a native SKSE/CommonLibSSE DLL hooking the price-calc
system directly, registering a C++ callback `(Actor* trader,
InventoryEntryData* objDesc, uint16_t level, GFxValue& updateObj, bool
is_buying)` returning a float multiplier — this is the one path that can
bypass the `fBarterBuyMin` floor, because it overrides price *after* the
vanilla calculation." Report 18 adds the reception evidence: this
architecture (native hook, JSON config, "no scripts, no dirty edits, no
save bloat") is what *The Gilded Road* ships on top of, and its
1,049-upvote/112-comment release thread is "the most enthusiastically
received economy mod release in the surveyed record" — real, strong
community validation of exactly this pattern, not a theoretical
alternative. Crucially, this callback signature already receives `Actor*
trader` — meaning a ChronicleBridge implementation of the same pattern
would not need `BGSEntryPoint`/CTDA authoring at all: at the moment the
hook fires, C++ code already has the vendor `Actor*` in hand, resolves it
through `IdentityMap` exactly like `HydrationPoller::ResolveLiveNpc` does
in reverse, looks up the cached `markup_multiplier` for that npc_id (the
same GET-polled cache shape hydration/avoidance already use), and returns
it as the float multiplier. This is architecturally the cleanest fit to
this slice's actual requirement (a fresh, continuously-computed
per-NPC float, not an authored condition) — but it is only reachable via
a **function-detour hook into an internal, unmapped engine function**,
which report 16/18 and this pass's own header search agree
CommonLibSSE-NG does not expose as a named `RE::` symbol. Locating and
verifying that function's real address (via SigMaker/Address Library
against the ADR-0008-pinned 1.6.1170 binary, the same tool family a
plugin like mod 144874's author would have used) is real, unstarted work
this pass did not attempt and is scoped outside a documentation-only
research pass.

**[F6] [RISK] This project's own established discipline already treats
inline/detour hooks as a materially different risk category from event
sinks — this slice would be the first to cross that line.**
`DeathEventSink.h`'s own header comment states its choice explicitly:
"Sinks `RE::TESDeathEvent` (research/22's verified mapping — a clean
top-level `BSTEventSink`, no inline hook required, unlike crime/bounty)."
Every ChronicleBridge C++ slice built so far — `DeathEventSink`
(event sink), `SpatialStreamer` (polls `RE::ProcessLists`, a documented
singleton), `HydrationPoller` (writes `BGSRelationship::level`, a
documented public field), `AvoidancePoller`/`AvoidanceGlobals` (writes a
`TESGlobal`'s `value`, also a documented public field) — used only
either a top-level `BSTEventSink` or a direct, named, header-declared
`RE::` field/function. A grep of this project's entire C++ source
(`adapters/skyrim/ChronicleBridge/src/*.{cpp,h}`) for `hook`,
`trampoline`, `REL::Relocation` (outside vendored headers), or
`SigScan`/`AddressLib` usage found **none** — this project has built four
real slices without ever needing a function-detour hook. A price-calc
detour would be the first.

## Recommendation

**Split this into two independently-real pieces, not one:**

1. **Detection ("barter opened with vendor X") is genuinely low-risk and
   buildable now**, following the exact pattern `DeathEventSink` already
   established: a new `BSTEventSink<RE::MenuOpenCloseEvent>` filtering on
   `menuName == RE::BarterMenu::MENU_NAME && opening`, then calling the
   real, documented `RE::BarterMenu::GetTargetRefHandle()` to resolve the
   vendor `Actor*`, then `IdentityMap` (the same reverse-resolution
   `HydrationPoller::ResolveLiveNpc` already implements) to get the
   Chronicle `npc_id`, then a cache lookup against
   `GET /whiterun/vendor-markup`'s already-polled response (same poller
   shape as `HydrationPoller`/`AvoidancePoller`). Every piece of this is a
   documented `RE::` API or an already-proven in-codebase pattern. **This
   half is realistic for a next implementation pass, at the same
   confidence level as hydration/avoidance.**

2. **The actual price write is not.** No documented CommonLibSSE-NG
   `RE::` field or function sets a per-transaction/per-vendor price
   multiplier; the real vanilla mechanism (`BGSEntryPoint::
   kModBuyPrices`/`kModSellPrices`) is authored-Perk-record content, not
   a runtime write, and does not fit "recomputed fresh every poll for any
   named-cast NPC" without per-NPC authored conditions (an N-perks or
   N-conditions scaling problem, not a clean design). The mechanism that
   *does* fit — the mod-144874-style native detour into the internal
   price-calc routine — is real, community-proven (and the best-received
   economy-mod pattern this project has surveyed), and gives the write
   itself the same "small, targeted, one field's worth of state" shape as
   `HydrationPoller`'s `BGSRelationship::level` write. But it requires
   locating and verifying an unmapped internal engine function's address
   for the pinned 1.6.1170 build — genuinely reverse-engineered work
   CommonLibSSE-NG's headers do not hand ChronicleBridge for free, unlike
   every prior slice's write target.

**Honest risk classification, matching report 24's own convention for
naming its `PutCreatedPackage` fallback's risk explicitly**: detection is
`[VERIFIED — documented API]`; the write is `[RISK — reverse-engineered
hook required]`, the first ChronicleBridge slice to need this category of
work. **Do not schedule the write half in the same implementation pass as
the detection half or as a peer to hydration/avoidance's next steps.**
Treat it as its own scoped spike: (a) confirm via Address Library/SigMaker
against the 1.6.1170 binary (ADR-0008's pin) whether the exact function
mod 144874 hooks is independently locatable or documented anywhere in the
CommonLibSSE-NG or Address Library community indices (not attempted in
this pass), and (b) only after that returns a concrete, verified address
should this move from research to an implementation ticket. If that
address search comes back empty or ambiguous, the honestly-scoped
fallback is to ship detection only (log/telemetry: "this barter session
should have carried a Nx markup") and defer the actual price write to
whenever this project is ready to take on its first inline hook — a
materially bigger commitment than any of hydration/avoidance/spatial
were, and one worth a deliberate go/no-go decision rather than an
implicit one.

## Caveats

- The exact internal function signature/address mod 144874 hooks was not
  independently located in this pass — this doc confirms the *pattern*
  is real (via reports 16/18, both citing the mod directly) and that
  CommonLibSSE-NG's headers do not expose it by name (via direct grep of
  the local header checkout), but finding the actual offset/signature is
  future work, not something resolvable from documentation alone.
- `RE::Setting::data` being a public, technically-writable field (F3) is
  noted for completeness, not as a viable mechanism — writing
  `fBarterBuyMin` globally would affect every vendor in the game
  simultaneously and cannot express a per-NPC/per-grudge multiplier; it
  is mentioned only to close out question 3's framing honestly, not as a
  recommended path.
- `RE::BarterMenu::GetTargetRefHandle()`'s `RELOCATION_ID(519283, 403520)`
  was read directly from the local CommonLibSSE-NG source checkout, the
  same trust level this project already extends to every other
  `RELOCATION_ID`-based CommonLibSSE-NG call in `HydrationPoller.cpp`/
  `AvoidanceGlobals.cpp` — reverse-engineered by the CommonLibSSE-NG
  maintainers, not Bethesda-documented, but the same already-accepted
  trust tier as this project's existing writes, not a new one.
- This pass did not attempt to build or run anything against a live game
  — purely a header/documentation verification pass, consistent with
  every other ChronicleBridge research doc's scope to date.
