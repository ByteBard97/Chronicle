# Lane 33 — overseer review and rulings (Tier 4a design doc)

**Date:** 2026-08-23 · **Overseer:** planning agent · **Re:**
`docs/design/tier-4a-schedule-write-back.md` (`d93c1b8`)

## Verdict: **accepted.** The design is precise, honest, and buildable.

Citation spot-checks (all verified): the keyframe-tick `covers` filter
(`framelog.py:268`), `state_at`'s never-replay-schedule behavior
(:648-654), the `schedule_rewrite` reserved schema row (§3:96),
`SCHEDULE_WRITE_BACK`'s stub registration (`rules.py:74,262`), the
per-pair roll mechanics (`schedule.py:114-125`, `rng.py:85-103`).

Design assessments worth stating: the overlay decision (T1) is correct
and its byproduct-fix of the latent schedule-reconstruction gap is the
right kind of free win; Decision T4's proof that roll-identity is
automatic from per-pair independence is the doc's load-bearing argument
and it holds — with the named precondition (an overlay never touches
another NPC's presence) correctly flagged as the thing to protect;
T7's "Run B is Run A with rule 17 disabled" is exactly what the
registry's construction-time toggle was built for.

## Rulings on the open points (coordinator authority, owner-delegated)

- **O1 — `mourning_triggers` convention: accepted.** Caller-supplied
  mapping, fixture authors add the deceased-naming slot. Propagated
  into lane 36's packet as an authoring note.
- **O2 — tunables: accepted.** `MOURNING_DURATION_TICKS = 72` (3
  game-days), construction-time destination; ordering load-bearing,
  numbers placeholder.
- **O3 — `schedule_rewrite` event type: approved at coordinator level**
  (same pattern as Tier-3's F2 — the schema row was already reserved
  with "fields defined with schedule write-back"; this doc is that
  definition). Fields filled into §3:96 today: `npc_id`, `location_id`,
  `start_tick`/`end_tick`, `cause`, `trigger_event_key`, `rule`.
- **O4 — `framelog.py` edit: accepted** and explicitly listed in
  lane 36's file boundaries (no repeat of lane 24's retroactive flag).
- **O5 — per-household mourning locations: deferred** to fixture design
  (T6/north-star); one construction-time destination per run suffices
  for T4a.1.

## Findings adopted into the lane plan

- F2 (latent schedule-reconstruction gap) is fixed *by* the design,
  via T3's unfiltered keyframe capture + replay branch — lane 36
  includes it.
- F3 (deceased-naming slot) is an authoring note in lane 36's packet.
- F4 (shared definition of "outside the mourner's changed sites"
  between the T4a.2 test and §3.9's merge-scan tool) is noted for the
  M5 tooling lane when it's packetized.

## Dispatch

Lane 36 (L-G: rule 17 core + T4a.1) packetized and dispatched; lane 37
(L-H: T4a.2 counterfactual, pure scenario test) queued behind it.
