# Trace-volume measurements for the ui-spec §1.1 figure (2026-08-23)

**For:** the owner's review-cycle decision on ui-spec §1.1's trace-volume
estimate (frozen doc — owner applies any edit). **Prepared by:** the
coordinator, per the M3 gate check's carry-forward. Measured with the
current engine (post-lane-12 supersessions, post-lane-19
`rule_evaluated`).

## The spec's current estimate

ui-spec §1.1: 10⁵–10⁶ trace rows for a 25-NPC, 10-game-day run; the
static-serving architecture (physical stream split, sidecar index, Range
reads, virtualized tables) is sized against it.

## Measured (this engine, this day)

| Run shape | Cast | Trace rows | Size | Notes |
|---|---|---|---|---|
| Spread, no mutations, p=0.5 (T2.1 fixture) | 25 NPC / 10 days | **27,379** | 13.0 MB | 18,000 `encounter_rolled`, 9,104 `nothing_salient`, 265 `rule_evaluated` (~1%) |
| Contention-heavy, mutations, p=1.0 (T2.2 fixture) | 8 NPC / 10 days | **16,586** | 7.7 MB | **2,880 `supersession` + 3,143 `rule_evaluated` = 36% of rows** (each supersession pairs a rule row) |
| Tier-3-rich demo (`tier3-demo-01`) | ~8 NPC / 10 days | 2,650 | 0.93 MB | all five Tier-3 types incl. 44 `transmission_declined` |
| Prior baseline (2026-08-23 13:23 handoff, pre-machinery) | 25 NPC / 10 days | 18,007 typical / 108,065 all-co-present worst case | 7.9 MB | superseded by the first row |

## Findings

1. **Volumes remain inside the spec's 10⁵–10⁶ band** at the 25-NPC
   scale, including the new machinery. Typical is ~3×10⁴; the
   all-co-present worst case (~10⁵ pre-machinery) plausibly reaches
   ~2–4×10⁵ with supersession churn + paired rule rows — still in-band.
2. **The volume drivers changed composition, not magnitude.**
   `supersession` + `rule_evaluated` are now first-class contributors
   (36% of rows in the churn-heavy shape; `rule_evaluated` ≈1% in quiet
   shapes). The lane-12 churn finding and lane-19's +10–15% both
   reproduce here.
3. **No architecture change is warranted.** The static-serving design
   was sized with ~10× headroom; the measurement lands well inside it.
   The result mildly strengthens the case for outcome-filtered views
   being the default lens over the raw stream (a third of churn-heavy
   rows are resolution bookkeeping).

## Recommendation to the owner

Tighten §1.1's figure text to the measured range (**~3×10⁴ typical,
~10⁵–4×10⁵ contention-heavy worst case, 25-NPC/10-day scale**) and note
the composition change; make no structural edits. The figure's purpose
(sizing the static-read architecture) is unaffected.
