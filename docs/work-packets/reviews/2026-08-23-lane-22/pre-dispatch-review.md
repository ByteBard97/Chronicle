# Lane 22 pre-dispatch review — provenance drill-down

Packet reviewed: `docs/work-packets/lane-22-provenance-drilldown.md`
Reviewer: Claude (Sonnet 5), same verification method as the lane 11/14/16/21
pre-dispatch reviews — every checkable claim verified against the live repo
and real run data, not taken on faith. **Following the lane-11 protocol this
time: implementation is NOT dispatched pending this review.**

---

## Reviewer: Claude — findings

### Confirmed accurate

- `chain_for` (`chronicle/claims.py:850-866`) walks only the original
  grounding evidence (index 0) back through `predecessor_belief_id` to the
  witness — a single linear chain. `evidence_for` (line 846) returns *all*
  evidence for a belief. The packet's DAG-honesty requirement correctly
  implies combining both, not `chain_for` alone.
- `Evidence` fields (`id`, `belief_id`, `evidence_type`, `source_id`,
  `predecessor_belief_id`, `gamets`, `strength`) at `claims.py:137-153`
  (packet cites ~119-136 — cosmetic ~18-line drift, not blocking).
- Dashboard-side `SocialState.evidence` is `Map<string, KeyframeEvidence>`
  keyed by evidence *id*, not belief id — "all evidence for belief X"
  requires a scan/filter, no index exists. Minor efficiency note, not
  blocking.
- `panels` codec (`urlState.ts`) is a plain `string[]` (comma-joined) — it
  can already express a drill target via a composite string (e.g.
  `"drill:belief-x"`) with **no codec extension needed**, resolving what the
  packet frames as an open risk.
- `docs/ui-spec.md:106` matches the packet's quoted §3.6 text verbatim.
- Real data supports DAG-honesty testing: at keyframe tick 239,
  `belief-auto-relief_caravaneer-4` has 5 distinct Evidence records and
  `belief-auto-ysolda-2` has 4 — genuinely corroborated beliefs exist in
  `carrier-mutation-01`, not just a synthetic-fixture need.

### Finding 1 — the `reconstruct.ts` supersession gap resurfaces here, worse than in lane 21

Lane 21 (landed, `bc3ede4`) found and documented that `reconstruct.ts`'s
`applyTraceRecord` has no `supersession` case — confirmed again here by
grepping the whole file for `"supersession"` and `"winner_belief_id"`: zero
matches. `applyTraceRecord` has exactly four cases (`belief_formed`,
`belief_corroborated`, `transmitted`, `encounter_rolled`/`nothing_salient`).
The four lane-12 replay fields (`teller_id`/`teller_belief_id`/`evidence_id`/
`winner_belief_id`) — added specifically so "the contested hearing is a real
Evidence record appended to the winner's belief, and post-keyframe replay
must be able to rebuild it" — are **entirely unconsumed**.

Concrete manifesting window, confirmed against `carrier-mutation-01`:
supersessions fire at ticks 26-28; the next keyframe is at tick 47. Keyframe
47 *does* bake in the real Evidence records (`evidence-auto-9`/`-11`) with
`predecessor_belief_id` chains back through the contested hearing — but
reconstructing at any T in `[28, 46]` omits them entirely, since nothing in
`applyTraceRecord` ever replays them. **`belief-auto-relief_caravaneer-4` —
the exact belief with 5 Evidence records the packet needs for its
DAG-honesty acceptance test — is also the belief where an early-T walk is
silently incomplete**, not erroring, just shorter than the true chain.

The packet's own text ("read, don't recompute — the reader's reconstructed
values at T are the truth") is asserted without the caveat this finding
demands. Two options for the coordinator: pin the real-run DAG-honesty test
to T≥47 (past the keyframe, sidestepping the gap, same workaround lane 21
used) and document the window as a known limitation; or decide this gap is
now common enough across lanes (21 and 22 both hit it) to warrant a
dedicated `reconstruct.ts` fix in its own lane, rather than each downstream
lane re-discovering and working around it independently.

