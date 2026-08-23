# Lane 3 — Tick quantum + constant rebaseline

**Status:** Ready to start. No dependencies (coordinate output with Lane 2's
schema doc — the quantum is recorded there). Deliverable is a decision note
plus a constants-only diff.
**Effort:** small-to-medium. The decision is easy; the rebaseline needs care.

## Context

The sim's time constants are **placeholder numbers with no physical unit**:
the schedule fixture uses quantum-agnostic bare ints
(`start_tick=0, end_tick=200`, `chronicle/fixtures/whiterun_schedule.py`),
and `chronicle/claims.py:57–67` defines
`CONFIDENCE_DECAY_HALF_LIFE = 500`, `VERBATIM_DECAY_HALF_LIFE = 200`,
`GIST_DECAY_HALF_LIFE = 2000`, `RUMOR_DORMANT_AFTER = 5000` — all in "ticks"
of undefined duration. The dashboard build plan (prerequisite 4) proposes a
**one game-hour tick quantum** — on its own merits: it aligns ticks with
game-days (24-tick keyframe cadence), keeps durations human-readable
("D11 06:20"), and caps trace volume. **Do not cite the fixture as
evidence for the quantum** — it isn't: its blocks are scaffolding sized to
scenario tick ranges (court scene `0–200`, Hulda `0–1000`), and its
docstring explicitly disclaims schedule realism ("not an attempt at a
complete Whiterun daily routine… a math-tier data concern"). At an
hour-quantum those blocks read as an 8-day court gathering and a 41-day
tavern shift — semantically odd, but functionally fine: the scenarios run
fixed tick ranges and the fixture covers them. **The fixture stays as-is;
a realistic daily-routine fixture is math-tier work, out of scope for every
current lane.** If you believe the quantum *forces* a fixture change, stop
and report it to the coordinator — no lane owns that file, and that's
deliberate.

That decision re-baselines every time constant — several placeholders will
turn out to be wrong in real units (e.g., 5,000 hours ≈ 208 days to
dormancy; is that intended?).

## Read first (in order)

1. `docs/dashboard-build-plan.md` §1 prerequisite 4.
2. `chronicle/claims.py` (the decay/dormancy constants and their comments),
   `chronicle/fixtures/whiterun_schedule.py` (the fixture ranges), and
   `scenarios/` (durations the tests exercise — e.g. 30/90-quiet-day runs).
3. `docs/v0.1-spec.md` rules 5/6/16 (the design intent behind decay and
   dormancy — the rebaseline must preserve intent, not numbers).

## Task

1. **Decision note** (`docs/decisions/0010-tick-quantum.md`, ADR format —
   see any existing ADR): one tick = one game-hour. Record the quantum, and
   the rebaselined constants with their derivations (e.g., "rumor dormancy
   after ~N quiet days → 24N ticks"). Where a placeholder looks wrong in
   real units, pick the value that matches the v0.1 spec's intent and say
   so explicitly.
2. **Constants diff:** update the values in `chronicle/claims.py` (and any
   other module constants that are time-denominated — grep for them) with
   comments naming the unit and derivation. **Logic must not change —
   constants only.**
3. Report the resulting ticks-per-10-game-days figure (240 at the proposed
   quantum) so Lane 2/M0 can sanity-check trace-volume estimates.

## Acceptance

- `uv run pytest` stays green. **If a scenario test encodes a timing
  assumption the rebaseline invalidates, do not edit the test to fit —
  report it**; test-expectation changes are a coordinator decision.
- `uv run ruff check .` clean.
- Every changed constant has a comment: unit + derivation + spec rule
  reference.

## File boundaries

- **Create:** `docs/decisions/0010-tick-quantum.md`.
- **Edit (constants only):** `chronicle/claims.py`, other `chronicle/`
  modules' time-denominated constants. Do not touch logic, fixtures, or
  tests.
- **Do not touch:** frozen docs (`ui-spec.md`, `scenario-ladder.md`,
  `ui-doctrines.md`), `docs/frame-log-schema.md` (Lane 2's — send the
  coordinator your quantum note for it).

## Conventions

- Do **not** `git commit` — leave changes for the coordinator.
