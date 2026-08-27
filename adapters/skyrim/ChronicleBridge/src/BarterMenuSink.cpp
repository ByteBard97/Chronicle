#include "BarterMenuSink.h"

#include "IdentityMap.h"

namespace ChronicleBridge {

    namespace {

        class BarterMenuHandler : public RE::BSTEventSink<RE::MenuOpenCloseEvent> {
        public:
            static BarterMenuHandler* GetSingleton() {
                static BarterMenuHandler singleton;
                return &singleton;
            }

            std::function<void(PendingBarterOpen)> onBarterOpen;

            RE::BSEventNotifyControl ProcessEvent(const RE::MenuOpenCloseEvent* a_event,
                                                   RE::BSTEventSource<RE::MenuOpenCloseEvent>*) override {
                if (!a_event || !a_event->opening || !onBarterOpen) {
                    return RE::BSEventNotifyControl::kContinue;
                }
                if (!(a_event->menuName == RE::BarterMenu::MENU_NAME)) {
                    return RE::BSEventNotifyControl::kContinue;
                }

                auto* vendor = ResolveBarterVendorActor();
                if (!vendor) {
                    return RE::BSEventNotifyControl::kContinue;
                }

                auto npcId = ResolveNpcIdForActor(vendor);
                if (!npcId) {
                    // Not a named-cast NPC (a generic merchant) -- nothing
                    // Chronicle-relevant to report. Deliberately NOT falling
                    // back to FallbackIdentity() the way DeathEventSink does
                    // for deaths: there is no grudge/markup state keyed on a
                    // generic "<plugin>:<hex>" identity, so logging one here
                    // would be noise with nothing to act on.
                    return RE::BSEventNotifyControl::kContinue;
                }

                onBarterOpen(PendingBarterOpen{.npcId = *npcId});
                return RE::BSEventNotifyControl::kContinue;
            }
        };

    }  // namespace

    RE::Actor* ResolveBarterVendorActor() {
        // research/26 F1: a real, documented static accessor -- no
        // menu-internal GFx/UI scraping, no reverse engineering.
        auto handle = RE::BarterMenu::GetTargetRefHandle();
        auto refPtr = RE::TESObjectREFR::LookupByHandle(handle);
        if (!refPtr) {
            SKSE::log::trace(
                "ChronicleBridge barter: BarterMenu opened but GetTargetRefHandle() did not resolve to a "
                "live reference");
            return nullptr;
        }

        auto* vendor = refPtr->As<RE::Actor>();
        if (!vendor) {
            SKSE::log::trace("ChronicleBridge barter: BarterMenu's target reference is not an Actor -- skipping");
            return nullptr;
        }
        return vendor;
    }

    std::optional<std::string> ResolveNpcIdForActor(RE::Actor* actor) {
        if (!actor) return std::nullopt;

        // Same forward FormRef -> named-cast resolution
        // DeathEventSink.cpp's ResolveActorIdentity already uses -- no new
        // IdentityMap reverse helper needed for THIS direction (Actor* ->
        // npc_id was already reachable via the existing ResolveFormRef +
        // ResolveNamedCast composition; only the OTHER direction, npc_id ->
        // Actor*, ever needed a genuinely new helper, ResolveChronicleNpcId,
        // which this direction doesn't use).
        auto ref = ResolveFormRef(actor);
        if (!ref) {
            SKSE::log::trace("ChronicleBridge barter: vendor actor has no resolvable FormRef -- skipping");
            return std::nullopt;
        }

        return ResolveNamedCast(*ref);
    }

    void RegisterBarterMenuSink(std::function<void(PendingBarterOpen)> onBarterOpen) {
        auto* handler = BarterMenuHandler::GetSingleton();
        handler->onBarterOpen = std::move(onBarterOpen);

        auto* ui = RE::UI::GetSingleton();
        if (!ui) {
            SKSE::log::error("ChronicleBridge: RE::UI::GetSingleton() returned null -- barter-menu sink NOT registered");
            return;
        }
        ui->AddEventSink<RE::MenuOpenCloseEvent>(handler);
        SKSE::log::info("ChronicleBridge: MenuOpenCloseEvent (BarterMenu) sink registered");
    }

}  // namespace ChronicleBridge