### Finding 2 — more severe, and blocking: the named invocation points don't render real belief data at all

`NpcInspector.vue` — the component both FeedScreen's and MapScreen's
inspector regions actually render — is **still entirely static fixture
data**. Its own header comment: *"Scope for this lane: the shell + the
Beliefs tab, skinned to the approved mockup... with static, schema-typed
fixture data — Lane 6's reader wires the real per-tick belief list at
integration."* That wiring never happened in any lane since. The belief
cards' confidence/gist/verbatim values, "told-by" chains, and even a
literal `"provenance ▸ 4 hops · 1 mutation"` placeholder link already sitting
in the template are all hardcoded mock strings, regardless of what
`npcName`/`asOfTick` props are actually passed.

**Lane 22's two named invocation points (FeedScreen's and MapScreen's
inspectors) don't display a single real belief today.** Implementing the
drill affordance exactly as scoped would attach a real, correct
`provenance.ts` derivation to fake, hardcoded belief ids with nothing real
underneath it — the panel would open, but drilling from it would either
show nothing matching or require inventing a fake belief id to demo against,
neither of which is what this lane is for.

This isn't a "proceed and file a finding" situation the way lanes 14/16/21's
gaps were — those were narrow, self-contained corrections inside the lane's
own boundaries. This is a scope question: either lane 22 must expand to
include wiring `NpcInspector.vue` to real beliefs first (a significant,
currently-unbounded addition, and `NpcInspector.vue` isn't in this packet's
Create/Edit list), or the packet needs a different, already-real invocation
point to drill from. No such point obviously exists yet — feed rows and map
markers don't render individual beliefs either, only summary/outcome data.

## Verdict

**Not safe to dispatch as written.** Two things need a coordinator decision
before implementation:

1. The `reconstruct.ts` supersession-replay gap needs either an explicit
   at-T caveat added to the "read, don't recompute" instruction (pin the
   real-run test to T≥47) or a decision to fix `reconstruct.ts` itself in
   its own lane, given this is now the second lane to hit the identical gap.
2. `NpcInspector.vue` is unwired mock data — lane 22 needs either an
   expanded scope to wire it to real beliefs first, or a different,
   already-real invocation point. Recommend the coordinator pick one before
   this lane starts, rather than have an implementer discover this mid-lane
   and improvise a scope expansion unsupervised.

---

## Coordinator — response

*(pending)*

---

## Coordinator ruling — 2026-08-23

Both findings verified against the repo and **accepted**; the lane is
re-sequenced, not redesigned.

**Finding (a) — supersession replay gap (blocks this lane): accepted.**
Lane 27 (`lane-27-supersession-replay.md`, already written) covers it —
its scope includes replaying the appended Evidence record
(`evidence_id`/`teller_id`/`teller_belief_id` from the amended §4:120
payload), which is exactly the chain-completeness case the reviewer
identified (`belief-auto-relief_caravaneer-4`, ticks 28–46). **Ruling:
lane 27 lands before lane 22.**

**Finding (b) — the invocation points are fixture data: accepted, and
it's the worse of the two.** Verified directly: `NpcInspector.vue`'s
Beliefs tab renders static fixture content (its own header has promised
the lane-6 wiring "at integration" since M1 — it never happened). The
reviewer is right that the packet's "attach the drill gesture to the two
inspectors" would have wired real provenance to fake belief ids.
**Ruling: new lane 28 (`lane-28-inspector-real-data.md`) wires the
inspector to real beliefs first — a transplant the whole dashboard needs
anyway, not drill-down-specific scope creep.** Lane 22's invocation
points are amended in-packet: the real inspector (post-28, both hosts)
plus the variant tree's holder table (lane 21 has since landed — the
original deferral is moot).

**Dispatch order: 27 → 28 → 22.** The packet's status section and
invocation-point pinning are amended to match. The review protocol
worked exactly as designed — thanks for holding the dispatch.
