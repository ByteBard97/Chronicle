# Native SKSE Plugin Prior-Art Research: "ChronicleBridge" for Chronicle (Skyrim SE/AE)

**Prepared:** 2026-08-23 · **Pinned runtime:** Skyrim SE 1.6.1170 (AE codebase) · **Framework:** CommonLibSSE-NG · **Toolchain:** Windows MSVC + CMake + vcpkg · **Deploy target:** Linux/Proton

## TL;DR

- **Most of Chronicle's event set is covered by native `RE::TES*Event` sinks** registered through `RE::ScriptEventSourceHolder` (NPC death, cell attach, quest stage, item transfer). **Dialogue start/end and crime/bounty change have NO native event source** and must be obtained by function hooks (trampoline) or polling — this is the single biggest engineering risk and the main reason a first-party events plugin is unavoidable.
- **The networking is a solved problem**: IXWebSocket (BSD-3-Clause) and cpp-httplib (MIT) are both on vcpkg, header-light, and statically linkable into an SKSE DLL; SkyrimNet proves a full HTTP/WS stack can live inside the game process with heavy work on worker threads and the game thread never blocked. All game-state reads must be marshaled to the main thread via `SKSE::GetTaskInterface()->AddTask`.
- **Recommendation: Option C (hybrid) is the strongest, but tilted toward first-party.** Build the event + spatial plugin first-party (you need the hooks and thread discipline regardless), and treat SkyrimWebSocket only as a protocol/reference to clone, not a dependency to install — its source is not confidently locatable and its Proton behavior is unverified. Ship runtime-agnostic (CommonLibSSE-NG multi-runtime) from day one.

## Key Findings

1. **Event sinks exist for 4 of 6 event classes.** `TESDeathEvent`, `TESCellAttachDetachEvent`, `TESQuestStageEvent`, and `TESContainerChangedEvent` are all real, shipped `BSTEventSink` sources in CommonLibSSE-NG, registered through `RE::ScriptEventSourceHolder::GetSingleton()->AddEventSink<T>(sink)`.
2. **Dialogue start/end and crime/bounty change do NOT exist as event sources.** These require alternative mechanisms (menu-open/close proxy + function hooks for dialogue; hooks on the crime-gold path or polling `GetCrimeGold` per faction for bounty).
3. **IXWebSocket is the best-fit networking library** (BSD-3-Clause, vcpkg, minimal dependencies with "no boost", per-connection OS threads, `ix::initNetSystem()` wraps WSAStartup); cpp-httplib (MIT, header-only, v0.53.0) is the best fit if HTTP/SSE is preferred over WebSocket — with the caveat that it uses **blocking** socket I/O and only supports HTTP/1.1.
4. **Threading is the core discipline**: event sinks fire on the main game thread; network I/O must run on its own thread; anything touching game state from the network thread must be bounced back through the SKSE task interface.
5. **`RE::ProcessLists::GetSingleton()->highActorHandles` is still the correct actor enumeration** for 1.6.1170, with a documented, working iteration idiom on the CreationKit wiki.
6. **Licensing is clean** for the recommended stack (IXWebSocket BSD-3, everything else MIT/permissive), but CrashLoggerSSE (GPL-3.0) and some community plugins (GPL-3.0) must NOT be copied from.

## Details

### Q1 — Event sinks for Chronicle's event set

**How sinks are registered.** CommonLibSSE-NG exposes the vanilla `BSTEventSource`/`BSTEventSink<T>` pattern. A sink class inherits `RE::BSTEventSink<EventT>`, implements `RE::BSEventNotifyControl ProcessEvent(const EventT*, RE::BSTEventSource<EventT>*)`, and registers via `RE::ScriptEventSourceHolder::GetSingleton()->AddEventSink<EventT>(sink)` (BSTEvent.h defines `AddEventSink`, `ng.commonlib.dev/_b_s_t_event_8h_source.html` line 59). A few UI-adjacent events (`MenuOpenCloseEvent`, `MenuModeChangeEvent`) are registered via `RE::UI::GetSingleton()->AddEventSink` instead.

Per-event determination for Chronicle's set:

