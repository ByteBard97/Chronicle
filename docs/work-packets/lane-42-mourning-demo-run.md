# Lane 42 — mourning demo run producer (Track A, small)

**Status:** Ready to start immediately. The schedule-diff view (lane
41) needs a run containing `schedule_rewrite` events; today only the
rung tests (tmp dirs) produce them.

**Effort:** small (producer script + generation + verification).

## Context

Same shape as lanes 17/29's producers (`scenarios/run_carrier_demo.py`,
`scenarios/run_tier3_demo.py`), but exercising rule 17: a kin dies, the
mourner reroutes to the temple, the rumor travels *through the changed
co-presence graph* — the T4a.2 narrative as a watchable demo.

## Read first

- `scenarios/test_tier4a_mourning.py` + `test_tier4a_counterfactual.py`
  — the fixture shapes (kinship edge, `mourning_triggers`, mourning
  location/duration, the deceased-naming slot discipline from F3/O1).
- `scenarios/run_tier3_demo.py` — the producer idiom.
- `docs/work-packets/reviews/README.md` — governance.

## Pinned decisions

- **Run id `mourning-demo-01`**, deterministic seed, fresh dir.
- **One mourning household** (2+ kin), a priest at the temple, a market
  crowd; the death is witnessed and the rumor propagates — the demo
  shows the priest hearing *because* of the reroute (the T4a.2
  narrative, as a demo).
- **Mourning duration long enough to span several encounter days**
  (the point is watching the reroute matter; 72+ ticks).
- No engine changes; the `mourning_triggers` mapping + kinship fixture
  are caller-supplied per the landed rule-17 mechanism.

## Task

1. `scenarios/run_mourning_demo.py` (producer, not a test).
2. Generate `runs/mourning-demo-01/`; verify via CLI: the
   `schedule_rewrite` event exists with the right fields; the mourner's
   encounters move to the temple during the window; restoration after
   `end_tick`; the priest is informed and the chain shows the reroute
   path. Report output tails.
3. Determinism: double-regeneration, diff modulo `wall_ts`.
4. Suite green.

## Acceptance

- The run exists with the smoke facts above, CLI-verified.
- Determinism verified.
- `uv run pytest -q` green, ruff clean.

## File boundaries

**Create:** `scenarios/run_mourning_demo.py`, `runs/mourning-demo-01/`
(generated)

**Do not touch:** everything else.

## Conventions

- **Local commits OK** (path-scoped); never push.
- File a delivery report on disk.
