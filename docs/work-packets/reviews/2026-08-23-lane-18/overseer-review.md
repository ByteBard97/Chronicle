# Lane 18 — overseer review (Tier 3 design doc)

**Date:** 2026-08-23 · **Overseer:** planning agent · **Re:**
`docs/design/tier-3-rule-registry-and-tell-decision.md` (commit `9de84de`)

## Verdict: **accepted.** Sound design, honestly bounded, ADR-liftable as promised.

## Citation spot-checks (all verified against the repo)

- R1: Driver ctor is keyword-only per-run (`driver.py:120-122`); the
  determinism harness does run two drivers per test
  (`test_determinism.py:68-74`). Per-run registry is correctly reasoned.
- R4/R5: "never deleted" event-sourcing discipline verified
  (`claims.py:66-68`); `_propagating_claims` is exactly the witness-path
  registry (`driver.py:208-209`) — R6's "propagation for free" holds.
- R8/O3: `form_grudge`'s victim-edge gate verified verbatim
  (`social.py:225-235`) — the self-victim wrinkle is real, and the
  doc is right that no engine path has hit it yet (social cascades are
  scripted).
- R10: `tell.decision` is registered (`rng.py:44`, with the comment
  tying the initial set to schema §4). No ADR-0009 change needed.
- F1 confirmed: no packet premise was wrong.

## One correction — F2 is smaller than reported (good news)

The doc says `escalation_warning` "must be added to frame-log-schema §3's
event vocabulary." In fact **§3 already reserves it** (line 95:
"`escalation_warning` | 3 — reserved | … Fields defined when the
threshold machinery lands"), and §4's `threshold_crossed` gloss (line
123) already references it. What L-C needs is to *fill in the reserved
row's fields* — exactly the deferred-definition mechanism the schema was
built with. **Disposition:** downgraded from owner-adjudication to
coordinator-handled — I'll approve the field definitions when L-C is
packetized, with a note to the owner. No schema-amendment cycle needed.

## Design assessment (the parts verification can't cover)

- The derived-accumulator decision (R4) is the best move in the doc —
  it eliminates a whole class of keyframe/replay state by reading what
  beliefs already reconstruct. Same event-sourcing discipline as lane
  12's trace-only supersessions.
- R9's gate placement (after `teller_and_hearer`, before mutation,
  resolution path ungated) is correct, and the rejected alternative
  (per-pair decline rows) shows the volume discipline F3 asks for.
- R10's `TELL_PROBABILITY = 1.0` migration default is the right kind of
  boring: the 186-test battery defines current behavior until fixtures
  opt out.
- The lane split correctly identifies `driver.py` contention as the
  serialization constraint (L-C through L-F).

## Owner adjudication queue (O1–O5, with coordinator recommendations)

Presented to the owner alongside this review; outcomes to be recorded
here and folded into the implementation-lane packets.

**RULED 2026-08-23 — all five accepted per the coordinator's
recommendations. The owner delegated the call in full ("use your
judgement — you are the boss"), so these carry owner authority via
delegation and are final for the implementation lanes:**

- **O1 — run-config record:** coordinator agrees with the doc — (b)
  `runs/index.json` metadata. Configuration, not derivation.
- **O2 — grudge decay magnitudes:** accept the proposed table
  (emotional 672 / evidentiary 336 ticks) as tunable-not-derived
  placeholders; the ordering is the load-bearing part. Same class as the
  coordinator-pinned `CONTESTED_CLAIM_CONFIDENCE_DENT`.
- **O3 — rule-8 self-victim:** coordinator leans **documented bypass**
  (`victim_id == holder_id` permitted in `form_grudge` with a comment
  naming rule 8's harm-to-self base case) over a synthetic self-edge —
  a self-relationship row is fake data; the bypass is honest code.
- **O4 — budget consolidation:** accept — 9+10 as one, 4 as
  schema-not-rule, effective 17/20. Registry still lists all 19 names.
- **O5 — `rule` field granularity:** agree with the doc — rule name in
  `rule`, sub-reason in the paired `rule_evaluated`'s `inputs`.

## Dispatch decision

L-A (registry core) and L-B (grudge decay) are ruling-free and
file-disjoint; the coordinator packetizes both for immediate parallel
dispatch (pending owner's O2 nod for L-B's constants, which are
placeholder-tunable either way). L-C/L-E wait for the F2 field
definitions (coordinator) and O3 (owner) respectively; L-D/L-F queue
behind L-A per the doc's serialization note.
