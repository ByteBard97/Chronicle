# ChronicleBridge design prep — live Whiterun spatial streamer (v0.2, first slice)

**Status:** design proposal for owner review. **No code to be dispatched
from this until the Stage-0 spike (in progress, game-side) confirms the
Proton↔Linux localhost networking path actually works** — per
`notes/ideas.md`'s own framing, this is the highest-risk unknown in the
whole bridge design and nothing downstream should be built ahead of it.
Written now so there's zero lag once that answer is in hand, not as
authorization to start building.

Sources: `docs/research/22-native-skse-plugin-prior-art.md` (the
ChronicleBridge architecture and actor-enumeration design, filed
2026-08-23); `docs/decisions/0001,0003,0004,0005` (external-service
architecture, substrate choice, timeline branching, sync handshake);
`docs/architecture.md` (FormID rule, SAL, hydration seam);
`dashboard/map/whiterun_map.json` (the existing `WhiterunWorld`
world→pixel transform); `docs/vision-v2.2.md` §5 (corrected 2026-08-24,
commit `f28a306`); direct conversation with the owner, 2026-08-24
(scope: ~1Hz, all NPCs outdoors in Whiterun, no coordinate once indoors
— see memory `project_chronicle_v0.2_realtime_npc_scope`).

Decisions here are prefixed **B** (bridge). Open points for the owner
are collected in §5.

---

## 0. What this slice actually is

