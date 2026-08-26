# ChronicleBridge in-game verification runbook

**Purpose:** every ChronicleBridge slice built so far (spatial streamer,
death extraction, hydration, avoidance's Python half) has only ever been
verified by compiling cleanly against real CommonLibSSE-NG headers —
none has ever run against a live game. This doc is the concrete
checklist for closing that gap, so "verify it works" isn't a vague
ask. Written so a session with in-game access (or the owner, playing
directly) can follow it step by step.

**Safety first — read before doing anything else:** slices 3 and 4
write persistent state into the save (`RE::BGSRelationship::level`).
**Back up the save file before testing any hydration/avoidance
behavior** (`Documents/My Games/Skyrim Special Edition/Saves/`, or
wherever NGVO's MO2 profile keeps saves — copy the whole folder). If
anything looks wrong (a CTD, a corrupted-seeming save, an NPC behaving
strangely), stop and restore from backup rather than continuing to test
on a save that might already be damaged.

## 0. One-time setup

1. Build the current `ChronicleBridge.dll` (`.claude/windows-build-machine.md`
   has the working recipe) and copy it into NGVO's MO2 mods folder per
   `adapters/skyrim/ChronicleBridge/README.md`'s `SKYRIM_MODS_FOLDER`
   build-time env var, or manually into
   `<mod>/SKSE/Plugins/ChronicleBridge.dll`.
2. Start the listener with `--live-run` pointed at a **dedicated
   live-play run**, never `runs/north-star-01` or any other fixture/demo
   run the test suite depends on:
   ```
   uv run --with pydantic python adapters/skyrim/listener/listener.py \
       --shared-secret <pick-something> --live-run <a-fresh-run-id>
   ```
   The run directory needs to exist first — `chronicle`'s own CLI or a
   short Python snippet using `chronicle.driver.Driver` can create an
   empty one; check `chronicle/tests/`'s fixtures for the minimal
   construction shape if unsure.
3. `Data/SKSE/Plugins/ChronicleBridge.ini` on the game side needs the
   listener's actual LAN IP/port/shared-secret if the game and the
   listener aren't on the same machine (`ChronicleBridge/README.md`'s
   "Runtime configuration" section has the exact ini shape).
4. Launch the game via NGVO/MO2. Check `ChronicleBridge.log` (SKSE's log
   folder, typically `Documents/My Games/Skyrim Special Edition/SKSE/`)
   for `"ChronicleBridge loaded -- spatial streamer + death-event +
   hydration-poll slices"` — confirms the DLL loaded and didn't crash on
   init.

## 1. Spatial streamer (already informally verified last session — re-confirm only if regressed)

- Walk outdoors in Whiterun. Check the listener's stdout/stderr for
  `POST /whiterun/positions` lines arriving roughly once per second.
- Open the dashboard against the listener's snapshot file
  (`adapters/skyrim/listener/README.md`) and confirm NPC dots move.

## 2. Death extraction

- Kill an NPC that resolves to a real named-cast identity (the 19 in
  `IdentityMap.cpp`'s `kNamedCast` — e.g. Braith, Carlotta Valentia).
  **Pick someone whose death doesn't matter to your playthrough** — this
  is genuinely killing an NPC permanently.
- Check `ChronicleBridge.log` for `"ChronicleBridge: TESDeathEvent sink
  registered"` (confirms registration happened) and, at the moment of
  death, a POST to `/whiterun/events` in the listener's log.
- Check the live run's `events.jsonl` for a new `npc_died` record with
  the correct `npc_id`, a real `gamets` value, and (if you know the
  killer) a `killer_id`.
- **What would indicate a real bug, not just "unverified":** a CTD at
  the moment of death; the wrong `npc_id` (cross-reference against
  `IdentityMap.cpp`'s table); a `gamets` value that looks wrong (e.g.
  negative, or wildly inconsistent with actual playtime — checks
  `RE::Calendar::GetHoursPassed()`'s real behavior, which this session
  could only compile against, never observe).

## 3. Hydration (the first WRITE path — most important to verify carefully)

- Get a named-cast NPC into a real grudge state (either by scripting
  one via `chronicle inject`/the CLI against the live run directly, or
  by triggering whatever in-game action eventually produces one through
  ChronicleBridge's own event extraction once more slices land).
- Watch the listener's log for `GET /whiterun/hydration` (every ~8s) and
  `POST /whiterun/hydration/ack` responses.
- Check `ChronicleBridge.log` for the line `"ChronicleBridge hydration:
  set relationship(...).level = ... (UNVERIFIED against a live save --
  compiled only...)"` — if this line appears, the write was attempted.
  **Confirm it actually did something**: use console commands in-game
  (`getrelationshiprank` on the two actors, or simply observe whether
  the two NPCs' vanilla-dialogue tone toward each other changed, since
  `GetRelationshipRank`-conditioned dialogue is common) to check whether
  the rank actually changed in the live game state.
- **The critical save-integrity check**: save the game, reload that
  save (or fully exit and relaunch), and check the relationship rank
  again. If it reverted to its pre-write value, `AddChange()`
  (`HydrationPoller.cpp`'s own documented uncertainty) was NOT
  sufficient to persist the write across a save/reload — a real finding
  to report back, not a success. If it holds, that's the first real
  evidence this write path is save-safe.
- If the log shows `"no existing BGSRelationship for (...) -- skipping
  per ruled scope"` for every pair you try, that's expected — most
  Chronicle-relevant grudge pairs won't have an authored vanilla
  relationship record at all (named explicitly in the design doc as the
  common case). Try a pair known to have one (e.g. a married couple, a
  parent/child pair already in the fixture cast) to get a real positive
  test.

## 4. Avoidance (Python-only so far — nothing to verify in-game yet)

No C++ consumer exists yet (`docs/design/chronicle-bridge-avoidance-out.md`
§2b — needs Creation Kit content authoring first). `GET
/whiterun/avoidance` can still be exercised directly with `curl` against
the listener while a live run has a real grudge, independent of the
game — see that endpoint's own tests
(`adapters/skyrim/listener/test_listener.py`) for the expected response
shape.

## 5. Reporting back

Whatever you find — success, a CTD, a wrong value, a write that doesn't
survive reload — write it into
`docs/design/chronicle-bridge-*.md`'s relevant "verified" status line
directly (each doc's status header is written to be updated exactly for
this). A negative result (something doesn't work) is exactly as useful
to record as a positive one — the whole point of the "compiled, not
verified" framing throughout this work is to make the boundary between
those two claims visible until real testing closes it.
