# Lane 12 — T2.3 conflicting-variant resolution (Track A, sim substrate)

**Status:** Ready to start immediately. The policy is frozen in
`docs/scenario-ladder.md` §T2.3 (v0.4 FINAL), the `supersession` trace
record shape is frozen in `docs/frame-log-schema.md` §4, and the reader
side already exists (CLI `trace` prints supersession records; dashboard
`types.ts:180` includes it). Lane 11 (M2 encounter feed, dashboard) runs
in parallel — disjoint trees (Python vs. dashboard/src).

**Effort:** medium-large (code + rung test).

## Context

Tier 2's own machinery forces this rung: the first time a holder of
variant A hears variant B, the one-belief-per-(holder, claim) invariant
meets a contradiction and the code currently has no answer —
`propagate.teller_and_hearer()` returns `None` when both parties hold
beliefs, and the driver writes a `nothing_salient`/`"both-informed"`
record and moves on (`driver.py:460–478`). Meanwhile `ClaimStore.retell()`
(claims.py:477–495) will silently create a *second* belief for a hearer
who already holds one — the invariant survives today only by driver
courtesy. T2.3 makes resolution a first-class store write path and closes
the T0.4 machinery gap it intersects.

The frozen policy (scenario-ladder.md §T2.3, v0.4 — quoted in full in
"Read first" below):

- **Evidence-type ordering with strength tiebreak:** the variant whose
  evidence chain terminates in the stronger evidence *type* wins —
  witnessed > reported; on a type tie, higher summed evidence strength
  wins. Pure claims-layer data (`Evidence.evidence_type`); **no
  social-state lookups** (the v0.3 trust-source tier was rejected and
  re-homed to a future rung with trust machinery).
- **Supersession is a separate record** naming loser and winner — never a
  write onto the losing variant (frozen lineage record).
- The winner takes a small **contested-claim confidence dent**.
- **Resolution is a first-class store write path** (sibling to
  `retell()`/`corroborate()`) that enforces the one-belief invariant **at
  the store** — the store *raises* on any duplicate-creating path.

The rung's assert list (verbatim, this is your acceptance):

> the named rule fires; the invariant holds and the store *raises* on any
> duplicate-creating path; both encounters are in the evidence chain; the
> supersession record exists and names both variants; the winner shows
> the dent; and the resolution direction flips when the fixture swaps
> which side holds the eyewitness.

## Read first (in order)

1. `docs/scenario-ladder.md` §T2.3 — the full rung text (line 60; it's
   one long line — `sed -n '60p' docs/scenario-ladder.md | fold -s`).
   Also line 162 (§9: "T2.3 adds a resolution write path to the claims
   store that enforces the one-belief invariant at the store level") and
   line 159 (UI consequence — informational only, dashboard is lane 11+).
   Frozen — do not edit; findings go to the coordinator.
2. `docs/frame-log-schema.md` §4, line 120 — the `supersession` record
   (**amended 2026-08-23 by the coordinator**, pre-implementation review
   findings 1–2 — see `reviews/2026-08-23-lane-12/`):
   `holder_id`, `claim_id`, `loser_variant_id` (string | null),
   `winner_variant_id` (string | null), `resolution_rule` (string — the
   named resolution rule), `confidence_dent` (number, [0,1]),
   `teller_id`, `teller_belief_id`, `evidence_id`, `winner_belief_id`.
   A null variant id = the claim's original telling (witness-held,
   un-varianted). The final four fields make resolution re-executable
   from the trace alone after a keyframe. Tier 2, live now. **Not**
   roll-bearing — no `roll_key`, and T2.3 needs no rolls (the rule is
   deterministic on existing Evidence data). Do NOT add an RNG purpose
   (that's an ADR-0009 registry change, out of bounds).
3. `chronicle/claims.py` — the store: `ClaimStore.witness` (441–475,
   note the content-disagreement raise at 452–463), `.retell` (477–495,
   the silent-duplicate hole), `.corroborate` (497–556, the
   confidence-`replace` precedent at 538–544), `belief_of` (590–598, the
   docstring that claims the invariant "by construction"),
   `chain_for` (566–582, the walk to the grounding witness — your
   "chain terminates in" primitive), `Evidence` (119–136), `Variant`
   (104–116), and the tunable-constant block (43–74) where your two new
   constants belong.
4. `chronicle/propagate.py:25–39` (`teller_and_hearer` — the guard this
   lane supersedes) and `chronicle/driver.py:460–478`
   (`_propagate_on_encounter`, the `"both-informed"` branch) plus the
   scripted wrapper pattern at `driver.py:196–275` (thin store wrapper +
   schema §4 trace emission — your `driver`-side supersession wrapper
   mirrors these exactly).
5. `scenarios/test_tier0_claims_mechanics.py:298–363` — the T0.4
   disagreeing-witness xfail (strict). Read the test body and its
   comments; this lane closes it (see Task 4).
6. `scenarios/test_tier2_mutation.py` — the rung-test idiom you're
   matching (fixtures, keyed-seed determinism, assertion style).
7. `chronicle/framelog.py` — the reader's trace replay (how
   `belief_formed`/`transmitted` fold into reconstructed state); you'll
   add supersession handling.
