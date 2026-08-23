# Lane 19 — Tier 3 L-A: rule-registry core (Track A, sim substrate)

**Status:** Ready to start immediately. The design is accepted and ruled
(`docs/design/tier-3-rule-registry-and-tell-decision.md`, overseer review
in `docs/work-packets/reviews/2026-08-23-lane-18/` — read both before
coding; decisions R1–R3 and R12 are your spec). Lane 20 (grudge decay,
`social.py`) runs alongside — disjoint files. This lane is the critical
path for L-C through L-F.

**Effort:** medium (new module + driver hooks + tests).

## Context

Tier 3's forced machinery: rules become named, toggleable,
trace-instrumented objects (ladder §8 consequence b), with the ten
implemented rules retro-registered and tiers 0–2 scenarios becoming
regression cases by default-on migration. The design doc's R1–R3 are
ruled and final; this packet pins the remaining implementation surface.

## Read first (in order)

1. `docs/design/tier-3-rule-registry-and-tell-decision.md` §1 (R1–R3)
   and §7 (R12) — the ruled design. Deviations come back as findings.
2. `docs/frame-log-schema.md:122` — the `rule_evaluated` record shape
   (`rule`, `inputs`, `fired`, `result`). Emit this exactly.
3. `chronicle/driver.py` — the hook sites: scripted wrappers (`:197`
   witness, `:232` retell, `:295` corroborate, `:314` resolve), mutation
   (`:563` `_decide_mutation`), the encounter sampler (`:486-511`), and
   the ctor (`:120-172`) where the registry lives.
4. `chronicle/claims.py` `stage_at` — rules 9–10's home (the stage
   machine is wrapped, not moved).
5. `chronicle/framelog.py` — how trace records are written/replayed;
   `rule_evaluated` rows are trace-only derivations (no keyframe state,
   no replay effect — verify the reader tolerates them, lane 11
   precedent: unknown record types are skipped).
6. `docs/work-packets/reviews/README.md` — governance; local commits
   fine (path-scoped), never push.

## Pinned implementation decisions (coordinator-set, 2026-08-23)

- **Module:** new `chronicle/rules.py`. `Rule` protocol per R1 (name
  from the §8 table string, tier, `evaluate(ctx) -> result | None`).
  The registry is constructed in `Driver.__init__` alongside the stores.
- **Toggle:** construction-time only — `disabled_rules: Collection[str]
  = ()` on `Driver.__init__`. Default all-on. Rules 11–19 register as
  **disabled stubs** from day one (R12) — they exist by name so the
  registry lists all 19, but emit nothing and run nothing.
- **Emission (R3's ruled contract):** every evaluation emits
  `rule_evaluated`, fired or not, with current accumulator values in
  `inputs`. A disabled rule emits nothing. `inputs` is caller-assembled
  context — rules never query stores themselves.
- **Retro-registration is by wrapper (R2):** thin `Rule` objects invoked
  at the existing call sites named in the design doc. **No refactoring
  of `claims.py`/`social.py` internals** — rules 9–10's wrapper lives at
  the `stage_at` call boundary you judge cleanest; if wrapping stage_at
  without touching claims.py proves awkward, that's a finding with a
  proposed minimal seam, not a license to refactor.
- **No behavior change.** Default-on means the 186-test battery passes
  untouched. If any existing test changes its outcome, the wrapper is
  wrong, not the test.

## Task

1. `chronicle/rules.py`: `Rule` protocol, `RuleContext`/`RuleResult`
   types, the registry (register/get/enabled, disabled-set handling).
2. Driver wiring: construct the registry in `__init__` (with
   `disabled_rules`); add the emission path (a `_emit_rule_evaluated`
   helper in the scripted-wrapper idiom).
3. Retro-register rules 1–10 as wrappers at the R2 call sites; register
   11–19 as disabled stubs.
4. Tests (`chronicle/tests/test_rules.py`):
   - every evaluation emits `rule_evaluated` with the schema fields,
     fired or not;
   - a disabled rule emits nothing and doesn't run;
   - all 19 §8 names are registered (1–10 enabled, 11–19 stubbed);
   - an existing scenario (one Tier-1 or Tier-2 test) shows
     `rule_evaluated` rows in its trace with no assertion changes;
   - `uv run pytest -q` fully green with zero edits to existing tests.

## Acceptance

- `uv run pytest -q` green (186 + your new tests), `uv run ruff check .`
  clean.
- `rule_evaluated` records match schema §4:122 field-for-field.
- No behavior change: the existing suite passes unedited.
- No new RNG purposes; no schema edits; no frozen-doc edits.

## File boundaries

**Create:** `chronicle/rules.py`, `chronicle/tests/test_rules.py`

**Edit:** `chronicle/driver.py` (registry construction, hooks, emission
helper)

**Do not touch:** `chronicle/social.py` (lane 20), `chronicle/claims.py`
(wrap at boundaries; awkwardness is a finding), `chronicle/rng.py`,
frozen/coordinator docs, `scenarios/`, `dashboard/`, `runs/`

## Conventions

- Match the driver/claims idiom: named constants, docstrings naming the
  rule numbers, no ad-hoc literals.
- **Local commits OK** (path-scoped, explicit adds); never push.
- Existing test assertions immutable; conflicts are findings.
- Report format: what you delivered, acceptance per criterion with
  command tails, findings list.
