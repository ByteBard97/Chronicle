# Lane 48 — Tier 5 L-J: succession resolution + T5.2/T5.3 (Track A)

**Status:** After **lane 47** lands (needs the role model + vacancy).
The design is accepted and ruled (S5/S6; overseer review in
`reviews/2026-08-24-lane-44/`).

**Effort:** medium (rule 19 + ranking + the counterfactual rung).

## Context

T5.2 (frozen): the successor resolves from relationship/faction state;
**varying the prior-relationship fixture while holding the seed
produces a different successor**. T5.3 (frozen): everything that
pointed at the holder resolves through the role — satisfied by
construction under the ruled narrow reading (S2/O1): nothing mirrors
onto the holder; `holder_of` is the only answer.

## Read first (in order)

1. `docs/design/tier-5-roles-and-vacancy.md` §3 (S5) and §4 (S6).
2. The frozen rung texts (ladder Tier 5).
3. Lane 47's landed `chronicle/roles.py` and driver vacancy wiring
   (read the committed code).
4. `chronicle/social.py` — `Relationship` (basis/basis_id), the
   `whiterun_court` fixture vocabulary
   (`chronicle/fixtures/whiterun_relationships.py`), and the lane-43
   `grudges()` accessor precedent for your bulk scan.
5. `chronicle/rules.py` — the rule-19 stub + the real-rule idiom.
6. `docs/work-packets/reviews/README.md` — governance.

## Pinned implementation decisions (ruled)

- **Resolution rule (S5):** among NPCs holding a `Relationship` edge
  whose `basis_id` matches the vacant role's `institution_id`, rank by
  edge `strength` descending; tie-break lower `npc_id` lexicographic.
  Zero qualifying edges → the role stays vacant (assertable outcome,
  not an error). **No roll, no new RNG purpose.**
- **Caller-assembled inputs:** the driver bulk-scans relationships (a
  new public accessor in the `grudges()` precedent — e.g.
  `relationships_to(basis_id)`) and hands the ranked list to the rule;
  the rule only picks the head (the T2.3 discipline).
- **Rule 19 registers replacing the stub** with a real (driver-owned)
  toggle: disabled → roles never resolve successors (stay vacant).
- **Installation:** the successor becomes `holder_id` (a `Role`
  `replace`), and a `status_changed` event with
  `status_kind = "role_appointed"` is injected (S4's vocabulary).
- **The counterfactual is fixture-carried (S5):** two runs, same
  `seed_id`, differing only in which fixture edge has higher
  `strength` → different successors. No `disabled_rules` toggle (the
  rule isn't the variable; the data is).
- **T5.3:** assert the design rule — after succession, no record in
  the store layer names the old holder *as the role's holder* (the
  only holder reference is `Role.holder_id`, and it's the successor);
  layer-4 records (obligations/grudges/relationships) are unchanged
  and still name NPCs directly (the narrow reading, accepted).

## Task

1. `chronicle/social.py`: the public bulk relationship accessor (+
   unit test).
2. `chronicle/rules.py`: `RoleVacancySuccessionRule` replaces the stub.
3. `chronicle/driver.py`: the ranking wiring (on vacancy, resolve +
   install + emit `role_appointed`).
4. `scenarios/test_tier5_succession.py` — T5.2: vacant role; two
   candidates with fixture edges of differing strength → the
   higher-strength candidate installed, with the `role_appointed`
   event; a tie broken lexicographically; zero qualifying edges →
   stays vacant. **The counterfactual twin:** same seed, swapped
   strengths → the other candidate wins (the stronger determinism
   claim, asserted exactly). Plus the T5.3 assertions above.
5. Suite green; registry count migration per the pre-authorized class.

## Acceptance

- `uv run pytest -q` green (lane-47 count + your new tests), ruff clean.
- The counterfactual passes exactly (fixture-carried, not seed-carried).
- T5.3's by-construction assertions pass; `role_appointed` records
  match §3:97.
- No new RNG purposes; no schema edits; **all 19 registry rules live
  after this lane** (the last stub fills).

## File boundaries

**Create:** `scenarios/test_tier5_succession.py`

**Edit:** `chronicle/social.py`, `chronicle/rules.py`,
`chronicle/driver.py` + the pre-authorized mechanical edits class

**Do not touch:** frozen/coordinator docs, `chronicle/roles.py`
(read-only — gaps are findings), other `scenarios/` files,
`dashboard/`, `runs/`

## Conventions

- Match the engine idiom; named constants with rule citations.
- **Local commits OK** (path-scoped, atomic `add && commit`); never push.
- File a delivery report on disk: delivered, acceptance per criterion
  with command tails, findings list.