8. `docs/work-packets/reviews/README.md` — governance + coordination
   rules. Lane agents do not commit.

## Pinned design decisions (coordinator-set; not frozen-doc text, but not up for re-litigation in-lane — deviations come back as findings)

- **Same-variant case is not a conflict.** When both parties hold beliefs
  about the claim *with the same variant*, the encounter stays
  `nothing_salient`/`"both-informed"`; the encounter path performs **no
  corroboration** (corroborate() is scripted-only today — adding
  encounter-driven corroboration would be a new rule over budget).
  Resolution fires only when the variants differ.
- **"Chain terminates in"** = `chain_for()`'s grounding-evidence walk:
  the terminal Evidence's `evidence_type`. Note `corroborate()` writes a
  third type string (`"corroborated"`, claims.py:548) that the dataclass
  comment doesn't list — corroborating evidence is never the *terminal*
  evidence by construction (index 0 is the grounding evidence), so the
  rule reads only witnessed/reported at the terminal. Surface the
  undocumented third type as a finding, don't "fix" it in passing.
- **Tiebreak sum** = the stored `strength` of all Evidence records
  supporting each side's belief (grounding + corroborations), summed
  as-stored (decay is a read-time/lazy concern, rule 19 — do not decay
  for the comparison). Deterministic; document the choice in code.
  **Exact tie (ruled 2026-08-23): the incumbent wins — the challenger
  must be strictly stronger to displace** (the only reading consistent
  with the rung's recorded rejection of keep-newer). The supersession
  record still fires and the standing incumbent takes the dent — a
  challenged belief is held less certainly even when nothing changes
  hands. Post-T0.4 the 1.0-vs-1.0 eyewitness standoff is the *default*
  case, not an edge case; the rung test must cover it.
- **The dent (ruled 2026-08-23):** `CONTESTED_CLAIM_CONFIDENCE_DENT = 0.1`
  in claims.py's tunables block (tunable-not-derived, same comment
  discipline as its neighbors; a challenge costs half the retelling
  haircut's 0.2). The winner's confidence **multiplies by
  `1 - CONTESTED_CLAIM_CONFIDENCE_DENT`**; the record's `confidence_dent`
  field carries the constant's value. The rung test asserts the dent
  *exists and matches the constant*, not a magic number inline.
- **Correction semantics (ruled 2026-08-23 — a supersession is a
  correction, not a transmission).** No new Variant is minted: the loser
  adopts the teller's variant **as-held**, so winner/loser ∈ the two
  pre-existing variants and the `transmitted` invariant (a variant on
  every transmission) is untouched. The only new store object is one
  appended Evidence on the winner's belief — `evidence_type="reported"`,
  `predecessor_belief_id` = the teller's belief, `strength` = the
  teller's pre-decay confidence (retell()'s "strength of the testimony
  as given" convention, claims.py:344-348). Belief fields:
  - *Challenger wins (adoption):* re-derive from the teller's belief
    exactly as `retell()` does (claims.py:326-336) —
    `confidence = teller.confidence * RETELL_CONFIDENCE_DECAY * (1 - dent)`,
    verbatim `* RETELL_VERBATIM_DECAY`, gist `* RETELL_GIST_DECAY`;
    `first_learned` **preserved** (it's when they first learned *of the
    claim*); `last_rehearsed` = resolution gamets.
  - *Incumbent wins (challenge repelled):* corroborate()-style
    decay-then-replace (claims.py:536-544) — decay the incumbent to the
    resolution gamets, then `confidence *= (1 - dent)`; verbatim/gist
    keep their decayed values; `last_rehearsed` = resolution gamets.
- **The rule's name** (`resolution_rule` field) is a module-level string
  constant, e.g. `"evidence-type-ordering+v1"`. One canonical spelling,
  used by the store, the trace record, and the test. (Rule budget:
  scenario-ladder §8 counts this rung's rule already — "pick one, name
  it as a rule, assert it" — so naming it here is within budget; do not
  add any *second* new rule.)
- **Losers never mutate.** The holder's *belief* is re-pointed at the
  winning variant (the belief is the holder's mutable relationship to
  the claim; the variant records are frozen lineage) — see "Correction
  semantics" above for the full field set of the re-point.
- **Rumor bookkeeping (ruled 2026-08-23):** `resolve()` maintains
  `_rumors`/`_rumor_sources` exactly as `retell()` does
  (`_record_hearing`/`_record_telling`, claims.py:401-427) — the hearer
  heard the incoming variant, the teller told theirs; the adoption side
  needs no re-keying (the hearing entry is what the re-pointed belief
  matches). The loser's rumor entry *stays* (they did hear it —
  event-sourcing discipline), so stage queries are defined as valid for
  the holder's **active variant only**: a stale-variant
  `rumor_stage_now()` query gets a clear error, not a bare
  `StopIteration` (claims.py:432-439).
