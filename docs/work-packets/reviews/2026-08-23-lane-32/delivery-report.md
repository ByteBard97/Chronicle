# Lane 32 delivery report — cli.py hygiene (Tier 2/3 record vocabulary)

**Delivered:** `59c2047` — `_FEED_RECORD_TYPES` brought current with schema
§4 (lanes 12–26), the `trace` supersession filter fixed per lane-17
finding 1, and a regression test that reproduces the exact under-report
case and is verified to fail without the fix.

## Acceptance, per criterion

- **`uv run pytest -q` green (205+), ruff clean.** ✓ — 206 passed (205 +
  1 new), 0 failed, 0 xfailed. `uv run ruff check .`: clean.
- **`feed`/`trace` verified against `tier3-demo-01` with output tails;
  the under-reported supersession case now listed, covered by test.**
  ✓ — `feed`, all 12 vocabulary types present in that run render without
  crashes or drops:

  ```
  $ CHRONICLE_RUNS_DIR=runs uv run python -m chronicle feed tier3-demo-01 --limit 0 | awk '/^tick/{print $5}' | sort | uniq -c
      308 encounter_rolled
        1 escalation_warning
        1 grudge_formed
     2098 nothing_salient
        2 obligation_issued
        2 obligation_resolved
        1 relationship_formed
        5 reputation_updated
      165 rule_evaluated
        1 threshold_crossed
       44 transmission_declined
       14 transmitted
  ```

  `tier3-demo-01` has no `supersession`/`mutation_applied` records (it's a
  Tier-3 cast, not Tier-2 mutation/resolution), so those two are verified
  instead against `runs/carrier-mutation-01` (lane-17's demo run, still on
  disk — `runs/` is gitignored but not deleted):

  ```
  $ CHRONICLE_RUNS_DIR=runs uv run python -m chronicle feed carrier-mutation-01 --limit 0 | awk '/^tick/{print $5}' | sort | uniq -c
     2228 encounter_rolled
        1 mutation_applied
      814 nothing_salient
        7 supersession
        7 transmitted
  ```

  `trace` against the same run's contested claim, before the fix this
  listed 4 of 7 supersessions (the lane-17 report's own number); after:

  ```
  $ CHRONICLE_RUNS_DIR=runs uv run python -m chronicle trace carrier-mutation-01 claim-market-murder --at 30 | sed -n '/supersessions involving/,$p'
  -- supersessions involving this claim's variants (7) --
    tick 26: relief_caravaneer -- variant-auto-1 superseded by variant-auto-4 via evidence-type-ordering+v1 (confidence_dent=0.1)
    tick 27: relief_caravaneer -- variant-auto-3 superseded by variant-auto-4 via evidence-type-ordering+v1 (confidence_dent=0.1)
    tick 27: relief_caravaneer -- variant-auto-1 superseded by variant-auto-4 via evidence-type-ordering+v1 (confidence_dent=0.1)
    tick 27: ysolda -- variant-auto-2 superseded by variant-auto-4 via evidence-type-ordering+v1 (confidence_dent=0.1)
    tick 28: relief_caravaneer -- variant-auto-4 superseded by (original telling) via evidence-type-ordering+v1 (confidence_dent=0.1)
    tick 28: ysolda -- variant-auto-3 superseded by variant-auto-4 via evidence-type-ordering+v1 (confidence_dent=0.1)
    tick 28: ysolda -- variant-auto-4 superseded by (original telling) via evidence-type-ordering+v1 (confidence_dent=0.1)
  ```

  All 7 now present, including both null-winner rows. Covered in-repo by
  `test_trace_lists_a_supersession_whose_loser_is_held_by_nobody`
  (`chronicle/tests/test_agent_debug_cli.py`) — a minimal two-NPC repro of
  the same mechanism (a `resolve()` that re-points the loser's only
  holder off its variant). Confirmed the test actually exercises the bug:
  stashed the `cli.py` fix and re-ran just this test — it fails
  (`0 supersessions`) without the fix, passes with it.

- **No schema/frozen-doc edits; boundaries respected.** ✓ — only
  `chronicle/cli.py` and `chronicle/tests/test_agent_debug_cli.py`
  touched, per the packet's file boundaries.

## What changed

1. `_FEED_RECORD_TYPES`: added `supersession`, `mutation_applied`,
   `transmission_declined`, `rule_evaluated`, `threshold_crossed`,
   `grudge_formed`, `reputation_updated`, `obligation_issued`,
   `obligation_resolved`, `relationship_formed`, `escalation_warning`.
2. `feed_command` now reads both `EVENTS_STREAM` and `TRACE_STREAM`
   (needed for `escalation_warning`, which is an event, not a trace
   record — schema §3:95 vs §4) via a new `_feed_type()` helper that
   checks `record_type` then `event_type`. Merge order is `(tick, stream,
   seq)` — events and trace keep independent `seq` counters, so at a tick
   where both streams produced rows the cross-stream order is
   deterministic but best-effort, not a causal guarantee. Documented in
   the docstring.
3. `trace`'s supersession filter: replaced the currently-held-variant set
   with the claim's full variant lineage (`state.claims._variants`,
   append-only — never pruned) unioned with `{None}` for the canonical
   telling, **and** added an explicit `claim_id` equality check on the
   payload (the record already carries `claim_id` directly — a cheaper
   and more precise filter than variant-membership alone; kept both
   since the variant check is what the packet named and the claim_id
   check is strictly additive precision, not a behavior change for any
   passing case).

## Findings

1. **The claim_id check is technically beyond the packet's literal "union
   over variant lineage" wording.** It's the more direct fix (the
   supersession payload already names its claim), and it's a no-op for
   every case the variant-lineage fix already covers (a record naming
   this claim's variants necessarily has this claim's claim_id) — flagged
   for the record, not because I think it changes any test's outcome.
2. **`_NPC_FIELDS` extended** with `target_id`/`observer_id`/`subject_id`/
   `issuer_id`/`debtor_id`/`beneficiary_id`/`from_id`/`to_id` — the
   Tier-3 record types' entity slots. Not explicitly asked for, but
   "verify feed renders each type... sensibly" reads as covering
   `--npc` filtering too; without this, `feed --npc <name>` would
   silently drop a `grudge_formed`/`reputation_updated`/`obligation_*`/
   `relationship_formed` row naming that NPC only in one of these fields.
   Mechanical, in-boundary (`cli.py` only), no existing test's expectation
   changed.
3. **`runs/carrier-mutation-01` and `runs/tier3-demo-01` are both still on
   disk** (`.gitignore:18` ignores `runs/`, as lane-17 already flagged) —
   used both for verification per the packet's "read first" list; neither
   was modified.
