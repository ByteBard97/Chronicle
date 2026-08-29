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

Not chased further this session to avoid burning additional live-game
launch cycles chasing an intermittent crash blind. Two open threads
for whoever continues live-suite work: (1) confirm/refute the
console-queue-race hypothesis for the `npc_died` timeout with a clean
`console_capture()` run, and (2) if the "Whiterun Guard" bootstrap
crash recurs, treat it as its own bug (possibly a guard AI/pathing
crash near the `WhiterunOrigin` coc point, unrelated to facegen) rather
than assuming it's the same root cause as slice 20's failure.

## Next mods to add (per the original ask: "quality of life... anything
that could help us debug it")

Not yet added, candidates for the next pass: a save-cleaning/testing
QoL mod and a console command enhancer (if any beyond vanilla).
