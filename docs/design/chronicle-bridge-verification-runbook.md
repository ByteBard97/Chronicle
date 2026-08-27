# ChronicleBridge in-game verification runbook

**Purpose:** every ChronicleBridge slice built so far (spatial streamer,
death extraction, hydration, vendor markup, avoidance's C++ consumer,
diegetic evidence) has only ever been verified by compiling cleanly
against real CommonLibSSE-NG headers — none has ever run against a live
game. This doc is the concrete checklist for closing that gap.

**Update (2026-08-27):** an external AI ("Kimi") produced a 4-path manual
test script (hydration, vendor markup, diegetic evidence, avoidance). Its
test *ordering*, time budgets, and cheat-sheet framing were good and are
kept below. But several of its technical claims were checked against this
project's real source and real UESP/community documentation, and were
**wrong in ways that would have burned session time on dead ends** — most
seriously, two of its four tests targeted the wrong mechanism entirely
(see the corrections table). This revision replaces those claims with
verified specifics. Anything not independently verifiable is marked
plainly as unverified, not silently assumed correct.

## Corrections table (Kimi's script vs. verified reality)

| # | Kimi's script said | Verified / corrected to | Why |
|---|---|---|---|
| 1 | Vendor Markup precondition: `prid <vendor>; SetRelationshipRank Player -2` | **Wrong mechanism.** `VendorMarkupCache.cpp` polls `GET /whiterun/vendor-markup` and only reacts to a Chronicle grudge/markup pair with `target_id == "the_player"` fed from the live run's data. Console `SetRelationshipRank` never touches this cache at all — it's a completely separate data path from `RE::BGSRelationship`. The real precondition is `chronicle inject <run_id> --type grudge_formed --payload '{"holder_id": "adrianne_avenicci", "target_id": "the_player", ...}'` (or the future dedicated vendor-markup event once one exists — check `chronicle/cli.py`/`docs/frame-log-schema.md` for the current accepted shape) against the live run directory, then wait for the ~8s poll. | `VendorMarkupCache.cpp`, `VendorMarkupCache.h` |
| 2 | Diegetic Evidence: manually `PlaceAtMe <YourEvidenceBaseForm> 1 1 1` via console | **Wrong mechanism entirely.** A real C++ consumer already exists (`EvidencePoller.cpp`) and does this automatically: it polls `GET /whiterun/evidence`, resolves the claim's `holder_id` to a live `Actor*`, and calls `believer->PlaceObjectAtMe(evidenceObject, true)` on the **NPC's own position**, not the player's. The evidence object is **not** a form you choose — it's hardcoded as a real authored `MiscItem` record (**correction 2026-08-27: this table originally said vanilla `Gold001`; that was the placeholder before evidence-object authoring landed and is now stale** — the real object is `ChroniclePatcher.esp:0x000a01`, editor ID `ChronicleEvidenceObject`, model `Clutter\BloodyRags\BloodyRags.nif`, see `EvidencePoller.cpp`'s `kEvidenceLocalFormId` comment for why this FormID is allocation-order-dependent and how to re-derive it if the named-cast roster changes). Manually console-spawning something yourself tests vanilla engine persistence, not ChronicleBridge. The real test is: inject a `belief_formed` event for a named-cast holder via `chronicle inject`, wait ~8s, then go find that NPC and look for the spawned evidence item at their feet. | `EvidencePoller.cpp`, `EvidencePoller.h` |
| 3 | Avoidance pair: "Ysolda and Carlotta Valentia" | **Would have silently failed for the wrong reason, at the time this was written.** At the time of the original test, only 4 of 171 possible pairs had real (non-placeholder) FormIDs wired into `AvoidanceGlobals.cpp`'s then-illustrative C++ lookup table, and Ysolda+Carlotta wasn't one of them. **Update (2026-08-27): this is now moot — `AvoidanceGlobals.cpp` was expanded to cover all 171 pairs** (generated programmatically from `tools/chronicle-patcher/out/chronicle-globals.json` via `tools/generate-avoidance-globals-table.py`, verified entry-by-entry against the source data). Any named-cast pair now resolves. `nazeem`/`ysolda` remains the recommended pick below purely for in-game travel convenience (they're the closest pair in the one live position snapshot captured so far), not because other pairs would fail. | `AvoidanceGlobals.cpp` |
| 4 | Global name: `Chronicle_GrudgeGlobal_<PairID>`, set via `Set <name> 1` | Real global name (`AvoidanceGlobals.h`/`.cpp`, `AvoidancePatchBuilder.cs`): **`ChronicleAvoidingPair_<npcA>_<npcB>`**, `npcA`/`npcB` sorted ordinally by `chronicle_npc_id` (not display name). For the recommended pair: `ChronicleAvoidingPair_nazeem_ysolda`. Also, `Set X 1` is not valid Skyrim console syntax — the real form is `set <globalname> to <value>` (confirmed via multiple independent sources below). Corrected command: `set ChronicleAvoidingPair_nazeem_ysolda to 1`. | `AvoidanceGlobals.h`, `AvoidancePoller.cpp`, `tools/chronicle-patcher/src/AvoidancePatchBuilder.cs` |
| 5 | Hydration precondition: `prid <NPC>; SetRelationshipRank Player -3` | **Wrong axis.** `HydrationPoller.cpp`'s `ApplyHydrationPair` resolves **both** `pair.holderId` and `pair.targetId` to `RE::TESNPC*` and calls `RE::BGSRelationship::GetRelationship(npc1, npc2)` — this is a pure **NPC↔NPC** write, the player is never involved. Setting the NPC's rank toward the player tests nothing this slice touches. Correct verification is `prid <npcA_refid>; getrelationshiprank <npcB_refid>` before and after ChronicleBridge's poll, on a pair known to have an authored vanilla `BGSRelationship` record (a married couple or parent/child; not independently confirmed for any specific named-cast pair from this session — see §3 below). | `HydrationPoller.cpp` |
| 6 | Vendor name "Adrienne Avenicci" | Spelling corrected: **Adrianne Avenicci** (`Skyrim.esm`, `0x01a67c`, `IdentityMap.cpp`'s `kNamedCast`). Confirmed as the Warmaidens forge vendor, and confirmed live-observed outdoors near Warmaidens in `whiterun-positions.json` (20372, -7896). | `IdentityMap.cpp`, `whiterun-positions.json` |
| 7 | Iron Dagger FormID `00012E4E` | Wrong. Real vanilla Iron Dagger base FormID is **`0001397E`** (confirmed independently via two community item-ID databases; could not reach UESP's own page directly — see verification notes). | web search, not this repo |
| 8 | `PlaceAtMe <formID> <count> <forcePersist> <initially_disabled>` | Wrong argument meaning for the **console command** (as opposed to the Papyrus `ObjectReference.PlaceAtMe()` function, which does take `forcePersist`/`initiallyDisabled`). The console command's real syntax is `PlaceAtMe <BaseID> <Count> <Distance> <Direction>` — there is no console-exposed force-persist/initially-disabled argument at all. Moot anyway per #2 above: the diegetic-evidence test doesn't use manual `PlaceAtMe`. | web search |
| 9 | `~10s greeting-cache staleness` | Likely conflated two different things. Vanilla generic-greeting reset timers found in community sources are **0.5–8 in-game hours**, not 10 seconds. The real ~10-second figure that *does* exist in Skyrim's engine is the AI package re-evaluation interval (`EvaluatePackage`/`evp` forces an immediate re-check instead of waiting out that interval) — a different mechanism from dialogue greeting caching. State this distinction explicitly to the owner rather than repeating Kimi's merged claim. | web search (not fully resolved — see notes) |

Item 1 (`SetRelationshipRank Player -3` / `getrelationshiprank`) syntax
itself, and the `prid`-then-bare-command targeting pattern, **is** real
and correctly formed Skyrim console syntax — that part of Kimi's script
was right; only the choice of *which axis* to write (player vs. NPC-pair)
was wrong for hydration specifically, and *irrelevant* for vendor markup's
actual data source.

| 10 | (this doc's own §3/§4/§5 preconditions, as originally written) | **Not executable with today's `chronicle` CLI as a single command.** `chronicle inject <run_id> --type grudge_formed --payload '...'` (no `--event`) is **compose-only** — it pretty-prints the JSON and writes nothing (`inject_command`'s docstring in `chronicle/cli.py`: "`--type`/`--payload` composes... does not write to the run's log"). The actual write path, `--event '<json>'`, only recognizes three event kinds: `npc_died`, `crime_witnessed`, `rumor_heard`. `grudge_formed` and `belief_formed` are **trace-stream derived records** (`docs/frame-log-schema.md` §4, producer tiers 3 and 0), not events-stream events, and `chronicle inject` has no trace-stream write path at all — confirmed empirically: `chronicle inject <run> --run <run> --at 0 --type grudge_formed --payload '{}'` → `chronicle: unknown event type 'grudge_formed' -- known kinds: crime_witnessed, npc_died, rumor_heard`. There is also no listener-side side door: `/whiterun/hydration`, `/whiterun/vendor-markup`, and `/whiterun/evidence` (`adapters/skyrim/listener/listener.py`) all compute their poll responses from `FrameLogReader.state_at()` — i.e. straight from the frame log. **Superseded by #11 below**, which found and verified the actual two-step recipe. | `chronicle/cli.py` (`inject_command`, `_EVENT_CLASSES`), `docs/frame-log-schema.md` §4, `adapters/skyrim/listener/listener.py` (`_hydration_pairs`, `_vendor_markup_pairs`, `_evidence_entries`) |
| 11 | (follow-up to #10, 2026-08-27) | **A real recipe exists — it just isn't a single `chronicle inject` call.** `chronicle inject`'s `--event` path genuinely CANNOT write a `Grudge` or `BeliefInstance` directly (#10 stands: those are trace-stream *derived* records, and `chronicle inject`'s write path only appends to the *events* stream — confirmed by reading `_inject_write` in full: it constructs an `Event` subclass and calls `writer.write_event()`, nothing else). But `chronicle/driver.py`'s own `Driver.crime_witnessed()` (rule 12's cascade) DOES derive a real `Grudge` + `BeliefInstance` from a `crime_witnessed` event when `victim_id == witness_id` — and that event kind IS one `chronicle inject --event` genuinely accepts. Verified end-to-end this session against a fresh scratch run (not `runs/north-star-01`): (1) `chronicle inject <run> --event '{"event_type": "crime_witnessed", "witness_id": "<a>", "perpetrator_id": "<b>", "crime_type": "assault", "victim_id": "<a>", "location_id": "...", "gamets": <t>}'` — this succeeds today, unlike `grudge_formed`; (2) reattach a `Driver` to that same run (replaying its state via `FrameLogReader.state_at()`, matching `chronicle/cli.py`'s own `_open_appending_writer`/`_branch_identity` reattachment pattern) and call `driver.crime_witnessed(...)` with the SAME ids and the injected event's `(save_uuid, generation, seq)` as `canonical_event_key` — this derives `Grudge(holder_id=<a>, target_id=<b>, severity=1.0)` and `BeliefInstance(confidence=0.95)`, confirmed by an independent, freshly-constructed `FrameLogReader.state_at()` re-read (not just the in-process driver's own view) and by `chronicle inspect <run> <a>`. Severity 1.0 clears `AVOIDANCE_GRUDGE_THRESHOLD` (0.5) and `MARKUP_SEVERITY_FLOOR` (0.2) with room to spare; confidence 0.95 clears `EVIDENCE_CONFIDENCE_THRESHOLD` (0.6). Setting `perpetrator_id="the_player"` (instead of a second NPC) produces `target_id="the_player"` for the vendor-markup precondition; a bystander witness (`victim_id=None`, no self-victim) produces the belief with no grudge cascade at all, for evidence-only seeding. Step 2 is **not** a CLI command — there is none — it's a small, real Python driver of `chronicle`'s own public simulation API, now wired into `tools/chronicle-devbench-runbook.py`'s `seed_crime_witnessed_grudge`/`_resume_driver` (see that file's module docstring for the full recipe, including a real auto-id-collision caveat this session found while verifying it). §3/§4/§5 below now document the real two-step recipe directly. | `chronicle/driver.py` (`Driver.crime_witnessed`, `Driver.suffer_harm`, `Driver.witness`), `chronicle/rules.py` (`GrudgeCreationRule`), `chronicle/social.py` (`form_grudge`, `GRUDGE_EMOTIONAL_WEIGHT`/`GRUDGE_EVIDENTIARY_WEIGHT`), `chronicle/claims.py` (`WITNESS_CONFIDENCE`), `chronicle/diegetic_evidence.py`, `chronicle/vendor_markup.py`, `chronicle/driver.py` (`AVOIDANCE_GRUDGE_THRESHOLD`), `tools/chronicle-devbench-runbook.py` (updated this session) |

## Deployment gap — RESOLVED since this section was first written

**Correction added 2026-08-27, later same day**: this section originally
recorded a real gap (`ChronicleBridge`/`ChroniclePatcher` mod folders
absent, `plugins.txt` missing the patcher plugin), checked directly at
14:56. That gap closed shortly after, evidently as part of `48d827c`
(15:12) — this section was never updated to say so, and an external AI
conversation cited the stale version of it as current fact. Re-checked
directly against the filesystem just now:

- `~/Games/ChronicleDev/mods/ChronicleBridge/SKSE/Plugins/
  ChronicleBridge.dll` exists.
- `~/Games/ChronicleDev/mods/ChroniclePatcherOutput/ChroniclePatcher.esp`
  exists.
- `profiles/Default/modlist.txt` has both `+ChronicleBridge` and
  `+ChroniclePatcherOutput` enabled.
- `profiles/Default/plugins.txt` has `*ChroniclePatcher.esp` enabled.
- `profiles/Default/loadorder.txt` orders it correctly: `Skyrim.esm,
  Update.esm, Dawnguard.esm, HearthFires.esm, Dragonborn.esm,
  _ResourcePack.esl, ...USSEP, SkyUI_SE.esp, ChroniclePatcher.esp` — after
  all masters it needs.

**Deployment is real and current as of this check.** What's still true,
unchanged: no one has launched the game against this deployed build yet
(the only `ChronicleBridge.log` found on this machine is from 2026-08-25,
a different install, and predates this 7-slice build by two days — it
logged the spatial-streamer-only slice, not current state). Don't cite
the bulleted gap-list above as current; it's kept only as a record of
what this section originally found.

**Pre-session checklist (owner's own manual MO2 steps — not automated
here per this task's scope):**

1. Copy `ChronicleBridge.dll` off the Windows machine
   (`C:\Users\geoff\ChronicleBridge\build\release\ChronicleBridge.dll`,
   confirmed present and freshly built) to this machine, e.g.:
   `scp geoff@192.168.0.211:'C:\Users\geoff\ChronicleBridge\build\release\ChronicleBridge.dll' /tmp/`
2. In MO2 (or by hand under `~/Games/ChronicleDev/mods/`), create a new
   mod folder, e.g. `ChronicleBridge/`, containing
   `SKSE/Plugins/ChronicleBridge.dll` — matches the shape
   `SKYRIM_MODS_FOLDER`'s build-time copy would have produced
   (`ChronicleBridge/README.md`). Enable it in MO2's left pane (adds a
   `+ChronicleBridge` line to `modlist.txt`).
3. Create a second mod folder for the patcher output, e.g.
   `ChroniclePatcherOutput/`, containing
   `tools/chronicle-patcher/out/ChroniclePatcher.esp` directly in its
   root (MO2 plugin folders put `.esp` files at the mod's top level, not
   under `Data/`). Enable it and **load-order it after** USSEP,
   Skyrim.esm and HearthFires.esm (it masters those three per its own
   generation comment) — check the box in `plugins.txt`'s load-order
   pane.
4. Optionally create `Data/SKSE/Plugins/ChronicleBridge.ini` inside the
   `ChronicleBridge` mod folder if the listener runs on a different
   machine than the game (`ChronicleBridge/README.md`'s "Runtime
   configuration" section has the exact ini shape and default
   `127.0.0.1:8765`).
5. Launch once via `tools/launch-chronicledev-skse.sh` and check
   `Documents/My Games/Skyrim Special Edition/SKSE/ChronicleBridge.log`
   for a clean load line before doing anything else.

None of steps 1–4 were performed by this pass — they require GUI/MO2
interaction (or at minimum touching `modlist.txt`/`plugins.txt`, which
this task was explicitly told not to do). This is the concrete,
un-skippable blocker before any of the 4 test paths below can be
attempted at all.

## Safety first — read before doing anything else

Slices 3–6 (hydration, vendor markup, avoidance, evidence) write
persistent state into the save. **Back up the save file before testing
any of them** (`Documents/My Games/Skyrim Special Edition/Saves/`, or
wherever this MO2 profile keeps saves — copy the whole folder). Make a
hard save named something distinct like `CHRONICLE_BASELINE` right before
starting (Kimi's suggestion — kept, it's a good habit). If anything looks
wrong (a CTD, a corrupted-seeming save, an NPC behaving strangely), stop
and restore from backup.

**Note on driving this remotely**: `docs/research/25-devbench-skse-mcp-verification.md`
previously confirmed `alandtse/devbench` (a real, actively-maintained
CommonLibSSE-NG plugin exposing console-command execution, save/load, and
state inspection over MCP/REST on `127.0.0.1:8920`) as a way to script
most of the steps below from an agent session instead of by hand. This is
still true and still relevant: `devbench` **is already installed** in
`~/Games/ChronicleDev/mods/devbench` (confirmed directly this session,
`SKSE/Plugins/devbench.dll` present) — one less one-time setup step than
previously thought, on top of `ChronicleBridge` itself needing to be
added per the checklist above.

## 0. One-time setup (after the deployment checklist above is done)

1. Start the listener with `--live-run` pointed at a **dedicated
   live-play run**, never `runs/north-star-01` or another fixture/demo
   run the test suite depends on:
   ```
   uv run --with pydantic python adapters/skyrim/listener/listener.py \
       --shared-secret <pick-something> --live-run <a-fresh-run-id>
   ```
   The run directory needs to exist first — `chronicle`'s CLI or a short
   Python snippet using `chronicle.driver.Driver` can create an empty
   one; check `chronicle/tests/`'s fixtures for the minimal construction
   shape if unsure.
2. `Data/SKSE/Plugins/ChronicleBridge.ini` needs the listener's actual
   LAN IP/port/shared-secret if game and listener aren't on the same
   machine.
3. Launch the game. Check `ChronicleBridge.log` for a clean load line
   confirming the DLL loaded and didn't crash on init.

## 1. Spatial streamer (already informally verified — re-confirm only if regressed)

- Walk outdoors in Whiterun. Check the listener's stdout/stderr for
  `POST /whiterun/positions` lines arriving roughly once per second.
- Open the dashboard against the listener's snapshot file and confirm
  NPC dots move.

## 2. Death extraction

- Kill an NPC that resolves to a real named-cast identity (the 19 in
  `IdentityMap.cpp`'s `kNamedCast`). **Pick someone whose death doesn't
  matter to your playthrough.**
- Check `ChronicleBridge.log` for the death-sink registration line, and,
  at the moment of death, a POST to `/whiterun/events` in the listener's
  log.
- Check the live run's `events.jsonl` for a new `npc_died` record with
  the correct `npc_id`, a real `gamets`, and (if known) `killer_id`.

## 3. Hydration — corrected precondition, ~15 min

The `prid`/`getrelationshiprank` commands below can be run manually, or via
`tools/chronicle-devbench-runbook.py hydration --npc-a <a> --npc-b <b>
--run <run_id>` (reads DevBench's `console` tool for you, prints the
captured output verbatim, AND — with `--run` — actually runs the real
two-step seeding recipe below and prints its verified result). **Unverified
against a live game** — the DevBench/console parts of that script have
never run against a real Skyrim process; the seeding recipe itself HAS
been verified against a real (scratch, non-fixture) `chronicle` run this
session, independent of any live game — see correction #11 above.

- **This is an NPC↔NPC write, not an NPC↔player write** (correction #5
  above). Pick a named-cast pair likely to have an authored vanilla
  `BGSRelationship` — e.g. a parent/child pair already in the fixture
  cast (Fralia Gray-Mane / Olfina Gray-Mane is a plausible candidate by
  family name, but this was **not independently confirmed** against CK
  data this session — don't assume it without checking in-game first).
- **Seed the pair with the real, verified two-step recipe (correction
  #11)** — not `--type grudge_formed --payload`, which does not work:
  1. `chronicle inject <run_id> --event '{"event_type": "crime_witnessed",
     "witness_id": "fralia_gray_mane", "perpetrator_id":
     "olfina_gray_mane", "crime_type": "assault", "victim_id":
     "fralia_gray_mane", "location_id": "whiterun", "gamets": <t>}'`
     against the live run directly (this genuinely writes — confirmed).
  2. Derive the grudge from it: `tools/chronicle-devbench-runbook.py
     hydration --npc-a fralia_gray_mane --npc-b olfina_gray_mane --run
     <run_id>` does both steps for you and prints the derived
     `Grudge(holder_id=fralia_gray_mane, target_id=olfina_gray_mane,
     severity=1.0)` plus an independent frame-log re-read confirming it
     landed. (There is no CLI-only equivalent of step 2 today — it drives
     `chronicle.driver.Driver.crime_witnessed()` directly, the same
     derivation a live tick loop or scenario script uses; see that
     script's module docstring and the runbook's correction #11 for why
     this is real, not a workaround.)
- Watch the listener's log for `GET /whiterun/hydration` (every ~8s) and
  `POST /whiterun/hydration/ack`.
- Check `ChronicleBridge.log` for the hydration-write log line — if it
  appears, the write was attempted.
- **Verify the actual game state changed**: `prid <npcA_refid>` then
  `getrelationshiprank <npcB_refid>` (real, confirmed console syntax —
  `prid` selects the reference, then the bare command takes the other
  actor and reads/writes the rank between them). If the log instead says
  `"no existing BGSRelationship for (...) -- skipping"`, that's the
  documented common case (`HydrationPoller.cpp`'s ruled scope: never
  creates a relationship, only mutates an existing one) — try a
  different pair.
- **The critical save-integrity check**: save, reload (or fully exit and
  relaunch), re-check the rank. If it reverted, `AddChange()` was NOT
  sufficient to persist the write — a real finding to report, not a
  success.

## 4. Vendor markup — corrected precondition, ~15 min

The vendor ref-resolution below can be run manually, or via
`tools/chronicle-devbench-runbook.py vendor-markup [--vendor-formid <id>]
--run <run_id>` (drives DevBench's `console`/`inspect` tools; with `--run`
it also runs the real, verified two-step seeding recipe and prints the
derived state). **Unverified against a live game** — the DevBench/console
parts have never run against a real Skyrim process; the seeding recipe
itself HAS been verified against a real scratch `chronicle` run this
session — see correction #11.

- Target: **Adrianne Avenicci** (correction #6 — not "Adrienne"),
  Warmaidens forge vendor, `Skyrim.esm:0x01a67c`.
- **Do not use `SetRelationshipRank`** — it has zero effect on this
  feature (correction #1). Instead, seed a real Chronicle grudge with
  `holder_id: "adrianne_avenicci"`, `target_id: "the_player"` via the
  verified two-step recipe (correction #11), not `--type grudge_formed
  --payload`:
  1. `chronicle inject <run_id> --event '{"event_type": "crime_witnessed",
     "witness_id": "adrianne_avenicci", "perpetrator_id": "the_player",
     "crime_type": "theft", "victim_id": "adrianne_avenicci",
     "location_id": "warmaidens", "gamets": <t>}'` against the live run.
  2. `tools/chronicle-devbench-runbook.py vendor-markup --run <run_id>`
     derives the grudge from that event (`Driver.crime_witnessed()`,
     rule 12) and prints `Grudge(holder_id=adrianne_avenicci,
     target_id=the_player, severity=1.0)`, confirmed by an independent
     frame-log re-read. Severity 1.0 clears `MARKUP_SEVERITY_FLOOR`
     (0.2) by a wide margin — expect the maximum markup multiplier
     (`MARKUP_CEILING`, 1.5×) once the poller picks it up.
- Give the poller (8s interval, `VendorMarkupCache.cpp`) time to pick it
  up **before** opening the barter menu.
- Give the player gold, then open the barter menu with Adrianne and
  compare the displayed price against the actual gold deducted on
  purchase — this specific comparison is exactly the open question
  `VendorPriceHook.h`'s own "UNVERIFIED CAVEAT" flags (whether the
  Scaleform "value" field this hooks multiplies is the same value the
  engine actually charges, or only the displayed figure). Kimi's idea
  here was sound; only the precondition was wrong.
- **On the first-vs-second-open question**: the real documented ordering
  risk (`VendorPriceHook.h`'s "ORDERING CAVEAT") is that `PostCreate`
  (where the price hook installs) may fire before
  `RE::BarterMenu::GetTargetRefHandle()`'s underlying static is populated
  for that menu instance — if the multiplier never appears, **close and
  reopen the barter menu** as the first troubleshooting step; that
  isolates "hook installed too early this once" from "the mechanism
  doesn't work at all." This is a different root cause than Kimi's
  framing (which suggested a cache-population race), but the same
  practical workaround.
- Iron Dagger FormID if you want a cheap, known-price test item:
  **`0001397E`** (correction #7), not `00012E4E`.

## 5. Diegetic evidence — corrected mechanism, ~5 min spawn + checked at end

The holder-ref resolution below can be run manually, or via
`tools/chronicle-devbench-runbook.py evidence --holder <npc_id> --run
<run_id>` (drives DevBench's `console`/`inspect` tools; with `--run` it
also runs the real, verified two-step seeding recipe and prints the
derived belief). **Unverified against a live game** — the DevBench/console
parts have never run against a real Skyrim process; the seeding recipe
itself HAS been verified against a real scratch `chronicle` run this
session — see correction #11.

- **This is fully automatic once seeded — do not manually `PlaceAtMe`
  anything** (correction #2). `EvidencePoller.cpp` polls `GET
  /whiterun/evidence` and, for each entry, spawns the real authored
  evidence item (`ChroniclePatcher.esp:0x000a01`, editor ID
  `ChronicleEvidenceObject` — not vanilla `Gold001`; that placeholder was
  superseded, see correction above — not a form you choose) at the
  **believer NPC's own position** via
  `Actor::PlaceObjectAtMe(evidenceObject, true)` (force-persistent).
- **Seed a real, well-evidenced belief with the verified two-step recipe
  (correction #11)** — a `belief_formed` record can't be written directly
  (it's trace-stream derived, not an events-stream kind), but a
  `crime_witnessed` event CAN, and deriving from it via `Driver.witness()`
  produces a real `BeliefInstance` at confidence 0.95 (`chronicle/
  claims.py`'s `WITNESS_CONFIDENCE`), comfortably above the 0.6 gate
  (`chronicle/diegetic_evidence.py`'s `EVIDENCE_CONFIDENCE_THRESHOLD`):
  1. `chronicle inject <run_id> --event '{"event_type": "crime_witnessed",
     "witness_id": "<holder>", "perpetrator_id": "unknown", "crime_type":
     "theft", "victim_id": null, "location_id": "whiterun", "gamets":
     <t>}'` against the live run — `victim_id: null` makes `<holder>` a
     bystander witness, so no grudge cascade fires, only the belief.
  2. `tools/chronicle-devbench-runbook.py evidence --holder <holder>
     --run <run_id>` derives the belief from that event and prints
     `BeliefInstance(confidence=0.95)`, confirmed by an independent
     frame-log re-read (and by `chronicle inspect <run_id> <holder>`).
- Wait ~8s for the poll, then go find that NPC and look for a spawned
  Gold item near their feet. Note the refID if you can (console-click
  it) for later.
- **The persistence check that actually matters** (Kimi's structure here
  was good, keep it): hard-save, then do a full detach/reattach cycle —
  fast-travel far enough away that the cell unloads, then travel back —
  not just a same-cell save/reload, which wouldn't exercise cell
  attach/detach at all. Confirm the spawned object is still there.
  `EvidencePoller.h`'s own header explicitly flags that whether a
  `PlaceObjectAtMe`-created reference survives save/reload has **never**
  been verified — this is the first real evidence either way.
- Note for cleanup: every successful spawn is forced-persistent and
  never retracted (`EvidencePoller.cpp`'s own documented tradeoff) — if
  you seed several test entries, expect several permanent Gold items in
  the save; `markfordelete` them from the console after the session if
  you care about save cleanliness.

## 6. Avoidance — corrected pair and console syntax, ~20 min

The console commands below can be run manually, or via
`tools/chronicle-devbench-runbook.py avoidance --pair nazeem_ysolda`
(reads the global, sets it, `prid`s both NPCs, and forces
`EvaluatePackage` on each, via DevBench's `console` tool). **Unverified
against a live game.** Of the four paths in this doc, avoidance is the
only one this tool can drive fully end-to-end today — it needs no
`chronicle inject` seeding at all, only the global write, so it isn't hit
by correction #10's gap.

- **Use `nazeem`/`ysolda`** (correction #3 — any of the 171 named-cast
  pairs now resolves, since `AvoidanceGlobals.cpp` was expanded to the
  full set on 2026-08-27; this pair is recommended purely for travel
  convenience, not because it's one of a limited working subset).
  Of all 171 pairs, nazeem/ysolda were the closest together in the
  one live position snapshot captured so far
  (`whiterun-positions.json`: Nazeem at (25078,-7167), Ysolda at
  (25059,-7450), ~284 units apart — both outdoor/daytime), which
  minimizes in-game travel/wait time during a real test session.
  **Caveat**: that snapshot's Ysolda entry is listed with a bare `"id":
  "ysolda"` instead of the `plugin:formid` shape every other entry has
  (e.g. `"Skyrim.esm:01a675"` for Carlotta) — this session could not
  explain that discrepancy (possibly post-resolution output rather than
  a raw ref, or a capture-time quirk); `IdentityMap.cpp` itself lists
  Ysolda plainly as `Skyrim.esm 0x01a69a`, matching the FormID
  `AvoidanceGlobals.cpp` expects. If Ysolda doesn't resolve cleanly
  in-game, fall back to `carlotta_valentia`/`saffir` — same table, same
  corrected global-naming rule below, just farther apart in that one
  snapshot (~2950 units) so budget more travel time.
- **Global name**: `ChronicleAvoidingPair_nazeem_ysolda` (sorted
  `chronicle_npc_id`s, correction #4 — not `Chronicle_GrudgeGlobal_*`).
- **Console syntax**: `set ChronicleAvoidingPair_nazeem_ysolda to 1` —
  not `Set X 1`. **Before setting it, read it first**:
  `getglobalvalue ChronicleAvoidingPair_nazeem_ysolda` (or `show
  ChronicleAvoidingPair_nazeem_ysolda` — either should print the current
  value). This one line is the difference between "the pair is real but
  avoidance behavior isn't kicking in" and "`ChroniclePatcher.esp` isn't
  actually installed/load-ordered" (see the deployment gap above) — the
  second failure mode would otherwise look identical to "avoidance
  doesn't work" and could eat the whole 20-minute budget on a false
  negative.
- `prid <nazeem_refid>; EvaluatePackage` and same for Ysolda, then watch
  `GetCurrentPackage`/`GetDistance` over 3–5 minutes.
- **Flag Kimi kept and is worth keeping**: a quest package at higher
  priority can mask the avoidance effect entirely — if nothing changes,
  check whether either NPC is mid-quest-package before concluding
  avoidance itself is broken.

## 7. Engine gotchas — verified status

- **Greeting-cache staleness**: Kimi's "~10s" figure is likely a
  conflation. Vanilla generic-greeting reset timers found in community
  sources are on the order of **0.5–8 in-game hours**, not seconds. The
  real ~10-second figure belongs to **AI package re-evaluation**
  (`EvaluatePackage`/`evp` forces an immediate check instead of waiting
  out that interval) — a different system. State this to the owner
  plainly rather than repeating the merged claim; this session could not
  fully pin the exact vanilla greeting-reset value (varies per dialogue
  entry, 0.5/2/8h all cited) so don't treat any single number as
  authoritative.
- **`EvaluatePackage` and mid-travel packages**: community sources
  (TES Alliance, gamesas forums) describe packages as evaluated on a
  ~10s cycle, and `EvaluatePackage` forces an immediate recheck — but if
  the *current* package runs to completion (reaches its destination)
  after `evp` was called, the *next* package evaluation may not process
  correctly in some cases. Treat `EvaluatePackage` as "nudge the AI to
  reconsider now" rather than "guaranteed instant package switch,"
  especially mid-travel. Not independently verified against a live game
  this session — could not reach UESP's own CK-wiki pages directly (see
  below).
- **Forced-persistent refs and base-form persistence**: `EvidencePoller`
  explicitly force-persists the *spawned reference* itself
  (`PlaceObjectAtMe(..., true)`), so the "base form must already be
  persistent" caveat Kimi raised doesn't apply the way it phrased it —
  the reference, not the base form (`ChroniclePatcher.esp:0x000a01`, a
  newly-authored MISC record), is what needs to survive, and the code
  already requests that.
  Whether it actually does survive across a full cell detach/attach
  cycle is exactly what §5's test is for — genuinely unverified either
  way before that test runs.
- **Sources reachable this session**: `skyrimcommands.com`,
  `elderscrolls.fandom.com` (partially — one page returned HTTP 402),
  general web search results citing UESP/TES Alliance/gamesas. **UESP's
  own domains (`en.uesp.net`, `ck.uesp.net`, `skyrimck.uesp.net`)
  returned HTTP 403 to every direct fetch attempt this session** — all
  UESP-sourced claims above are via search-result snippets citing UESP,
  not a direct read of the page. If precision matters before the real
  session, someone with a normal browser should open those UESP pages
  directly rather than trusting this secondhand relay.

## 8. Reporting back

Whatever you find — success, a CTD, a wrong value, a write that doesn't
survive reload — write it into `docs/design/chronicle-bridge-*.md`'s
relevant "verified" status line directly. A negative result is exactly
as useful to record as a positive one.