- **T0.4 scope (ruled 2026-08-23):** single-slot disagreement only —
  `witness()` raises a clear error naming the follow-up on multi-slot
  disagreement rather than writing a lossy variant; the limitation is
  named in the code comment and the report. Lineage pin:
  witness-disagreement variants **root at the claim by design**
  (`parent_variant_id=None`, `mutated_slot` = the disagreed slot) — a
  second, legitimate kind of lineage root alongside the un-varianted
  original telling. **Witness-after-rumor raises** at `witness()` this
  lane (the rung's "raises on any duplicate-creating path" read
  conservatively); witness-after-rumor auto-resolution is named as a
  follow-up rung candidate — that flow has no write path this lane, a
  real but bounded gap.

## Task

1. **`ClaimStore.resolve()` (or `supersede()` — one canonical name)** in
   `chronicle/claims.py`: first-class write path, sibling to
   `retell()`/`corroborate()`. Implements the frozen policy per the
   pinned correction semantics (no new Variant; one appended Evidence;
   belief re-point + dent); produces the supersession record payload
   (schema §4:120 **as amended 2026-08-23** — field names exactly,
   including `teller_id`/`teller_belief_id`/`evidence_id`/
   `winner_belief_id` and nullable variant ids); enforces the
   one-belief-per-(holder, claim) invariant at the store — **raise** on
   any path that would create a duplicate belief. This closes the
   silent-duplicate hole in `ClaimStore.retell` (hearer already holds a
   belief → `retell` routes to resolution when variants differ, raises
   otherwise per the pinned decisions) **and** the holder-level duplicate
   in `witness()` (witness-after-rumor raises per the T0.4 scope ruling).
2. **Driver wiring:** in `_propagate_on_encounter`, replace the
   both-informed decline with the conflict check: differing variants →
   resolution (emit `supersession` via a scripted wrapper mirroring
   `driver.retell` etc., driver.py:196–275); same variant → unchanged
   `nothing_salient` behavior. Keep the caller-supplies-context
   discipline — no social-state lookups.
