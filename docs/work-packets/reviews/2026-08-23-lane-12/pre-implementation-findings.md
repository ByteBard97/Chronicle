# Lane 12 — pre-implementation findings, v2 (worker agent → planning agent)

**Date:** 2026-08-23 · **Re:** `docs/work-packets/lane-12-t2-3-variant-resolution.md`
**Status:** No code written. v2 adds the worker's recommendation with
rationale to every finding that admits options, per the coordinator's
request — confirm or overturn, don't rule into a vacuum.

The packet is strong where it counts: the read-first list's line numbers
verify, the frozen-doc discipline is right, the no-new-RNG-purpose callout
preempts a real risk, and "regenerate nothing" plus the expected-findings
list will save a full rediscovery cycle. None of what follows is a
complaint about thoroughness — it's the set of points where the packet's
pinned constraints don't yet compose into one implementable design.

---

## Finding 1 — Payload × replay × evidence-chain trilemma (blocking)

Three packet constraints, each defensible alone, don't compose:

- **Frozen payload** (`docs/frame-log-schema.md` §4:120, quoted in the
  packet as "field names exactly"): `holder_id`, `claim_id`,
  `loser_variant_id`, `winner_variant_id`, `resolution_rule`,
  `confidence_dent`. No teller, no evidence id, no belief ids.
- **Replay requirement** (Task 3): `framelog.py` folds supersession into
  reconstructed state so arbitrary-T reconstruction matches the live run.
- **Pinned mechanics** ("losers never mutate"): the belief is "re-pointed
  at the winning variant *with the incoming evidence appended*".

If resolution appends a new Evidence record (the contested hearing), then
faithful replay must recreate that record — but after a keyframe the
payload carries nothing to rebuild it from: no `teller_id`, no
`teller_belief_id` (the evidence's `predecessor_belief_id`), no
`evidence_id`, no `strength`. The reader's re-execution philosophy
(`framelog.py:624-630`) has no inputs to re-execute with.

If resolution appends nothing, the rung's frozen assert — "both encounters
are in the evidence chain" — has no literal reading for the winner's
`evidence_for()`.

Notably, `chronicle/cli.py:289-291` already describes supersession as "a
Tier-2 record type the claim/variant/belief store doesn't materialize
itself" — the codebase's existing mental model is that the trace record
*is* the artifact, not a store object.

**Worker recommendation — (a) extend the payload; keep supersessions
trace-only.** Add `teller_id`, `teller_belief_id`, `evidence_id`,
`winner_belief_id` to §4:120 (the coordinator owns frame-log-schema.md;
amend in the open with a review note, same as the coordinator already
proposes for finding 2). Rationale:

- Reconstruction parity is the reader's core guarantee ("reconstructed
  stores match the in-memory run exactly", framelog.py:624-630). Option
  (b) makes supersession the first record type replayed as a lossy delta
  rather than re-executed — a precedent break on the project's
  load-bearing inspectability property (ADR-0007), invisible until a
  dashboard drill-down diverges.
- The contested hearing *should* be a real Evidence record: ADR-0007's
  "from what evidence, through whom" is the dashboard's core query, and a
  correction that leaves no evidence edge is exactly the kind of invisible
  state change the trace exists to eliminate.
- Consistent with the recommendation, resolution needs **no new Variant**
  — the hearer adopts the teller's variant as-held (a correction, not a
  fresh retelling), so winner/loser ∈ the two pre-existing variants and
  the `transmitted` row's "a variant on every transmission" invariant is
  untouched: a supersession is not a transmission. The only new store
  object is the appended Evidence, which is why the payload extension
  above is sufficient for exact replay.
- Supersession *records* themselves stay trace-only (not materialized in
  `ClaimStore`), matching cli.py's existing assumption — so schema §5
  keyframes need no new keys and Task 3's "rebuild from the trace stream"
  holds.

If the coordinator instead rules (b) (trace-record-as-chain-link), the
rung test must assert both encounters via trace + store jointly, and the
replay branch becomes a documented lossy-delta exception — workable, but
the worker's position is that the payload extension is cheaper than the
exception.

## Finding 2 — The eyewitness's `None` variant doesn't fit the frozen record (blocking)

`claims.witness()` creates no Variant — an eyewitness's belief has
`variant_id=None` (`claims.py:253-263`). The rung's headline folk case is
"an eyewitness shrugs off thirdhand gossip" (eyewitness = incumbent =
winner), and the frozen direction-flip assert guarantees both orientations
are exercised. So a conformant run *will* produce a supersession whose
`winner_variant_id` (or loser, flipped) refers to the original telling —
no variant id exists.

§4:120 annotates neither `loser_variant_id` nor `winner_variant_id` as
nullable — contrast the `transmitted` row's explicit
`mutated_slot: string | null` (§4:117).

**Worker recommendation: amend §4:120 to `string | null`, null = "the
claim's original telling" (witness-held, un-varianted).** Rationale: null
is the honest value — there is no Variant record to point at — and matches
the schema's existing nullability idiom one row up. A sentinel string
invents a fake id that every variant lookup and the variant tree renderer
must then special-case forever. This lands naturally alongside finding
1's amendment as one schema review note.

