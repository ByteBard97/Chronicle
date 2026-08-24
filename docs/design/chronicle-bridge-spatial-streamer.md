# ChronicleBridge design prep — live Whiterun spatial streamer (v0.2, first slice)

**Status:** design proposal, decisions resolved this pass (2026-08-24).
**No code to be dispatched from this until the Stage-0 spike (in
progress, game-side) confirms outbound networking from inside the
Proton prefix reaches the Linux host** — per `notes/ideas.md`'s own
framing, this is the highest-risk unknown in the whole bridge design
and nothing downstream should be built ahead of it.

Sources: `docs/research/22-native-skse-plugin-prior-art.md` (the
ChronicleBridge architecture and actor-enumeration design, filed
2026-08-23); `docs/decisions/0001,0003,0004,0005` (external-service
architecture, substrate choice, timeline branching, sync handshake);
`docs/architecture.md` (FormID rule, SAL, hydration seam);
`dashboard/map/whiterun_map.json` (the existing `WhiterunWorld`
world→pixel transform); `docs/vision-v2.2.md` §5 (corrected 2026-08-24,
commit `f28a306`); `notes/inbox/skse-http-test-harness-plan.md`
(SKSE_HTTP's actual client/server direction); direct conversation with
the owner, 2026-08-24 (scope: ~1Hz, all NPCs outdoors in Whiterun, no
coordinate once indoors — see memory
`project_chronicle_v0.2_realtime_npc_scope`).

Decisions here are prefixed **B** (bridge).

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
actually asked for"). **Resolved (B1/O1): build only this slice
first.** Nothing the owner said implies wanting deaths/crimes/dialogue
extraction yet — that stays real future work, not this lane.

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
  not a Papyrus timer — this needs `RE::ProcessLists`, a native-only
  structure Papyrus can't reach at all, so there's no meaningful
  "Papyrus-first" version of this specific piece (checked directly
  earlier in this design conversation).
- **Payload per tracked actor:** a stable identity (§3), `x`, `y` (no
  `z` — the map is a 2D top-down render, `whiterun_map.json`'s
  transform is 2D-only).

## 2. B2 — Where the code lives (resolved)

`adapters/skyrim/ChronicleBridge/` — not a decision so much as two
already-committed docs agreeing: `adapters/skyrim/README.md`'s own
charter names that directory "the only place in the repo allowed to
know Skyrim exists," and research/22 already named the plugin
ChronicleBridge. A CommonLibSSE-NG CMake project (research/22's
recommended scaffold), buildable independently of `chronicle/` —
`chronicle/` never imports it, matching every other lane's
engine-agnostic discipline.

## 3. B3 — Identity mapping (resolved: hand-maintained + fallback)

Per `architecture.md`'s FormID rule (load-order-relative, must never be
persisted raw): the plugin resolves each actor to `(plugin_name,
local_form_id)` at the point of sampling, not a bare `FormID` integer.

**Resolved:** a small hand-maintained table maps the named cast's
`(plugin_name, local_form_id)` to Chronicle's existing npc_ids
(`jarl_balgruuf`, `proventus`, ...); anything not in that table (guards,
generic citizens — `highActorHandles` will return plenty of these, and
the owner asked for "all the NPCs in Whiterun," not just the named
cast) gets a generic fallback id, the stringified `(plugin_name,
local_form_id)` pair itself. Auto-deriving the mapping from the load
order was considered and rejected: it can't invent a Chronicle npc_id
for someone the belief engine has never modeled, so it would solve
nothing the fallback doesn't already solve, for real added complexity.

## 4. B4 — Transport (resolved: outbound-only, direction matches Stage-0)

A live position isn't a belief, rumor, grudge, or derivation — it fails
`docs/frame-log-schema.md`'s own "three things only" rule (inputs,
derivations-with-inputs, acceleration) on its face. **This does not go
through `chronicle/events.py` or the frame log at all** — it's a
separate, non-canonical live feed.

**Resolved (supersedes this doc's earlier draft, which got the
transport direction wrong):** the plugin is an outbound **client**,
never a server. It pushes position snapshots out to a small listener
running on the Linux host, the same direction Stage-0 is built to
prove (SKSE_HTTP's actual mechanism — confirmed against
`notes/inbox/skse-http-test-harness-plan.md` — is "the game itself
acts as an HTTP client, sending a request out to a server that we run
locally," never the reverse). The earlier draft called for an embedded
`ix::WebSocketServer` *inside* the plugin, with the Linux side
connecting in — the opposite direction, and exactly the unverified,
higher-risk case `notes/ideas.md` names explicitly ("an in-process
WebSocket server bound to `127.0.0.1` inside the Proton prefix is
reachable from a native-Linux Python process"). A successful Stage-0
result proves outbound-from-prefix works; it proves nothing about
inbound-to-prefix. Since this slice only ever needs to push data out —
no inbound commands, nothing needs to reach into the game — there is
no reason to take on the unverified direction at all. **Drop the
`ix::WebSocketServer` dependency from this slice entirely.** Either
reuse SKSE_HTTP's `sendLocalhostHttpRequest` at ~1Hz with a JSON body,
or have ChronicleBridge make its own outbound connection with an
already-license-vetted client library (`cpp-httplib`, MIT, already in
research/22's dependency table) — verify which is more practical once
building starts; both satisfy "outbound only, matches what Stage-0
proves."

The listener on the Linux side (new, minimal, not `chronicle/`)
receives these pushes and makes them available to the dashboard.

**Resolved (browser delivery): file-polling, not a live server.** The
dashboard is currently a pure static-read, no-backend app (`AGENTS.md`,
the vision) — that invariant is what `check-range`'s tests and
`RunReader`'s whole poller design are built around. The listener writes
a small rolling JSON snapshot file; the dashboard's existing polling
machinery reads it the same way it already tails
`events.jsonl`/`trace.jsonl`. Zero change to the no-backend invariant —
a snapshot file is just one more thing to poll.

## 5. Still open

- **O5 (partially open) — exact outbound call.** `sendLocalhostHttpRequest`
  vs. a self-made `cpp-httplib` client connection — a build-time
  finding, not a design decision; either is fine, whichever proves
  simpler once the plugin scaffold exists.
- **Inbound-to-prefix remains unverified and is deferred entirely** —
  nothing in this slice needs it, so it isn't being tested or assumed;
  revisit only if a future slice genuinely needs the game to receive
  something (e.g. hydration overrides).

## 6. Dashboard-side consequence (out of this doc's scope to design)

A live position overlay on the existing map view, converting each
`(x, y)` through `whiterun_map.json`'s existing `transform` formula —
confirmed already correct for this exact worldspace, no new coordinate
work needed there. Left for its own lane once the plugin side has
something real to consume.
