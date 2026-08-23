# Lane 23 — delivery report (tell-decision gate, T3.4)

Worker: Kimi (Track A). Packet: `docs/work-packets/lane-23-tell-decision.md`.
Committed path-scoped as `50e7357` (local; not pushed).

## Delivered

- **`chronicle/rules.py`** — `TellDecisionRule` replaces the rule-15 stub:
  two-stage evaluation per R10 (stage 1: `inputs["motive"]` present →
  decline, no roll; stage 2: `roll_value >= threshold` → decline). `fired`
  means the gate *declined*; O5 sub-reason in `inputs`/`result`, never the
  rule name. Module docstring updated (stub set is now 11–14, 16–19).
- **`chronicle/driver.py`** — the gate in `_propagate_on_encounter` after
  `teller_and_hearer`, before `_decide_mutation` (R9); T2.3's resolution
  path untouched. New ctor params: `claim_privacy: Mapping[str, str]`
  (claim kind → subject slot; presence = private — the
  `mutation_candidates` idiom) and `tell_probability` (constant
  `TELL_PROBABILITY = 1.0`, migration-safe). `_tell_decline_motive` does
  the kinship lookup driver-side (`social.relationship(teller, subject,
  "kinship")`); `_write_transmission_declined` emits §4:121
  field-for-field, `roll_key` null on motive declines / the `tell.decision`
  key (draw = claim ordinal in the propagating loop) on roll declines.
  `_evaluate_rule`'s `outcome` is now optional for computing rules.
- **`scenarios/test_tier3_tell_decision.py`** — the rung: two first-hand
  holders (scripted witnesses — a scripted retell from the motivated
  holder would be the *author* violating the motivation, not the sim), one
  kin-motivated. Asserts zero `transmitted` from the keeper across all
  ticks; one decline per encounter opportunity (48/48, counted against
  `encounter_rolled`, not hardcoded); declines name the rule with
  `roll_key: null`; the gossip transmits exactly once; `rule_evaluated`
  fires on both outcomes with `motive: "kin-motive"` in inputs. Plus a
  stage-2 twin test (`tell_probability=0.0`): roll-declines carry the
  `tell.decision` roll_key with `draw: 0`.
- **`chronicle/tests/test_rules.py`** — the mechanical consequence of the
  packet's "replacing the rule-15 stub" pin: stub assertions moved to rule
  11, enabled count 10→11. Flagged pre-build; no other test edits.

## Acceptance

- `uv run pytest -q`: **198 passed, 0 failed** (196 + 2 new). `uv run ruff
  check .`: clean. No existing test edited except the two lane-19 stub
  assertions above; no behavior change at defaults (the battery is the
  proof — gate live, threshold 1.0, no privacy mappings).
- `transmission_declined` matches §4:121 field-for-field (asserted);
  deterministic declines carry `roll_key: null`, roll declines the keyed
  `tell.decision` key.
- No new RNG purposes (TELL_DECISION was pre-registered); no frozen-doc or
  schema edits (the row was already reserved).

## Findings

1. **`propagate.py` untouched despite being in bounds.** The packet allowed
   it for context assembly, but the motive check is one lookup and lives
   naturally in the driver next to `_decide_mutation`; adding a
   propagate.py seam would be indirection without a caller. Noted so the
   coordinator knows the allowance went unused.
2. **Motive vocabulary is kinship-only.** R10 mentioned "kinship edges to
   the subject, grudges" as motive inputs; T3.4 exercises only kinship, so
   `_tell_decline_motive` implements exactly that ("kin-motive").
   Grudge-based or faction-based motives slot into the same helper when a
   rung needs them — flagging so L-lanes don't assume generality that
   isn't there.
3. **M4 note for Track B:** `transmission_declined` now has a producer,
   but `cli.py`'s `_FEED_RECORD_TYPES` still lists three outcome types
   (out of this lane's bounds). The dashboard lane adding the fourth
   outcome state may want the CLI feed updated in the same pass.
4. **Volume:** rule 15 adds one `rule_evaluated` per resolved transmission
   pair — bounded by encounter volume, same backlog item as before.
