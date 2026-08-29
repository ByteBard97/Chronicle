# SimpleSkyrim: a stable debug modlist, and the first confirmed end-to-end live run

**2026-08-28.** This closes the M3 "does ChronicleBridge actually work in a
live game" question with a real, repeatable positive result, and leaves
behind `~/Games/SimpleSkyrim` as a lightweight, purpose-built debug
instance separate from NGVO (playthrough) and the retired ChronicleDev
mess from earlier the same night.

## What's proven, concretely

A 140-second continuous run in Whiterun, zero crashes, with the full
target stack loaded and active:

- **Base:** SKSE 2.2.6, Address Library, CrashLogger, USSEP (+ its 4
  required Creation Club masters: Fish, AdvDSGS, Curios, SurvivalMode)
- **Debug tooling:** devbench (the MCP/REST test-bench mod)
- **QoL:** SkyUI, PapyrusUtil, powerofthree's Papyrus Extender
- **Ours:** ChronicleBridge.dll + ChroniclePatcher.esp
- **The fix that made it possible:** Face Discoloration Fix
  (`FaceGenFixes.dll`, Exit-9B, v1.0.3) — see "The facegen crash" below.

With the listener running, ChronicleBridge's full HTTP loop was
confirmed live: `POST /whiterun/positions` → `204`, all four poll routes
(`hydration`/`avoidance`/`evidence`/`vendor-markup`) → `200`. The
listener's snapshot file filled with **27 live NPCs**, including
named-cast identity resolution (e.g. `sigurd`). This is the first time
any of this has been observed working end-to-end against a real,
running game.

## The facegen crash (the real blocker this session, not ChronicleBridge)

Every crash tonight after the initial USSEP/missing-master issue was
**`EXCEPTION_ACCESS_VIOLATION` in `BSFaceGenModel`/`BSFaceGenNiNodeSkinned`**,
~85 seconds into Whiterun — long enough for NPC heads to stream in.
Root cause (confirmed by isolation: pure vanilla held stable 110s;
USSEP+CC together crashed at 85s): **USSEP and the Creation Club NPCs
ship regenerated FaceGen data that can mismatch at runtime**, a
well-documented SSE modding issue, unrelated to Proton/Wine and
unrelated to ChronicleBridge. The community-standard fix is
**Face Discoloration Fix** (Exit-9B, github.com/Exit-9B/Face-Discoloration-Fix,
Nexus 42441) — a small SKSE-only plugin (no ESP, Address-Library-based,
works on 1.6.1170) that turns the mismatch into a logged warning +
regenerated face instead of a crash. Installed as a loose
`SKSE/Plugins/FaceGenFixes.dll`; confirmed loaded and its hooks
installed via its own log (`FaceGenManager.cpp: Installed hooks for
face discoloration fix`).

**If any future modlist on this project reintroduces USSEP or
Creation-Club NPCs and starts seeing a `BSFaceGen*` CTD ~60-90s into
a populated cell, this is almost certainly the same issue — install
Face Discoloration Fix before spending time on anything else.**

## Instance layout

`~/Games/SimpleSkyrim` — a portable MO2 instance, **hardlink-cloned**
from ChronicleDev (`cp -al`, near-zero extra disk: apparent size 26G,
real extra usage ~0), then stripped and repointed. Own Proton prefix:
`compatdata/4190904831` (`~/Games/launch-simpleskyrim-skse.sh`, same
`moshortcut://SKSE` pattern as the other instances).

**Resolved (2026-08-29):** launching through MO2's `moshortcut://SKSE`
was unreliable during initial bring-up — sometimes the whole MO2
process silently died before spawning anything, for reasons never
diagnosed. Rather than fight MO2 for a debug-only instance, the
direct-loader + loose-deploy pattern was promoted into the repo as
this instance's real management method:

- **`tools/launch-simpleskyrim-direct.sh`** — invokes
  `skse64_loader.exe` directly through Proton, bypassing MO2/usvfs
  entirely. Promoted from the session's throwaway
  `/tmp/direct-launch-simple.sh`.
- **`tools/deploy-simpleskyrim-loose.sh`** — reads
  `profiles/Default/modlist.txt`'s `+`/`-` lines (MO2's own enabled-mod
  bookkeeping) and rsyncs each enabled mod folder's content into
  `Stock Game/Data`, honoring MO2 priority order (top wins) and its
  `Root/` convention (deploys to the game root, not `Data/`, for SKSE's
  loader/DLL). Idempotent and re-runnable.

Running the deploy script for the first time caught real drift:
`modlist.txt` still marked ChronicleBridge, ChroniclePatcherOutput,
SkyUI, PapyrusUtil, po3, and USSEP as **disabled**, even though all six
were part of the proven 140s stable run. `modlist.txt` has been
corrected to `+` all six (EngineFixes and the CC-AE-Content quarantine
folder stay `-`), so it is now the **single source of truth** for what
this instance runs — the "loose Data files vs MO2 bookkeeping" split
described below is resolved.

