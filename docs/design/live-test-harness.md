# Live-game test harness — design (2026-08-28)

**Status:** accepted design, being implemented. Supersedes the manual
parts of `chronicle-bridge-verification-runbook.md`; that doc stays as
the reference for *what* each slice should do in-game, this one is
*how it gets verified without a human at the keyboard*.

## Goal

One command verifies every ChronicleBridge slice against a real, running
Skyrim on this Linux box, with nobody watching. The owner reads a pytest
report afterwards, not a game screen during. Failures are real
assertions with captured evidence (log lines, console output, listener
state), not "it looked wrong".

## What the first-boot spike established (2026-08-28, this machine)

Everything below was observed, not inferred:

- `tools/launch-chronicledev-skse.sh` (MO2 → `moshortcut://SKSE` under
  GE-Proton10-14, `DISPLAY=:1`) brings `SkyrimSE.exe` up and DevBench
  (`devbench.dll` 1.15.1, already installed in the instance) answers
  `GET http://127.0.0.1:8920/api/health` **~10s after launch, from the
  Linux host directly** — Wine loopback is host loopback, exactly as the
  bridge's own POSTs to `:8765` already proved. No SSH tunnel, no
  Windows box involved for running tests.
- ChronicleBridge loads (`skse64.log`: `loaded correctly (handle 1)`),
  reads `ChronicleBridge.ini` (absent → defaults), and starts polling all
  four routes every 8s **at the main menu**, before any save exists.
- `POST /api/tool/console {"command":"coc WhiterunOrigin"}` **from the
  main menu** starts a new game directly in Whiterun: `playerLoaded:true`
  in ~40s, `inspect scene` = cell `WhiterunOrigin`, worldspace
  `WhiterunWorld`, and `inspect refs formType=Actor` lists 68 loaded
  actors including all 19 named-cast NPCs. No save file is needed to
  bootstrap.
