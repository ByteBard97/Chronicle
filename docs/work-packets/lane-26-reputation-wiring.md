# Lane 26 — Tier 3 L-F: observer-local reputation wiring (Track A, sim substrate)

**Status:** Serial after **lane 25** (driver.py contention). Design R11
ruled (design doc §6); the Beta accumulator and record shapes already
exist (`social.py`, schema §4:128).

**Effort:** medium (belief-acquisition hooks + rung test).

## Context

T3.5 (frozen, `docs/scenario-ladder.md:76`): the player becomes Thane.
Assert: reputation rows update for **informed NPCs only**; uninformed
NPCs unchanged — any global jump is a bug (the observer-locality
tripwire). The ruled design (R11): reputation evidence is driven by
belief acquisition, nothing else — witness path → `"witnessed"`,
encounter retell → `"reported"`, corroboration → `"corroborated"`.

## Read first (in order)

1. `docs/design/tier-3-rule-registry-and-tell-decision.md` §6 (R11).
2. `docs/scenario-ladder.md:76` — the frozen rung text.
3. `chronicle/social.py` — `update_reputation` (:298-353), priors
   (:62-63), kind weights (:64-68), the observer-local key discipline
   (:16-19, :490-491).
4. `chronicle/driver.py` — the belief-forming paths (witness, retell,
   corroborate) where acquisition hooks go; lane-19's `_evaluate_rule`.
5. `docs/frame-log-schema.md` §4:128 — `reputation_updated` (inputs +
   result; emit field-for-field).
6. `docs/work-packets/reviews/README.md` — governance.

## Pinned implementation decisions (coordinator-set, 2026-08-23)

- **Trigger:** reputation rows update exactly when an NPC **gains or
  corroborates a belief** whose claim kind is registered as
  reputation-relevant (caller-supplied per-kind mapping —
  `mutation_candidates` idiom — mapping claim kind → `subject_id` slot,
  `positive`, `context`).
- **Evidence kind maps to the acquisition path**: witness →
  `"witnessed"`, encounter/scripted retell → `"reported"`, corroborate →
  `"corroborated"`. Weights come from the existing
  `REPUTATION_WEIGHT_BY_KIND`.
- **Subject/positive/context derive from the claim's slots** via the
  caller-supplied mapping — never from a global flag (the tripwire is
  structural: no acquisition, no update).
- **Rule 16 registers** replacing the stub; default enabled. No mapping
  registered → zero rows → behavior identical to today.

## Task

1. Rule 16 in `chronicle/rules.py` + acquisition hooks in the driver's
   witness/retell/corroborate paths (respecting the mapping's absence).
2. `scenarios/test_tier3_reputation.py` — the T3.5 rung: a
   Thane-status event witnessed by some NPCs and not others (the
   fixture controls who witnesses/hears). Assert: every informed NPC
   has the expected `reputation_updated` rows with the right kind
   (witnessed for witnesses, reported for hearers); **every uninformed
   NPC's reputation store is byte-identical** (the tripwire, asserted
   per NPC, not just in aggregate); corroboration adds a
   `"corroborated"` row; each update carries a paired `rule_evaluated`.
3. Suite green; no behavior change with no mapping registered.

## Acceptance

- `uv run pytest -q` green (prior count + your new tests), ruff clean.
- `reputation_updated` matches §4:128 field-for-field.
- The observer-locality tripwire passes per NPC as written above.
- No schema/frozen-doc edits; no new RNG purposes.

## File boundaries

**Create:** `scenarios/test_tier3_reputation.py`

**Edit:** `chronicle/rules.py` (rule 16), `chronicle/driver.py`
(acquisition hooks + mapping)

**Do not touch:** frozen/coordinator docs, `rng.py`, `social.py`
(read-only — the accumulator is complete), `claims.py`, other
`scenarios/` files, `dashboard/`, `runs/`

## Conventions

- Match the social/driver idiom; rule citations in docstrings.
- **Scenario-authoring notes (lane-24 delivery):** engine-internal
  events consume branch seqs — hand-numbered fixture seqs must skip
  past them; scripted pre-run writes aren't visible to
  `FrameLogReader` until a flush.
- **Pre-authorized mechanical edits (lane-25 precedent):** registering
  rule 16 replacing its stub requires the `test_rules.py` enabled-count
  migration (13 → 14) — authorized, same class as lanes 23/24/25.
  New unit tests go in the idiom-correct home (`test_social.py` /
  `test_rules.py`) even though the packet doesn't list them by name.
- **Local commits OK** (path-scoped, explicit adds); never push.
- Existing test assertions immutable; conflicts are findings.
- Report format: delivered, acceptance per criterion with command
  tails, findings list.
