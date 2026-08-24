# Lane 47 — Tier 5 L-I: role model + vacancy + duty lapse (Track A)

**Status:** Ready to start immediately. The design is accepted and ruled
(`docs/design/tier-5-roles-and-vacancy.md` — decisions S1–S6 are your
spec; overseer review in `docs/work-packets/reviews/2026-08-24-lane-44/`).
The `role_lapse` schema reservation is retired (§3:98 superseded);
`status_changed` is the lapse vocabulary.

**Effort:** medium (new module + vacancy wiring + T5.1 rung).

## Context

T5.1 (frozen, ladder): a steward is killed. Assert: role vacant;
duties lapse with defined effects; lapse effects are events
propagating through Tiers 1–4 machinery. This lane is the role model
core (S1), objective vacancy detection (S3), and the lapse-event
cascade (S4). Succession is lane 48.

## Read first (in order)

1. `docs/design/tier-5-roles-and-vacancy.md` §1 (S1/S2), §2 (S3/S4) —
   the ruled design. Deviations come back as findings.
2. The frozen rung text (ladder Tier 5).
3. `chronicle/events.py` `StatusChanged` (lane 39) + the lane-39
   anchor test (`chronicle/tests/test_driver.py`) — the lapse-event
   pattern.
4. `chronicle/driver.py` — `inject_event`'s `NPCDied` branch
   (:284-286, the `_deceased` precedent your vacancy branch sits
   beside) and the `self.claims`/`self.social` composition idiom.
5. `chronicle/social.py` — the store-shape discipline `RoleStore`
   mirrors (frozen dataclasses, `dataclasses.replace` mutations).
6. `docs/work-packets/reviews/README.md` — governance.

## Pinned implementation decisions (ruled — see the design doc + review)

- **New module `chronicle/roles.py`** with `Duty`, `Role`, `RoleStore`
  exactly per S1's shape (`install`/`role`/`holder_of`/`roles_held_by`;
  frozen dataclasses, `replace` mutations).
- **Vacancy is objective (S3):** an `NPCDied` branch in `inject_event`
  (beside `_deceased`) vacates each role the deceased held —
  `holder_id = None`, `vacated_at = event gamets`. No trace record for
  the vacancy itself (derived state, replayable from `NPCDied` events).
- **Lapse events (S4):** on vacancy, one `StatusChanged` per duty:
  `npc_id` = the former holder (dead-anchor precedent), `status_kind`
  = the duty's `lapse_status_kind`, `detail` = the duty's `name`.
  Propagation is ordinary (witnessed off the canonical key by whoever's
  positioned, per the caller-supplied claim kind).
- **The design rule from O1's ruling:** nothing stores a holder's
  npc id as a proxy for the role; `holder_of` is the only answer.

## Task

1. `chronicle/roles.py` per S1 (+ unit tests in the idiom-correct home).
2. `chronicle/driver.py`: `self.roles`, the `inject_event` vacancy
   branch, the lapse-event injection.
3. `scenarios/test_tier5_vacancy.py` — T5.1: a steward role installed
   with duties; the steward dies (`NPCDied`). Assert: the role is
   vacant (`holder_of` → None, `vacated_at` set); one `StatusChanged`
   per duty with the right fields; the lapse events are witnessed and
   propagate (a `transmitted` record exists for the lapse claim);
   `state_at` reconstruction shows the vacancy (replay from `NPCDied`,
   not a keyframe dependency); rule-19's registry row isn't needed for
   vacancy itself (vacancy is objective — assert it happens with the
   rule stub still in place).
4. Suite green; no behavior change without an installed role.

## Acceptance

- `uv run pytest -q` green (223 + your new tests), ruff clean.
- The rung asserts pass as written; `StatusChanged` lapse records match
  §3:97 field-for-field.
- No new RNG purposes; no schema edits (§3:98 is superseded; §3:97 is
  the vocabulary).
- Replay-from-log vacancy (no keyframe requirement) covered by test.

## File boundaries

**Create:** `chronicle/roles.py`, `scenarios/test_tier5_vacancy.py`

**Edit:** `chronicle/driver.py` + the pre-authorized mechanical edits
class (idiom-correct test homes)

**Do not touch:** frozen/coordinator docs, `chronicle/social.py`
(read-only this lane — lane 48 gets the accessor), `chronicle/rules.py`
(lane 48), other `scenarios/` files, `dashboard/`, `runs/`

## Conventions

- Match the engine idiom; named constants with rule citations.
- **Local commits OK** (path-scoped, atomic `add && commit`); never push.
- File a delivery report on disk: delivered, acceptance per criterion
  with command tails, findings list.
