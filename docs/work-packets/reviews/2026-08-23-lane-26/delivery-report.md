# Lane 26 delivery report — observer-local reputation wiring (T3.5)

**Delivered:** `fa553c7` — rule 16 live (acquisition-driven reputation
hooks on witness/retell/corroborate), the T3.5 status-deference rung
(`scenarios/test_tier3_reputation.py`), and the pre-authorized
registry-test migration. **Tier 3's machinery is complete: T3.1–T3.5 all
have green rungs; rules 1–16 are live in the registry.**

## Acceptance, per criterion

- **`uv run pytest -q` green:** 205 passed, 0 failed, 0 xfailed (203
  prior + 2 new: the rung and the no-mapping regression test). Tail:
  `205 passed in 2.33s`.
- **ruff clean:** `All checks passed!`
- **`reputation_updated` field-for-field per §4:128:** every hook update
  goes through the existing `driver.update_reputation` wrapper — the same
  emission code as the scripted path, so the shape holds by construction.
- **Observer-locality tripwire, per NPC:** the rung asserts the row-observer
  set is exactly {proventus, irileth, hulda} (witnessed / witnessed /
  reported + proventus's corroborated), and carlotta — alone at the
  market, never informed — has zero trace rows as observer and a `None`
  store lookup. No aggregate-only assertion.
- **Corroboration adds a `"corroborated"` row:** irileth's testimony
  corroborates proventus's belief post-run; proventus's rows are exactly
  `["witnessed", "corroborated"]`.
- **Each update pairs with a rule_evaluated:** count equality plus set
  equality on (observer, kind) pairs, and each row's inputs carry
  claim/subject/context/kind/positive with the resulting alpha/beta/
  uncertainty in result.
- **No behavior change with no mapping registered:** dedicated regression
  test — beliefs form and spread (`belief_formed`/`transmitted` present),
  zero `reputation_updated`, zero rule-16 `rule_evaluated` rows.
- **No schema/frozen-doc edits; no new RNG purposes:** confirmed — the
  hook is deterministic; the commit touches only rules.py, driver.py,
  test_rules.py, and the new scenario file.

## Findings / choices flagged for the coordinator

1. **Re-hearings produce no reputation row.** The retell hook lives
   inside the `not hearer_already_held` branch alongside rule 11's hook:
   R11's trigger is "gains or corroborates a belief," and a re-hearing
   (the T2.3 conflict-2 carve-out) mints nothing. This falls out of the
   ruled text but is worth a explicit note: repeated hearings of the same
   content never inflate reputation.
2. **Resolution path produces no row.** Encounter-driven contested
   hearings route through `driver.resolve()`, not `retell()` — so a
   supersession re-points a belief without a reputation update. That
   matches R11's three-path pin (witness/retell/corroborate); flagging in
   case "re-pointed to new content" should count as acquisition in a
   future rung.
3. **Anchor event is a `RumorHeard` proclamation.** No status-change
   event type exists; lane 23 set the precedent of anchoring a claim on
   an existing event class while the claim kind carries the semantics.
   If a `StatusChanged` event class is wanted (events.py + a framelog
   serialization branch), that's a small follow-up lane — the schema's
   §3 event table would need a coordinator amendment first.
4. **Missing subject slot fails loud.** `claim.slots[subject_slot]`
   raises KeyError if a registered kind's claim lacks the slot — a
   fixture bug surfaced immediately, the same posture as
   mutation_candidates. Not a silent skip.
5. **`test_rules.py` migration 13 → 14** under the packet's
   pre-authorization; no assertion bodies changed, only the count literal
   and comment (same class as lanes 23/24/25).

## Board state

Track A's Tier 3 is done. Per the coordinator's note, the tracks now
converge (Claude finishing M3); the next planning cycle (Tier 4a vs. the
seam lanes) is the coordinator's. Standing by.
