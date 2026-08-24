# Lane 49 delivery report — T6 north-star composition test

**Delivered:** `ccd3afc` — `chronicle/fixtures/north_star.py` (new),
`scenarios/test_north_star.py` (new), `scenarios/run_north_star_demo.py`
(new). No engine files touched; `carrier_schedule.py` and
`whiterun_relationships.py` were left completely unedited (the packet
permitted extending them, but composing over them unedited from the
new fixture module was both sufficient and lower-risk — zero chance of
disturbing lane 13's or the jarl-death scenarios' existing assertions,
since I never touch their source).

## Acceptance, per criterion

- **`uv run pytest -q` green (240 + new tests), ruff clean.** ✓ — 242
  passed, 0 failed, 0 xfailed (240 prior + 2). `uv run ruff check .`:
  clean.
- **The four beats pass as automated assertions; the test fails loudly
  if any mechanism doesn't compose.** ✓ — `test_north_star_composition`
  asserts, in one run:
  1. **Succession** — `jarl_of_whiterun` resolves to `irileth`
     immediately on death (rule 19, no tick loop needed), ranked from
     the *unedited* `whiterun_relationships.py` court edges
     (irileth 0.95 > proventus 0.85); `steward_of_whiterun` (Proventus)
     is untouched — a second role, same institution, no interference.
  2. **Grief/grudge** — two independent `schedule_rewrite` overlays
     (one per household kin, not one shared event — "his household
     mourns on their calendars," plural), both to the temple; each kin
     holds a grudge whose `source_belief_id` is their own death belief.
  3. **The rumor** — at least one Markarth resident's evidence chain
     names the caravaneer *and* carries a weapon slot mutated from the
     original ("a dagger" → "a poisoned blade" at the seed this test
     pins) — asserted by walking `chain_for()`, not just checking belief
     existence.
  4. **The ripple** — a test-side aggregate function computes negative
     sentiment over `reputation_updated` records for two populations
     (the guard, the market cast); asserted non-`None` for both, backed
     by real rows in the trace, and checked architecturally read-only
     (`"aggregate" not in inspect.getsource(chronicle.rules)`).
  A second test regenerates the whole composition twice independently
  and asserts byte-identical events/trace streams (modulo `wall_ts`).
- **`runs/north-star-01` exists with the walkthrough beats present,
  CLI-verified.** ✓ — generated via
  `scenarios/run_north_star_demo.py`; CLI-inspected:
  ```
  $ CHRONICLE_RUNS_DIR=runs uv run python -m chronicle inspect north-star-01 irileth --at 240
  -- beliefs (1) --
    belief belief-irileth-death
      claim       : claim-balgruuf-assassination (npc_death) slots={...}
  -- relationships held (1) --
    -> jarl_balgruuf basis=shared_employer strength=0.9500
  ```
  ```
  $ CHRONICLE_RUNS_DIR=runs uv run python -m chronicle trace north-star-01 claim-balgruuf-assassination --at 240 | grep -A2 "markarth_resident_3:"
  holder markarth_resident_3:
    proventus (belief belief-proventus-death, confidence stored 0.9500) <- witnessed via proventus
    caravaneer (belief belief-auto-caravaneer-4, confidence stored 0.7600) <- reported via proventus
  ```
  The producer's own smoke check also passes: `jarl succeeded by:
  irileth`, `priest ever informed: True`, `Markarth's mutated belief(s):
  [('markarth_resident_3', 'a poisoned blade')]`.
- **No new RNG purposes; no schema edits; no new rules.** ✓ — `git
  diff chronicle/rng.py docs/frame-log-schema.md chronicle/rules.py`
  for this lane is empty. The rule budget stays at 19/19 live, 0 new.
- **Determinism.** ✓ — the test's own two-regeneration check, plus an
  independent verification for the demo producer: two runs into fresh
  `mktemp -d` `CHRONICLE_RUNS_DIR`s, diffed with `wall_ts` masked —
  `events.jsonl` 15==15, `trace.jsonl` 10326==10326, byte-identical.

## What was built

`chronicle/fixtures/north_star.py` composes three existing, unedited
sources: `carrier_schedule()` (the cross-hold backbone, lane 13),
`seed_whiterun_via_driver()` (the court/tavern relationship edges,
unedited), and two things genuinely new (per the design doc's own
finding that most of the north star was already built): household
kinship edges (`frothar`/`nelkir` → `jarl_balgruuf`) and a
temple/priest. `build_driver(run_id, seed_id, ...)` is the single entry
point both the test and the demo producer use — one fixture, one
run-length knob (the caller decides how many ticks to actually run;
the schedule itself always spans the full window). Two `Role`s
(`jarl_of_whiterun`, `steward_of_whiterun`) share the `whiterun_court`
institution, exercising Tier 5's mechanism at two scales in one
fixture per the ruled O4.

`scenarios/test_north_star.py` scripts the assassination (an `NPCDied`
witnessed by the household, the court, and the guard, each carrying an
explicit `weapon`/`killer` slot) and asserts the four beats above.
`scenarios/run_north_star_demo.py` is the same script wrapped as a
producer, at the full `carrier_schedule.END_TICK` (240-tick) window,
for the M7 stranger walkthrough.

## Findings

1. **The seed had to be worker-chosen and verified, same as
   `run_carrier_demo.py`'s precedent.** `_decide_mutation`'s rolls are
   genuinely probabilistic; I scanned several candidate `seed_id`
   values and picked `"north-star-2"`, the first that reliably produces
   a mutated variant reaching Markarth through the caravaneer. Recorded
   directly in both the test and the producer's source, with the
   reasoning inline, not just in this report.
2. **No edits to `carrier_schedule.py`/`whiterun_relationships.py` were
   needed.** The packet permitted extending them ("extension only");
   composing over them unedited from the new module turned out to be
   sufficient for every beat this lane needed, and it means `git diff`
   for this lane touches zero pre-existing fixture files — the lowest-
   risk way to guarantee lane 13's and the jarl-death scenarios' own
   assertions can't have been disturbed (verified anyway: full battery
   green, including `test_tier2_carrier.py` and
   `test_jarl_death_social_cascade.py`).
3. **The double-role-holding question Tier 5's design doc flagged as
   deferred (O4 there) surfaced here in exactly the shape predicted**:
   Proventus is simultaneously the sitting Steward and a (losing)
   candidate for Jarl succession, and nothing needed to special-case
   this — he simply loses to Irileth's higher relationship strength
   while his own Steward role is never even evaluated (he never died).
   No engine gap; confirms the deferral was safe.
4. **The aggregate's "read-only" check is a source-grep, not a runtime
   proof.** `"aggregate" not in inspect.getsource(chronicle.rules)` is
   cheap and catches the obvious failure mode (a rule literally reading
   an aggregate value), but a rule could in principle read something
   aggregate-shaped under a different name. Flagging as a known
   limitation of this specific check, not a claim that it's exhaustive
   — a stronger architectural test is a possible M6+ refinement, not
   blocking this lane.
