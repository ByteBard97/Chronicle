# Lane 20 — Tier 3 L-B: grudge decay (Track A, sim substrate)

**Status:** Ready to start immediately. Design accepted and ruled
(`docs/design/tier-3-rule-registry-and-tell-decision.md` §3, R7 — read
it first). Lane 19 (registry core, `driver.py`/`rules.py`) runs
alongside — disjoint files (`social.py` is yours). Small lane.

**Effort:** small (one function + constants block + unit tests).

## Context

Grudge decay is "the missing twin of belief decay" (Tier 3 intro).
`Grudge` already carries `emotional_strength`/`evidentiary_strength`/
`last_rehearsed`/`forgiveness_threshold` (`social.py:100-118`). The
ruled design (R7): decay-at-read via a pure `grudge_at(grudge, gamets)`
sibling to `claims.py`'s `stage_at()`, applying `claims._decay` from
`last_rehearsed`. No new records, no mutation — state is derived, not
destroyed.

**Constants (ruled 2026-08-23, tunable-not-derived placeholders — owner
delegated):**

| Constant | Value | Note |
|---|---|---|
| `GRUDGE_EMOTIONAL_HALF_LIFE` | 672.0 ticks (~28 game-days) | slower than belief confidence (168) by a wide margin — anger outlives the story |
| `GRUDGE_EVIDENTIARY_HALF_LIFE` | 336.0 ticks (~14 game-days) | between confidence (168) and gist (1440) — the facts fade faster than the feeling |

The **ordering** is load-bearing (emotional > evidentiary > belief
confidence half-lives); the magnitudes are placeholders with the same
comment status as `claims.py:43-74`.

## Read first

1. The design doc §3 (R7) — the ruled shape.
2. `chronicle/social.py` — `Grudge` (:100-118), the module's existing
   constants (:62-68), `form_grudge` (do not touch it — lane 21/L-E
   territory).
3. `chronicle/claims.py` — `_decay` (:94-95), `stage_at`'s decay-at-read
   pattern, and the tunables-block comment discipline (:43-74) your new
   block mirrors.
4. `chronicle/tests/test_social.py` — the test idiom you're extending.
5. `docs/work-packets/reviews/README.md` — governance; local commits
   fine (path-scoped), never push.

## Task

1. **Constants block** in `social.py` (new tunables section, ruled
   values, placeholder-status comments with half-life derivations in
   game-days per ADR-0010).
2. **`grudge_at(grudge, gamets)`** — pure decay-at-read: emotional and
   evidentiary strengths decayed from `last_rehearsed` via
   `claims._decay` with their respective half-lives. `forgiveness_threshold`
   becomes the "cooled" floor: expose (return or companion predicate)
   whether the decayed grudge is below it — the grudge is never deleted.
3. **Unit tests** in `chronicle/tests/test_social.py`:
   - both strengths decay with elapsed time; emotional decays slower
     than evidentiary (the constants-ordering assert);
   - both decay slower than belief confidence over the same elapsed
     window (T3.2's "grudge decays slower than the rumor" at the
     constants level);
   - the cooled-floor predicate flips at the right threshold crossing;
   - determinism/no-mutation: `grudge_at` never mutates its input.

## Acceptance

- `uv run pytest -q` green (186 + lane 19's + your new tests),
  `uv run ruff check .` clean.
- `grudge_at` is pure (no mutation, no store access, no I/O).
- Constants match the ruled table; ordering asserts green.
- No schema/frozen-doc edits; no changes outside the boundary files.

## File boundaries

**Edit:** `chronicle/social.py` (constants block + `grudge_at`),
`chronicle/tests/test_social.py` (new tests only — no assertion edits)

**Do not touch:** `chronicle/driver.py`/`rules.py` (lane 19),
`form_grudge` internals, everything else.

## Conventions

- Match the module idiom; docstrings naming rules 12–13.
- **Local commits OK** (path-scoped, explicit adds); never push.
- Report format: delivered, acceptance per criterion with command
  tails, findings list. (Expected finding: whether any existing caller
  should already read `grudge_at` — e.g. threshold consumers — but
  wiring consumers is a later lane's call, not yours.)
