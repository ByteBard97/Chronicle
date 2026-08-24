# Lane 30 pre-dispatch review — M4 diff panel

Packet reviewed: `docs/work-packets/lane-30-diff-panel.md`
Reviewer: Claude (Sonnet 5), same verification method as every prior
pre-dispatch review this session — every checkable claim verified
against the live repo and real run data, not taken on faith.
**Following the lane-11 protocol: implementation is NOT dispatched
pending this review.**

---

## Finding — the panel's entire premise doesn't hold: `SocialState` has no layer-4 data at all

The packet's "Read first" item 4 says to read `reconstruct.ts` for "the
`SocialState` shape incl. layer-4 (grudges/obligations/reputation
Maps)" — treating this as existing substrate to build on. It doesn't
exist. Verified directly:

- `reconstruct.ts`'s `SocialState` interface has exactly six fields:
  `tick`/`claims`/`variants`/`beliefs`/`evidence`/`rumors`. No grudge,
  obligation, or reputation field of any kind.
- `applyTraceRecord`'s switch has cases for `belief_formed`,
  `belief_corroborated`, `transmitted`, `supersession` (lane 27), and
  `encounter_rolled`/`nothing_salient` (no-op) — nothing for
  `grudge_formed`, `obligation_issued`, `obligation_resolved`,
  `reputation_updated`, or `threshold_crossed`. All five silently
  vanish into the `default` skip-and-continue branch today.
- `types.ts`'s `KeyframeState` has `grudges?`/`obligations?`/
  `reputations?` fields, but they're typed as bare
  `Record<string, unknown>[]` — no `KeyframeGrudge`/`KeyframeObligation`/
  `KeyframeReputation` interfaces exist, and `fromKeyframeState` never
  reads them into `SocialState`.
- Grepped the whole dashboard: **zero** files read reconstructed
  grudge/obligation/reputation state. The only related hit is
  `mapMarkers.ts`'s own comment self-documenting this exact gap ("G
  (grudge) need Tier 3/4 state the reader doesn't reconstruct"), plus
  `timelineMarkers.ts` reading a raw `grudge_formed` trace record
  directly off the trace stream (bypassing `SocialState` entirely) just
  to render one cosmetic timeline-marker label.
- The Python side is fully wired and the data is real and present:
  `chronicle/framelog.py`'s `serialize_state` writes non-empty
  `grudges`/`obligations`/`reputations` arrays into every keyframe.
  Confirmed in `runs/tier3-demo-01`'s two keyframes (ticks 23, 47):
  `grudges=1, obligations=2, reputations=5` at each. The data is there
  on disk — nothing on the TypeScript side has ever been taught to read
  it.

This is categorically bigger than lane 27's gap (one missing trace
record type between keyframes, on data the reader otherwise already
modeled). Here, the entire keyframe-level data model for three of
`SocialState`'s conceptual layers doesn't exist on the dashboard side —
not the types, not the keyframe hydration, not any trace-record replay
case. A diff panel that's supposed to show "grudge formed/decayed,
obligation transitions, reputation moves" (the packet's own Task 1 list)
has nothing to diff.

### What this blocks specifically

Lane 30's Task 1 (`socialDiff.ts`) asks for delta rows covering "grudge
formed/decayed-crossing, obligation transitions, reputation moves" —
none of that is computable without first: (a) typing
`KeyframeGrudge`/`KeyframeObligation`/`KeyframeReputation`, (b) reading
them off keyframes in `fromKeyframeState`, and (c) adding
`applyTraceRecord` cases for the five record types above (`grudge_formed`,
`obligation_issued`, `obligation_resolved`, `reputation_updated`,
`threshold_crossed`) so between-keyframe deltas are correct too — the
identical "stale until next keyframe" failure mode lane 27 fixed for
supersessions would otherwise recur across every one of these five
record types simultaneously.

Belief/claim/stage deltas (the panel's other half — confidence changes,
new/lost beliefs, stage transitions) **are** fully computable today;
`SocialState` already models that layer correctly and lane 27 closed
its one known gap.

### Confirmed accurate (everything else)

