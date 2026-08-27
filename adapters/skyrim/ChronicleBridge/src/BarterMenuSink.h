#pragma once

// Fifth ChronicleBridge slice -- the DETECTION half of
// docs/design/chronicle-bridge-vendor-markup-out.md's grudge-driven vendor
// markup feature, per docs/research/26-vendor-price-markup-hook.md's own
// split. Sinks RE::MenuOpenCloseEvent (research/26 F2: a real, minimal,
// already-documented CommonLibSSE-NG event type -- BSFixedString menuName +
// bool opening, nothing else) via RE::UI::GetSingleton()->AddEventSink, the
// real registration mechanism confirmed in RE/U/UI.h (RE::UI publicly
// derives from BSTEventSource<MenuOpenCloseEvent> and exposes a templated
// AddEventSink<T> that forwards to it) -- NOT RE::ScriptEventSourceHolder,
// which is DeathEventSink.h's registration target for RE::TESDeathEvent, a
// different event family. Otherwise this is the exact same "clean top-level
// BSTEventSink, no inline hook required" shape DeathEventSink.h's own header
// comment already established.
//
// When "BarterMenu" opens (RE::BarterMenu::MENU_NAME, RE/B/BarterMenu.h),
// resolves the vendor via RE::BarterMenu::GetTargetRefHandle() (research/26
// F1: a real documented static accessor, RELOCATION_ID-backed the same way
// every other ChronicleBridge RE:: write/read already trusts -- no
// menu-internal GFx/UI scraping, no reverse engineering), then resolves that
// Actor* to a Chronicle npc_id via IdentityMap's EXISTING forward chain
// (ResolveFormRef + ResolveNamedCast -- the same composition
// DeathEventSink.cpp's own ResolveActorIdentity already uses). IdentityMap
// did not need a new reverse (Actor* -> npc_id) helper for this: that
// direction was already covered by the forward resolution functions it
// already had; only the OTHER direction (npc_id -> Actor*, for
// HydrationPoller/AvoidancePoller's writes) ever needed a genuinely new
// helper (ResolveChronicleNpcId), and this slice doesn't need that one.
//
// *** DELIBERATE SCOPE LIMIT (research/26's own recommendation, restated
// here so it isn't lost): this slice is DETECTION ONLY. It performs no
// price write, installs no hook/detour/trampoline, and touches
// RE::BarterMenu through nothing but its one documented static function.
// The actual price write requires a reverse-engineered internal price-calc
// hook (research/26 F5/F6) -- explicitly out of scope for this slice and
// for whoever reads this file next; do not add one here without a separate,
// deliberate go/no-go decision, per that doc's own Recommendation section.
// ***
//
// ProcessEvent (like DeathEventSink's) runs synchronously on the main
// thread -- only fast, main-thread-safe work happens inline (identity
// resolution). The optional read-only markup-fetch-and-log this slice may
// also do is network I/O and must happen off that thread, same discipline
// as every other network call in this plugin -- see plugin.cpp for how the
// callback below is drained.
//
// *** UNVERIFIED AT RUNTIME (same "compiles only" caveat HydrationPoller.h/
// AvoidancePoller.h already carry for their own writes): whether the
// static RELOCATION_ID global GetTargetRefHandle() reads is already
// populated at the exact instant MenuOpenCloseEvent dispatches with
// opening == true (menu construction vs. event dispatch ordering) is not
// something either header confirms -- this has only been compiled, never
// exercised against a live game. The code fails safe either way (a null
// resolve is logged at trace and skipped, never crashes), but if nothing
// ever appears in the log for a real barter-menu open, this ordering
// assumption -- not sink registration -- is the first thing to suspect. ***

#include <functional>
#include <string>

namespace ChronicleBridge {

    struct PendingBarterOpen {
        std::string npcId;  // resolved per IdentityMap -- never a raw FormID.
    };

    // Registers the menu-open/close sink with RE::UI. Must be called during/
    // after SKSE::MessagingInterface::kDataLoaded -- same lifecycle rule
    // DeathEventSink's own RegisterDeathEventSink follows for
    // RE::ScriptEventSourceHolder; RE::UI::GetSingleton() is equally safe to
    // call at that point.
    //
    // onBarterOpen fires only when BarterMenu opens against a vendor that
    // resolves to a KNOWN named-cast npc_id (IdentityMap::ResolveNamedCast).
    // A vendor with no named-cast entry (a generic merchant/guard) is
    // silently skipped -- there is no Chronicle grudge/markup state keyed on
    // a generic fallback identity, so there is nothing to log or fetch a
    // markup for.
    void RegisterBarterMenuSink(std::function<void(PendingBarterOpen)> onBarterOpen);

}  // namespace ChronicleBridge
