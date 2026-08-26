# DevBench (alandtse) — Verification of a Secondhand MCP/REST SKSE-Plugin Claim

**Document File ID:** docs/research/25-devbench-skse-mcp-verification.md
**Date:** 2026-08-26

## TL;DR

The secondhand claim is **mostly real, more capable than described, and wrong on one
specific, load-bearing point: the license.** `alandtse/devbench` exists, is a genuine
CommonLibSSE-NG SKSE plugin, is exceptionally actively maintained (15 tagged releases
in ~3 months, latest 2026-08-24), and really does run both an MCP server and a REST
API on one `127.0.0.1`-only port (`8920` for SE/AE, `8921` for VR) — console-command
execution with captured output, main-thread task marshalling, menu inspection/answer,
save/load + enumeration, and rich game-state inspection (player/actor/quest/inventory/
effects/refs) are all real, verified directly from the README and commit history, not
paraphrased. It also has a documented C-ABI (`RegisterTool`/`RegisterToolExtension`/
`EmitEvent`) for other SKSE plugins — including a hypothetical ChronicleBridge
integration — to add tools, and that specific glue (`DevBenchAPI.h`/`.cpp`) is
separately MIT-licensed and usable from a closed-source or GPL-incompatible plugin
with zero copyleft obligation.

**What the secondhand paraphrase got wrong:** the project as a whole is
**GPL-3.0-or-later** (with a modding + linking exception), **not MIT**. Only the small
cross-plugin API shim is MIT. This is a real, verifiable distinction — the plaintext
GPL-3 license and the MIT-only carve-out are both in the repo — and it matters if
ChronicleBridge ever considered vendoring DevBench's core rather than just linking
against the MIT glue to talk to a separately-installed DevBench instance.