## Mod state: reconciled

`profiles/Default/modlist.txt` is authoritative. `Stock Game/Data` is
a *build artifact* of `tools/deploy-simpleskyrim-loose.sh`, not
hand-maintained state — re-run the script after enabling/disabling a
mod there (it does not remove files for mods you disable; clear
`Data/` or re-clone `Stock Game` from a clean baseline first if you
need a disabled mod's files gone, not just inactive).

## Live-test harness, pointed at this instance

`adapters/skyrim/livetest/targets.py` now has a `SimpleLocalTarget`
(`CHRONICLE_LIVE_TARGET=simple`), alongside the existing `local`
(ChronicleDev/MO2) and `windows` targets. It targets the loose
`Stock Game/Data` layout directly and asserts the unattended-launch
ini keys into the Proton prefix's real `Skyrim.INI` (under
`Documents/My Games/Skyrim Special Edition/`, not MO2's
`profiles/Default/skyrim.ini` — that file is irrelevant to a
direct-loader launch) — confirmed by diff to differ from the MO2
profile copy and to be missing the unattended keys before the harness
asserts them:

```
CHRONICLE_LIVE=1 CHRONICLE_LIVE_TARGET=simple CHRONICLE_LIVE_LOCAL_OK=1 \
  uv run --with pydantic --with pytest pytest adapters/skyrim/livetest -rA -x
```

Run against a real launch on 2026-08-29 — the harness's 16 tests had
never once executed against a live game before this. Result: **7/16
passed** before stopping on the first failure (`-x`):

- Slice 00 (load/startup, 4 tests) and slice 10 (spatial streamer
  positions, 3 tests, including named-cast identity + engine-position
  match for `nazeem`) all passed clean.
- Slice 20 (`test_console_kill_produces_npc_died`) **failed**: killing
  `brenuin` (`prid 0002C90F` + `kill`) via DevBench's fire-and-forget
  console never produced a matching `npc_died` event within 20s.
  Notably, an *unrelated* actor (`Skyrim.esm:0c97d2` — not in the named
  cast, likely wildlife/an ambient NPC near the Whiterun exterior spawn)
  **did** die and post correctly at tick 8, right after `coc whiterun`
  — twice, back-to-back at the same tick (`seq=0` and `seq=1`, ~45ms
  apart, same `npc_id`), suggesting `DeathEventSink` may double-fire
  for a single death. So `DeathEventSink`/the HTTP path clearly work;
  the console-driven `kill` on `brenuin` specifically didn't land.
  Leading hypothesis, not yet confirmed: `console()` is "fire-and-forget"
  (`devbench.py`'s own docstring warns the console hasn't necessarily
  drained when `exec` returns) and the test's `prid` → `sleep(0.5)` →
  `kill` sequence may be racing DevBench's internal command queue even
  outside the documented capture-marker race. Next step: rerun slice 20
  alone with `console_capture()` on both commands to see the game's own
  console echo and confirm whether `prid` actually selected brenuin
  before `kill` fired, rather than guessing further.

