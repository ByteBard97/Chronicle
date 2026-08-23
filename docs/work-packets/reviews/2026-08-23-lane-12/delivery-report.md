# Lane 12 — delivery report (T2.3 conflicting-variant resolution)

**Date:** 2026-08-23 · **Lane agent:** Kimi (Track A) · **Packet:** `docs/work-packets/lane-12-t2-3-variant-resolution.md` (as amended by the coordinator's rulings of 2026-08-23, consensus loop in `pre-implementation-findings.md`)

**No commit**, per protocol. Suite state at delivery: **180 passed, 2 failed, 0 xfailed** — both failures are the blocking conflicts below, each a case where the amended packet's rulings contradict an already-accepted test's assertions ("existing test assertions are immutable; conflicts are findings"). Everything else in the lane is implemented, tested, and green.

## What was delivered

- **Task 1 — `ClaimStore.resolve()`** (`chronicle/claims.py`): first-class write path implementing the ruled policy — evidence-type ordering (terminal grounding evidence, witnessed > reported), summed-strength tiebreak (all Evidence records supporting each side's belief, as-stored, no decay), strict-stronger-to-displace (exact tie → incumbent stands, record fires, incumbent dented). Correction semantics as ruled: no new Variant, one appended `reported` Evidence on the winner's belief (source = teller, predecessor = teller's belief, strength = teller's pre-decay confidence), adoption re-derives via the retell decays × (1 − dent) with `first_learned` preserved, repelled challenge follows corroborate's decay-then-replace × (1 − dent). Rumor bookkeeping identical to `retell()`; loser entry stays. Returns a `Resolution` NamedTuple whose field names match amended §4:120 exactly (the driver spreads it into the payload). New constants `RESOLUTION_RULE = "evidence-type-ordering+v1"` and `CONTESTED_CLAIM_CONFIDENCE_DENT = 0.1` in the tunables block with the rule-citation comment discipline. Guards: `retell()` closes the silent-duplicate hole (same content → raise; differing content → routes to `resolve()` *before* the pure constructor mints anything, since a correction mints no Variant); `witness()` raises on witness-after-rumor.
- **Task 2 — driver wiring** (`chronicle/driver.py`, `chronicle/propagate.py`): new pure lookup `conflicting_pair()` (both informed + held *content* differs — content comparison, so an eyewitness vs. an unmutated retelling of their own story is not a conflict; deterministic direction, lexicographically smaller id tells, no roll). `_propagate_on_encounter` routes differing-variant both-informed encounters through a scripted `driver.resolve()` wrapper that emits the `supersession` record field-for-field per amended §4:120 (no `location_id` — the schema row carries none). Same-content stays `nothing_salient`; no encounter-path corroboration.
- **Task 3 — reader replay** (`chronicle/framelog.py`): `supersession` records are **re-executed** through `claims.resolve()` from the amended payload (`teller_belief` fetched via the established `chain_for(...)[0][0]` pattern); recorded loser/winner/rule/dent fields are cross-check material, not inputs. No keyframe changes — supersessions are trace-only, matching `cli.py`'s existing assumption.
- **Task 4 — T0.4 closed**: `witness()` grows the disagreeing-second-witness path — single-slot disagreement produces a Variant rooted at the claim by design (`parent_variant_id=None`, `mutated_slot` = the disagreed slot, deterministic id `{claim_id}-witness-disagreement-{witness_id}`); multi-slot disagreement raises naming the follow-up; canonical claim never rewritten. Xfail marker removed (the only test-file edit; body byte-identical — `git diff` shows the decorator removal alone). Supporting change: `driver.witness`'s `belief_formed` payload now carries the slots **as the witness reported them** (kwargs) rather than the stored claim's — identical values for agreeing witnesses (all pre-existing logs/tests unaffected), and what lets replay re-execute the disagreement branch exactly, synthesized variant id included. Schema §4:114's row is generic ("`claim_slots` (object)"), so no schema edit — but the semantics nuance is flagged here for the coordinator.
- **Task 5 — rung test** (`scenarios/test_tier2_resolution.py`, 6 tests): named rule fires (record's `resolution_rule` == the constant); invariant raises (same-content retell, witness-after-rumor, multi-slot disagreement, resolve-without-incumbent); both encounters in the winner's evidence chain; supersession record exists naming both variants (incl. null = original telling); winner shows exactly the constant dent; direction flip (eyewitness stands / rumor-holder adopts); strength tiebreak incl. corroboration counting toward the sum; exact-tie two-eyewitness standoff; encounter-driven run with one supersession per tick and arbitrary-T reconstruction parity across a keyframe boundary (rebuilt belief `==` live, compounding dents included).
- **Task 6 — regenerate nothing**: `runs/whiterun-jarl-01` untouched. Resolution would **not** change its trace: it has 186 `both-informed` rows but zero mutations, so all held content is canonically equal and every one stays a `nothing_salient` under content-based conflict detection (distinct variant ids with identical slots do not conflict — by design).

## Acceptance criteria

- `uv run pytest -q`: **180 passed, 2 failed, 0 xfailed** — the T0.4 test passes unmarked (176th), the rung test adds 6; the 2 failures are the conflicts below. Tail:
  ```
  FAILED chronicle/tests/test_claims.py::test_claim_store_rejects_the_same_claim_id_with_different_content
  FAILED chronicle/tests/test_framelog.py::test_distinct_source_counting_survives_a_keyframe_boundary
  2 failed, 180 passed in 2.07s
  ```
- `uv run ruff check .`: `All checks passed!`
- Rung assert list incl. direction flip and exact-tie: green (`scenarios/test_tier2_resolution.py`, 6 passed).
- Store-level invariant raises, covered by test: implemented per the ruling — **but see Conflict 2**: the ruling itself is what fails an accepted test.
- Records match amended §4:120 field-for-field: asserted in two rung tests (`_SUPERSESSION_FIELDS` set equality) — green.
- `chronicle trace` prints supersession against a fixture run — verified (built a scratch run; output tail):
  ```
  -- supersessions involving this claim's variants (1) --
    tick 1: proventus -- variant-gossip superseded by None via evidence-type-ordering+v1 (confidence_dent=0.1)
  ```
- Arbitrary-T reconstruction reflects resolution (winner variant + dented confidence), keyframe boundary included: green.
- No new RNG purposes; no frozen-doc edits; no dashboard edits: confirmed (`git status` shows only `chronicle/claims.py`, `chronicle/driver.py`, `chronicle/framelog.py`, `chronicle/propagate.py`, `scenarios/test_tier0_claims_mechanics.py` (marker only), `scenarios/test_tier2_resolution.py` (new)).

## Blocking conflicts (rulings vs. accepted tests — disposition requested)

### Conflict 1 — `chronicle/tests/test_claims.py::test_claim_store_rejects_the_same_claim_id_with_different_content` (~line 314)

The accepted unit test asserts the pre-T0.4 behavior: a disagreeing second witness **raises**. Task 4 (confirmed in the rulings) makes exactly that call **succeed** and produce a Variant. Same scenario, opposite assertion — unfixable without touching the test. Note the test's *intent* ("disagreement belongs on a Variant... not silently rewriting the shared canonical claim") is what the new code now does; only its mechanism assertion (raise) is stale. **Recommendation:** authorize updating this test to assert the T0.4 path (variant produced, rooted at the claim, canonical slots unchanged) — mirroring the scenario test — plus a rename, since "rejects" no longer describes it. The strict-xfail duplicate coverage then becomes redundant.

### Conflict 2 — `chronicle/tests/test_framelog.py::test_distinct_source_counting_survives_a_keyframe_boundary` (line 371)

The accepted test's *premise* is deliberate duplicate beliefs: four scripted same-content retellings to one holder (`belief-hulda-1..4`) to exercise `_rumor_sources` distinct-source counting across a keyframe (rule 7's re-hearing case). Task 1's "raises otherwise" makes the second retelling raise. This is not a stale-mechanism issue like Conflict 1 — it's the ruling meeting rule 7: **post-T2.3, the encounter path never re-hears** (same-content both-informed declines), so if the store also raises, `_record_hearing`'s re-hearing branch and distinct-source counting become unreachable machinery. **Recommendation:** amend "raises otherwise" to carve out the re-hearing: a same-content re-tell to an informed hearer (distinct or repeat source) mints no variant/belief/evidence, records the hearing (exposure/distinct counting), and returns the existing variant/belief. The conflicted test then passes unchanged — its snapshot assertions are live-vs-reconstruction symmetric and its tail asserts rumor counts only. Open sub-question for the ruling: what the driver wrapper emits for a re-hearing (a `transmitted` record referencing the *existing* hearer belief keeps the feed honest without new schema). The alternative — keep the raise and rewrite the test — retires rule-7 exposure counting in practice; the worker's position is that would be a real behavioral regression of an accepted Lane-4 feature.

## Findings (packet's expected four + new)

1. **§7 line 125 stale "trust-source" wording — confirmed.** scenario-ladder.md:125 still says "T2.3 resolution policy: trust-source with strength tiebreak" against the v0.4 evidence-type-ordering amendment. Frozen doc; noted only.
2. **Undocumented `"corroborated"` evidence-type string — confirmed.** `Evidence`'s docstring (claims.py) lists `"witnessed" | "reported"`; `corroborate()` appends `"corroborated"`. Not "fixed" in passing, per the packet. `resolve()`'s appended hearing uses `"reported"`, consistent with the documented two.
3. **propagate.py caller-supplies-context attribution — confirmed with nuance.** The ladder's "the caller-supplies-context pattern propagate.py already uses" is loosely attributed: propagate.py's lookups take the ClaimStore directly and carry no caller-supplied domain data; the pattern's canonical instances are `driver.py`'s `mutation_candidates` and `social.py`'s `form_grudge` lookup discipline. No code issue.
4. **`nothing_salient` reason enum — confirmed as a gloss gap, not a wrong value.** Post-lane, `"both-informed"` means "both hold and content *agrees*" (conflicts now produce `supersession`). The enum string remains accurate for its narrowed meaning; §4:118's gloss references only `teller_and_hearer()` and predates `conflicting_pair()`. Coordinator-owned doc; noted.
5. **New — T2.2's run now resolves *heavily*.** Re-running `scenarios/test_tier2_mutation.py` (green; goldens unmoved — they pin the first two auto-ids, which precede any divergence): the 10-day tavern run now emits **2,880 supersession records** vs. 7 transmitted (previously those encounters declined as `nothing_salient`). Consequences to weigh: (a) trace volume roughly doubles-to-triples on contention-heavy runs — relevant to the outstanding ui-spec §1.1 trace-volume figure; (b) the pinned semantics make a badgered holder's confidence dent *every* encounter (rung test asserts the compounding); the rulings never discussed repeat challenges by the same pair; (c) mutation-heavy casts now generate constant contention churn. This is the literal implementation of the pins, not a deviation — surfaced because the magnitude only became visible at run scale.
6. **New, cosmetic — CLI null rendering.** `cli.py`'s supersession line prints `None` for a null variant id ("superseded by None"). Suggest `(original telling)` when someone next owns cli.py; do-not-touch per this packet.

## Awaiting

Coordinator disposition of Conflicts 1–2; both are one-ruling fixes. On either disposition the worker applies it and re-runs the battery; nothing else in the lane is known-open.

---

## Addendum — dispositions applied (2026-08-23, same day)

Both dispositions from `overseer-review.md` are applied; battery re-run:
**183 passed, 0 failed, 0 xfailed; `uv run ruff check .` clean.** (The
overseer's target was 182; the +1 is the re-hearing semantics getting its
own test function — `test_t23_same_content_retell_is_a_rehearing` — while
the raise test kept its name and its three remaining raise cases.)

- **Conflict 1:** the stale unit test is rewritten and renamed —
  `test_disagreeing_second_witness_produces_a_variant_never_rewrites_claim`
  asserts the T0.4 path (Variant produced, rooted at the claim,
  `mutated_slot` named, canonical slots asserted unchanged twice). Its
  original intent is preserved verbatim in the assertions.
- **Conflict 2:** the re-hearing carve-out is in. `retell()` on an informed
  hearer now never raises: differing content → `resolve()`; same content →
  re-hearing (mints nothing, records hearing + telling, returns the
  existing records). The scripted wrapper emits `transmitted` referencing
  the existing variant/hearer-belief ids, at the telling's own gamets (not
  the variant's creation tick), with `teller_id` from the teller's belief
  (the returned grounding evidence's `source_id` names the *original*
  teller — wrong for a re-hearing). The conflicted Lane-4 test passes
  unchanged.
- **Two guard rails added in the same seam** (documented here since the
  disposition text didn't name them): scripted `retell` that routes to
  resolution raises `TypeError` directing the caller to `driver.resolve()`
  (a store-level resolution without its supersession record would break
  the trace-is-the-artifact discipline); and the one unruled corner — a
  scripted re-hearing of content the hearer holds as the un-varianted
  original telling (variant `None`) — raises a clear error rather than
  emitting a `transmitted` record with no variant to reference. Surface
  for a future ruling if a scenario ever needs it.
- **Replay parity for re-hearings** is covered by the conflicted Lane-4
  test itself (live-vs-reconstructed snapshot equality across a keyframe),
  now green.