**Bottom line for the verification-runbook question:** DevBench could automate almost
everything in `docs/design/chronicle-bridge-verification-runbook.md` *once a live game
session already exists with both plugins loaded* — including the parts that currently
read as "have a human play the game," via its `console`, `game`, `scenario`, and
`inspect` tools. It does **not** eliminate the need for an actual Skyrim process to be
launched (DevBench is in-process; it doesn't exist until Skyrim does) or the build-step
setup. See §5 for the concrete breakdown.

## 1. [VERIFIED] The repository is real, active, and matches the shape of the claim

- Repo: <https://github.com/alandtse/devbench> — confirmed via `gh api
  repos/alandtse/devbench`. Description: *"MCP + REST test bench for Skyrim SKSE mod
  development: register tools/events into one localhost endpoint (AI agents and plain
  HTTP)."*
- `created_at`: 2026-05-31. `pushed_at`: 2026-08-24. Language: C++. Not a fork.
  10 stargazers, 2 forks, 4 open issues — small but real and live.
- Release cadence (via `gh api repos/alandtse/devbench/tags`): v1.9.1 → v1.15.1 across
  the observation window, latest `v1.15.1` on 2026-08-24 ("bump CommonLib for address
  library v5 flag," #70), preceded the same day by `v1.15.0` on 2026-08-21 ("support
  Skyrim AE 1.7.99," #69). This is automated semantic-release tagging on a project
  under active, ongoing development — the opposite of an abandoned or one-shot repo.
- `alandtse` is confirmed (via `gh api users/alandtse/repos`) to be the real,
  well-known maintainer of numerous shipped SKSE plugins in this exact ecosystem
  (Buffout4, CrashLoggerSSE, Spell-Perk-Item-Distributor, PapyrusExtenderSSE,
  po3-Tweaks, and CommonLibSSE-NG's own VR fork `CommonLibVR`) — this is not a
  same-name confusion or a fabricated identity.

## 2. [PARTIALLY-REFUTED] License: GPL-3.0, not MIT — except the cross-plugin glue

The secondhand claim called the whole project MIT-licensed. The repo's own metadata
(`gh api repos/alandtse/devbench` → `"license":{"key":"gpl-3.0", ...}`) and its README
License section say otherwise:

> `[GPL-3.0-or-later](COPYING) WITH [Modding Exception AND GPL-3.0 Linking Exception
> (with Corresponding Source)](EXCEPTIONS)`. ... The cross-plugin **API glue is
> separately MIT** and **carries no copyleft effect**: `include/DevBenchAPI.h`,
> `DevBenchAPI.cpp`, and `DevBenchAPI.LICENSE.txt`. **Any** SKSE plugin — _including
> closed-source / non-GPL mods_ — may vendor those files ... to talk to devbench with
> **zero GPL obligation**.

`[UNVERIFIED-CLAIM-REFUTED]` — the whole-project-MIT claim is false as stated. The
practically-relevant fact for ChronicleBridge is narrower and better: the *integration
surface* (the only part ChronicleBridge would ever link against) is MIT, so
ChronicleBridge's own license posture is unaffected either way. This is exactly the
kind of "conflated with the interesting part" error a secondhand AI paraphrase would
make — DevBench's own docs go out of their way to draw this distinction, so it wasn't
subtle in the source.

## 3. [VERIFIED] Nexus Mods listing exists at mod id 181326

<https://www.nexusmods.com/skyrimspecialedition/mods/181326> is titled "DevBench" —
confirmed via web search (direct `curl`/`WebFetch` to Nexus both returned Cloudflare
403s, a routine anti-bot block, not evidence against the page's existence; the search
engine's cached title and snippet corroborate the GitHub project 1:1, describing it as
"a dev tool for programmatically interfacing with Skyrim including MCP or http access,"
version 1.12.0 as of 2026-07-31). Several other real, findable Nexus pages by the same
author cross-reference it as a dependency: **Floating Damage NG and Combat Logger**
(mod 184159, "exposes devbench host status ... gates devbench registration behind an
explicit opt-in"), **ImGui VR Helper** (mod 183466, "added a synthetic input/cursor
bridge for devbench"), **Open Shaders** (mod 180419, "exposes weather via devbench"),
and a **"Skyrim-Claude Code Modder's Toolkit"** (mod 176043) that is explicitly
described as using DevBench "to drive the running game directly for testing fixes" —
i.e., someone else in this exact modding community is already using DevBench for the
same class of problem this report is investigating (agent-driven in-game test
automation). No GitHub repo under that toolkit's name exists in `alandtse`'s account,
so it appears to be Nexus-only (a config/profile package, not source) — not
independently verified further, out of scope for this report.

## 4. [VERIFIED] What it actually exposes — read from source, not paraphrase

All of the following is quoted or directly derived from the repo's own `README.md`
(fetched via `gh api repos/alandtse/devbench/readme`), not from any secondhand
description.

- **Both MCP and REST, on one port, same registry.** "an in-process server that
  exposes mod functionality to AI agents (MCP) and to plain HTTP clients (REST)
  through one endpoint." A `ToolRegistry` is registered once; a `McpAdapter` and
  `RestAdapter` both reflect it. MCP is **streamable-HTTP at `POST
  http://127.0.0.1:<port>/mcp`**; REST is `POST /api/tool/<name>` plus `GET
  /api/tools` for the schema listing. This refutes any reading of the secondhand
  claim as "REST that got mislabeled MCP" — it is genuinely both, over the same
  `httplib` server, by explicit design.
- **Bind address: `127.0.0.1` only, not configurable to a wider interface.**
  Verbatim from the README's Safety section: *"Bound to `127.0.0.1` only. The bench
  has no auth and can execute arbitrary commands in the game process — that is
  acceptable for a local dev bench but it must never be bound to a
  network-reachable address."* And again under Configuration: *"Bind address is
  fixed to `127.0.0.1`."* **This is the decisive fact for LAN reachability: DevBench
  is not reachable from another machine's network stack at all** — not
  misconfigured-by-default-but-changeable, but hard-coded loopback-only, on purpose,
  as a stated safety property (unauthenticated arbitrary command execution). The
  only way to reach it from a different machine (e.g., a Linux agent host talking to
  a separate Windows gaming rig over SSH) is a local SSH port-forward
  (`ssh -L 8920:127.0.0.1:8920 <windows-host>`) terminating on the Windows box
  itself — loopback-bound services are the textbook case this actually works for,
  unlike a service that additionally checks `Host`/origin headers or refuses
  non-local `Bind`. This report did not test an actual tunnel end-to-end; the
  reachability claim above is architectural, not empirically confirmed against
  ChronicleBridge's specific machine topology.
- **Port**: deterministic per runtime — **`8920` for SE/AE, `8921` for VR** —
  falling forward to the next free port if taken, with the actually-bound port
  written to `Data/SKSE/Plugins/devbench/runtime.json` for discovery. Matches the
  secondhand claim's `8920` exactly for the SE/AE case ChronicleBridge cares about.
- **Console command execution with captured output: real, not exaggerated.** The
  `console` tool: `action='exec'` queues a command on the main thread;
  `capture=true` "fences it between marker commands"; `action='read'` "slices
  ConsoleLog's buffer between the markers and returns `{ markersFound, lines:[…] }`."
  This is a genuine console-log-scraping capture mechanism, not a guess or a stub —
  described in enough mechanical detail (marker-fencing a ring buffer) that it reads
  as an implemented, tested feature rather than an aspirational one.
- **Main-thread task marshalling: real, and specifically synchronous.** The design
  section states handlers "that touch game/render state marshal to the main thread
  via `MainThread::RunAndWait`, which **returns the value synchronously**" — the
  README explicitly frames this as differentiating DevBench from a fire-and-forget
  task queue: "an agent gets data back, not just an ack." Third-party integrators are
  told to use SKSE's own `TaskInterface` the same way — consistent with, not
  contradicting, the secondhand claim's specific mention of
  `SKSE::GetTaskInterface()->AddTask()`.
- **Menu-open detection and interaction: real, and more capable than "detection."**
  The `menu` tool: `list` (open menus + modal state), `describe` (a
  `MessageBoxMenu`'s body/buttons), `accept` (answer a Yes/No modal by button index,
  running its real callback), `open`/`close` (via the UI queue), and `invoke`
  (dispatch to a consumer-registered handler for a mod's own custom menu). This goes
  beyond "detects when a menu opens" to actually answering modals programmatically —
  directly relevant to any ChronicleBridge test scenario that would otherwise stall
  on a MessageBox.
- **Save/load triggering and enumeration: real.** The `game` tool: `list` (enumerate
  the saves directory), `loadLast`, `load`/`save` by name. Documented as
  fire-and-forget, with completion observable via `lifecycle` events
  (`postLoadGame`, etc.) — exactly the kind of event the runbook's own save/reload
  integrity check needs to key off deterministically instead of a guessed sleep.
- **Game-state inspection: real and broader than the secondhand paraphrase implied.**
  The `inspect` tool alone covers `state`, `health` (off-main-thread liveness),
  `vm` (Papyrus VM health), `scene` (cell/worldspace/position/weather), `mods`
  (load order), `player` (level/race/actor values/equipped), `inventory`,
  `quests` (journal + objectives), `effects` (active magic effects), and `refs`
  (identify a reference by FormID or the console-selected ref). There is also a
  separate `papyrus` tool that can `call` an arbitrary global or member Papyrus
  function and get the **return value** back synchronously (not just fire a
  console `cgf`) — this is a materially more powerful state-inspection primitive
  than "player/actor/quest/inventory data," not a lesser or exaggerated version of
  it.
- **C-ABI for other SKSE plugins to register tools: real, documented, and MIT.**
  `DevBenchAPI::GetDevBenchInterface001()` returns null if DevBench is absent
  (safe to link against unconditionally); `RegisterTool(name, jsonSchema, handler,
  ctx)` and `EmitEvent(topic, payload)` are the two primary entry points, with
  `RegisterToolExtension` (v1.5.0+) for attaching a sub-capability to an existing
  base tool (e.g. a custom `inspect` kind) instead of growing the top-level tool
  list. A real third-party consumer already exists and is cited in the README:
  [Open Shaders](https://github.com/alandtse/open-shaders) (a fork of Community
  Shaders) registers a `feature` tool this way. This is the exact mechanism a
  hypothetical ChronicleBridge integration would use.
- **Target runtime and build system.** `xmake.lua` (fetched via
  `gh api repos/alandtse/devbench/contents/xmake.lua`) shows DevBench builds with
  **xmake**, C++23, against **CommonLibSSE-NG via a git submodule pointed at
  `alandtse/CommonLibVR` (the `ng` branch)** — not vcpkg, and not the same
  `commonlibsse-ng` package/registry ChronicleBridge consumes. ChronicleBridge's own
  `adapters/skyrim/ChronicleBridge/vcpkg.json` depends on plain `commonlibsse-ng` +
  `cpp-httplib`, resolved via `vcpkg-configuration.json`'s `colorglass/vcpkg-colorglass`
  registry overlay (baseline commit `6fb127f7…`) — a *different* build toolchain
  (CMake+vcpkg vs. xmake+submodule) than DevBench's own core, though both ultimately
  track CommonLibSSE-NG mainline. Commit history confirms DevBench added explicit
  **Skyrim AE 1.7.99 support** on 2026-08-21 (release v1.15.0, PR #69) and bumped
  CommonLib again three days later for an "address library v5 flag" (v1.15.1, PR
  #70) — i.e., it is being kept current with exactly the kind of runtime-version
  churn this project's own ADR-0008 (pinning to 1.6.1170) was written to defend
  against. **This is a real compatibility question to resolve, not a blocker**:
  DevBench's *core* build system differs from ChronicleBridge's, but the
  integration path a ChronicleBridge author would actually use — vendoring the MIT
  `DevBenchAPI.h`/`.cpp` pair directly, or pulling the `devbench-api` vcpkg overlay
  port the README documents (`cmake/ports/devbench-api/`) — does not require
  ChronicleBridge to adopt xmake at all. The two plugins only need to agree on a
  compatible CommonLibSSE-NG ABI at the process level (both loaded into the same
  running Skyrim), which is a substantially weaker constraint than sharing a build
  system, but was not empirically tested in this report (no build was attempted).

## 5. Decisive assessment: could this automate the verification runbook?

`docs/design/chronicle-bridge-verification-runbook.md`'s premise is that verifying
ChronicleBridge in-game currently requires a human to build the DLL, launch the game,
watch logs, type console commands, and judge the result by eye. Mapping DevBench's
real, verified tool surface (§4) against that runbook's five sections:

- **§0 one-time setup (build DLL, start listener, launch game via MO2):**
  **not automatable by DevBench.** DevBench is an in-process SKSE plugin — it does
  not exist as a callable endpoint until Skyrim.exe is already running with it
  loaded. Building `ChronicleBridge.dll`, placing both DLLs into the MO2 profile,
  and the very first cold launch of Skyrim through MO2 all have to happen through
  some other mechanism (a human, or separate desktop automation outside DevBench's
  own scope — DevBench's README documents no way to launch Skyrim itself).
- **§1 spatial streamer** ("walk outdoors, check dashboard/log for POST lines"):
  **automatable.** `game action=loadLast` or `load` gets into a scene deterministically;
  `console action=exec command="player.moveto <ref>"` or a recorded `record`/`replay`
  scenario can move the player outdoors without a human; `inspect kind=scene` /
  `kind=refs` gives ground truth to cross-check against what the listener received,
  closing the loop entirely inside one `scenario` call.
- **§2 death extraction** ("kill a named-cast NPC, check log + `events.jsonl`"):
  **automatable, with one caveat.** `console` can `prid <formid>` then `kill` a
  specific named-cast actor without any manual targeting, and `inspect kind=refs`
  can resolve/confirm the FormID first. The caveat: this validates the death *event
  path* end-to-end, but a console-triggered `kill` is not bit-identical to death by
  organic combat — if ChronicleBridge's `TESDeathEvent` sink ever behaved
  differently for scripted vs. gameplay-caused deaths (plausible if it inspects
  `actorKiller` or combat state), a console-only test could pass while a real-combat
  death still fails. Not a hypothetical DevBench can rule out from its own docs
  alone.
- **§3 hydration** ("watch for polls/acks, run `getrelationshiprank`, save/reload,
  check persistence"): **fully automatable, and this is DevBench's strongest fit.**
  The `console` tool's capture mode can run `getrelationshiprank` before and after a
  save/reload cycle and return the exact numeric line ChronicleBridge's own runbook
  currently asks a human to read off-screen. `scenario` can chain the entire
  sequence — trigger the grudge state, wait for the hydration poll/ack via
  `waitFor`/`waitUntil`, run `getrelationshiprank`, `game action=save`, `game
  action=load`, wait for `postLoadGame`, run `getrelationshiprank` again — into one
  API call with a structured per-step transcript, which is exactly the
  save-integrity check the runbook calls "the most important to verify carefully."
- **§4 avoidance:** the runbook itself already says this is Python-only, testable
  with `curl` independent of the game — DevBench is irrelevant here either way.
- **§5 reporting back:** unaffected; still a human/agent editing markdown, not a
  DevBench concern.

**Net assessment:** DevBench could turn the *body* of the runbook (sections 1–3, the
actual command-and-observe loop) into something a future agent session drives
end-to-end via `scenario`/`console`/`game`/`inspect` calls, with structured JSON
results instead of a human reading a log by eye — genuinely closing the "compiled
only, never run against a live game" gap this project has been flagging as an
open risk. What it does **not** eliminate: (1) a live Skyrim process has to be
started and get to a loaded save at least once per session by something other than
DevBench itself; (2) DevBench and ChronicleBridge must be installed together in the
same MO2 profile, which is a one-time manual/scripted setup step, not a DevBench
feature; (3) network reachability from a Linux agent host requires an SSH
port-forward onto the Windows box specifically because DevBench is
loopback-bound-by-design — solvable, but unverified end-to-end in this report; and
(4) console-triggered test actions (a scripted `kill`, a scripted `moveto`) are a
different — probably good-enough, but not proven identical — stimulus than organic
player behavior, so DevBench narrows rather than fully closes the gap between
"agent-verified" and "human-playtested."

## Sources

- <https://github.com/alandtse/devbench> (repo metadata via `gh api repos/alandtse/devbench`)
- <https://github.com/alandtse/devbench/blob/main/README.md> (full text fetched via `gh api repos/alandtse/devbench/readme`; all quotes in §4 and the License text in §2 are verbatim from this file)
- <https://github.com/alandtse/devbench/blob/main/xmake.lua> and `.gitmodules` (via `gh api repos/alandtse/devbench/contents/...`) — build system, CommonLibSSE-NG submodule source (`alandtse/CommonLibVR`, `ng` branch)
- <https://github.com/alandtse/devbench/commits/main> — commit log via `gh api repos/alandtse/devbench/commits`, showing v1.15.0 ("support Skyrim AE 1.7.99," 2026-08-21) and v1.15.1 ("bump CommonLib for address library v5 flag," 2026-08-24)
- <https://github.com/alandtse/devbench/tags> — release history v1.9.1 → v1.15.1
- <https://github.com/alandtse> (via `gh api users/alandtse/repos`) — confirms the maintainer's real, extensive Skyrim-modding history (Buffout4, CrashLoggerSSE, SPID, PapyrusExtenderSSE, po3-Tweaks, CommonLibVR, etc.)
- <https://www.nexusmods.com/skyrimspecialedition/mods/181326> (DevBench) — page existence and title confirmed via web search (direct fetch blocked by Cloudflare 403, a routine bot-block, not evidence against existence)
- <https://www.nexusmods.com/skyrimspecialedition/mods/184159> (Floating Damage NG and Combat Logger), <https://www.nexusmods.com/skyrimspecialedition/mods/183466> (ImGui VR Helper), <https://www.nexusmods.com/skyrimspecialedition/mods/180419> (Open Shaders), <https://www.nexusmods.com/skyrimspecialedition/mods/176043> (Skyrim-Claude Code Modder's Toolkit) — cross-referenced via web search as real DevBench-dependent Nexus listings by the same author
- `/home/geoff/projects/Chronicle/adapters/skyrim/ChronicleBridge/vcpkg.json` and `vcpkg-configuration.json` (this repo) — ChronicleBridge's own CommonLibSSE-NG dependency mechanism, for the build-system comparison in §4
- `/home/geoff/projects/Chronicle/docs/design/chronicle-bridge-verification-runbook.md` (this repo) — the runbook mapped against DevBench's tool surface in §5
