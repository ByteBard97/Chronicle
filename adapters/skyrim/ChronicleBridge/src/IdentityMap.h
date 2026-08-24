#pragma once

// Design doc B3 (docs/design/chronicle-bridge-spatial-streamer.md): resolve
// every sampled actor to a stable identity that is never a raw FormID
// (architecture.md's FormID rule -- load-order-relative, silently corrupts
// after any mod-list change). Two cases:
//
//   1. The named cast Chronicle's belief/rumor/grudge engine already models
//      (jarl_balgruuf, proventus, ...) -- a small hand-maintained table,
//      keyed by (plugin_name, local_form_id) so it survives a load-order
//      change (the plugin name + local id pair is stable; the resolved
//      FormID is not).
//   2. Everyone else `RE::ProcessLists::highActorHandles` returns (guards,
//      generic citizens) -- the owner asked for "all the NPCs in
//      Whiterun," not just the named cast, so these still get tracked,
//      just under a generic fallback identity: "<plugin_name>:<local_id
//      as lowercase hex>". This is NOT a Chronicle npc_id and the belief
//      engine will never recognize it -- it exists purely so the
//      dashboard's live map has *something* stable to key a marker on.

#include <optional>
#include <string>

namespace ChronicleBridge {

    struct FormRef {
        std::string pluginName;
        std::uint32_t localFormId;  // the lower 24 bits of the resolved FormID -- load-order-independent.
    };

    // Returns the hand-maintained Chronicle npc_id for a known cast member,
    // or std::nullopt if this FormRef isn't in the table (case 2, above --
    // the caller falls back to FallbackIdentity, not an error).
    std::optional<std::string> ResolveNamedCast(const FormRef& ref);

    // The generic fallback identity for anyone not in the named-cast table.
    std::string FallbackIdentity(const FormRef& ref);

    // Resolve an actor's FormID into a FormRef (plugin name + local id),
    // per architecture.md's FormID rule -- this is the ONLY place in this
    // plugin allowed to look at a raw RE::FormID.
    std::optional<FormRef> ResolveFormRef(RE::TESForm* form);

}  // namespace ChronicleBridge
