#include "SpatialStreamer.h"

namespace ChronicleBridge {

    std::vector<NpcPosition> SampleWhiterunExteriorPositions() {
        std::vector<NpcPosition> out;

        auto* processLists = RE::ProcessLists::GetSingleton();
        if (!processLists) return out;

        // highActorHandles: actors currently running full AI/animation/physics
        // (docs/research/22's verified figure: typically 10-50 entries, <50us
        // to iterate) -- deliberately NOT every actor in the worldspace ever
        // placed, only what the engine itself is actively simulating right
        // now. Tracking only what the game already tracks is the live-case
        // application of vision-v2.2.md §5's "honest fake" discipline
        // (design doc §1).
        for (auto& handle : processLists->highActorHandles) {
            auto actorPtr = handle.get();
            if (!actorPtr || actorPtr->IsDead() || !actorPtr->Is3DLoaded()) {
                continue;
            }

            auto* cell = actorPtr->GetParentCell();
            if (!cell || cell->IsInteriorCell()) {
                // Indoors (or no cell at all) -- absent from this snapshot,
                // not a stale/placeholder entry (design doc §1).
                continue;
            }

            auto* world = actorPtr->GetWorldspace();
            if (!world || world->GetFormID() != kWhiterunWorldFormId) {
                continue;
            }

            auto ref = ResolveFormRef(actorPtr.get());
            if (!ref) continue;  // couldn't resolve a stable identity -- skip, don't guess.

            auto id = ResolveNamedCast(*ref).value_or(FallbackIdentity(*ref));

            // GetDisplayFullName() is the same string the game's own UI
            // shows (dialogue subtitles, activation prompts) -- verify this
            // resolves against the actual CommonLibSSE-NG Actor/TESObjectREFR
            // headers on first build; not yet compiled against.
            std::string name = actorPtr->GetDisplayFullName();

            const RE::NiPoint3 pos = actorPtr->GetPosition();
            out.push_back(NpcPosition{.id = std::move(id), .name = std::move(name), .x = pos.x, .y = pos.y});
        }

        return out;
    }

}  // namespace ChronicleBridge