| Chronicle event | Native source in CommonLibSSE-NG? | Mechanism |
|---|---|---|
| **NPC death** | ✅ `RE::TESDeathEvent` (`RE/T/TESDeathEvent.h`) — has `dead` bool (fires twice: pre- and post-death), `actorDying`, `actorKiller` | `ScriptEventSourceHolder::AddEventSink<TESDeathEvent>` |
| **Cell attach/load** | ✅ `RE::TESCellAttachDetachEvent`; also `RE::TESCellFullyLoadedEvent` for full load | `ScriptEventSourceHolder::AddEventSink` |
| **Quest stage change** | ✅ `RE::TESQuestStageEvent` (has `formID`, `stage`) | `ScriptEventSourceHolder::AddEventSink<TESQuestStageEvent>` |
| **Item transfer** | ✅ `RE::TESContainerChangedEvent` (has `oldContainer`, `newContainer`, `baseObj`, `itemCount`, `reference`) | `ScriptEventSourceHolder::AddEventSink<TESContainerChangedEvent>` |
| **Dialogue start/end** | ❌ **No dedicated event source** | Proxy via `MenuOpenCloseEvent` for `"Dialogue Menu"` (open/close ≈ start/end of the *menu*), OR hook the dialogue subsystem. For NPC speech lines, no native event — hook required. |
| **Crime/bounty change** | ❌ **No dedicated event source** | Hook the crime-gold code path, or poll `TESFaction::GetCrimeGold()` per crime faction and diff. |

**Confirmed-absent callouts:**
- **There is no `TESDialogueEvent` / dialogue-start event** in CommonLibSSE-NG. The community solution for "dialogue is happening" is to sink `MenuOpenCloseEvent` and filter for the Dialogue Menu (as done in unpaused-menu plugins like SkyrimSouls, `kassent/SkyrimSouls/Hook_Game.cpp`, which override `ReceiveEvent(MenuOpenCloseEvent*)`). This detects the *player conversation menu* opening/closing, not arbitrary NPC-to-NPC dialogue.
- **There is no crime/bounty-changed event.** Bounty lives as "crime gold" on each hold's crime `TESFaction`; the Papyrus surface is `Faction.GetCrimeGold()` (CreationKit wiki, `GetCrimeGold - Faction`). A native plugin must either trampoline-hook the internal AddCrimeGold path or poll per-faction crime gold and diff against last-known values. The nine crime factions have fixed FormIDs (e.g. Whiterun `000267EA`).

**Real production plugins to pattern from (event sinks):**
- **powerof3 / PapyrusExtenderSSE** (`github.com/powerof3/PapyrusExtenderSSE`) — a large, mature CommonLibSSE plugin ("442 functions, 82 events, 4 script objects") that registers dozens of event sinks and re-dispatches them; canonical reference for multi-event sink management. (License: MIT — verify at repo.)
- **himika / libSKSE `GameTESEvents.cpp`** (`github.com/himika/libSKSE/blob/master/skse/skse/GameTESEvents.cpp`) — although old-SKSE, it enumerates *every* `TESEventSourceHolder::GetEventSource<T>()` including `TESQuestStageEvent`, `TESContainerChangedEvent`, `TESCellAttachDetachEvent`, `TESDeathEvent` — an authoritative map of which events have sources.
- **chesko256 / SimplyKnock `GameEvents.cpp`** — clean single-plugin event-sink example.
- **SkyrimScripting/SKSE_Template_GameEvents** and **skyrim.dev/skse/events** — the minimal reference sink (a single `OurEventSink` multiply-inheriting several `BSTEventSink<T>` and implementing each `ProcessEvent`). Good starting skeleton; not production-grade.

### Q2 — Networking inside the plugin

**Libraries people actually use, and vcpkg status:**

| Library | vcpkg port (current) | License | Static-link into SKSE DLL? | Notes |
|---|---|---|---|---|
| **IXWebSocket** | `ixwebsocket` v12.0.1 (2026-06) | **BSD-3-Clause** | Yes — "minimal dependencies (no boost)" | Client + server; `ix::initNetSystem()` calls `WSAStartup`; server spawns a new OS thread per connection. Author has noted he has little time to maintain it now. |
| **cpp-httplib** | `cpp-httplib` v0.53.0 (2026-08) | MIT (© 2017 yhirose) | Yes — single header | **Blocking** socket I/O + thread pool; **HTTP/1.1 only**; HTTPS via OpenSSL/mbedTLS; WebSocket recently added; "not the one you want" for non-blocking / massive concurrency (fine for one local consumer). |
| **CivetWeb** | `civetweb` | MIT | Yes — C library, embeddable | HTTP/HTTPS + WebSocket; master thread + worker pool; widely used as embedded server, "free from GPL." |
| **Boost.Beast** | `boost-beast` | Boost Software License 1.0 (permissive) | Yes, but heavy | Full Asio-based HTTP/WS; large dependency footprint. |
| **uWebSockets** | `uwebsockets` | Apache-2.0 | Yes | High-performance; more setup. |