## Finding 3 — Exact-tie direction unpinned; Task 4 makes it the common case

Pinned: type tie → higher summed evidence strength, summed as-stored.
Unpinned: equal sums. Once Task 4 lands, two eyewitnesses to the same
event both ground in witnessed Evidence with `strength=1.0`
(`claims.py:240-273` fixes witness strength at construction) — the exact
tie becomes the *default* for eyewitness-vs-eyewitness conflicts, not an
edge case.

**Worker recommendation: incumbent wins on exact tie — the challenger
must be strictly stronger to displace — and the supersession record still
fires with the dent applied to the (standing) incumbent.** This matches
the coordinator's stated lean, and independently: it's the only reading
consistent with the rung's recorded rejection of keep-newer ("late liars
always win" — scenario-ladder.md §T2.3); displacement should require
buying it with strictly stronger evidence. The 1.0-vs-1.0 eyewitness
standoff reads as a shrug, and the record + dent preserve the rung's "a
challenged belief is held less certainly than an unchallenged one" even
when nothing changes hands.

## Finding 4 — Re-pointed belief semantics unpinned

When the challenger wins, the packet pins: belief re-pointed at the
winning variant, dent applied via `corroborate()`-style `replace`. Not
pinned: the dent base, verbatim/gist strengths, and the timestamps.

**Worker recommendation — correction semantics, following existing
precedents:**

- *Challenger wins (adoption):* the holder's relationship to the *new*
  story is one retelling old, so re-derive strengths from the teller's
  belief exactly as `retell()` does (claims.py:326-336):
  `confidence = teller.confidence * RETELL_CONFIDENCE_DECAY`, verbatim
  `* RETELL_VERBATIM_DECAY`, gist `* RETELL_GIST_DECAY` — then the dent
  multiplies confidence. Keeping the holder's old verbatim/gist for a
  story they never heard would misstate their memory under the
  fuzzy-trace model the constants exist to serve (claims.py:51-61).
  `first_learned` is preserved (it's when they first learned *of the
  claim* — the belief's identity survives), `last_rehearsed` = resolution
  gamets.
- *Incumbent wins (challenge repelled):* follow the `corroborate()`
  precedent (claims.py:536-544): decay the incumbent to the resolution
  gamets, then `confidence *= (1 - dent)`; verbatim/gist keep their
  decayed values; `last_rehearsed` = resolution gamets.
- The appended Evidence's `strength` follows the `retell()` convention
  (claims.py:344-348): the teller's pre-decay confidence — "the strength
  of the testimony as given."

Rationale: every number above is composed from constants the codebase
already owns; nothing new is invented beyond the (pinned) dent constant
itself.

## Finding 5 — T0.4's model covers only single-slot disagreement; two unaddressed edges

The byte-identical T0.4 body (scenarios/test_tier0_claims_mechanics.py:308-363)
is satisfiable as specified — verified (appendix). But:

- `Variant.mutated_slot: str | None` encodes "exactly one slot mutated
  from its predecessor" (claims.py:104-116). A witness disagreeing on
  **two or more** slots has no representation.
- A T0.4 variant roots at the claim with `parent_variant_id=None` — a
  second *kind* of lineage root the T2.2 rung's "no variant without a
  predecessor" discipline (scenarios/test_tier2_mutation.py:123-130)
  didn't contemplate.
- Task 1's invariant guard names `retell()` but not `witness()`'s
  holder-level duplicate: an NPC who holds a rumor about an event and
  *later witnesses it*.

**Worker recommendation — scope line plus conservative guard:**

- Lane scope: T0.4 handles single-slot disagreement; `witness()` raises a
  clear error on multi-slot disagreement naming the follow-up, rather than
  silently writing a lossy variant. The limitation is named in the code
  comment and the report.
- Lineage pin: "witness-disagreement variants root at the claim by
  design" (`parent_variant_id=None`, `mutated_slot` = the disagreed slot).
- Witness-after-rumor: **raise** at `witness()` this lane (the rung's
  "raises on any duplicate-creating path" read conservatively), with
  "witness-after-rumor auto-resolution" named as a follow-up rung
  candidate. The worker flags the cost honestly: that flow then has no
  write path at all this lane — a real but bounded gap, preferable to
  inventing an unfrozen write path in-lane.

## Finding 6 — Rumor-state bookkeeping unpinned

Resolution re-points `belief.variant_id`, but `RumorState` is keyed
`(npc_id, claim_id, variant_id)` and `rumor_stage_now()` matches the
belief by `variant_id` (claims.py:432-439). Unmaintained, stage queries
for the adopted variant raise `StopIteration`, and T2.5's
dormancy/reactivation misbehaves for every resolved holder.

**Worker recommendation — confirm the coordinator's mechanical ruling,
with one named edge:** `resolve()` records the hearing/telling exactly as
`retell()` does (claims.py:487-494): the hearer heard the incoming
variant, the teller told theirs. The loser's rumor entry *stays* (they
did hear it — event-sourcing discipline), which leaves
`rumor_stage_now(holder, claim, loser_variant)` with no matching active
belief post-supersession; recommend one line in the packet defining stage
queries as valid for the holder's active variant only (a stale-variant
query gets a clear error, not `StopIteration`). The adoption side needs no
re-keying: `_record_hearing` on the incoming variant creates the entry
the re-pointed belief will match.

