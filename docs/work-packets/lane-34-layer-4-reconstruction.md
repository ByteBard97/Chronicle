# Lane 34 — dashboard layer-4 reconstruction (Track B, precursor)

**Status:** Ready to start immediately. **Blocks lanes 30 and 31.**
Surfaced by lane 30's pre-dispatch review (verified by the coordinator):
the Python writer serializes full layer-4 state into every keyframe
(`state.relationships/grudges/obligations/reputations/schedules` —
`runs/tier3-demo-01` carries 1/1/2/5/9 respectively), but the dashboard
has no types, no hydration, and no replay for any of it —
`grudge_formed`, `obligation_issued`, `obligation_resolved`,
`reputation_updated`, `threshold_crossed`, `relationship_formed` all
silently no-op in `applyTraceRecord` today.

**Effort:** medium (types + hydration + six replay cases + tests).

## Context

Lane 27 fixed one missing replay case (`supersession`). This lane is
the whole layer: teach the dashboard's reader the social-state data
model the sim has been writing since lane 4. The diff panel (lane 30)
and rule log (lane 31) both build on it — a diff panel without
grudge/obligation/reputation deltas isn't the M4 view at all, which is
why descoping was rejected.

## Read first (in order)

1. `docs/work-packets/reviews/2026-08-23-lane-30/pre-dispatch-review.md`
   — the diagnosis (with the coordinator's ruling appended).
2. `dashboard/src/log/reconstruct.ts` — `SocialState`, keyframe
   hydration, `applyTraceRecord` (the lane-27 `supersession` case is
   your replay idiom).
3. `dashboard/src/log/types.ts:104-106` — the untyped placeholders
   (`Record<string, unknown>[]`) you're replacing with real types; the
   `KeyframeState` shape.
4. `docs/frame-log-schema.md` — §5 (keyframe layer-4 fields) and §4's
   record shapes: :121-128 (`relationship_formed`, `grudge_formed`,
   `obligation_issued`, `obligation_resolved`,
   `reputation_updated`, `threshold_crossed`).
5. The Python field shapes you're mirroring: `chronicle/social.py`
   (`Grudge` :100-118, `Relationship`, `Obligation`, the reputation
   record) — keyframes serialize these verbatim.
6. `runs/tier3-demo-01/` — real keyframes + real trace records of all
   six types to test against.
7. `docs/work-packets/reviews/README.md` — governance.

## Pinned implementation decisions

- **Real types, not `unknown`:** `KeyframeGrudge`, `KeyframeObligation`,
  `KeyframeReputation`, `KeyframeRelationship` in `types.ts`, matching
  the Python fields (social.py) and schema §5. The placeholder
  `Record<string, unknown>[]` fields become typed (readers tolerate
  absence — the M1-era note at types.ts:87 stands).
- **SocialState grows four maps:** `relationships`, `grudges`,
  `obligations`, `reputations` (keyed per the Python store's keys —
  read `chronicle/social.py`'s keying and mirror it; document choices).
- **Replay = apply the recorded outcome** (the lane-27 idiom):
  `relationship_formed` inserts; `grudge_formed` inserts;
  `obligation_issued` inserts, `obligation_resolved` transitions status
  (+ gamets/excuse); `reputation_updated` replaces the keyed
  accumulator with the record's carried values (it carries
  inputs-plus-result, §4:128 — apply the result);
  `threshold_crossed` is trace-only bookkeeping (no state effect —
  verify, don't assume; note in the header).
- **Schedules:** out of scope (M5's schedule-diff lane will need them;
  type the field as optional-passthrough if free, else leave — note in
  the report).
- **Reader tolerance:** older runs without layer-4 keyframe fields
  hydrate to empty maps (the `whiterun-jarl-01` case).

## Task

1. Types (above) + hydration + `SocialState` maps.
2. The six replay cases.
3. Tests: synthetic (each record type's replay; older-run tolerance)
   + real-run against `tier3-demo-01`: hydrate its final keyframe and
   assert the four maps' contents match the Python-side counts
   (1/1/2/5), and reconstruct across the grudge/obligation/reputation
   ticks to verify replay (e.g. at a T before the first post-grudge
   keyframe, the grudge exists via delta replay alone — the lane-27
   test pattern).
4. Consumers stay out of scope (lanes 30/31 build on this) — but
   verify `MapScreen`/`FeedScreen` still pass unedited (empty maps on
   older runs are invisible).

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- Real-run: layer-4 state reconstructs correctly at arbitrary T,
  keyframe-hydrated and delta-replayed — covered by tests.
- Older runs hydrate to empty maps without errors — covered by test.
- No new dependencies; no edits outside File boundaries.

## File boundaries

**Edit:** `dashboard/src/log/types.ts`, `dashboard/src/log/reconstruct.ts`
(+ their tests)

**Do not touch:** views/components (no consumers this lane),
`src/derived/*`, stores, frozen docs, `runs/`, Python

## Conventions

- TS strict; **local commits OK** (path-scoped); never push.
- Existing test assertions immutable; conflicts are findings.
- File a delivery report on disk. Report format: delivered, acceptance
  per criterion with command tails, findings list.
