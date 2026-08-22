---
date: 2026-08-22
sources:
  - "session source-reading pass, 2026-08-22 (explore agent; repos cloned to /tmp/chronicle-externals/ and read directly — SkyrimWebSocket @63b4d0c, generative_agents, uesp-gamemap, where-are-you, doticu-npc-lookup)"
topic: "Dashboard prior art at source level — WS wire protocol, replay/step-file schema, map projection, NPC enumeration"
status: filed
---

# Dashboard prior art: source-level read

Companion to report 12 (asset/licensing survey): this pass read the actual
source of the four closest projects to extract implementable patterns —
exact file:line references, protocol shapes, and data formats. Resolves
report 12's flagged uncertainty about SkyrimWebSocket.

## Findings

- **[BUILD-ON, decisive] SkyrimWebSocket verified and adopted as the live-telemetry reference.** MIT LICENSE file confirmed (© 2026 andreyvelsk); CommonLibSSE-NG multi-runtime (SE/AE/VR) — **compatible with the 1.6.1170 pin by construction**; very active (last commit 2026-08-18, v1.16.0). Single-author bus factor stands; MIT makes it forkable.
- **[BUILD-ON] Adopt its wire protocol verbatim as Chronicle's canonical transport** (`PROTOCOL.md`): client-driven `subscribe`/`query`/`unsubscribe`/`heartbeat`/`command` → `data`/`commandResult`/`error`, with a **field-key registry** (clients request fields by string key with client-chosen aliases) and `sendOnChange` diffing, 50 ms minimum push. Chronicle's Python core and dashboard should speak this protocol from day one, so headless-sim and in-game feeds are drop-in interchangeable.
- **[BUILD-ON] Adopt its spatial JSON block as Chronicle's canonical `ActorLocation` schema** (`PlayerPosition.cpp:86-132`, `QuestMarkers.cpp:831-872`): `{x, y, z, angle, worldspace, worldspaceFormId, parentWorldspace, parentWorldspaceFormId, cell, cellFormId, isInterior}`. Coordinates are **cell/worldspace-local, never globally unified** — matching report 12's per-cell-layer constraint. Interior→parent-worldspace resolution is a documented 5-stage fallback chain (`PlayerPosition.cpp:8-84`). Map-marker enumeration already yields free Whiterun anchors (marker typeIds: WhiterunCastle=39, WhiterunCapitol=40).
- **[BUILD-ON, concrete fork plan] The missing bulk-actor stream has exact hook points.** SkyrimWebSocket never touches `RE::ProcessLists` today. Fork plan: new `ActorReader.cpp` resolver (pattern after `MapMarkers.cpp`) iterating `ProcessLists::GetSingleton()->highActorHandles`, emitting the spatial block + formId + `GetDisplayFullName()`; register in `s_json_registry` (`FieldRegistry.cpp:199`) — flows through subscribe/query/sendOnChange with zero server changes. Its threading pattern (asio timer → `SKSE::GetTaskInterface()->AddTask` marshals reads onto the game thread → post back to IO thread; EventBus version counters so heavy resolvers run once per change, `GameReader.cpp:106-117`) stays untouched.
- **[BUILD-ON] Smallville's replay machinery is the sim-trace template** (Apache-2.0 confirmed via GitHub API): per-step `movement/<step>.json` = `{persona: {name: {movement:[x,y], pronunciatio, description, chat}}, meta:{curr_time}}` (`reverie.py:371-402`); offline fold into one delta-compressed `master_movement.json` — **a persona appears in a step only if something changed** (`compress_sim_storage.py:35-51`). Frontend loads the whole trace client-side and interpolates one-step-per-tile tweens. **Smallville has no seek slider — only play/pause** (`demo.html:22-27`); Chronicle adds the scrubber. Copy: step schema + delta compression + load-whole-trace + interpolation loop + per-agent panel. Skip: Phaser, Tiled, Django, sprite atlases.
- **[BUILD-ON] uesp-gamemap's projection is the ~10-line affine report 12 predicted** (MIT confirmed): `xN=(x-minX)/rangeX; yN=abs((y-maxY)/rangeY)` (Y-flip; `gamemap.js:1416-1417`), then × pixel dims through vendored MIT leaflet-rastercoords (`zoom = ceil(log2(max(w,h)/tileSize))`). Per-worldspace bounds constants (`posLeft/…/posBottom`, `cellSize`, `maxZoom`) are server-side — Chronicle calibrates its own, as report 12 already concluded. Marker layer pattern: tile pyramid base + one ephemeral overlay layer rebuilt from a data array + zoom-gated labels. Reimplement, don't vendor.
- **[RISK] NPC enumeration has two patterns with different costs.** Where Are You (k0mp1ex/where-are-you, **MIT** — public source found this pass) enumerates via `RE::TESForm::GetAllForms()` under read lock, filtering `IsUnique()` (`src/Papyrus.cpp:45-60`) — a full-form scan, fine for a startup census, wrong for a per-tick feed. The live feed is the `ProcessLists` pattern above. doticu-npc-lookup has **no OSI license** (Papyrus+SkyUI anyway) — do not copy.
- **[DESIGN-INPUT] Headless-sim/later-game symmetry is now fully specified:** the dashboard consumes `{step → per-agent {movement, status-emoji, description, chat}}` (Smallville shape) where "movement" for headless Whiterun is schedule-block location, and later the same stream shape arrives from SkyrimWebSocket's spatial block. One frontend, two feeds — this operationalizes report 12's dual-source design input.

## Flagged uncertainties

- `ProcessLists` high-actor radius semantics: `highActorHandles` covers the actively-AI'd actors near the player; WhiterunWorld when the player is inside is fine, but "all Whiterun NPCs while the player is in Riften" needs the low-process lists or an offline census — the dashboard's *headless* feed never has this problem, only the live one.
- SkyrimWebSocket's `sendOnChange` diffs by serialized-string compare — cheap for scalars, potentially wasteful for a 30-actor array; the fork may want per-actor field aliases instead of one array field.
