# Lane 4 — M0: frame-log substrate (Track A)

**Status:** BLOCKED until Lanes 1–3 land (ADR-0009, frame-log schema v1,
ADR-0010). Do not start early — this lane implements what they decide.
**Effort:** large. This is the dashboard's foundation.

## Context

`chronicle/` today is pure-function stores (`events`, `claims`, `social`,
`propagate`, `schedule`) driven directly by scenario tests. There is no tick
loop, no log writer, no trace. This lane builds all three per
`docs/dashboard-build-plan.md` §2 M0.

## Read first (in order)

1. `docs/ui-spec.md` §1.1–§1.3 (the frozen contract you implement).
2. `docs/frame-log-schema.md` (Lane 2 — your payload spec).
3. `docs/decisions/0009-keyed-randomness.md` (Lane 1 — your RNG interface).
4. `docs/decisions/0010-tick-quantum.md` (Lane 3 — units).
5. `docs/dashboard-build-plan.md` §2 M0 (acceptance criteria — they are
   yours, verbatim).
6. `chronicle/` (all of it) and `scenarios/` (the three existing tests are
   your M0 acceptance drivers).

## Task

1. **`chronicle/driver.py`** — the tick loop: advance tick, sample
   encounters, apply retellings/decay/thresholds, emit records. Shape it
   from the start for **start-from-keyframe + injected events** (the
   deferred fork milestone needs it; shaping now is cheap, retrofitting is
   not). Refactor the three existing `scenarios/` tests to run through the
   driver — **their assertions must not change**.
2. **Keyed RNG** in `chronicle/schedule.py`'s `sample_encounters()` per
   ADR-0009 (interface change: callers pass `seed_id`, not `rng`). Update
   call sites; keep scenario tests green (their determinism guarantee is
   preserved by keying, not by stream order). **Warning:** keying changes
   roll *values*, not just their independence — the sampled encounter
   pattern in `test_jarl_death_encounter_driven_propagation.py` will differ
   from the sequential-stream pattern. If an assertion flips for this
   reason, report it to the coordinator — do not edit the test or tune the
   seed to force green.
3. **`chronicle/framelog.py`** — writer + reader, per the schema doc:
   - Writer: `runs/<run_id>/` with `events.jsonl` / `trace.jsonl`,
     `index.json` (tick → byte offset per stream + keyframe offsets)
     written incrementally with **atomic write-temp-rename**, keyframes
     every K ticks (default one game-day = 24 ticks), newline framing,
     **flush after every tick's record batch** (the liveness contract from
     the schema doc — LIVE tailing latency is polling cadence, not buffer
     length), run
     registered in `runs/index.json`. `runs/` path overridable via
     `CHRONICLE_RUNS_DIR`.
   - Reader: random access to derived state at any T from log alone
     (nearest keyframe + replayed deltas + analytic decay at read time —
     decay is closed-form, `claims.py:71`; never sample histories into the
     log).
4. **Measure trace volume** on a 25-NPC 10-game-day-equivalent run and
   report the exact row count (the coordinator records it into ui-spec
   §1.1 as it requests).

## Acceptance (from the plan, verbatim)

- The three existing `scenarios/` tests emit frame logs when run through
  the driver — and stay green with unchanged assertions.
- Reader reconstruction at arbitrary T matches the in-memory run exactly.
- Scanning the streams rebuilds an identical `index.json` (index is pure
  acceleration — ui-spec §1.1 three-things rule).
- `uv run pytest` green; `uv run ruff check .` clean.

## File boundaries

- **Create:** `chronicle/driver.py`, `chronicle/framelog.py`,
  `chronicle/rng.py` (per ADR-0009 — the keyed-roll choke point), new tests
  under `chronicle/tests/` as needed.
- **Edit:** `chronicle/schedule.py` (RNG rework), `scenarios/` (driver
  rewiring only — no assertion changes), `.gitignore` (`runs/`).
- **Do not touch:** `chronicle/claims.py`/`social.py` logic (Lane 3 owns
  the constants; if you find a logic bug, report it, don't fix it),
  `dashboard/` (Lane 5's), frozen docs, `docs/frame-log-schema.md` (gaps
  → report to coordinator, don't edit).

## Conventions

- Do **not** `git commit` — the coordinator commits.
- Follow existing code style: dataclasses, type hints, docstrings citing
  spec rules where applicable.
