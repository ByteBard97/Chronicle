# Lane 36 — Tier 4a L-G: schedule write-back (rule 17) + T4a.1 (Track A)

**Status:** Ready to start immediately. The design is accepted and ruled
(`docs/design/tier-4a-schedule-write-back.md` — decisions T1–T7 are your
spec; overseer review in `reviews/2026-08-23-lane-33/`). The
`schedule_rewrite` schema fields are filled (§3:96, coordinator ruling
O3). `framelog.py` is explicitly in-bounds (ruling O4).

**Effort:** medium-large (one coupled mechanism + rung test).

## Context

T4a.1 (frozen, `docs/scenario-ladder.md:82`): kin dies → mourning block
inserted (temple, N days) → original schedule restored after → the
rewrite is itself an event causally linked to the death. This lane is
the first time state writes back into behavior — the overlay design
(T1) keeps the base schedule immutable, and the roll-identity
precondition (T4) must hold: an overlay never touches another NPC's
presence.

## Read first (in order)

1. `docs/design/tier-4a-schedule-write-back.md` — the ruled design.
   Deviations come back as findings.
2. `docs/scenario-ladder.md:82` — the frozen rung text.
3. `docs/frame-log-schema.md` §3:96 — the filled `schedule_rewrite`
   fields: `npc_id`, `location_id`, `start_tick`/`end_tick`, `cause`,
   `trigger_event_key`, `rule`.
4. `chronicle/schedule.py` (`ScheduleBlock`, `npcs_present_at`,
   `sample_encounters`), `chronicle/driver.py` (tick loop reads the
   schedule fresh each tick; the rule-16 acquisition-hook call sites
   the trigger mirrors), `chronicle/rules.py` (rule-17 stub;
   `TellDecisionRule`'s real-rule shape).
5. `chronicle/framelog.py` — `:268` (the keyframe filter T3 drops) and
   `state_at` (:638-785, the replay branch T3 adds).
6. `docs/work-packets/reviews/README.md` — governance.

## Pinned implementation decisions (ruled — see the design doc + review)

- **Overlay (T1):** base schedule immutable; `_schedule_overlays` list;
  **one shared effective-schedule helper** used by both the live driver
  and replay (T3 — exactly one place this logic can drift).
- **The event (T2):** one `schedule_rewrite` per rewrite, fields per
  §3:96; restoration is `end_tick` reached — no separate record.
- **T3:** drop the `covers(tick)` filter in `serialize_state`'s
  schedules key (full base schedule per keyframe) + add the
  `schedule_rewrite` replay branch in `state_at` (events-stream scan,
  active overlays at T).
- **Trigger (T5):** belief acquisition at the rule-16 call sites
  (witness/retell-first-time/corroborate) + kinship edge to the
  deceased (the lane-23 lookup). **Authoring note (F3/O1, ruled):**
  mourning-eligible death claims must carry a deceased-naming slot
  (e.g. `"deceased": "jarl_balgruuf"`) — the `mourning_triggers`
  construction-time mapping points at it. Your rung fixture does this.
- **Latch (T6):** never re-insert for the same (mourner,
  trigger_event_key) — log-derived (the lane-24-amended R5 pattern).
- **Toggle:** real (driver-owned) — disabling rule 17 suppresses the
  rewrite itself; T4a.2's Run B depends on it (T7).
- **Tunables (ruled O2):** `MOURNING_DURATION_TICKS = 72`,
  construction-time destination.
- **Precondition to protect (T4):** the overlay overrides only the
  mourner's own presence. Add the code comment the doc recommends at
  the `sample_encounters` call site (per-pair independence is what
  T4a.2's guarantee stands on).

## Task

1. `chronicle/events.py`: the `schedule_rewrite` event dataclass (§3:96
   fields) + the framelog serialization branch (in-bounds, O4).
2. `chronicle/schedule.py`: the shared effective-schedule helper (base
   + active overlays; override only the overlay NPC's own blocks).
3. `chronicle/driver.py`: overlay state, the rule-17 trigger wiring at
   the acquisition call sites, `mourning_triggers` mapping, the
   tunables, the event injection, `rule_evaluated` emission.
4. `chronicle/framelog.py`: the two T3 edits.
5. `chronicle/rules.py`: `ScheduleWriteBackRule` replaces the stub
   (real rule, caller-assembled booleans only).
6. `scenarios/test_tier4a_mourning.py` — T4a.1: kin dies; the mourner's
   block is inserted (assert presence at the temple during the window,
   absence from their base site, no other NPC's presence changed —
   the T4 precondition, asserted); restoration after `end_tick` (back
   to base); the event exists with the right `trigger_event_key`;
   the latch (re-hearing the death doesn't re-insert); `state_at`
   reconstruction inside the mourning window shows the overlay (the T3
   replay branch — the latent-gap fix, asserted directly).
7. Suite green; no behavior change with no `mourning_triggers`
   registered.

## Acceptance

- `uv run pytest -q` green (206 + your new tests), ruff clean.
- `schedule_rewrite` records match §3:96 field-for-field.
- The rung asserts pass as written, incl. the T4 precondition and the
  reconstruction-in-window check.
- No new RNG purposes; no other schema edits (§3:96 is filled).

## File boundaries

**Create:** `scenarios/test_tier4a_mourning.py`

**Edit:** `chronicle/events.py`, `chronicle/schedule.py`,
`chronicle/driver.py`, `chronicle/framelog.py` (explicitly in-bounds),
`chronicle/rules.py`, plus the pre-authorized mechanical edits class
(registry count migration in `test_rules.py`; new unit tests in their
idiom-correct homes)

**Do not touch:** frozen/coordinator docs beyond §3:96 (filled),
`rng.py`, `social.py` (read-only), other `scenarios/` files,
`dashboard/`, `runs/`

## Conventions

- Match the engine idiom; named constants with rule citations.
- **Local commits OK** (path-scoped); never push.
- Existing test assertions immutable except the pre-authorized class;
  conflicts are findings.
- File a delivery report on disk: delivered, acceptance per criterion
  with command tails, findings list.