Not the full ChronicleBridge plugin research/22 sketches (event sinks
for deaths/crimes/dialogue/quest-stages, hydration overrides,
save/reload sync). Deliberately **just the spatial streamer** — the
smallest real slice that delivers what the owner actually asked for:
walk to Whiterun, watch NPCs' positions update live on the dashboard
map while they're outdoors, nothing once they're inside. Everything
else research/22 designed is real and still the eventual shape of
`adapters/skyrim/`, but sequencing it all into one first deliverable
would be exactly the kind of scope creep this project has avoided all
along (the same discipline as "no economy before v0.4," applied here
to "no full event-extraction pipeline before the one thing that was
actually asked for").

## 1. Scope, precisely

- **Where:** `WhiterunWorld` (form `0x0001A26F`, confirmed against
  `dashboard/map/whiterun_map.json`'s `worldspace` field) — exterior
  cells only.
- **Who:** every actor `RE::ProcessLists::highActorHandles` reports as
  currently loaded there (research/22's own perf numbers: 10-50 actors,
  <50 microseconds to iterate) — not Chronicle's own named-cast fixture
  list. If an actor isn't in that list, the game itself isn't actively
  simulating them right now; tracking only what the engine already
  tracks is the same "honest fake" discipline vision-v2.2.md §5 already
  commits to for the headless case, applied to the live case instead.
- **When tracked:** `actor->GetParentCell()` exterior AND
  `Is3DLoaded()` true. The instant an actor's parent cell is interior,
  they are simply **absent** from the next snapshot — no stale
  position, no placeholder, matching the owner's own framing exactly
  ("all the NPCs who are outside in Whiterun have a coordinate until
  they enter a building").
- **Cadence:** ~1 Hz (owner-approved tradeoff — explicitly not
  animation-frame-rate). A `SKSE::GetTaskInterface()` periodic task,
  not a Papyrus timer (research/22's rationale: this needs
  `RE::ProcessLists`, a native-only structure Papyrus can't reach at
  all, so there's no meaningful "Papyrus-first" version of this
  specific piece — see the earlier conversation turn where this was
  checked directly).
- **Payload per tracked actor:** FormID (resolved to a stable identity
  per §3, never stored raw per `architecture.md`'s FormID rule), `x`,
  `y` (no `z` — the map is a 2D top-down render, `whiterun_map.json`'s
  transform is 2D-only).

## 2. B1 — Where the code lives

`adapters/skyrim/` per `adapters/skyrim/README.md`'s own charter ("the
only place in the repo allowed to know Skyrim exists") and ADR-0001's
isolation rationale. Concretely `adapters/skyrim/ChronicleBridge/`, a
CommonLibSSE-NG CMake project (research/22's recommended scaffold),
buildable independently of `chronicle/` — `chronicle/` never imports
it, matching every other lane's engine-agnostic discipline.

## 3. B2 — Identity mapping, not raw FormIDs

Per `architecture.md`'s FormID rule (load-order-relative, must never be
persisted raw): the plugin resolves each actor to `(plugin_name,
local_form_id)` at the point of sampling, not a bare `FormID` integer.
This composite key is Chronicle's actual npc identity going forward —
the same discipline the eventual full event-extraction pipeline will
need anyway, so building it correctly now rather than raw-FormID-first-
then-fixing-later avoids exactly the class of silent-corruption bug the
ADR warns about.

**Not yet resolved (owner input needed, §5 O3):** whether the mapping
from `(plugin_name, local_form_id)` to a Chronicle-style npc_id
(`jarl_balgruuf`, `proventus`, ...) is a small hand-maintained table for
the named cast plus a generic fallback for unnamed NPCs, or something
auto-derived from the load order at startup.

## 4. B3 — Transport is a side-channel, not the frame log

A live position isn't a belief, rumor, grudge, or derivation — it fails
`docs/frame-log-schema.md`'s own "three things only" rule (inputs,
derivations-with-inputs, acceleration) on its face. **Decision: this
does not go through `chronicle/events.py` or the frame log at all.**
It's a separate, non-canonical live feed: the plugin's embedded
`ix::WebSocketServer` (research/22's Option C) pushes position
snapshots; a small Python-side listener (new, minimal — not
`chronicle/`) receives them and makes them available to the dashboard.

**Not yet resolved (owner input needed, §5 O4):** exactly how that
listener exposes the feed to the browser. The dashboard is currently a
pure static-read, no-backend app (`AGENTS.md`, `vision`) — introducing
any live push-to-browser channel is a small but real architectural
exception to that invariant, worth the owner's explicit sign-off rather
than a default I pick myself. Candidates: (a) the listener writes a
tiny rolling JSON file the dashboard's existing polling machinery reads
the same way it already tails `events.jsonl`/`trace.jsonl`, staying
fully within "static-read" by treating position snapshots as just
another file to poll; (b) a small dev-only local WebSocket/SSE server
the dashboard subscribes to directly, matching the `npm run dev`
server's own already-local-only nature. (a) is the more conservative,
doctrine-preserving choice and is my default recommendation absent
other input.

## 5. Open points for the owner

- **O1 — Sequencing.** Confirm building only the spatial streamer
  first (§0), deferring the full event-sink/hydration pipeline
  research/22 designed to a later slice, once this one is proven live
  against a real game session.
- **O2 — Plugin location/name.** Confirm `adapters/skyrim/ChronicleBridge/`
  (§2) as both location and name, or propose otherwise.
- **O3 — Identity mapping approach.** Hand-maintained table vs.
  auto-derived (§3).
- **O4 — How the feed reaches the browser.** File-polling side-channel
  (recommended, preserves the no-backend invariant) vs. a small local
  live server (§4).
- **O5 — Does this wait on the Stage-0 spike's exact result, or only
  on "networking works at all"?** The spike tests SKSE_HTTP's
  request/reply pattern; this design calls for an embedded WebSocket
  *server* instead (a different, if related, networking primitive).
  Recommendation: treat a successful Stage-0 result as sufficient
  proof that Proton↔Linux localhost networking works in principle, and
  let this slice's own first build be the concrete test of the
  WebSocket-server variant specifically — not a reason to run a second
  separate spike first.

## 6. Dashboard-side consequence (out of this doc's scope to design)

A live position overlay on the existing map view, converting each
`(x, y)` through `whiterun_map.json`'s existing `transform` formula —
confirmed already correct for this exact worldspace, no new coordinate
work needed there. Left for its own lane once §5's open points are
ruled and the plugin side has something real to consume.
