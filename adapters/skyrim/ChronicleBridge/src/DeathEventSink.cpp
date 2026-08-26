#include "DeathEventSink.h"

#include <chrono>

#include "IdentityMap.h"

namespace ChronicleBridge {

    namespace {

        // Resolves a raw game reference (actorDying, actorKiller, or a cell)
        // through the exact same FormRef/named-cast/fallback chain
        // SpatialStreamer.cpp already uses for positions -- this slice
        // introduces no new identity-resolution logic, per the design doc's
        // §2 instruction to reuse IdentityMap.cpp unchanged.
        std::optional<std::string> ResolveActorIdentity(RE::TESForm* form) {
            auto ref = ResolveFormRef(form);
            if (!ref) return std::nullopt;
            return ResolveNamedCast(*ref).value_or(FallbackIdentity(*ref));
        }

        // ADR-0010: 1 tick = 1 gamets = 1 game-hour. RE::Calendar is the
        // engine's own in-game-time singleton; GetHoursPassed() returns a
        // monotonically-increasing double counting real in-game hours since
        // the game/save started (NOT wall-clock hours, and NOT reset by
        // sleeping/waiting -- both of those still advance in-game time,
        // which is exactly the "ticks keep advancing" semantics ADR-0010's
        // tick quantum wants). This is the only field on RE::Calendar that
        // matches "a single monotonic hours-elapsed number," as opposed to
        // GetDay()/GetMonth()/GetYear() (calendar-date components, would
        // require reconstructing an hours-since-epoch value by hand) or
        // GetTimescale() (a game-hours-per-real-second multiplier, not a
        // clock value at all). Verify GetHoursPassed()'s exact name against
        // the real CommonLibSSE-NG header on first build -- research/22
        // does not name it explicitly, this is inferred from the documented
        // engine field its known offset/RTTI, not confirmed compiled
        // knowledge, before this session's Windows-build-machine pass.
        double CurrentGamets() {
            auto* calendar = RE::Calendar::GetSingleton();
            if (!calendar) return 0.0;
            return static_cast<double>(calendar->GetHoursPassed());
        }

        class DeathEventHandler : public RE::BSTEventSink<RE::TESDeathEvent> {
        public:
            static DeathEventHandler* GetSingleton() {
                static DeathEventHandler singleton;
                return &singleton;
            }

            std::function<void(PendingGameEvent)> onDeath;

            RE::BSEventNotifyControl ProcessEvent(const RE::TESDeathEvent* a_event,
                                                   RE::BSTEventSource<RE::TESDeathEvent>*) override {
                if (!a_event || !a_event->actorDying || !onDeath) {
                    return RE::BSEventNotifyControl::kContinue;
                }

                // actorDying/actorKiller are RE::TESObjectREFRPtr (a smart
                // pointer to the reference), per research/22's table --
                // .get() hands back the raw RE::TESObjectREFR* IdentityMap's
                // ResolveFormRef(RE::TESForm*) already accepts (TESObjectREFR
                // derives from TESForm). Verify this exact smart-pointer
                // type against the real TESDeathEvent header on first build
                // -- research/22 only names the fields, not their C++ types.
                auto* dyingForm = a_event->actorDying.get();
                auto npcId = ResolveActorIdentity(dyingForm);
                if (!npcId) {
                    // Couldn't resolve even a fallback identity (no
                    // originating plugin file) -- skip, don't guess, same
                    // discipline SpatialStreamer.cpp uses for positions.
                    return RE::BSEventNotifyControl::kContinue;
                }

                PendingGameEvent event;
                event.npcId = std::move(*npcId);
                event.gamets = CurrentGamets();
                event.wallTs =
                    std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();
                // cause stays the default "unknown" (design doc D2).

                if (a_event->actorKiller) {
                    event.killerId = ResolveActorIdentity(a_event->actorKiller.get());
                }

                if (auto* cell = dyingForm ? dyingForm->GetParentCell() : nullptr) {
                    if (auto cellRef = ResolveFormRef(cell)) {
                        event.locationId = ResolveNamedCast(*cellRef).value_or(FallbackIdentity(*cellRef));
                    }
                }

                onDeath(std::move(event));
                return RE::BSEventNotifyControl::kContinue;
            }
        };

    }  // namespace

    void RegisterDeathEventSink(std::function<void(PendingGameEvent)> onDeath) {
        auto* handler = DeathEventHandler::GetSingleton();
        handler->onDeath = std::move(onDeath);

        auto* eventHolder = RE::ScriptEventSourceHolder::GetSingleton();
        if (!eventHolder) {
            SKSE::log::error("ChronicleBridge: ScriptEventSourceHolder::GetSingleton() returned null -- death sink NOT registered");
            return;
        }
        eventHolder->AddEventSink<RE::TESDeathEvent>(handler);
        SKSE::log::info("ChronicleBridge: TESDeathEvent sink registered");
    }

}  // namespace ChronicleBridge
