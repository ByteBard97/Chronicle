#pragma once

// Sixth ChronicleBridge slice -- the WRITE half of docs/design/chronicle-
// bridge-vendor-markup-out.md's grudge-driven vendor markup feature, per
// docs/research/28-vendor-price-hook-address-library-spike.md's confirmed
// [BUILD-ON] recommendation (downgraded there from research/26's [RISK --
// reverse-engineered hook required]). BarterMenuSink.h/.cpp (the DETECTION
// half, already built) proved the vendor-Actor*->npc_id resolution chain
// works; this file reuses that exact chain (ResolveBarterVendorActor +
// ResolveNpcIdForActor, both shared out of BarterMenuSink.h/.cpp) and adds
// the actual price manipulation report 28's F2/F3 document:
//
//   1. A vtable-slot swap on RE::VTABLE_BarterMenu[0], overriding
//      RE::IMenu::PostCreate() (vfunc index 0x2) via
//      REL::Relocation<std::uintptr_t>::write_vfunc() -- installed exactly
//      once, at plugin load (InstallVendorPriceHook(), called from
//      plugin.cpp's SKSEPluginLoad). Every symbol involved is real,
//      documented, Address-Library-backed CommonLibSSE-NG surface (report
//      28 F2): RE::VTABLE_BarterMenu (Offsets_VTABLE.h), RE::IMenu::
//      PostCreate (a real named virtual BarterMenu inherits, not
//      overrides -- IMenu.h), and REL::Relocation<std::uintptr_t>::
//      write_vfunc (Relocation.h). This is a vtable POINTER WRITE, not a
//      code-cave/detour into unmapped engine code -- report 28's whole
//      point is that no such unmapped function needs to be found at all.
//   2. Inside the overridden PostCreate, resolves the vendor the same way
//      BarterMenuSink.cpp does, then looks up a player-directed markup
//      multiplier for that npc_id via VendorMarkupCache::
//      GetPlayerMarkupMultiplier. If (and only if) one exists, swaps the
//      barter menu's "UpdateItemCardInfo" ActionScript member for a
//      RE::GFxFunctionHandler that multiplies the "value" field of the
//      per-row update object by that multiplier before forwarding to the
//      saved original callback -- report 28 F3's documented flow,
//      re-implemented here from the real CommonLibSSE-NG API shapes report
//      28 quotes (RE::GFxFunctionHandler, RE::GFxValue::Get/SetMember,
//      RE::GFxMovie::CreateFunction, RE::make_gptr) -- NOT copied from
//      DynamicPrices-SKSE's source, which carries no LICENSE file per
//      report 28's own caveat. That source was read only as a reference
//      for which real engine calls to use, and this implementation departs
//      from it in one deliberate way report 28's Recommendation step 3
//      calls out: no cross-DLL JSON callback-registration indirection,
//      since ChronicleBridge is both the hook owner and the multiplier's
//      only consumer -- VendorMarkupCache::GetPlayerMarkupMultiplier is
//      called directly, in-process.
//
// Per report 28's Recommendation step 4 / this task's own step 5: a vendor
// with no player-directed markup entry gets NO callback swap installed at
// all -- PostCreate still calls the real original unconditionally, and
// simply never touches "UpdateItemCardInfo" if GetPlayerMarkupMultiplier
// returns std::nullopt. This is simpler and strictly safer than installing
// a multiply-by-1.0 passthrough for every vendor: a vendor with no
// grudge-markup state has literally zero code added to its barter-menu
// callback chain.
//
// *** ORDERING CAVEAT, not resolved by this slice, same class of gap
// BarterMenuSink.h's own header comment already flags for
// MenuOpenCloseEvent: PostCreate fires during BarterMenu's OWN
// construction, which may plausibly run BEFORE RE::BarterMenu::
// GetTargetRefHandle()'s underlying static is populated for this
// particular menu instance (construction vs. "target already set" is not
// something either header confirms an ordering for) -- if so,
// ResolveBarterVendorActor() would return nullptr here MORE often than it
// does for BarterMenuSink's MenuOpenCloseEvent-based detection (which fires
// once the menu is already on the UI stack, plausibly later). The code
// fails safe either way (a null resolve is traced and skipped, never
// installs a hook, never crashes) -- but if the price hook never appears
// to fire against a live game, this ordering assumption, not the vtable
// swap or the Scaleform callback swap itself, is the first thing to
// suspect. ***
//
// *** UNVERIFIED CAVEAT, restated from report 28's own Caveats section,
// not resolved by this slice: whether the AS3 "value" field this technique
// multiplies is the same value the engine actually charges/pays on
// Buy/Sell, or only the displayed list/tooltip figure, has NOT been
// confirmed against a live game session -- this plugin has only been
// compiled, never run against a live game. Treat the PRICE EFFECT as
// unverified even though the HOOK MECHANISM itself (the vtable swap
// installing cleanly and the Scaleform callback swap firing on real
// barter-menu opens) is expected to work, per report 28's fully-
// documented-API finding. A short live-game smoke test -- open a barter
// menu against a named-cast vendor with a seeded player-directed grudge,
// and watch whether the actual gold charged on Buy/Sell reflects the
// multiplier, not just the displayed price -- is the one thing that would
// close this gap; it has not been attempted here. ***

namespace ChronicleBridge {

    // Installs the RE::VTABLE_BarterMenu[0] PostCreate vtable-slot swap.
    // Call exactly once -- vtable pointer writes are process-global and
    // idempotent-unsafe to repeat: a second call would save the FIRST
    // swap's replacement function as the "original" to forward to, not the
    // real game function, silently breaking every barter menu thereafter.
    // plugin.cpp calls this from the kDataLoaded branch of OnSkseMessage,
    // alongside every other RE:: singleton registration this plugin does
    // -- no BarterMenu can be constructed before a save is loaded, so that
    // point is already early enough; there is no need to install any
    // earlier, at raw plugin load, and doing so would just be a
    // separately-reasoned-about exception to this plugin's one
    // registration-lifecycle rule for no real benefit.
    void InstallVendorPriceHook();

}  // namespace ChronicleBridge