**Rerun attempt (2026-08-29, same session):** rewrote the test to use
`console_capture()` (echoes the game's own console output) instead of
fire-and-forget `console()`, to confirm or rule out the queue-race
hypothesis above. The rerun never reached that code: the game crashed
during the bootstrap `coc WhiterunOrigin` load itself, ~2 minutes in,
before the test's own console commands ran at all --
`EXCEPTION_ACCESS_VIOLATION` writing to `0xF4` (null-pointer field
clear) with `RSI` a `TESObjectLAND*` and a `Character* "Whiterun Guard"`
on the stack, no ChronicleBridge/DevBench frames anywhere in the call
stack -- a vanilla-engine crash, not related to the death slice or to
ChronicleBridge. **This did not happen on the first full-suite run**
(bootstrap + slices 00/10 completed clean, twice, including a 140s
stable Whiterun session earlier this session) -- so this looks
intermittent, not deterministic, and is a different failure mode from
the original `npc_died` timeout. The `console_capture()` diagnostic
change in `test_20_death.py` is a real improvement (better failure
signal) and was kept; the original queue-race hypothesis for the
`npc_died` timeout is still unconfirmed.

Research pass (web search + EngineFixesSkyrim64 GitHub issues, r/skyrimmods,
STEP/Wabbajack wikis) found **no matching documented issue** for the
bootstrap crash's exact offset/instruction/stack shape -- genuinely
unconfirmed, not a known community bug with a standard fix. The closest
adjacent thing is SSE Engine Fixes (`aers/EngineFixesSkyrim64`), which
patches a broad class of similar vanilla null-pointer crashes in
general, but nothing there names this specific case. (Note: `EngineFixes`
is already in this instance's `mods/` folder but deliberately disabled
in `modlist.txt` -- an earlier preflight check
(`adapters/skyrim/livetest/targets.py`) flags it as hanging SKSE plugin
load without its own preloader, so enabling it isn't a free trial.)

Separately: `test_20_death.py` was rewritten to target the victim with
Skyrim's console dot-syntax (`0002C90F.kill` / `0002C90F.resurrect`)
instead of the two-step `prid <ref>` + `kill` pair the original design
doc specified -- the two-step form is exactly what DevBench's own
`console()` docstring warns is fire-and-forget and may not have drained
before the next command fires, and is the only place in this harness
using that pattern (every other slice's console command takes its
target as an argument directly). This is a real fix, not just a
diagnostic, and is the more likely explanation for the original
`npc_died` timeout than the bootstrap crash below (which happened on a
separate rerun, before either version of the death test's own commands
ran).

**Immediate rerun to confirm the dot-syntax fix hit a third, different
failure**: the game process never came up within DevBench's 30s health
check at all -- no crash log, no error in the launch log, nothing left
running once it timed out. This attempt launched immediately after the
bootstrap-crash rerun above. `CrashLoggerSSE`'s own log shows it
"auto-opened" the prior crash log with the OS's default handler right
at the moment of that crash -- plausibly spawning a Wine `notepad.exe`
(matching a stuck-notepad/MO2-"Unlock" issue seen earlier this session
with a different launch path) that could have held a lock or delayed
the very next launch past the 30s window. Unconfirmed -- no stuck
process was still present by the time this was investigated, since the
harness's own teardown had already run.

**Stopped live-game cycling for this session at this point.** Three
consecutive rapid relaunches went clean -> crash -> total launch
failure -- a degrading pattern consistent with insufficient cooldown
between back-to-back Proton/Wine launches (prefix locks, GPU driver
state, a lingering crash-log viewer) rather than a regression in the
mod set itself, which was proven stable for 140s+ and passed 7/16 live
tests clean earlier in this same session. Hammering more launches
back-to-back risks corrupting the diagnosis further, not clarifying it.

Three open threads for whoever continues live-suite work, in priority
order: (1) relaunch once, cold (after a real gap, not immediately after
a prior attempt), to get a clean read on whether the dot-syntax fix
resolves the original `npc_died` timeout -- this is still the most
likely real fix and wasn't actually exercised yet; (2) if the
"Whiterun Guard" bootstrap crash recurs on a *cold* launch, treat it as
its own bug, unconfirmed by research; (3) if a launch fails to come up
within 30s again, check for a stuck Wine `notepad.exe` or similar
crash-log-viewer process before assuming it's the same root cause as
either of the above.

**Update (2026-08-29, later same session):** thread (1) resolved on a
cold relaunch, but the console `<ref>.kill` dot-syntax still didn't
produce `npc_died`. Diagnosed further with Papyrus (`Actor.Kill()`/
`IsDead()`/`GetActorValue`) instead of console commands entirely --
confirmed `IsDead()` never even went true after 3 console-based
attempts, ruling out ChronicleBridge-side identity resolution as the
cause. Switching the test to call `Actor.Kill()` via Papyrus directly
(the harness's own documented "reliable assertion primitive," no
marker/queue race) fixed it: **confirmed passing on two separate live
runs**, `npc_died` landing with the correct `npc_id`, `gamets`, and
listener POST every time. `test_20_death.py` now uses this approach
permanently. Root cause of the original console-only failures was never
fully pinned down (essential-flag research was inconclusive; DevBench's
console exec is confirmed to route through the real engine
`ExecuteCommand`) -- worth another look if console-driven test actions
are needed elsewhere, but not blocking any further work now.

**New finding, same session:** with the death slice fixed, a full
live-suite run got to **9/16 passing** (slices 00, 10, 20, and 30's
first test) before hitting a new, distinct bug:
`test_30_hydration.py::test_rank_survives_save_and_load` -- DevBench's
`game action=save` logs that it received the command
(`devbench: game save 'chronicle-live-hydration'` in its own log) but
**no `.ess` file is ever written anywhere** (checked the real
Documents/My Games Saves folder, the MO2-remnant `__MO_Saves` folder,
and a broad disk search), and the harness's `waitFor: saveGame` scenario
step times out at 60s. Leading hypothesis: this instance launches by
invoking `skse64_loader.exe` directly, bypassing MO2 and its virtual
filesystem entirely (see "Resolved" section above) -- MO2 may normally
provide some save-path plumbing (a registry override, a redirected
Documents folder) that a direct launch lacks, silently breaking the
native save call. A research agent was dispatched to check DevBench's
actual save-action source for confirmation; result pending as of this
write-up. See `GOALS.md`'s "Current state" section for the live status
of this thread.

## Next mods to add (per the original ask: "quality of life... anything
that could help us debug it")

Not yet added, candidates for the next pass: a save-cleaning/testing
QoL mod and a console command enhancer (if any beyond vanilla).
