# Lane 48 delivery report — succession resolution (rule 19, T5.2/T5.3)

**Delivered:** landed in `d95b7e6` (see the commit-note at
`docs/work-packets/reviews/2026-08-24-lane-48-commit-note.md` — a git
race bundled this lane's files under an unrelated commit message;
content verified byte-for-byte correct and complete). Per the ruled
design (`docs/design/tier-5-roles-and-vacancy.md` decisions S5/S6,
overseer review `docs/work-packets/reviews/2026-08-24-lane-44/`).

## Acceptance, per criterion

- **`uv run pytest -q` green (lane-47 count + new tests), ruff clean.**
  ✓ — 240 passed, 0 failed, 0 xfailed (235 prior + 5 rung tests).
  `uv run ruff check .`: clean.
- **The counterfactual passes exactly (fixture-carried, not
  seed-carried).** ✓ —
  `test_t5_2_the_counterfactual_is_fixture_carried_not_seed_carried`:
  two drivers, same `seed_id`, identical construction, differing only
  in which of two relationship edges (`irileth`/`proventus`) has the
  higher `strength` — irileth succeeds in one, proventus in the other.
  No `disabled_rules` toggle used (rule 19 is enabled in both — the
  data is the variable, not the rule, exactly per S5/T7's precedent
  from Tier 4a's `disabled_rules` toggle used for a *different*
  purpose there).
- **T5.3's by-construction assertions pass; `role_appointed` records
  match §3:97.** ✓ —
  `test_t5_3_holder_of_is_the_only_reference_and_layer_four_records_are_unchanged`:
  after succession, the relationship edge that made the successor a
  candidate is byte-identical to what `form_relationship` originally
  returned, and its `to_id` still names the dead former holder — nothing
  rewrites it. `role_appointed` events carry `npc_id` (the successor),
  `status_kind="role_appointed"`, `detail` (the role id), `location_id`
  (`None`) — field-for-field against §3:97.
- **No new RNG purposes; no schema edits; all 19 registry rules live.**
  ✓ — `git diff chronicle/rng.py docs/frame-log-schema.md` for this
  lane is empty. `_default_rules()`'s docstring now reads "All 19 §8
  rules live... 12-13 remain stubs" — verified via
  `test_registry_lists_all_nineteen_ladder_rules_with_stubs_disabled`
  (17 enabled of 19, up from 16).

## What was built

- **`social.py`** — `relationships_to(basis_id)`: a bulk scan across
  every relationship regardless of basis type (a "faction" edge and a
  "shared_employer" edge to the same institution both count), the same
  bulk-scan precedent `grudges()` set (lane 43, O3) for a query with no
  single holder to key off. New unit test covers the cross-basis case
  and the empty case.
- **`rules.py`** — `RoleVacancySuccessionRule`: `fired = has_candidate`,
  a single caller-assembled boolean (the driver does all the ranking;
  the rule only asks whether it found a winner). Real, driver-owned
  toggle. Replaces the registry's last stub — `_default_rules()`'s
  docstring updated to reflect all 19 raw names now live.
- **`driver.py`** — `_institution_strengths(institution_id)`: the best
  (max) relationship strength each candidate NPC has toward an
  institution. `_resolve_succession(role, tick, gamets)`: ranks
  candidates (excluding the dead — `not in self._deceased`), descending
  strength then ascending `npc_id`, evaluates the rule, and on a fire
  installs the successor (`RoleStore.succeed`) and injects a
  `role_appointed` `StatusChanged` event. Wired directly into
  `_vacate_roles_on_death` (lane 47), right after vacancy and the duty
  lapse cascade, so succession resolves in the same objective moment
  the role becomes vacant — no separate trigger needed.
- **`scenarios/test_tier5_succession.py`** — five tests: the
  higher-strength candidate succeeds (with the `role_appointed` event
  and the `rule_evaluated` row both checked); the fixture-carried
  counterfactual; a lexicographic tie-break (`"aldric"` over
  `"beatrice"` at equal strength); zero qualifying candidates leaves the
  role vacant (asserted as a real, non-error outcome, with the paired
  `fired: false` row); T5.3's by-construction check.

## Findings — two boundary deviations, both mechanical and necessary

1. **`chronicle/roles.py` gained `RoleStore.succeed()`**, despite the
   packet listing it as "do not touch... gaps are findings." Lane 47's
   S1 shape had `install()` (first-time registration only — raises on
   a duplicate id) and `vacate()`, but nothing to install a *new*
   holder onto an *already-existing* (now-vacant) role — a genuine gap
   in the original shape, not something I could route around without
   either reaching into `RoleStore`'s private `_roles`/
   `_roles_by_holder` dicts from `driver.py` (worse: a write-reach
   from outside the store, risking the index falling out of sync,
   unlike the existing read-only reach precedents elsewhere in this
   codebase) or leaving succession unimplementable. `succeed()` mirrors
   `vacate()`'s exact bookkeeping. Same "mechanical, necessary,
   flagged" norm as lane 24's `framelog.py` branch and lane 25's
   `form_grudge` bypass — both retroactively ruled in-bounds.
2. **`scenarios/test_tier5_vacancy.py` (lane 47's file) needed one
   stale assertion updated.** That lane's T5.1 rung asserted "no
   `rule_evaluated` row at all" for rule 19, which was true while rule
   19 was a stub — landing rule 19 here means every vacancy now
   evaluates succession (that fixture seeds no court relationships, so
   it fires `false`, not absent). Updated the assertion to check
   `fired is False` and `candidate_count == 0` instead of asserting
   zero rows, with a comment explaining why. This is the same kind of
   "landing a stub changes a previously-correct assertion elsewhere"
   consequence lane 24 hit with the registry-count test, now hitting a
   scenario test instead of a unit test.

Both deviations are minimal, directly traceable to the design doc's own
S5/S6 decisions, and left the affected files' *intent* unchanged —
flagging for the record, not asking forgiveness after the fact.
