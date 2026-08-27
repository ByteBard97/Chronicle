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
| 2 | Diegetic Evidence: manually `PlaceAtMe <YourEvidenceBaseForm> 1 1 1` via console | **Wrong mechanism entirely.** A real C++ consumer already exists (`EvidencePoller.cpp`) and does this automatically: it polls `GET /whiterun/evidence`, resolves the claim's `holder_id` to a live `Actor*`, and calls `believer->PlaceObjectAtMe(evidenceObject, true)` on the **NPC's own position**, not the player's. The evidence object is **not** a form you choose — it's hardcoded as vanilla `Gold001` (`Skyrim.esm`, FormID `0x0000000F`), an explicitly-flagged throwaway placeholder (see `EvidencePoller.cpp`'s `kPlaceholderLocalFormId` comment). Manually console-spawning something yourself tests vanilla engine persistence, not ChronicleBridge. The real test is: inject a `belief_formed` event for a named-cast holder via `chronicle inject`, wait ~8s, then go find that NPC and look for a spawned Gold item at their feet. | `EvidencePoller.cpp`, `EvidencePoller.h` |
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

## Deployment gap — checked directly against `~/Games/ChronicleDev`, 2026-08-27

This is real, current state, not assumed:

- **`~/Games/ChronicleDev/mods/`** has 9 mods installed (Address Library,
  Crash Logger, `devbench`, EngineFixes, PapyrusUtil, powerofthree's
  Papyrus Extender, Skyrim Script Extender, SkyUI, USSEP). **There is no
  `ChronicleBridge` mod folder and no `ChroniclePatcher` mod folder.**
  `find ~/Games/ChronicleDev -iname "*ChronicleBridge*"` and
  `*ChroniclePatcher*` both return nothing.
- **`~/Games/ChronicleDev/profiles/Default/plugins.txt`** only has
  `unofficial skyrim special edition patch.esp` and `SkyUI_SE.esp`
  enabled — `ChroniclePatcher.esp` is not installed or load-ordered.
- **The repo's own generated patcher output does exist**:
  `tools/chronicle-patcher/out/ChroniclePatcher.esp` is present on this
  machine (171/171 pairs resolved per `AvoidanceGlobals.cpp`'s 2026-08-27
  comment) — it just hasn't been moved into the MO2 instance yet.
- **The Windows build machine mirror is further along than
  `.claude/windows-build-machine.md`'s note suggests.** That note (dated
  2026-08-26) says the mirror "currently has only slice 1." Checked
  directly via SSH on 2026-08-27: `C:\Users\geoff\ChronicleBridge\src\`
  now has **all 26 source files / all 7 slices**, and
  `C:\Users\geoff\ChronicleBridge\build\release\ChronicleBridge.dll`
  exists, built at the same timestamp as the source sync (01:22 PM). The
  full-slice DLL has already been built successfully — it just hasn't
  been copied to this Linux machine or into the MO2 instance. That stale
  note should be corrected the next time someone touches it.

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

- **This is an NPC↔NPC write, not an NPC↔player write** (correction #5
  above). Pick a named-cast pair likely to have an authored vanilla
  `BGSRelationship` — e.g. a parent/child pair already in the fixture
  cast (Fralia Gray-Mane / Olfina Gray-Mane is a plausible candidate by
  family name, but this was **not independently confirmed** against CK
  data this session — don't assume it without checking in-game first).
- Seed the pair with `chronicle inject <run_id> --type grudge_formed
  --payload '{"holder_id": "<a>", "target_id": "<b>", ...}'` (see
  `docs/frame-log-schema.md`'s `grudge_formed` row and
  `chronicle/cli.py`'s `inject_command` for the exact required/optional
  fields) against the live run directly.
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

- Target: **Adrianne Avenicci** (correction #6 — not "Adrienne"),
  Warmaidens forge vendor, `Skyrim.esm:0x01a67c`.
- **Do not use `SetRelationshipRank`** — it has zero effect on this
  feature (correction #1). Instead, seed a Chronicle grudge/markup pair
  with `holder_id: "adrianne_avenicci"`, `target_id: "the_player"` via
  `chronicle inject` against the live run, and give the poller (8s
  interval, `VendorMarkupCache.cpp`) time to pick it up **before**
  opening the barter menu.
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

- **This is fully automatic once seeded — do not manually `PlaceAtMe`
  anything** (correction #2). `EvidencePoller.cpp` polls `GET
  /whiterun/evidence` and, for each entry, spawns vanilla `Gold001`
  (`Skyrim.esm:0x0000000F`, an explicit placeholder — not a form you
  choose) at the **believer NPC's own position** via
  `Actor::PlaceObjectAtMe(evidenceObject, true)` (force-persistent).
- Inject a `belief_formed` event for a named-cast holder via `chronicle
  inject` (see `docs/frame-log-schema.md`'s `belief_formed` row for the
  required fields: `belief_id`, `claim_id`, `holder_id`, `evidence_id`,
  `claim_kind`, `claim_slots`, `canonical_event_key`).
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
  the reference, not the base form (`Gold001`, a common vanilla MISC
  item), is what needs to survive, and the code already requests that.
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
