# Lane 25 delivery report — obligation violation cascade (T3.3)

**Delivered:** `f7453f4` — rule 14 live (violation cascade in
`driver.violate_obligation`), the ruled O3 self-victim bypass in
`form_grudge`, the T3.3 favor-ledger rung
(`scenarios/test_tier3_obligations.py`), and the packet-authorized
registry-test migration.

## Acceptance, per criterion

- **`uv run pytest -q` green:** 203 passed, 0 failed, 0 xfailed (200 prior
  + 3 new: the rung, the plain-violation regression test, the bypass unit
  test). Tail: `203 passed in 2.34s`.
- **ruff clean:** `All checks passed!`
- **grudge_formed / reputation_updated field-for-field per §4:124/128:**
  the cascade emits both records through the existing `driver.form_grudge`
  / `driver.update_reputation` wrappers — the same emission code the
  schema-shaped scripted paths already use, so the shapes hold by
  construction.
- **Rung asserts as written:** three favors issued; `obl-favor-1`
  fulfilled (no cascade — asserted: zero grudge_formed from it, and the
  resolutions list is exactly `[(favor-1, fulfilled), (favor-2,
  violated)]`); `obl-favor-2` refused with proventus + hulda present →
  exactly one grudge_formed (adrianne vs ulfberth, `obligation_violated`),
  one reputation_updated per present observer (witnessed, negative,
  subject ulfberth), **none** for carlotta (absent witness) or olfrid
  (present non-witness); one rule_evaluated naming
  `obligation-issue-fulfill-violate` with the obligation in inputs and
  `{grudge_id, reputation_observer_ids}` in result. Presence is derived
  through real `npcs_present_at(schedule, 2)`, not a hand-written set.
- **Bypass unit-tested:** `test_form_grudge_self_victim_bypasses_the_edge_gate`
  (self-victim allowed, emotional 1.0, severity formula unchanged); the
  pre-existing `test_form_grudge_rejects_a_missing_relationship_to_the_victim`
  covers the third-party missing-edge raise, still passing unmodified.
- **No schema/frozen-doc edits; no new RNG purposes:** confirmed — the
  cascade is deterministic (no rolls); `git diff` of the commit touches
  only the six listed files.
- **No behavior change outside the new cascade:** the cascade is opt-in
  (see flag 1); `test_framelog.py`'s existing scripted violation
  (tick 7, no cascade params) passes byte-identical, and a dedicated
  regression test pins the plain-violation shape.

## Findings / deviations flagged for the coordinator

1. **Cascade is opt-in via `violation_evidentiary_strength=None` default.**
   The pin says the severity is "caller-supplied"; making it required
   would break `test_framelog.py:337`'s existing call (immutable
   assertions, no packet authorization to edit). Implemented: caller
   supplies the severity → cascade fires; omits it → exactly the
   pre-lane-25 behavior. This also gives lane 26 a clean legacy path.
2. **`source_belief_id = obligation.id` in the cascade grudge.** The
   Grudge field is required and no belief exists on the violation path
   (scripted store mutation; the rung asserts no belief records). The
   obligation record is the grievance's source, so its id fills the
   field. If the coordinator wants a sentinel convention instead (e.g.
   `obligation:<id>`), it's a one-line change.
3. **Self-victim emotional strength = 1.0.** O3 pinned skipping the
   raise and forbade synthetic self-edges, but the emotional component's
   source was unpinned — with no edge to read, I set it to 1.0
   (self-regard is total; harm-to-self as rule 8's base case). Severity
   then follows the unchanged formula: `0.5*1.0 + 0.5*evidentiary`.
4. **Rule 14 disabled ⇒ cascade fully suspended (behavioral gate).** The
   generic RecordedRule docstring says disabling suspends instrumentation
   only, but rule 14's cascade is new behavior this lane introduced (like
   rules 6/7's driver-owned steps and rule 11's gate), so
   `disabled_rules=(OBLIGATION_LIFECYCLE,)` now means "violations resolve
   but never cascade." Noted in the wrapper's docstring.
5. **`chronicle/tests/` edits beyond the packet's listed files** (same
   posture as lane 24's framelog.py flag): `test_rules.py`'s enabled
   count 12 → 13 is mechanically required by the "rule 14 registers
   replacing the stub" pin (lanes 23/24 migrated the same assertion);
   the bypass unit test went to `test_social.py` next to the existing
   `form_grudge` tests, the idiom-correct home. No assertion bodies
   changed — only the count literal and its comment.
6. **Reputation context = `obligation.action`** per R8's "context from
   the obligation's action" — so per-observer rows key on
   (observer, debtor, action); two refused favors with different actions
   produce distinct reputation contexts. Calling it out because it makes
   "context" per-favor rather than per-violation-kind.

## Board state

Lane 25 complete. Lane 26 (reputation wiring / `"reported"` rows via
propagation) is the queued successor per the coordinator's dispatch note
("after 25 comes lane 26, and that completes Tier 3's machinery").
