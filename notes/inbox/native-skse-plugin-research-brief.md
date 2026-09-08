# Research brief — native SKSE plugin for Chronicle's game seam (2026-08-23)

**Status:** a research pass, not a build lane. Produces a report in the
`docs/research/` idiom (file:line/URL citations, license verification,
what-exists-vs-what-doesn't). Direction context:
`notes/inbox/native-skse-plugin-direction.md`; substrate decisions:
`docs/decisions/0001` and `0003`; existing research to build on, not
re-derive: `docs/research/01` (substrate survey), `11` (transport),
`12`/`13` (telemetry channel, ActorLocation schema, ProcessLists hook
points).

**The shape we're researching:** a first-party CommonLibSSE-NG plugin
("ChronicleBridge") that (a) hooks native game events and (b) streams
them — plus periodic actor spatial state — out of the game process to
Chronicle's Python bridge, with no Papyrus in the path. The owner has
shipped this exact category before (a native C++ plugin inside a host
app exposing an HTTP/JSON API to an external process, 442-function
surface, codegen included) — so "possible" is settled; this pass is
about *which existing code and libraries* get us there fastest and what
the sharp edges are.

## Questions (answer each with citations; name what's absent)

1. **Event sinks.** For our event set — NPC death, crime/bounty,
   dialogue start/end, cell attach/load, quest stage change, item
   transfer — which `RE::TES*Event`/SKSE event sources cover each?
   Find 2–3 real, shipped CommonLibSSE-NG plugins with clean event-sink
   code to pattern from (the SkyrimScripting `SKSE_Template_GameEvents`
   repo is the starting point, not the answer). Note which of our
   events have *no* native sink and need a different mechanism
   (and what that mechanism is).
2. **Networking inside the plugin.** Prior art for HTTP/WebSocket
   client *or* server embedded in an SKSE plugin: which libraries do
   people actually use (cpp-httplib, ixwebsocket, uWebSockets,
   Boost.Beast), are they vcpkg-available, and do they statically link
   cleanly into an SKSE DLL? **What does SkyrimWebSocket itself use
   under the hood** — read its source (report 13 read its protocol;
   this pass reads its implementation). Its wire protocol is already
   our canonical spatial schema — if its internals are sound, the
   report should say whether consuming it (install) or cloning its
   pattern (first-party) wins on evidence.
3. **Threading model.** CommonLibSSE-NG threading constraints: on what
   thread do event sinks fire, what may/may not be touched off the main
   game thread, and the correct marshaling idiom to a network thread
   (`SKSE::GetTaskInterface()->AddTask` and friends). Find one shipped
   plugin that does networking or heavy off-thread work and document
   its discipline.
4. **Build/deploy topology.** The plan: build on a Windows machine
   (MSVC + CMake + vcpkg, the CommonLibSSE-NG native path), deploy the
   DLL to the Linux/Proton NGVO install. Verify: any Proton-specific
   socket caveats for an in-process *server* socket (SKSE_HTTP's
   outbound client is separately being probe-verified); anything about
   Address Library / multi-runtime builds we must do from day one
   (engine-update fragility rule: an update breaks the adapter, never
   the sim).
5. **Actor enumeration for the spatial stream.** Confirm the
   `RE::ProcessLists` hook points filed in reports 12/13 are still
   accurate for 1.6.1170 (the pinned runtime), and find one concrete
   code example of iterating loaded actors + reading position/rotation.
6. **License hygiene.** Every candidate library/plugin: license
   verified (MIT/BSD/permissive only — the project ships nothing
   Bethesda-derived and no copyleft in the plugin).

## Output

`docs/research/22-native-skse-plugin-prior-art.md` (next number per the
index) + an index row. Recommendation section at the end: first-party
build vs. SkyrimWebSocket install vs. hybrid (first-party events +
SkyrimWebSocket spatial), with the evidence. No code written; no repo
files touched outside `docs/research/`.