**SkyrimWebSocket implementation (the canonical spatial-schema mod).** The mod is distributed as `SkyrimWebSocket.dll` (Nexus "SkyrimWebMonitor", mod 184005, author andreyvelsk). Verbatim from the Nexus page: *"1) Copy SkyrimWebSocket.dll SKSE plugin to Data/SKSE/Plugins/ folder 2) The plugin listens on ws://127.0.0.1:8765 by default. If you want to launch app on remote android device, redefine listen address in SkyrimWebSocket.ini file."* Rebinding to a non-loopback address for LAN/Android then requires opening port 8765 in the firewall. This confirms it runs a real in-process listening TCP socket inside the game. A companion PWA (`andreyvelsk.github.io/SkyrimWebMonitor`) consumes the stream. **The underlying WebSocket library is not stated by the author.** A derivative first-party bridge (DovahLink Bridge, Nexus 188165) states it "adapts implementation techniques from SkyrimWebSocket by andreyvelsk … used under its MIT license" and bundles **Boost, fmt, spdlog, CommonLibSSE-NG** — which points (inference, not confirmation) to **Boost.Beast** as SkyrimWebSocket's underlying WS stack. A GitHub repo `github.com/andreyvelsk/SkyrimWebSocket` is referenced in a YouTube description but its contents could not be independently verified, and no threading-model documentation was found.

**Conclusion on consume-vs-clone.** Because (a) the SkyrimWebSocket source could not be confidently located/verified, (b) its underlying library and threading model are undocumented, and (c) its licence is MIT (so cloning its wire protocol/technique is permitted), the evidence favors **cloning its wire protocol first-party rather than installing it as a hard dependency**. Chronicle already treats its wire protocol as canonical; re-implementing that protocol over IXWebSocket/cpp-httplib gives full control of threading and version-pinning.

**SkyrimNet / Mantella-adjacent networking.** SkyrimNet (`github.com/MinLL/SkyrimNet-GamePlugin`) is the strongest existence proof that a **full HTTP server + web dashboard + MCP server can run entirely inside a single SKSE DLL**, "No WSL. No Python launcher." Its docs confirm the dashboard at `http://127.0.0.1:8080/` (a legacy web UI runs on a secondary port, 8081 by default, now deprecated) and, verbatim from the README: *"SkyrimNet runs a Model Context Protocol server on port 8889 that exposes 44+ tools to external AI assistants."* Its inbound HTTP-server library is **closed-source and undisclosed** (the public repo contains only ESP/Papyrus/prompt/UI assets, not the DLL source); only **libcurl** (outbound API calls) and **Inja** (prompt templating) are confirmed. Mantella, by contrast, runs its server in a **separate `Mantella.exe`** on `localhost:4999` (docs point users to `...\Mantella\SKSE\Plugins\MantellaSoftware\Mantella.exe`) — the opposite architecture, and the one Chronicle should avoid if in-process is the goal.

### Q3 — Threading model

**Where sinks fire.** `BSTEventSink::ProcessEvent` callbacks fire **on the main game (simulation) thread**, synchronously within the engine's event dispatch. This means: reads of game state inside `ProcessEvent` are safe, but any blocking work (network send) inside `ProcessEvent` will stall the game and must be avoided — copy the data you need out of the event and hand it to your own queue/thread.

