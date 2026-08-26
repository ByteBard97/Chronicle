# ChronicleBridge design prep — NPC death extraction (v0.2, second slice)

**Status:** design proposal, no code dispatched from the C++ side yet.
Autonomous design pass, 2026-08-25 — flag for owner review before the
`ChronicleBridge/` (C++) half is built; the Python-side half described in
§3 is low-risk, fully headless-testable, and has already landed
(`chronicle inject`'s `--origin-kind`/`--origin-detail` flags, this
session).

Sources: `adapters/skyrim/README.md` (the seam's stated charter — "In:
game events... arrive here and get turned into `chronicle.events`
appends" — this slice is literally that, for one event kind);
`docs/research/22-native-skse-plugin-prior-art.md` (native event sink
mapping, `RE::TESDeathEvent`); `docs/decisions/0004-timeline-branching.md`
and `0005-sync-handshake.md` (the full save/branch sync design this slice
deliberately does not implement yet — see §1); `chronicle/events.py`
(`NPCDied`, `EventLog.append`'s idempotency contract);
`chronicle/cli.py` (`chronicle inject`'s existing write path);
`docs/frame-log-schema.md` §3 (`origin.kind` enum, `npc_died` fields);
`docs/design/chronicle-bridge-spatial-streamer.md` (slice 1 — the
precedent for scoping a slice down honestly and naming what's deferred).

---

## 0. What this slice actually is

Not the full "In" direction `adapters/skyrim/README.md` describes (deaths,
crimes, cell attach/load, dialogue, quest stages, item transfers) — just
**NPC deaths**, and only onto **a single, developer-designated live run**
with **no real multi-save branch awareness**. Everything else stays real
future work. This is the same discipline as slice 1: build the smallest
real thing, name the rest honestly.

Why deaths first: it's the one event every version of the vision doc's
north-star scenario is built around ("the player assassinates Jarl
Balgruuf"), Chronicle already has a canonical `NPCDied` event type and a
fully tested write path for it, and — unlike crime/bounty — CommonLibSSE-NG
exposes a clean top-level event sink (`RE::TESDeathEvent` via
`RE::BSTEventSink`, `docs/research/22` §"Native Event Sink Mapping"), no
inline hook/detour required.

## 1. The dependency this slice deliberately does not build

Every canonical `Event` (`chronicle/events.py`) requires a branch key —
`save_uuid`, `generation`, `seq` — and `EventLog.append()`'s idempotency
guarantee is keyed on exactly that triple. The *real*, save-aware version
of "a live death event lands in the correct branch" needs the full
sync-handshake ADR-0005 describes: `OnInit`/`OnPlayerLoadGame` dual-hook
detection, a `g_isLoading` guard, the co-save timeline record
(`save_uuid`/`generation`/`event_seq`), the `SYNC_TIMELINE`/
`TIMELINE_READY` handshake, and epoch fencing against stale post-reload
writes.

**None of that exists yet, anywhere in this repo.** There is no co-save
read/write code, no SKSE serialization callback registration, no epoch
concept on the Python side. Building it is a real, sequenced, native-code
project of its own — it needs a live game and the Windows build machine to
even test, and it is not something this pass (or any headless pass)
should attempt to fake or shortcut. Naming it here is the point: a future
session should build the sync-handshake shim as its own lane, not
discover this dependency by finding v0.2 event-extraction silently unable
to do the one thing it was built for.

**Resolved (D1): this slice does not wait for it, and does not pretend to
solve it.** It targets a single run whose `(save_uuid, generation)` a
human names when starting the listener — exactly the same trust model
slice 1 already has for "the whole snapshot file is one live session, no
save-awareness at all." A death detected while a *different* save is
actually loaded in-game (or after a reload the listener doesn't know
about) lands in the wrong branch. This is a known, named limitation, not
a silent bug — it must be stated in the listener's own `--help` text and
this doc, not just here.

## 2. Scope, precisely

- **What:** `RE::TESDeathEvent`, registered via
  `RE::ScriptEventSourceHolder::GetSingleton()->AddEventSink<RE::TESDeathEvent>(...)`
  during/after `SKSE::MessagingInterface::kDataLoaded` (per research/22's
  documented registration lifecycle — registering earlier risks null
  singletons).
- **Where:** no worldspace restriction (unlike slice 1's Whiterun-only
  scope) — a death is a discrete, low-frequency event, not a per-tick
  spatial poll, so there's no perf reason to filter by location. If the
  eventual fixture cast (`chronicle/fixtures/whiterun_schedule.py`) is
  Whiterun-only, deaths of NPCs outside that cast are still real events,
  just for `npc_id`s Chronicle doesn't yet track — see §4's identity note.
- **Payload:** `actorDying`'s resolved identity (same `FormRef`/
  `IdentityMap` resolution slice 1 already built —
  `adapters/skyrim/ChronicleBridge/src/IdentityMap.cpp` needs no changes
  for this slice), the in-game `gamets`-equivalent clock value at the
  moment of death, and — when resolvable — the killer's identity and the
  cell/location. `RE::TESDeathEvent` provides `actorDying`; `actorKiller`
  is present on the same event per research/22's table, no extra hook
  needed for the common case.
- **Cause:** `TESDeathEvent` doesn't carry a structured cause code (no
  "combat" vs. "scripted" vs. "console-command" enum in the event
  payload itself, per research/22 — not verified against the actual
  compiled headers yet). **Resolved (D2): cause is a fixed string
  `"unknown"` for this slice** unless/until a follow-up pass finds a
  reliable way to distinguish it; `NPCDied.cause` is a plain string field
  (`chronicle/events.py`), not an enum, so this is forward-compatible —
  richer cause detection can land later without a schema change.

## 3. What's actually buildable and tested today (no game, no C++)

The Python-side half of this slice needs no live game to build or test,
and has already landed this session:

- **`chronicle inject`'s `--origin-kind`/`--origin-detail` flags**
  (`chronicle/cli.py`). The frame-log schema already defines
  `origin.kind: "scenario" | "console" | "adapter"`
  (`docs/frame-log-schema.md` §3), but the write path always stamped
  `{"kind": "console", "detail": "chronicle inject"}` regardless of
  caller — a real provenance gap for a system whose whole thesis is
  evidence chains with correct provenance. A future ChronicleBridge
  listener shelling out to this exact tested write path (the same idiom
  the dashboard's injection console already uses) can now stamp
  `--origin-kind adapter --origin-detail "chronicle-bridge death event"`
  instead of being mislabeled as a human typing at the console.
  Backward-compatible: omitting both flags reproduces the exact prior
  behavior (verified by the existing
  `test_inject_event_appends_a_console_origin_record` test, unchanged).
  New tests: `test_inject_event_stamps_a_custom_origin_kind_and_detail`,
  `test_inject_event_rejects_an_unknown_origin_kind`
  (`chronicle/tests/test_agent_debug_cli.py`).

**Not yet built** (proposed, not implemented, this pass): a
`/whiterun/events` (or similarly-named) POST endpoint on
`adapters/skyrim/listener/listener.py`, analogous to `/whiterun/positions`
— receives a validated death payload and shells out to
`chronicle inject <run_id> --event '<json>' --origin-kind adapter --origin-detail "chronicle-bridge death event"`
as a subprocess (matching the "listener stays Skyrim-plumbing, never
imports `chronicle/` directly" boundary the listener's own README states),
where `<run_id>` is a value the listener was started with (a new
`--live-run` CLI flag, mirroring `--shared-secret`). This is genuinely
buildable and testable headlessly with a synthetic HTTP POST (no game
needed) — proposed as the next concrete lane, not built in this pass,
because it needs an owner decision first: **should a death detected live
actually write into one of the existing demo runs (`runs/north-star-01`
etc.), or does this need a fresh "live play" run created for it?**
Writing into a demo run used by the M7-gated dashboard walkthrough risks
corrupting the exact fixture the release gate depends on — this should
not be decided unilaterally.

## 4. Named-cast identity gap (a real, separate blocker, not new to this slice)

Per `HANDOFF-2026-08-25-1930.md`: none of the NPCs actually observed
outdoors this session exist in Chronicle's own fixture cast
(`jarl_balgruuf`, `proventus`, `irileth`, `hulda`, `ysolda`,
`whiterun_guard_1` only). A live death of, say, Nazeem would resolve to
the honest fallback identity (`FallbackIdentity`, `<plugin>:<formid>`),
which is a valid `npc_id` string for `NPCDied.npc_id` but one no other
Chronicle machinery (schedules, relationships) knows anything about — the
event would append cleanly but produce no cascade, because there's
nothing in the fixture cast for it to cascade through. This is expected
and correct, not a bug: it's the same "the fake is honest" doctrine
(vision-v2.2.md §5) applied to identity instead of movement. Worth stating
plainly so a future session doesn't mistake "the assassination test only
works for `jarl_balgruuf`" for a defect.

## 5. Deferred / non-goals for this slice

- Real save/branch sync (§1) — its own future lane.
- Crime/bounty, cell attach/load, dialogue, quest-stage, item-transfer
  extraction — real future work per `adapters/skyrim/README.md`'s
  charter, each with its own sink/hook shape (research/22's table), not
  bundled into this slice.
- Structured death cause beyond the fixed `"unknown"` string (§2, D2).
- The listener's `/whiterun/events` endpoint and `--live-run` flag (§3) —
  designed here, not implemented, pending the owner decision on run
  target.
