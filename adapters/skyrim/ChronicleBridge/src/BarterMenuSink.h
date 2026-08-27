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
// *** UPDATED SCOPE (was DETECTION ONLY -- corrected here, not left stale):
// research/26 originally scoped this file to detection-only, deferring the
// actual price write pending a reverse-engineered hook. research/28 found
// that hook needs no reverse engineering at all (a documented vtable-slot
// swap + Scaleform-callback-swap, both fully inside already-vendored
// CommonLibSSE-NG surface) -- see VendorPriceHook.h/.cpp for the WRITE
// half, which shares this file's vendor-Actor*->npc_id resolution chain
// (ResolveBarterVendorActor/ResolveNpcIdForActor, below) rather than
// duplicating it. This file itself still performs no write and installs no
// hook -- it remains the event-sink-based DETECTION path, now one of two
// ways this plugin reacts to a barter-menu open (this one via
// RE::MenuOpenCloseEvent for logging/telemetry; VendorPriceHook.cpp via the
// PostCreate vtable swap for the actual price mutation, since the price
// write must happen before Scaleform's own item-card update fires, not
// merely "on menu open"). ***
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
#include <optional>
#include <string>

namespace ChronicleBridge {

    struct PendingBarterOpen {
        std::string npcId;  // resolved per IdentityMap -- never a raw FormID.
    };

    // Shared with VendorPriceHook.cpp (docs/research/28-vendor-price-hook-
    // address-library-spike.md, the WRITE half of this feature): resolves
    // the actor currently targeted by an open BarterMenu via
    // RE::BarterMenu::GetTargetRefHandle() + RE::TESObjectREFR::
    // LookupByHandle + Actor::As<RE::Actor> -- the exact chain
    // BarterMenuHandler::ProcessEvent already used before this was factored
    // out. Returns nullptr (traced internally, not warned -- a common
    // transient case) if no live Actor currently resolves.
    RE::Actor* ResolveBarterVendorActor();

    // Shared with VendorPriceHook.cpp: the same forward FormRef ->
    // named-cast npc_id resolution BarterMenuHandler::ProcessEvent already
    // used before this was factored out (ResolveFormRef + ResolveNamedCast
    // -- see this file's own header comment for why no reverse IdentityMap
    // helper was needed for this direction). Returns std::nullopt for a
    // non-named-cast vendor (a generic merchant/guard) -- there is no
    // Chronicle grudge/markup state keyed on a generic fallback identity.
    std::optional<std::string> ResolveNpcIdForActor(RE::Actor* actor);

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
