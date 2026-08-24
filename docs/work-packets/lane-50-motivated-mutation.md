# Lane 50 — T2.4: motivated-mutation hook (Track A, micro-lane)

**Status:** Ready to start immediately (independent of lane 49; the
design is named in `docs/design/north-star-fixture.md` Decision N4 and
ruled in the lane-45 review). T2.4 has been parked since v0.1 for lack
of faction data — the north-star fixture work supplies it.

**Effort:** small-medium (one engine hook + the parked rung).

## Context

T2.4 (frozen, `docs/scenario-ladder.md:61`): faction-aligned NPC
retells with allegiance-consistent slot substitution (rule-based; the
LLM gossip-hub tier later slots behind this interface). Assert:
**substitution direction matches allegiance.** Example from the vision:
a Stormcloak blacksmith retells the Jarl's death as an Imperial plot.

## Read first (in order)

1. `docs/design/north-star-fixture.md` Decision N4 — the hook's
   design (ruled). Deviations come back as findings.
2. `docs/scenario-ladder.md:61` — the frozen rung text.
3. `chronicle/driver.py` — `_decide_mutation` (:1062-1117): the
   `mutation_candidates` mapping, the slot roll, the value roll
   (:1113-1117).
4. `chronicle/social.py` — `Relationship` (`"faction"` basis +
   `basis_id`), the bulk-accessor idiom (lane 43's `grudges()`).
5. `chronicle/rules.py` `TellDecisionRule` — the deterministic-decline,
   `roll_key=None` idiom you're mirroring for the value side.
6. `docs/work-packets/reviews/README.md` — governance.

## Pinned implementation decisions (ruled)

- **New caller-supplied mapping** (the `mutation_candidates` idiom):
  `allegiance_candidates: Mapping[tuple[str, str, str], str]` keyed
  `(claim_kind, slot, faction_basis_id)` → the single deterministic
  value.
- **The hook (N4):** in `_decide_mutation`, after the existing slot is
  chosen, if the teller holds a `"faction"` relationship whose
  `basis_id` has an entry for `(claim.kind, slot)`, use the mapped
  value directly — **no value roll** (`roll_key=None` for the value
  side, the TellDecisionRule stage-1 idiom). Unmapped tellers keep
  today's uniform-random behavior — migration-safe by construction.
- **Rule budget: untouched.** This is a caller-supplied policy input
  to rule 7 (mutation policy), not a new rule — no registry change,
  no new RNG purpose. (The deterministic value path uses no roll; the
  slot roll is unchanged.)
- **Schema gloss (coordinator-handled):** `mutation_applied`'s
  `roll_key` field gets a nullable annotation for the deterministic
  allegiance path (the §4:121 `transmission_declined` idiom) — the
  coordinator amends §4:119's gloss at dispatch; the lane emits it
  accordingly.

## Task

1. `chronicle/driver.py`: the `allegiance_candidates` construction
   param + the N4 hook in `_decide_mutation`.
2. `scenarios/test_tier2_motivated_mutation.py` — the T2.4 rung: a
   faction-aligned teller (fixture edge, e.g. Stormcloak) retells the
   death claim; the mutated slot substitutes to the allegiance-mapped
   value **deterministically** (assert the exact value, not a roll
   distribution), the emitted `mutation_applied` carries the slot
   roll_key and a null value roll_key, and an unaligned teller's
   substitution stays uniform-random (keyed roll present).
3. Suite green; no behavior change without the mapping registered.

## Acceptance

- `uv run pytest -q` green (240 + your new tests), ruff clean.
- Substitution direction matches allegiance, asserted exactly;
  unmapped tellers unchanged (the regression proof: full suite
  unedited).
- No new rules, no new RNG purposes; the schema gloss amendment is the
  coordinator's, not yours.

## File boundaries

**Create:** `scenarios/test_tier2_motivated_mutation.py`

**Edit:** `chronicle/driver.py` + the pre-authorized mechanical edits
class

**Do not touch:** `chronicle/rules.py`, `chronicle/rng.py`,
`chronicle/social.py` (read-only — use the public accessors),
frozen/coordinator docs (the §4:119 gloss is the coordinator's),
other `scenarios/` files, `dashboard/`, `runs/`

## Conventions

- Match the engine idiom; named constants with rule citations.
- **Local commits OK** (path-scoped, atomic `add && commit`); never push.
- File a delivery report on disk: delivered, acceptance per criterion
  with command tails, findings list.