**What may/may not be touched off-thread.** Game object state (forms, references, actor 3D, inventory, `ProcessLists`) must **not** be read or mutated from a background/network thread — the engine is not thread-safe and pointers can be invalidated (use-after-free) at any time by the sim thread. The correct discipline:
- Network thread receives/needs data → schedule a closure onto the main thread.
- The canonical marshaling idiom is `SKSE::GetTaskInterface()->AddTask([...]{ /* touch game state here on main thread */ });`. The `TaskInterface` explicitly "allows scheduling tasks to be executed on the main game thread, which is essential for thread-safe operations" (SKSE API, CommonLibSSE docs; see Ryan-rsm-McKenzie's TaskInterface implementation gists).
- For reads that feed the outbound spatial stream, snapshot on the main thread (in a task or in the periodic update hook) into a plain POD/JSON struct, then enqueue that snapshot to the network thread for serialization + send.

**Shipped plugin documenting this discipline.** SkyrimNet's README is the best public statement of correct practice: *"all heavy work is isolated onto worker threads, so a stuck network call or a slow LLM can never freeze, stutter, or take down the game process"*; *"The game thread is never blocked on a network request, a database query, or a TTS render — every piece of heavy work runs asynchronously and streams its results back into the game as they become available"*; and game data is *"touched only through guarded patterns — reference-counted entity wrappers, validity checks before every use, strict lock ordering."* This is exactly the model ChronicleBridge should adopt. IXWebSocket's server design ("Run a server and give each connection its own WebSocket object. Each connection is handled in a new OS thread") means the network side is already off the game thread by construction.

### Q4 — Build / deploy topology

**Standard project setup (confirmed).** The standard CommonLibSSE-NG plugin is a Windows build: Visual Studio 2022 + CMake 3.25+ + vcpkg (with `VCPKG_ROOT` env var), pulling CommonLibSSE-NG via vcpkg/CMake. Templates (SkyrimScripting, CharmedBaryon Sample Plugin) auto-download CommonLibSSE-NG through vcpkg; use the `x64-windows-static` triplet so dependencies statically link into one DLL. There is **no supported Linux-native or cross-compilation build of CommonLibSSE-NG plugins** — the established path is **build the DLL on Windows (or Windows CI), then deploy the DLL into the Proton prefix's `Data/SKSE/Plugins`**. SKSE DLL-drop mods are the category that "just works" under Proton.

**Multi-runtime / Address Library (must do from day one).** CommonLibSSE-NG "has support for Skyrim SE, AE, and VR, and is able to create builds for any combination of these runtimes, including all three … a single DLL that works in any Skyrim runtime. For Skyrim AE, both versions before 1.6.629 and those after are supported in a single DLL (both struct layouts are supported)." Building runtime-agnostic + shipping against **Address Library for SKSE Plugins** (Nexus 32444, "load a database that stores offsets so your DLL plugin can be version independent without requiring to be recompiled") means engine offsets are resolved by database lookup, so a future engine update breaks only the address-mapped adapter layer, never the higher-level sim logic — exactly Chronicle's "engine update breaks only the adapter" requirement. Pin behavior to 1.6.1170 but keep the NG multi-runtime abstractions in place. (Note: Bethesda announced an incoming Skyrim update as of 2026-08-14, per silverlock.org — another reason to lean on Address Library from day one.)

**Proton / Wine caveats for an in-process SERVER socket (important, partially unverified).**
- WinSock calls from a Windows DLL are translated by Wine to host Linux sockets; a loopback (`127.0.0.1`) bind inside the game generally works because Wine uses the host network stack with no NAT, so a native Linux consumer on the same machine can usually reach `127.0.0.1:PORT`.
- **There is documented failure precedent for the *consumer/browser-launch* path, not the bind itself:** Mantella's Proton bug (art-from-the-machine/Mantella issue #521, "Browser GUI does not load if running through Proton/Wine") states verbatim: *"If running Skyrim through Steam Proton or Lutris (GOG version), the Mantella UI does not open automatically. If entering the provided localhost url, the browser shows 'Loading' but it is frozen and will not actually load."* Mantella's server is a *separate exe*, so that is a cross-process case, but it is the closest public data point.
- **No confirmed first-hand report of an in-DLL localhost server (SkyrimNet/CHIM) being reached successfully under Proton/Steam Deck was found.** This is a genuine evidence gap and should be de-risked with an early spike: build a trivial IXWebSocket/cpp-httplib server into a test DLL, run under the exact Proton version, and confirm a Linux-side client can connect to the bound port.
- Historic Wine notes warn about localhost UDP quirks and `SO_REUSEADDR`/port-rebind timing (WineHQ forums), and `err:winsock:interface_bind` warnings for broadcast; for a straightforward TCP/WS loopback these are unlikely to bite, but bind to `127.0.0.1` explicitly, run `WSAStartup`/`ix::initNetSystem()` once, and make the port configurable.
- Because the game runs *inside* the Proton prefix, a consumer that runs natively on host Linux is the simplest topology. Chronicle's Python bridge should be able to reach the Wine-hosted loopback port; verify empirically.

### Q5 — Actor enumeration for the spatial stream

**`ProcessLists` hook point is current for 1.6.1170.** `RE::ProcessLists::GetSingleton()->highActorHandles` (a `BSTArray<ActorHandle>`) remains the accurate way to enumerate loaded/high-process actors; the field is present in the current CommonLibSSE-NG headers (`RE/P/ProcessLists.h`, confirmed in the NG class-member index). "High" actors are those being actively processed (in/near loaded cells). `middleHighActorHandles` / `lowActorHandles` exist if a broader set is needed.

**Concrete, working iteration + position-read example** (CreationKit wiki, "SKSE Plugin Development/Iterating all Actors/NPCs", ck.uesp.net):

```cpp
const auto processLists = RE::ProcessLists::GetSingleton();
if (!processLists) { return; }
for (auto& targetHandle : processLists->highActorHandles) {
    const auto actorPtr = targetHandle.get();   // NiPointer<Actor>; refcounts
    if (!actorPtr) { continue; }
    RE::Actor* actor = actorPtr.get();
    // Position / rotation:
    RE::NiPoint3 pos = actor->GetPosition();     // world position
    float angleZ = actor->GetAngleZ();           // heading; GetAngle() for full NiPoint3
    RE::TESObjectCELL* cell = actor->GetParentCell();
    RE::TESWorldSpace* ws = actor->GetWorldspace();
    // ... serialize snapshot ...
}
```

`GetPosition()`, `GetAngle()`/`GetAngleZ()`, `GetParentCell()`, and `GetWorldspace()` are all on `RE::TESObjectREFR`/`RE::Actor` in CommonLibSSE-NG. **Critical safety note (from a real bug fix):** the doodlum/skyrim-community-shaders PR #1765 ("fix(grass collision): catch trashed actor pointers") shows that handle→pointer resolution can yield trashed pointers (they added a `(uintptr_t)actorPtr.get() < 0x00007FFFFFFFFFFF` sanity check); validate the pointer and guard against use-after-free. Do this enumeration **on the main thread** (e.g., inside your periodic task), snapshot to POD, then hand off to the network thread.

### Q6 — License hygiene

| Component | License | Verdict for Chronicle (MIT/BSD only, no GPL/Bethesda) |
|---|---|---|
| CommonLibSSE-NG (CharmedBaryon / alandtse) | MIT | ✅ OK |
| SKSE (silverlock) | Custom permissive ("provided as is", non-infringement) — link-time dependency, not shipped | ✅ OK (standard for all SKSE plugins) |
| Address Library for SKSE Plugins | Free modder's resource (data, not code) | ✅ OK |
| **IXWebSocket** | **BSD-3-Clause** (machinezone/IXWebSocket, v12.0.1) | ✅ OK |
| cpp-httplib | MIT (© 2017 yhirose, v0.53.0) | ✅ OK |
| CivetWeb | MIT | ✅ OK |
| Boost.Beast / Boost | Boost Software License 1.0 (permissive, BSD-like) | ✅ OK |
| uWebSockets | Apache-2.0 | ✅ OK (permissive; note patent clause — acceptable but not MIT/BSD) |
| nlohmann/json | MIT | ✅ OK (for JSON serialization) |
| spdlog / fmt | MIT | ✅ OK (logging) |
| SkyrimWebSocket (andreyvelsk) | MIT (per DovahLink attribution) | ✅ OK to clone technique/protocol; ⚠️ source not verified |
| PapyrusExtenderSSE (powerof3) | MIT | ✅ OK to read as pattern |
| himika/libSKSE, SimplyKnock, SkyrimSouls | Verify individually before copying (SkyrimSouls & several old-SKSE repos are not clearly MIT) | ⚠️ read-only reference; confirm license before lifting code |
| **CrashLoggerSSE (alandtse)** | **GPL-3.0-or-later WITH modding exception** | ❌ **Do NOT copy code** (copyleft) |
| **NPC Pathing NG** and other "gpl-v3"-tagged SKSE repos | GPL-3.0 | ❌ **Do NOT copy code** |
| SkyrimNet plugin binary | Closed-source (public repo is assets only) | ❌ Not a code source; reference README concepts only |

## Recommendations

**Adopt Option C (hybrid), weighted toward first-party**, staged as follows:

1. **Stage 0 — Proton socket spike (do this first, ~1 day).** Build a trivial CommonLibSSE-NG DLL that opens an IXWebSocket (or cpp-httplib) server on `127.0.0.1:<port>` and confirm Chronicle's native-Linux Python bridge can connect through the Proton prefix. **Benchmark that changes the plan:** if loopback bind/connect fails or is flaky under the target Proton build (as Mantella's GUI path failed in issue #521), fall back to binding `0.0.0.0` on a firewalled port, or reconsider a file/named-pipe transport. This gap is currently unproven and is the highest-risk unknown.

2. **Stage 1 — First-party events + spatial plugin.** Implement `ChronicleBridge` as a single CommonLibSSE-NG multi-runtime DLL:
   - Register sinks for `TESDeathEvent`, `TESCellAttachDetachEvent`, `TESQuestStageEvent`, `TESContainerChangedEvent` via `ScriptEventSourceHolder`.
   - Implement the two missing events: dialogue via `MenuOpenCloseEvent` (Dialogue Menu) plus a trampoline hook if line-level fidelity is needed; crime/bounty via a hook on the crime-gold path or a per-faction `GetCrimeGold()` poll in the periodic task (nine fixed crime-faction FormIDs).
   - Spatial stream: enumerate `ProcessLists::highActorHandles` on the main thread on a fixed cadence, snapshot position/angle/cell/worldspace to POD (with the PR-#1765 pointer sanity guard), hand to the network thread.
   - Threading: never block in `ProcessEvent`; all game-state reads on the main thread; use `SKSE::GetTaskInterface()->AddTask` for any main-thread work requested by the network side.

3. **Stage 2 — Networking.** Use **IXWebSocket** if Chronicle's canonical schema is WebSocket-framed (it is, per SkyrimWebSocket) — its per-connection-thread server model keeps I/O off the game thread by construction; add **cpp-httplib** instead/additionally if you also want a plain HTTP/SSE control channel (accepting its blocking-I/O, HTTP/1.1-only constraints, which are fine for one local consumer). Re-implement SkyrimWebSocket's wire protocol first-party (permitted under its MIT license) rather than installing the mod — this keeps threading and version-pinning under Chronicle's control. Pull both via vcpkg manifest, static triplet (`x64-windows-static`).

4. **Stage 3 — Hardening.** Add pointer-validity guards on actor handle resolution (per community-shaders PR #1765), make port/bind configurable via INI (as SkyrimWebSocket does), dedupe `TESDeathEvent` double-fire, filter `TESContainerChangedEvent` noise, and pin to Address Library so an engine update past 1.6.1170 breaks only the offset layer.

**When to switch to Option B (install SkyrimWebSocket as-is):** only if the Stage-0 spike shows SkyrimWebSocket already runs reliably under your Proton target AND its spatial schema is a 100% match AND you can obtain and audit its source for the threading model. Given the source could not be verified, this is unlikely to be the better path — and it covers only the *spatial* half, not Chronicle's event set.

**Reject Option A-pure (fully first-party including a hand-rolled socket stack):** no reason to hand-roll WebSocket framing when IXWebSocket/cpp-httplib are MIT/BSD, on vcpkg, and static-link cleanly. "First-party" should mean *your event/spatial logic and your protocol*, on top of a permissive library.

## Caveats

- **Proton in-process localhost is unverified.** The single most important open question — does an in-DLL listening socket under Proton reliably accept a Linux-side client — has no confirmed public evidence either way; the closest data point (Mantella issue #521) is a *separate-process* failure. Treat Stage 0 as a gate.
- **SkyrimWebSocket internals are inferred, not confirmed.** Its underlying library (likely Boost.Beast, by inference from the DovahLink derivative that bundles Boost) and threading model are not documented in a primary source; its GitHub repo could not be verified. Do not depend on it as a black box.
- **SkyrimNet's inbound server library is undisclosed** (closed-source); it proves the *architecture* is viable but is not a code source. Only its outbound stack (libcurl) and templating (Inja) are confirmed.
- **Dialogue and crime/bounty require hooks**, which are the version-fragile parts of the plugin; isolate them behind the Address-Library adapter so an engine update localizes the breakage.
- **`TESDeathEvent` fires twice** (dead=false then dead=true); dedupe. `TESContainerChangedEvent` fires for every inventory move including internal engine transfers; filter to the transfers Chronicle cares about.
- **Version-era note:** all engine claims here are anchored to the AE/1.6.x CommonLibSSE-NG headers (current as of 2026). `highActorHandles`, the `TES*Event` set, and the multi-runtime DLL capability are all confirmed against the NG headers; offset-level fragility is handled through Address Library, not source-level API. cpp-httplib and IXWebSocket vcpkg versions cited are current as of Aug 2026 and will advance.