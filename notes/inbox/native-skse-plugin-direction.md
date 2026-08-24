# Native C++ SKSE plugin — direction captured from conversation (2026-08-23)

## Context

While building the tiny SKSE_HTTP probe (see
`notes/inbox/skse-http-test-harness-plan.md` and
`notes/inbox/skse-http-test-harness-impl-plan.md`), a bigger architectural
question came up that's worth keeping on record before it gets lost.

## The question

Could Chronicle skip SKSE_HTTP (and Papyrus scripting for event emission
generally) and instead write our own native SKSE plugin — a CommonLibSSE-NG
DLL — that hooks game events in C++ and sends them out over HTTP,
WebSocket, or even raw UDP directly, with no Papyrus involved at all?

## Conclusion reached

**Yes, and this is architecturally the better long-term answer, not just an
alternative.** This is in fact what ADR-0003's "standalone bridge" choice
already implies — a plugin built on CommonLibSSE-NG + Address Library is
Chronicle's own native code, not a dependency on someone else's DLL like
SKSE_HTTP.

Reasoning:

- **SKSE_HTTP becomes unnecessary, not complementary.** It only exists to
  give Papyrus scripts a way to call out to HTTP. If C++ is doing the event
  hooking, it can also do the networking itself, directly, in any wire
  format (JSON, protobuf, whatever) — SKSE_HTTP would just be a redundant
  middle layer at that point.
- **Scales far better than per-NPC Papyrus scripts.** CommonLibSSE-NG event
  sinks (TESDeathEvent, TESHitEvent, etc.) hook globally, once, rather than
  needing a script instance attached to every one of ~1,000 NPCs. Papyrus
  also has real per-frame call-count limits that would become painful at
  that scale.
- **Sidesteps the entire Papyrus-compiler toolchain problem** hit while
  building the probe (missing vanilla `Scripts/Source` files, needing
  Bethesda's `Archive.exe` to unpack `Skyrim - Misc.bsa`). C++ hooking via
  CommonLibSSE-NG's own headers never touches the Papyrus compiler at all.
- **UDP is a good fit for high-frequency, low-criticality telemetry**
  (e.g. periodic position ticks) where dropped packets don't matter.
  Discrete important events (deaths, crimes) probably still want
  HTTP/WebSocket-style delivery guarantees. A hybrid is plausible.

## Complexity comparison (user-supplied, load-bearing context)

The user has already shipped `nuxp` (`/home/geoff/projects/Flora/nuxp`) —
a C++ plugin for Adobe Illustrator exposing 442+ SDK functions across 19
suites via a local HTTP server + SSE stream, consumed by a TypeScript
frontend over HTTP/JSON. Real threading hazards (wrong-thread SDK calls
crash Illustrator silently, no error message) and a tree-sitter-based code
generator were both required to make that project viable.

Chronicle's Skyrim plugin is expected to be **categorically simpler** than
`nuxp`, for two independent reasons, both agreed in conversation:

1. **Read-only telemetry vs. two-way arbitrary command execution.**
   `nuxp`'s hard problem is that the frontend can call any of 442 functions
   to *mutate* live Illustrator document state — that's what demands the
   careful threading discipline. Chronicle's plugin (for this phase) only
   *observes* game events and pushes them out; it never needs to reach back
   into the game and change anything. The two-way "inject state back into
   the game" direction (AI-package overrides etc., per
   `adapters/skyrim/README.md`'s "Out" direction) is explicitly a later
   concern, not phase 1.
2. **No codegen needed.** `nuxp` required building a tree-sitter parser to
   mechanically generate hundreds of bindings — a meta-problem on top of
   the plugin itself, only justified at 442-function scale. Chronicle needs
   a handful of hand-written event hooks; codegen doesn't pay for itself at
   that size, so this whole category of infrastructure is skipped entirely.

CommonLibSSE-NG is also better-trodden ground than Adobe's raw SDK — years
of community plugins to copy patterns from, versus `nuxp`'s harder starting
position.

## Build environment decision

- Compile on the user's separate Windows machine (SSH in, enable Windows'
  built-in OpenSSH server), using Visual Studio Build Tools + CMake, since
  CommonLibSSE-NG's tooling assumes MSVC and that's the well-documented
  path. Cross-compiling a Windows DLL from this Linux box via MinGW-w64
  would fight unsupported friction for no real benefit.
- The compiled `.dll` is portable — only the *build* needs Windows; it gets
  copied (`scp`/`rsync`) into NGVO's MO2 mods folder on this Linux box for
  actual testing/use, same as any other SKSE plugin.

## Status / next steps

- **Not started yet.** This is a captured direction, not a plan. The
  user may spin up research agents to look for existing CommonLibSSE-NG
  code that already does pieces of this (event-sink patterns, minimal
  HTTP/WebSocket-serving plugin templates) before committing to a design.
- The SKSE_HTTP Papyrus probe (see the two docs linked above) is still
  being finished in parallel as the smallest possible end-to-end proof
  that Skyrim can talk to an external process — that work isn't wasted
  even if the native-plugin path supersedes SKSE_HTTP later, since the
  Python-listener half of it is reusable regardless of what's on the
  Skyrim side.
- No design doc, no ESP/plugin skeleton, no CommonLibSSE-NG scaffolding
  exists yet for the native path. Treat this file as the brief for
  whatever picks that up next (a planning agent, a research pass, or
  direct implementation).

## Resolved (2026-08-24): probe vs. ChronicleBridge

`ChronicleBridge` (`adapters/skyrim/ChronicleBridge/`) got built the
night after this doc was written and its source is complete -- spatial
streamer, identity map, outbound HTTP client, INI-based config. It
**supersedes the SKSE_HTTP Papyrus probe** for this seam, exactly per
this doc's original reasoning: no Papyrus, no per-NPC scripts, no CK
toolchain dependency. The probe's Python-listener half
(`adapters/skyrim/listener/`) was always the reusable part regardless,
and stays in use. The probe's Skyrim-side half (`~/skse-http-probe/`,
`~/Games/NGVO/mods/ZZChronicleProbe/`) is now moot -- not deleted, just
no longer worth finishing the ESP for. Remaining work is compiling
ChronicleBridge on Windows and testing it against a live game, not
picking between the two paths.