- `docs/ui-spec.md` §3.7 matches the packet's quoted text verbatim.
- `urlState.ts`'s `filters` codec (`Record<string, string>` via
  `filtersCodec`) can already hold `npc`/`rule`/`type` keys with zero
  codec changes — the packet's claim holds.
- `runs/tier3-demo-01` has exactly 2 keyframes (ticks 23, 47; run length
  48) — a T1=47/T2=23 pair is directly testable against real data, and
  lane 29's `LOOP_START_TICK=4` fix didn't change the keyframe cadence.
- Real `rule_evaluated`/`grudge_formed`/`reputation_updated`/
  `threshold_crossed` samples pulled from `tier3-demo-01/trace.jsonl` —
  field shapes confirmed, available for whoever wires the reader.
- Minor, non-blocking correction to the reading list: item 6 groups
  lane 22's `panelUrlState.ts` (drill-panel-specific, hardcoded
  `"drill:"` prefix against the `panels` codec) together with the rule
  chip's `/rules?filters=...` link target, which needs a *different*
  codec (`filters`) and no special helper at all — just
  `filtersCodec.encode` directly. Worth a one-line packet correction so
  an implementer doesn't go looking for a reusable pattern that doesn't
  apply here.

## Verdict

**Not safe to dispatch as written.** The gap is large enough that I
don't think it's mine to silently absorb into lane 30's scope the way
lane 16 absorbed its two self-contained UI bugs — this is a
data-modeling decision (new types, a fromKeyframeState extension, five
new `applyTraceRecord` cases) that changes `SocialState`'s public shape,
which lane 30's own file boundaries explicitly forbid touching
(`src/log/*` is "read/reuse — findings only"). Two ways to resolve:

1. **A precursor lane** (the lane-27-style pattern): teach
   `reconstruct.ts` to model and replay grudges/obligations/reputation
   first — types, keyframe hydration, and all five trace-record cases —
   then lane 30 builds `socialDiff.ts` on real substrate. This is
   larger than lane 27 (five record types instead of one, plus new
   types), but it's also the SotB the M4 rule-firing log (lane 31) and
   any future NPC-inspector "grudges/obligations held" tab will need
   too — not a one-off cost for lane 30 alone.
2. **Descope lane 30 to belief/claim/stage deltas only** for now (fully
   supported today), ship that, and follow with a second diff-panel
   pass once the layer-4 reader substrate lands. Risk: the packet's own
   Task 1 and ui-spec §3.7 both frame the full social-state diff
   (not just beliefs) as the point of the panel — a beliefs-only first
   cut may not satisfy the spec's intent, and rule chips would have
   nothing to link to for the grudge/obligation/reputation rules that
   fired in the window.

I'd lean toward (1) given how much of Tier 3's own record vocabulary
(rule_evaluated's inputs reference grudges/obligations directly) and
lane 31's rule-firing log both sit downstream of the same gap — but
that's a scope/sequencing call, not mine to make unilaterally.

---

## Coordinator — response

*(pending)*

---

## Coordinator ruling — 2026-08-23

**Option 1 — the precursor lane.** Verified independently before ruling:
the Python writer's keyframes carry full layer-4 state
(`state.relationships/grudges/obligations/reputations/schedules` =
1/1/2/5/9 in `tier3-demo-01`), while `types.ts` holds untyped
`Record<string, unknown>[]` placeholders (:104-106) that nothing reads
and `reconstruct.ts` has no hydration or replay for any of the six
layer-4 record types. The review's framing is exactly right — a whole
missing data layer, not another lane-27-sized case.

Descoping (option 2) was rejected: a diff panel without
grudge/obligation/reputation deltas isn't the §3.7 view at all — Tier 3
is the social-state tier; claims-only diffing is M3.5, not M4.

**New lane 34 (`lane-34-layer-4-reconstruction.md`) is the precursor:**
real types, keyframe hydration, `SocialState` layer-4 maps, and the six
replay cases, against real `tier3-demo-01` data. **Dispatch order:
34 → 30 → 31.** Lane 30's packet needs no amendment (its premise was
right; the substrate just hadn't been built yet). The review protocol
has now caught two whole-layer gaps before they shipped — this is the
process working as designed.