3. **Reader replay:** `chronicle/framelog.py` folds `supersession`
   records into reconstructed state — re-executed, not approximated: the
   amended payload's `teller_id`/`teller_belief_id`/`evidence_id`/
   `winner_belief_id` give replay everything needed to rebuild the
   appended Evidence and the belief re-point + dent exactly, so
   arbitrary-T reconstruction and `cli.inspect` match the live run
   (framelog.py:624-630's parity guarantee holds for supersession too).
   Keyframes carry no supersession data (schema §5; supersessions stay
   trace-only, matching cli.py's existing assumption) — rebuild from the
   trace stream, consistent with the existing keyframe/delta discipline.
4. **Close T0.4:** implement the disagreeing-second-witness → Variant
   path the xfail at `scenarios/test_tier0_claims_mechanics.py:298–313`
   names (same claim id, disagreeing slots hang off a Variant of the one
   shared Claim, canonical slots unchanged), then **remove the xfail
   marker** — the test body stays byte-identical (this marker removal is
   explicitly authorized for this lane; it is the only test-file edit
   permitted).
5. **Rung test:** `scenarios/test_tier2_resolution.py` (new) covering the
   frozen assert list: named rule fires (the `resolution_rule` string in
   the emitted record); store raises on a duplicate-creating path; both
   encounters appear in the winner's evidence chain; the supersession
   record exists and names loser + winner; the winner's confidence shows
   exactly the constant dent; and the direction-flip fixture (swap which
   side holds the eyewitness → the other variant wins). Seeded,
   deterministic (same discipline as the T2.1/T2.2 tests).
6. **Regenerate nothing.** Do not regenerate `runs/whiterun-jarl-01` —
   the writer refuses existing run dirs and the demo run's regeneration
   is the coordinator's call (note in your report whether resolution
   would change its trace).

## Acceptance

- `uv run pytest -q` green **including the former T0.4 xfail now passing
  unmarked** (suite goes from 175+1 xfail to 176+0 — or whatever the new
  rung test adds on top), `uv run ruff check .` clean.
- The rung's assert list passes as automated tests (Task 5), including
  the direction flip **and the exact-tie case** (two eyewitnesses,
  1.0 vs 1.0 → incumbent stands, record fires, incumbent dented).
- Store-level invariant: a direct `ClaimStore.retell()` (or any store
  path) that would create a second belief for (holder, claim) raises —
  covered by test; witness-after-rumor and multi-slot witness
  disagreement raise their ruled errors — covered by test.
- Emitted `supersession` records match schema §4:120 **as amended
  2026-08-23** — field names and types exactly, including the four
  replay fields and nullable variant ids; `chronicle trace` prints them
  against a fixture run (the CLI reader already handles the record —
  verify, don't assume).
- Reconstruction at arbitrary T reflects the resolution (test: state at
  T after the supersession tick shows the winner variant + dented
  confidence).
- No new RNG purposes; no frozen-doc edits; no dashboard edits.

## File boundaries

**Create:**
- `scenarios/test_tier2_resolution.py`

**Edit:**
- `chronicle/claims.py` (resolve path, invariant raise, constants,
  T0.4 variant-on-disagreement path)
- `chronicle/driver.py` (encounter wiring + scripted supersession wrapper)
- `chronicle/framelog.py` (replay)
- `chronicle/propagate.py` (only if the conflict check belongs there —
  keep it lookup-only/pure like the rest of the module)
- `scenarios/test_tier0_claims_mechanics.py` — **only** the xfail marker
  removal (lines ~298–313); assertions untouched

**Do not touch:**
- `docs/ui-spec.md`, `docs/scenario-ladder.md`, `docs/ui-doctrines.md`,
  `docs/frame-log-schema.md` (frozen / coordinator-owned — findings only)
- `chronicle/rng.py` (no new purposes)
- `dashboard/`, `runs/`, other `scenarios/` test files
- `chronicle/cli.py` (the reader already prints supersession — if you
  find a gap, report it)

## Conventions

- Match the claims.py/driver.py idiom: named constants in the tunables
  block with rule-number citations, docstrings naming the rule, no ad-hoc
  literals at call sites.
- **No `git commit`** — the coordinator reviews and commits (governance
  ruling, `docs/work-packets/reviews/README.md`). This supersedes any
  older packet text saying agents commit.
- Existing test assertions are immutable (the single authorized exception
  is Task 4's marker removal). Conflicts are findings.
- Report format: what you delivered, acceptance status per criterion with
  command output tails, and a findings list. Expected findings (already
  known to the coordinator — confirm or refute, don't re-derive):
  §7 line 125's stale "trust-source" wording vs. the v0.4 amendment; the
  undocumented `"corroborated"` evidence-type string; propagate.py's
  doc-vs-code mismatch on caller-supplies-context; the `nothing_salient`
  reason enum (`"both-informed"`) vs. post-resolution semantics.