## Finding 7 — Wording trap in pinned decision 1

"When both parties hold beliefs about the claim *with the same variant*,
the encounter stays `nothing_salient`/`"both-informed"` (**with
corroboration exactly as today**)." Today the encounter path performs **no**
corroboration — `driver.py:468-478` writes `nothing_salient` and
continues; `corroborate()` is scripted-only.

**Worker recommendation — confirm the coordinator's strike:** "same
variant → unchanged `nothing_salient` behavior; the encounter path
performs no corroboration."

---

## Appendix — packet claims verified against the repo

- **T0.4 byte-identical body is satisfiable.** The test calls
  `driver.witness()` twice on one claim id with one differing slot and
  asserts: same claim id, belief's `variant_id` set, variant rooted at the
  claim with the disagreeing slot, canonical claim slots unchanged
  (test_tier0_claims_mechanics.py:331-362). A witness-side variant path in
  `witness()` satisfies it without touching the body.
- **T0.3's raise is unaffected by the T0.4 path.** The
  `pytest.raises(ValueError)` at line 284 uses a *new* claim id for an
  already-claimed event — that raise comes from the `_claim_id_by_event`
  check (claims.py:444-450), upstream of the content-disagreement branch
  T0.4 relaxes.
- **CLI claim verified.** `cli.py:356-370` already lists supersession
  records per claim; the acceptance item is a real verify, not a build.
- **Acceptance arithmetic:** 175+1 xfail → 176+0 after marker removal,
  plus whatever `test_tier2_resolution.py` adds. Consistent.
- Current tree state at review time: `uv run pytest -q` = 175 passed,
  1 xfailed; `uv run ruff check .` clean.

## What the worker needs back

Rulings (confirmations or overturns) on the recommendations above; the
schema amendment for findings 1–2 as one review note. Worker holds until
the rulings addendum lands in the packet, then implements against the
amended packet. No objection to Lane 11 dispatching in parallel — the
trees are disjoint.

---

## Coordinator rulings — 2026-08-23 (planning agent)

All seven recommendations **confirmed**; none overturned. Each was
verified against the code before ruling (constants claims.py:46-49,
`Variant` 104-116, `Evidence` 119-136, schema §4:116-120). The packet is
amended in place; implement against it.

1. **Trilemma → (a) confirmed.** §4:120 amended (one review note covering
   findings 1–2): added `teller_id`, `teller_belief_id`, `evidence_id`,
   `winner_belief_id`. Supersessions stay trace-only; **no new Variant on
   adoption** — the hearer adopts the teller's variant as-held (a
   correction, not a transmission). Re-execution parity (ADR-0007,
   framelog.py:624-630) is load-bearing; the lossy-delta exception (b)
   was rightly rejected.
2. **Null variant confirmed.** §4:120 now annotates
   `loser_variant_id`/`winner_variant_id` as `string | null`, null = the
   claim's original telling — the schema's existing nullability idiom.
3. **Exact tie confirmed: incumbent wins** (challenger must be strictly
   stronger); the record still fires and the standing incumbent takes the
   dent. Packet now requires the exact-tie case in the rung test — post-
   T0.4 it's the default eyewitness-vs-eyewitness case.
4. **Correction semantics confirmed**, composed from existing constants
   exactly as recommended (adoption re-derives via retell()'s decays with
   `first_learned` preserved; repelled challenge follows corroborate()'s
   decay-then-replace; appended evidence strength = teller's pre-decay
   confidence). One gap the worker left open, now pinned by the
   coordinator: **`CONTESTED_CLAIM_CONFIDENCE_DENT = 0.1`**, multiplicative
   (`confidence *= 1 - dent`), tunable-not-derived with the same comment
   discipline as its neighbors — a challenge costs half the retelling
   haircut's 0.2.
5. **T0.4 edges confirmed.** Single-slot scope (multi-slot raises a clear
   error naming the follow-up; limitation named in code comment +
   report); witness-disagreement variants root at the claim by design;
   witness-after-rumor **raises** this lane, auto-resolution named as a
   follow-up rung candidate. The bounded-gap acknowledgment is accepted
   as written.
6. **Rumor bookkeeping confirmed**, including the named edge:
   `resolve()` records hearing/telling exactly as `retell()`; the loser's
   rumor entry stays; stage queries are valid for the holder's active
   variant only — stale-variant query gets a clear error, not
   `StopIteration`.
7. **Wording strike confirmed.** Packet now reads: same variant →
   unchanged `nothing_salient` behavior; the encounter path performs no
   corroboration.

**Schema amendment executed** in `docs/frame-log-schema.md` §4:120 (dated
2026-08-23, citing this review). Coordinator-owned file, amended in the
open per the governance ruling; flagged to the owner in the session
report alongside Track A's earlier outstanding ratification list.

**Lane 12 is cleared for implementation against the amended packet.**
