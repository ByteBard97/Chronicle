# Lane 17 — delivery report (carrier+mutation demo run + CLI supersession polish)

Worker: Kimi (Track A). Packet: `docs/work-packets/lane-17-carrier-mutation-demo-run.md`.
No commits made; boundaries respected (created `scenarios/run_carrier_demo.py` +
`runs/carrier-mutation-01/`; edited `chronicle/cli.py` + `chronicle/tests/test_agent_debug_cli.py` only).

## What was delivered

1. **`scenarios/run_carrier_demo.py`** — producer over `carrier_schedule()`,
   jarl-demo idiom: tick-0 murder at the Whiterun market (victim
   `whiterun_merchant`, not a cast member — every scheduled NPC stays alive,
   the T2.6 shape), witnessed by `belethor`; `driver.run(0, END_TICK)`;
   prints record counts by type for both streams. Parameters per the pins:
   `seed_id="carrier-mutation-demo"`, `encounter_probability=0.35`,
   `mutation_candidates` registered in the T2.2 mapping shape
   (perpetrator/cause/location, lore-flavored values).
2. **`runs/carrier-mutation-01/`** — generated once (the dir did not exist;
   no deletion of any kind was needed or performed).
3. **CLI polish** — `chronicle/cli.py`'s supersession line now renders a
   null variant id as `(original telling)` (both loser and winner fields;
   lane-12 finding 6). No other engine changes.
4. **Test** — `test_trace_supersession_renders_a_null_variant_id_as_the_original_telling`
   in `chronicle/tests/test_agent_debug_cli.py`: its own tiny run (the
   shared `run_dir` fixture produces zero supersessions, so extending it
   would have shifted ~10 other tests' expectations — see finding 1 in my
   pre-build review). Scripted mutated retell + repelled challenge →
   winner_variant_id None; asserts `variant-gossip superseded by (original
   telling)` and that `None` appears nowhere in the trace output.

## Acceptance status

- **Run exists with smoke facts, verified via CLI:**
  - Record counts (producer output tail):
    ```
    events.jsonl: 12 records
      crime_witnessed: 1
      keyframe: 10
      npc_died: 1
    trace.jsonl: 3058 records
      belief_formed: 1
      encounter_rolled: 2228
      mutation_applied: 1
      nothing_salient: 814
      supersession: 7
      transmitted: 7
    ```
    `mutation_applied` 1 > 0 ✓; `supersession` 7 > 0 ✓ (churn far below the
    T2.2 precedent's 2,880 — smaller cast, p=0.35; counts reported, dynamics
    untouched).
  - Markarth-resident beliefs exist ✓ — `inspect carrier-mutation-01
    markarth_resident_1` shows belief `belief-auto-markarth_resident_1-12`,
    `last_rehearsed=96.0` (the caravaneer's exact Markarth arrival tick),
    rumor stage `heard`.
  - Caravaneer in Markarth chains ✓ — `trace carrier-mutation-01
    claim-market-murder`: all three Markarth residents' chains pass through
    `caravaneer` ("reported via caravaneer").
- **Determinism verified** ✓ — regenerated twice into fresh temp
  `CHRONICLE_RUNS_DIR`s (`mktemp -d`), diffed with `payload.wall_ts` masked
  (the harness's rule): events 12==12, trace 3058==3058, byte-identical
  modulo `wall_ts`. PASS.
- **Battery** ✓ — `uv run pytest -q`: **186 passed, 0 failed, 0 xfailed**
  (185 + 1 new CLI test). `uv run ruff check .`: clean.
- **Scope** ✓ — no engine changes beyond `cli.py`'s rendering fix; no
  fixture edits; no scenario-test edits; `runs/whiterun-jarl-01` untouched.

## Findings

1. **trace's supersession filter under-reports for this run.** `cli.py:361`
   filters supersessions to variants in `variant_ids`, which is built from
   beliefs *held at the inspection tick*. 3 of this run's 7 supersessions —
   including both null-winner ones (tick 28, loser `variant-auto-4` → winner
   None) — are invisible at every `--at`, because the moment the loser
   re-points to the original telling, `variant-auto-4` is held by nobody and
   drops out of the filter. The dashboard lanes (16/18) read raw trace
   records and are unaffected; this is CLI-view completeness only. Fixing
   the filter is outside this lane's boundary ("the null-variant rendering
   only"), so I'm reporting it: candidate for a future cli.py hygiene lane
   (e.g. union over the claim's known variant lineage instead of
   currently-held variants).
2. **The packet's integration note is stale on one mechanism:** it says the
   coordinator "commits" `runs/carrier-mutation-01/` at integration, but
   `.gitignore:18` ignores `runs/` (zero run files tracked today;
   `whiterun-jarl-01` is also local-only). The run is on disk where the
   dashboard's `CHRONICLE_RUNS_DIR` mechanism reads it; if integration wants
   it in git it needs a force-add or a gitignore exception. No action taken
   — flagging so integration doesn't assume a commit can pick it up.
3. **Seed was worker-chosen, as flagged pre-build:** `carrier-mutation-demo`
   satisfied all smoke facts on the first attempt; no seed-shopping occurred.
   The seed is a named constant in the producer for the coordinator to re-pin
   if desired.