- Blockers found: (1) EngineFixes without its preloader hangs SKSE
  plugin loading (`plugin did not preload`) — disabled in the dev
  instance's `modlist.txt`, it's irrelevant to testing our plugin.
  (2) The Anniversary Edition upsell `MessageBoxMenu` ("Thanks for
  buying…", one `DOWNLOAD` button, no cancel) opens at the main menu,
  survives `coc`, and pauses the simulation while open; accepting it
  downloads 2.5 GB of Creation Club content into MO2's `overwrite/` and
  triggers a data reload that crashed the process (CrashLogger
  2026-08-28 14:20:04). That content is quarantined in
  `mods/CC-AE-Content (quarantined)/` (disabled). Suppression is a
  config-level fix, see §2.5. (3) `xdotool` keystrokes never reach the
  game (DirectInput under Wine ignores XTest) — DevBench is the only
  input channel, which is fine.
- A game-side `MessageBoxMenu` or `Console` menu being open, or the
  window losing focus during a load, stops the frame counter; DevBench
  main-thread tools then 504. The harness must never leave a modal open
  and must not touch X11 at all (screenshots via DevBench `capture`).

## 1. Shape

A pytest suite, **`adapters/skyrim/livetest/`**, opt-in:

```
CHRONICLE_LIVE=1 uv run --with pydantic --with pytest pytest adapters/skyrim/livetest -rA
make live-check     # the same
```

Without `CHRONICLE_LIVE=1` every test skips (first `skipif` in the repo;
the marker is registered in `pyproject.toml`). `adapters/` stays out of
`testpaths`, so `make test` never launches a game.

Why pytest and not a bespoke script: assertions, per-test isolation,
`-rA` reporting, junit XML for free, and it's the idiom every other
test in the repo already uses. Why not "an agent drives MCP each time":
that's babysitting an agent instead of a game — non-reproducible and
token-expensive. The `devbench` MCP entry in `.mcp.json` stays for
ad-hoc digging when a test fails.

## 2. Components

```
adapters/skyrim/livetest/
  conftest.py        session fixtures: listener, game, bootstrap; report hook
  devbench.py        thin DevBench REST client (health/tool/console-capture/scenario)
  harness.py         launch, wait-for-health, bootstrap, dismiss-modals, teardown
  bridge_log.py      ChronicleBridge.log reader (grep anchors, wait-for-line)
  seeding.py         wraps tools/chronicle-devbench-runbook.py's verified seed recipe
  test_00_load.py    plugin banner + registrations + listener reachable
  test_10_positions.py
  test_20_death.py
  test_30_hydration.py
  test_40_avoidance.py
  test_50_vendor_markup.py
  test_60_evidence.py
```

Each unit has one job and is importable/testable without a game:
`devbench.py` and `bridge_log.py` get ordinary unit tests with canned
JSON / log text under `chronicle/tests/` (auto-collected).

### 2.1 Session fixture: `live_session`

Order, with hard timeouts on every wait:

1. **Preflight** (fail fast, no game yet): `CHRONICLE_LIVE=1`; nothing
   listening on `:8765` or `:8920` (a stale listener from another
   session is an error, not something to reuse); `SkyrimSE.exe` not
   running; launch script, dev instance, DLL, ESP, devbench all present;
   `EngineFixes` disabled in `modlist.txt`.
2. **Scratch run dir**: `runs_dir = <scratchpad or tmp>/live/<ts>/runs`;
   create an empty run `live-<ts>` via `Driver(...).close()` (the
   only empty-run recipe that exists — `chronicle/tests/
   test_devbench_runbook_seeding.py:46-50`).
3. **Listener**: subprocess `listener.py --live-run live-<ts>
   --shared-secret <random> --port 8765 --snapshot-path <scratch>/
   positions.json`, env `CHRONICLE_RUNS_DIR=<runs_dir>` (the listener
   has no `--runs-dir` flag; the same path is passed to every seeding
   call — a mismatch makes every GET return `[]`). Stderr captured to
   `<scratch>/listener.log`. Wait for `GET /whiterun/hydration` → 200.
4. **Bridge ini**: write `mods/ChronicleBridge/SKSE/Plugins/
   ChronicleBridge.ini` with `Host/Port/SharedSecret/LogLevel=debug`
   (backed up and restored on teardown).
5. **Launch**: `tools/launch-chronicledev-skse.sh` as a subprocess,
   stdout to `<scratch>/launch.log`. Wait ≤120s for
   `GET /api/health` `ok:true`; then for `lastLifecycle == "dataLoaded"`.
6. **Bootstrap**: dismiss any modal (§2.5), `console exec coc
   WhiterunOrigin`, poll `inspect state` every 3s ≤180s for
   `playerLoaded:true`, clearing safe modals each poll and re-issuing
   the `coc` once at the halfway point (DevBench's own suite does this:
   a main-menu `coc` sometimes doesn't take on the first try); then
   `menu list` must contain `HUD Menu`; dismiss any modal again;
   assert frame counter advances ≥30 frames over 2s (the "game is
   actually simulating" check — catches the paused-by-modal and
   paused-by-focus states before any slice test runs).
7. **Baseline save**: `game save chronicle-live-baseline`, wait for
   `saveGame` lifecycle. Slices that need a persistence check reload it.
8. **Yield** a `LiveSession` object: devbench client, listener handle,
   run id/dir, bridge-log reader, secret, scratch dir.
9. **Teardown** (always, also on failure): `console exec qqq`, wait
   ≤20s for the process to exit, else `pkill SkyrimSE.exe`; terminate
   the listener; restore the ini; copy `ChronicleBridge.log`,
   `skse64.log`, `devbench.log`, any `crash-*.log`, listener log and
   the run dir into `<scratch>/artifacts/`; print the artifact path in
   the terminal summary.

### 2.2 DevBench client (`devbench.py`)

Stdlib `urllib`, same error taxonomy as `tools/chronicle-devbench-
runbook.py`'s client (unreachable / HTTP error / timeout, each its own
message), plus what the tool script lacks:

- `papyrus_call(script, function, self=None, args=()) -> value`: **the
  assertion primitive.** Typed, synchronous, no marker race. Used for
  `Actor.GetRelationshipRank(self=A, args=[{"form": B}])`,
  `ObjectReference.GetDistance`, `GlobalVariable.GetValue`,
  `ObjectReference.IsDisabled`. Unknown functions 404 cleanly.
- `console(cmd)`: fire-and-forget `exec` for commands with no Papyrus
  equivalent (`coc`, `kill`, `resurrect`, `player.moveto`, `prid`).
  Capture (`capture=true` + `read`) is used only for diagnostics, never
  for assertions: `read` slices the *last* fence in the scrollback and
  can return the previous window with `markersFound:true` (DevBench
  `ConsoleLogCapture.cpp:19`). When used, wait ≥300ms and include a
  nonce in the command.
- `scenario(steps) -> transcript`: `waitFor` lifecycle events
  (`postLoadGame`, `saveGame`) placed *after* their trigger in the same
  call (only events after the step begins count), `waitUntil:
  playerLoaded/noModal`. **HTTP 200 is not success** — check `body.ok`
  and each `results[].ok`.
- `wait_frames(n, within_s)`: `GET /api/health` frame-counter liveness;
  `lastLifecycle` from the same route.
- `refs(formType, radius)` / `ref(formId | editorId)` / `scene()` /
  `player()` / `mods()`. Plugin-local FormIDs are composed by the
  harness: `(index << 24) | local` from `inspect mods` (light:
  `0xFE000000 | (index << 12) | local`), self-checked once per session
  against an EditorID lookup.
- `save(name)` / `load(name)`: via the `game` tool, never raw console
  (`save`/`load` as console commands deadlock the engine per DevBench's
  own tool description). Completion = `lastLifecycle`/`waitFor`.
- 504 from any main-thread tool is retryable (loading screen, modal,
  pause), not fatal; the client retries with backoff up to a deadline.

### 2.3 Modal policy (`harness.dismiss_modals`)

`menu list` → if `messageBoxOpen`, `menu describe`. Then:

- Body matches a known-safe prompt (content-mismatch on load, "Ok"-only
  informational boxes) → `menu accept` the safe button.
- The AE upsell ("Thanks for buying Skyrim Anniversary Edition") →
  **never accept**; it must not appear at all (§2.5). If it does, the
  session fails preflight with the fix spelled out.
- Anything else → fail with the body text in the assertion message.

### 2.6 Targets — where the game runs (`targets.py`)

**Owner ruling 2026-08-28, after the spike: Skyrim must not run on the
Linux box; live runs go to the Windows machine.** The harness therefore
abstracts the machine as a `Target` with a handful of operations
(preflight, write/restore the bridge ini, launch, running?, kill, sync
logs). `CHRONICLE_LIVE_TARGET=windows` is the default;
`local` (the Proton instance the spike used) additionally requires
`CHRONICLE_LIVE_LOCAL_OK=1` so it can't be picked by accident.

`RemoteWindowsTarget`: game launched over SSH (`.claude/
windows-build-machine.md` host). An SSH-spawned process lands in session
0 with no desktop, so the launch command must hand off to the
interactive session — the mechanism (scheduled task via `schtasks /run`,
or equivalent) is settled by the machine inventory and configured via
`CHRONICLE_WIN_LAUNCH`. DevBench is loopback-only by design, reached via
`ssh -L 8920:127.0.0.1:8920` (transport already proven 2026-08-26). The
listener stays on this box; the bridge ini's `Host` is this box's LAN IP
(`CHRONICLE_LINUX_LAN_IP`) and the listener binds `0.0.0.0` already.
`ChronicleBridge.log` is `scp`'d to the scratch dir before every read
(`BridgeLog(refresh=...)`).

### 2.5 AE upsell popup suppression

Research (2026-08-28, four agents + source inspection) found **no mod
that suppresses it** — the "No AE popup" mods people cite don't exist,
the three that do are `StartMenu.swf` banner edits built against
≤1.6.629, and every major modlist just tells users to click DOWNLOAD
once because they *want* the CC files. `MessageBoxData` has no
cancel-index field, which is why Escape does nothing on a one-button
box and DevBench reports `cancelIndex:-1`. Pressing DOWNLOAD requires
`bEnablePlatform=1` + a Steam login and drops the files into MO2's
`overwrite/` (Nexus article 6749) — exactly what the spike saw.

The fix is ini-level, and it is what the working NGVO instance already
has and ChronicleDev was missing:

```
[Bethesda.net] bEnablePlatform=0
[General]      bModManagerMenuEnabled=0  bFreebiesSeen=1
               bAutoSkipMainMenuLogin=1  sIntroSequence=  bAlwaysActive=1
```

`bFreebiesSeen` is contested (BethINI deletes it as "unrecognised"; the
STEP wiki says it works), so the keys are **re-asserted before every
launch** by `ini.assert_keys_in_file` (order-preserving, CRLF-safe,
unit-tested) rather than trusted to persist. Applied to the local
profile on 2026-08-28; the Windows profile gets it via
`CHRONICLE_WIN_SKYRIM_INI`. If the popup still appears, the harness
refuses to continue (never accepts it) and names this section.

### 2.4 Seeding (`seeding.py`)

Imports `tools/chronicle-devbench-runbook.py` via
`importlib.util.spec_from_file_location` (the repo's established trick)
and calls `seed_crime_witnessed_grudge(run_id, runs_dir, witness_id,
perpetrator_id, crime_type, self_victim, location_id, gamets)`. It does
not reimplement the recipe. Three shapes: NPC↔NPC self-victim grudge
(hydration + avoidance from one seed), NPC→`the_player` self-victim
grudge (vendor markup), bystander belief (evidence).

## 3. Slices and their assertions

Every slice test follows: precondition → stimulus → wait for the
*bridge's own* evidence (log line via `bridge_log.wait_for`, listener
ack state, or `events.jsonl`) → verify **game state** via DevBench →
where the runbook demands it, save/load and verify again.

| # | Test | Stimulus | Asserted |
|---|---|---|---|
| 00 | load | (session) | `ChronicleBridge.log` has banner, `ini loaded … sharedSecret=set`, `TESDeathEvent sink registered`, `MenuOpenCloseEvent (BarterMenu) sink registered`, `BarterMenu PostCreate vtable-slot swap installed`; no `ERROR` lines; no `returned status` warnings after the listener came up. |
| 10 | positions | player standing in Whiterun | `positions.json` mtime advances ≥3 times in 5s; contains ≥10 named-cast ids; for `nazeem`, x/y within 50 units of `inspect refs formId=0x0001A6A4`. |
| 20 | death | `prid 0002C90F` (Brenuin, expendable) + `kill`; afterwards `resurrect` | `events.jsonl` gains `npc_died` with `npc_id=brenuin`, `gamets>0` within 15s; listener log shows the POST. |
| 30 | hydration | seed `fralia_gray_mane`→`olfina_gray_mane` self-victim grudge (rank −2 expected) | Poll/ack: listener records `applied` **or** `no_relationship`. If `no_relationship`, sweep the other candidate pairs (`idolaf/lars`, `carlotta/lucia`, `amren/saffir`, `sigurd/adrianne`) until one applies; if none has an authored `BGSRelationship`, the test **fails with that finding** (it is the answer the runbook asks for). On `applied`: Papyrus `Actor.GetRelationshipRank(self=A, B)` reads −2 (Foe); `game save`+`load`, `waitFor postLoadGame`, rank still −2. |
| 40 | avoidance | same seed as 30 (one grudge serves both) | Within 20s: log `avoidance: set ChronicleAvoidingPair_fralia_gray_mane_olfina_gray_mane = 1`; Papyrus `GlobalVariable.GetValue(self=<composed ChroniclePatcher.esp FormID from AvoidanceGlobals' table, or EditorID>)` → 1.0; listener ack `applied`. Behaviour (distance growing) is **recorded, not asserted** — package evaluation is engine-timed and quest packages can mask it. |
| 50 | vendor markup | seed `adrianne_avenicci`→`the_player` grudge | Listener serves the pair (`GET /whiterun/vendor-markup` contains it — depends on the listener fix, see §5); within 20s log `vendor-markup: cached 1.50x for vendor 'adrianne_avenicci'`. **The barter-price assertion is not automatable**: `BarterMenu` only opens from dialogue and DevBench's `menu open` explicitly can't open target-ref menus. The test ends with a printed manual step (talk to Adrianne, compare displayed vs charged) and is marked `xfail(strict=False, reason=…)` for that final check only. |
| 60 | evidence | seed bystander belief for `nazeem` | Within 20s log `evidence: spawned evidence object at 'nazeem''s position`; `inspect refs formType=MiscObject radius=…` after `player.moveto 0001A6A4` finds editorId `ChronicleEvidenceObject`; listener ack `applied`. Persistence: `coc` to `RiverwoodSleepingGiantInn` then `coc WhiterunOrigin` (forces a cell detach/attach), refresh → still present; then `game save`/`load` → still present. |

Seeds use distinct `gamets` (10, 20, 30…) — `chronicle inject` refuses
a tick below the run's max tick.

## 4. Non-goals

- Organic-behaviour realism: scripted `kill`/`coc`/`moveto` are the
  stimuli. Good enough to prove the plumbing; not a substitute for a
  playthrough, and the report says so.
- Parallel runs, multiple instances, VR, the Windows machine.
- Replacing the runbook's prose or the tool script's CLI.

## 5. Prerequisite fixes (dispatched alongside this design)

1. **Listener vendor-markup filter** (`listener.py:694`): `the_player`
   is not in `NAMED_CAST_NPC_IDS`, so a player-directed grudge is never
   served, while `VendorMarkupCache.cpp` accepts *only* player-directed
   pairs. Dead end-to-end until fixed. Python + tests.
2. **Bridge logging** (`plugin.cpp:54`): spdlog pinned to `info`, all
   poller diagnostics at `trace`, non-2xx GET statuses at trace. Add
   `LogLevel` ini key, promote non-2xx to warn, add an info line when
   the vendor-markup cache changes. Rebuilt on the Windows box, DLL
   redeployed.
3. **Dev instance**: EngineFixes disabled; CC content quarantined; AE
   popup suppressed (§3.2 mechanism per research); `bAlwaysActive=1`
   added to `skyrim.ini [General]` (its effect under Wine is verified by
   the fixture's frame-advance check rather than assumed).

## 6. Testing the harness itself

- `devbench.py`, `bridge_log.py`, modal policy: unit tests with canned
  responses under `chronicle/tests/test_livetest_*.py`.
- The live suite is its own integration test; first full run's output
  (pass/fail per slice, artifacts) gets recorded in
  `chronicle-bridge-verification-runbook.md` §8 "Reporting back".
