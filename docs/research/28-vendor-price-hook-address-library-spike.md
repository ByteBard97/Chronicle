---
date: 2026-08-26
sources:
  - local CommonLibSSE-NG header/source checkout at
    /home/geoff/projects/skyrim-re-toolkit/type-importer/vendor/CommonLibSSE-NG
    (RE/B/BarterMenu.h, RE/I/IMenu.h, RE/G/GFxFunctionHandler.h,
    RE/I/ItemList.h, REL/Relocation.h, RE/Offsets_VTABLE.h)
  - github.com/JerryYOJ/DynamicPrices-SKSE (public GitHub repo,
    src/scaleform/DynamicPrices/DynamicPrices.cpp +
    DynamicPrices.h, fetched directly via `gh api`) — found via
    GitHub code search on the exact callback signature quoted in this
    task's own prompt and in docs/research/26; author name and
    behavior match Nexus mod 144874 "Dynamic Prices Framework" as
    surveyed in docs/research/16/18, treated as strong (not
    Nexus-page-confirmed, since nexusmods.com/skyrimspecialedition/mods/144874
    returned HTTP 403 to a direct fetch — the same Cloudflare block this
    project's other research docs already worked around) circumstantial
    identification, not a certainty
  - docs/research/26-vendor-price-markup-hook.md (this doc's direct
    predecessor and premise — its F5/Recommendation is the specific claim
    this pass tests)
  - GitHub code search (`gh api search/code`) for the exact DPF callback
    signature, which is what surfaced the JerryYOJ/DynamicPrices-SKSE
    repo among 7 total hits (2 of the other 6 were this project's own
    already-filed research docs)
topic: "Locating the real internal-engine hook target for grudge-driven vendor price markup, for the pinned 1.6.1170 build"
status: filed
---

# Vendor Price-Markup Hook: Address Library Spike — What Report 26 Got Half Right

**Document File ID:** docs/research/28-vendor-price-hook-address-library-spike.md

## TL;DR

Report 26 filed the vendor-price-markup mechanism as `[RISK —
reverse-engineered hook required]`, framing the remaining unknown as "an
internal, unmapped engine function" that mod 144874 (Dynamic Prices
Framework, JerryYOJ) allegedly detours into directly, and recommending a
SigMaker/Address-Library spike to find it before scheduling any build
work. **That framing was wrong, and the spike this doc ran found something
better: DPF's actual open-source implementation (`github.com/JerryYOJ/
DynamicPrices-SKSE`) shows it never touches an unmapped internal function
at all.** Read directly, `DynamicPrices.cpp` does two things, both fully
inside CommonLibSSE-NG's already-documented, Address-Library-backed
surface: (1) a **vtable-slot swap** on `RE::IMenu::PostCreate()` — vtable
index `0x2`, a real documented virtual in `RE/I/IMenu.h:68`, reached via
`RE::VTABLE_BarterMenu[0]` (`REL::VariantID(267991, 214926, 0x172ebf0)`,
already sitting unused in this project's own local CommonLibSSE-NG
checkout at `include/RE/Offsets_VTABLE.h:3998`) and `REL::Relocation::
write_vfunc()` (a real public method, `REL/Relocation.h:392`); and (2) a
**Scaleform/GFx UI-layer function swap** — it replaces the barter menu's
ActionScript `"UpdateItemCardInfo"` callback via `RE::GFxFunctionHandler`
+ `GFxMovieView::CreateFunction()` (both real, header-confirmed
CommonLibSSE-NG types), intercepting the per-item-row price value *after*
Flash/ActionScript has already asked native code to compute it, multiplying
it, then forwarding to the saved original callback so display/flow stays
intact. **No internal, unmapped native price-calculation function is
located, named, or hooked anywhere in this implementation** — the "hooks
the price-calc system directly" language report 16/18 inherited from
mod-description summaries was a simplification of a UI-callback-swap
technique, not a literal native-code detour. **Recommendation: this is
buildable now**, using only APIs this project's local CommonLibSSE-NG
checkout already exposes, at a risk tier closer to `DeathEventSink`'s
event-sink pattern than to a from-scratch SigMaker hunt — with one real,
honestly-flagged caveat this pass could not verify without a live game
session: whether the AS3-side "value" this technique multiplies is the
same value the engine actually charges/pays on `Buy`/`Sell`, or only the
displayed tooltip figure (see Caveats).

## Findings

**[F1] [VERIFIED] The real DPF implementation is public, found via GitHub
code search on the exact callback signature this task's own prompt (and
report 26) already quoted verbatim.** Searching GitHub code search for
`InventoryEntryData GFxValue is_buying` (a fragment unique enough to be
load-bearing) returned 7 hits total, two of which were this project's own
already-filed research markdown, and among the rest:
`JerryYOJ/DynamicPrices-SKSE` at `src/scaleform/DynamicPrices/
DynamicPrices.cpp` and `.h`. The author name (`JerryYOJ`), the exact
callback signature, the `Data/SKSE/DynamicPrices/*.json` config-folder
convention ("create a folder under your mod's SKSE folder named
DynamicPrices with a JSON file to register the callback" — independently
confirmed by a separate web search of the mod's own description text),
and the "NativeCallbacks" JSON key all match report 16/18's and this
task's description of mod 144874 exactly. This project could not load
`nexusmods.com/skyrimspecialedition/mods/144874` directly (HTTP 403,
Cloudflare — the exact expected block this task's own brief anticipated)
to get a byte-for-byte Nexus-page confirmation that this GitHub repo is
literally the shipped DLL's source, so treat the identification as
strong circumstantial match, not a notarized fact.

**[F2] [VERIFIED] The "hook" is a vtable-slot swap on a real, documented
`RE::IMenu` virtual function — not a raw code-cave/detour into unmapped
engine code.** The relevant lines from `DynamicPrices::Install()`:

```cpp
void DynamicPrices::Install() {
	REL::Relocation<std::uintptr_t> Vtbl{ RE::VTABLE_BarterMenu[0] };
	_PostCreate = Vtbl.write_vfunc(0x2, &PostCreate);
}
```

Every symbol here is already real and present in this project's own local
CommonLibSSE-NG checkout, independently confirmed by direct grep, not
taken on the source repo's word:

- `RE::VTABLE_BarterMenu` — `include/RE/Offsets_VTABLE.h:3998`:
  `constexpr std::array<REL::VariantID, 1> VTABLE_BarterMenu{
  REL::VariantID(267991, 214926, 0x172ebf0) };` — a real,
  Address-Library-ID-backed (`267991` SE / `214926` AE) vtable relocation,
  the exact same `RELOCATION_ID`/`VariantID` idiom report 26's F1 already
  vetted for `BarterMenu::GetTargetRefHandle()`'s `RefHandle`. This entry
  already exists in the checkout — it was simply unused by any code in
  this project (or, per report 26's F6 grep, anywhere in ChronicleBridge)
  until this pass looked for it.
- `RE::IMenu::PostCreate()` — `include/RE/I/IMenu.h:68`:
  `virtual void PostCreate();  // 02 - { return; }` — a real, named,
  documented virtual function at vtable index `0x2`, inherited (not
  overridden) by `BarterMenu`, confirmed by cross-referencing
  `RE/B/BarterMenu.h`'s own override list (`~BarterMenu` at 00, `Accept`
  at 01, `ProcessMessage` at 04, `PostDisplay` at 06 — `02`/`03`/`05` are
  conspicuously absent, i.e. inherited straight from `IMenu`, exactly
  where `PostCreate` lives).
- `REL::Relocation<T>::write_vfunc(idx, newFunc)` —
  `include/REL/Relocation.h:392` — a real public member function on the
  same `REL::Relocation` template this project's every prior slice
  already uses for reads; this is its documented write-a-vtable-slot
  overload.

This means "hook BarterMenu at the moment it's constructed" requires
**zero fresh reverse-engineering** — it is a vtable pointer swap on an
address this checkout already carries an Address Library ID for, onto a
function CommonLibSSE-NG already names.

**[F3] [VERIFIED] The actual price *manipulation* happens one layer up,
in Scaleform/GFx (Flash UI), not in native price-calculation code at
all — DPF replaces the barter menu's ActionScript `UpdateItemCardInfo`
callback, not any native price function.** From `PostCreate`:

```cpp
RE::GFxValue oldf;
root.GetMember("UpdateItemCardInfo", &oldf);

RE::GFxValue newf;
auto&& impl = RE::make_gptr<DynamicPrices>(std::move(oldf), std::move(hashMap), thiz);
barter->uiMovie->CreateFunction(&newf, impl.get());

root.SetMember("UpdateItemCardInfo", newf);
```

and then, in the replaced callback's `Call()`:

```cpp
RE::GFxValue value(RE::GFxValue::ValueType::kNumber);
a_updateObj.GetMember("value", &value);
value.SetNumber(value.GetNumber() * mult);
a_updateObj.SetMember("value", value);
...
oldFunc.Invoke("call", a_params.retVal, a_params.argsWithThisRef, a_params.argCount + 1);
```

`RE::GFxFunctionHandler` (base class DPF's `DynamicPrices` type derives
from) and `GFxValue`/`GetMember`/`SetMember`/`Invoke` are all real,
header-confirmed CommonLibSSE-NG types
(`include/RE/G/GFxFunctionHandler.h`) — this is the same "replace an
ActionScript-callable native function object" technique used throughout
the wider Scaleform-menu-modding ecosystem (SkyUI's own extension
mechanism works this way), not novel to DPF and not requiring any
sig-scan of its own. The vendor's `Actor*` is obtained the same way
report 26's F1 already found — a `RefHandle` relocation matching
`RE::BarterMenu::GetTargetRefHandle()`'s underlying static (DPF's copy:
`RELOCATION_ID(519283, 405823)`; this project's current local checkout
has `RELOCATION_ID(519283, 403520)` for the same SE ID `519283` — same SE
offset, differing AE offset, most likely reflecting a different
CommonLibSSE-NG snapshot DPF was built against rather than any error;
**use this project's own local checkout's number, not DPF's, since
ADR-0008 pins 1.6.1170 and that's the header this project actually
vendors** — treat the discrepancy as a version-drift caveat to
double-check against the Address Library DB directly before writing
code, not as evidence either number is wrong).

**[F4] [VERIFIED] `RE::ItemList::GetSelectedItem()` (used to identify
which row/item is being priced) is likewise a real, already-declared
CommonLibSSE-NG member**, `include/RE/I/ItemList.h:27`, so the full chain
from "menu opened" → "which vendor" → "which item row" → "multiply its
price" resolves entirely inside already-documented API surface.

**[F5] [CORRECTS REPORT 26] Report 26's central risk claim — "no
`RE::`-exposed... this is an internal, unmapped engine function" — was
an inference from mod *descriptions* (Nexus/community summaries saying a
plugin "hooks the price-calc system directly"), not from reading any
actual implementation; this pass is the first to read one.** The
description-level framing ("hooks the internal price-calculation
routine") is not technically false at a narrative level — the price
figure IS intercepted before it reaches the player — but it conflates
"before the player sees it" with "inside native price-calculation code,"
which turned out not to match the real technique at all. This is worth
naming plainly: report 26 did the right thing by flagging the gap
honestly and scoping a follow-up spike rather than guessing at an
address; this pass's finding is that the follow-up spike's premise
(there must be an unmapped native function to find) doesn't hold up once
real source is read.

## Recommendation

**Build this now, using only report 28's confirmed API surface — do not
schedule a SigMaker/Address-Library address hunt, because there is no
unmapped function left to hunt for.** Concretely, ChronicleBridge's C++
side would need:

1. A vtable-swap install step (once, at plugin load), following
   `DynamicPrices::Install()`'s exact shape:
   ```cpp
   REL::Relocation<std::uintptr_t> vtbl{ RE::VTABLE_BarterMenu[0] };
   _origPostCreate = vtbl.write_vfunc(0x2, &ChronicleBarterHook::PostCreate);
   ```
2. Inside the overridden `PostCreate`, resolve the vendor `Actor*` via the
   same `RefHandle` relocation report 26's F1 already trusts (or, more
   simply, just call the already-public `RE::BarterMenu::
   GetTargetRefHandle()` wrapper directly instead of re-declaring the raw
   relocation — no reason to duplicate what CommonLibSSE-NG already
   exposes cleanly), then `IdentityMap`-resolve it to a Chronicle `npc_id`
   exactly as `HydrationPoller::ResolveLiveNpc` already does.
3. Swap the barter menu's `"UpdateItemCardInfo"` ActionScript member via
   `RE::GFxFunctionHandler` + `uiMovie->CreateFunction()`, following
   DPF's `Call()` shape, but replacing DPF's "ask other DLLs via
   GetProcAddress" indirection with a direct in-process call to
   ChronicleBridge's own already-polled `markup_multiplier` cache for
   that `npc_id` (the same GET-polled cache shape `HydrationPoller`/
   `AvoidancePoller` already use per report 26's F5) — this is a
   *simplification* of DPF's design (no need for the cross-DLL JSON
   callback-registration indirection at all, since ChronicleBridge would
   be both the hook owner and the multiplier's only consumer).
4. Use `SKSE::GetTrampoline()` only if a raw inline/codecave hook is ever
   needed elsewhere — it is **not** needed for this slice; `write_vfunc`
   is a simpler, self-contained vtable-pointer write that doesn't require
   the trampoline allocator at all, which is itself a lower-risk profile
   than report 26 assumed.

**Revised risk classification**: downgrade from report 26's `[RISK —
reverse-engineered hook required]` to **`[BUILD-ON — vtable-swap +
Scaleform-callback-swap, both fully inside documented CommonLibSSE-NG
surface]`**. This is a new *pattern* for ChronicleBridge (its first
vtable/UI-layer hook, versus every prior slice's plain field write or
`BSTEventSink`), so it is fairly scoped as its own implementation step
rather than folded silently into hydration/avoidance-tier work — but it
is not the same order of unstarted, open-ended R&D report 26 described.
It is buildable in the next implementation pass, pending the one
verification caveat below.

## Caveats

- **Not verified in this pass, and the one thing that would need a live
  game session to settle**: does the `"value"` field DPF's replaced
  `UpdateItemCardInfo` multiplies actually drive the gold amount
  exchanged on `Buy`/`Sell`, or only the displayed tooltip/list figure
  (with the real transaction gold computed by a separate, still-internal
  native call)? DPF's real-world reception (report 16/18: it backs *The
  Gilded Road*, the best-received economy mod this project's survey
  found) is strong circumstantial evidence it does affect the real
  transaction, not just cosmetics — mods with only-cosmetic price display
  don't earn "regional economy overhaul" framing — but this pass read
  source, it did not decompile `BarterMenu.swf`'s ActionScript or run the
  game to confirm the data flow end-to-end. This is the one item worth a
  short live-game smoke test before committing an implementation
  timeline, not a reason to redo the address search.
- **`JerryYOJ/DynamicPrices-SKSE` carries no LICENSE file** (GitHub
  reports `license.key: "other"` / `spdx_id: "NOASSERTION"`, confirmed by
  direct `gh api` query) — treat this as a real, useful reference for the
  *pattern* (as this doc does), not as code to vendor or copy verbatim
  into ChronicleBridge without contacting the author.
- The `RefHandle` relocation ID discrepancy noted in F3 (`405823` in
  DPF's source vs. `403520` in this project's local checkout, same SE ID
  `519283`) should be spot-checked against the Address Library's own
  database directly (or simply avoided by calling the existing
  `RE::BarterMenu::GetTargetRefHandle()` wrapper instead of hand-rolling
  the relocation a second time) before writing code — flagged, not
  resolved, in this pass.
- This pass did not attempt to build, compile, or run anything against a
  live game, per this task's own scope — it is a source-reading and
  header-cross-referencing pass, one step more concrete than report 26's
  documentation-only pass (which had no implementation source to read
  yet) but still short of an in-game verification.
- The Nexus mod page (144874) itself remained unreachable (HTTP 403,
  Cloudflare) in this pass, exactly as anticipated by this task's brief;
  the identification of `JerryYOJ/DynamicPrices-SKSE` as that mod's
  source rests on strong circumstantial matches (author handle, exact
  callback signature, exact config-folder convention), not a page-level
  confirmation.
