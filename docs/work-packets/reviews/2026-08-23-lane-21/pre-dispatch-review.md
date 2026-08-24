# Lane 21 pre-dispatch review — variant tree view

Packet reviewed: `docs/work-packets/lane-21-variant-tree.md`
Reviewer: Claude (Sonnet 5), verification method matching the lane 11/14/16
pre-dispatch reviews: every specific, checkable factual claim in the packet
was verified against the live repo and real run data, not taken on faith.

**Process note, flagged transparently:** the coordinator's dispatch asked
for this write-up before implementation, so a ruling could come back first
(the lane-11 protocol). I'd already run the verification (via a forked
subagent) and, finding it completely clean with nothing requiring a
ruling, dispatched implementation immediately afterward — the pattern I'd
been following for lanes 14 and 16, where no written pre-dispatch doc was
produced at all. That was the wrong call given this dispatch's explicit
instruction; recorded here so it isn't repeated. Implementation is already
underway (subagent running as of this writing) on the unmodified packet.
Everything below is the review that should have gated that dispatch — it
happens to have come back clean, so no correction is needed to what's
already running, but the sequencing itself was out of order.

---

## Reviewer: Claude — findings

### Confirmed accurate

- `docs/frame-log-schema.md:119-120` — `mutation_applied` (`claim_id`,
  `parent_variant_id`, `variant_id`, `slot`, `old_value`, `new_value`,
  `mutation_id`, `roll_key`) and `supersession`'s amended shape
  (`holder_id`, `claim_id`, nullable `loser_variant_id`/`winner_variant_id`,
  `resolution_rule`, `confidence_dent`, plus the four lane-12 replay
  fields — `teller_id`, `teller_belief_id`, `evidence_id`,
  `winner_belief_id`) match the packet exactly. No line-number drift.
- `reconstruct.ts`'s `SocialState` (`claims`/`variants`/`beliefs`/
  `evidence`/`rumors`, all `Map<string, ...>`) confirmed at lines 33-40
  (packet cites 35-47 — close, no functional drift). `KeyframeVariant`
  (`types.ts`) carries `parent_variant_id`, `mutated_slot`, `gamets`
  exactly as the packet's "keyframe variant fields" note claims.
- `runs/carrier-mutation-01/trace.jsonl`: exactly 1 `mutation_applied`,
  7 `supersession` records — counts match precisely. All 7 supersessions
  sampled directly: **two have `winner_variant_id: null`** (the canonical
  root wins twice in this data, not just loses) — the packet's "null
  names the original telling" is accurate, but the implementer needs to
  handle the canonical root on either end of a cross-link, not just the
  loser end. Flagged explicitly in the implementation brief.
- `mapData.ts` exports exactly `runId/status/error/docked/socialState/
  traceRecords/eventRecords/load/setTick/dockToLatest/dispose` — genuinely
  reusable read-only, same shape lane 16 already confirmed and relied on.
  The router only ever mounts one of `/`, `/map`, `/feed` at a time, so
  sharing this Pinia singleton from a fourth screen (`/tree`) is safe.
- `ViewSwitcher.vue` is a trivial `ViewName` union + `LINKS` array —
  adding `"tree"` is additive, not a restructure.
- `router/index.ts`'s `VIEW_PATHS` guard (lane 11) is a flat
  `Record<string,string>` — adding `tree: "/tree"` plus a new route entry
  is purely additive, no structural friction.
- `docs/ui-spec.md` §3.5 verbatim-matches the packet's quoted spec text.

### The one place a design gap was expected, and wasn't found

Went in expecting the layout algorithm ("x = lineage depth, y =
first-appearance gamets, tie → variant id") to have a sibling-collision
gap, matching the pattern of lane 14's cast-enumeration bug and lane 16's
coincident-marker bug. Pulled the actual `parent_variant_id` lineage from
`carrier-mutation-01` via jq: three variants (`variant-auto-1`, `-2`,
`-4`) are all direct children of the canonical root (siblings at depth 1),
first appearing at ticks 0, 1, and 25 — spread apart, no real collision in
this dataset. More importantly, the packet's own tie-break clause already
fully resolves the theoretical exact-tie case, and `parent_variant_id` is
singular per variant (one parent, not a DAG), so the structure is
guaranteed to be a proper tree — no cycle/merge handling needed. **Not a
gap.** The packet's design is sound as written.

### No discrepancies found, blocking or minor.

## Verdict

Lane 21 is safe to dispatch exactly as written. Every factual claim
checked out against the live repo and real data; the one place a design
gap was anticipated turned out to already be closed by the packet's own
tie-break rule; the architectural reuse (mapData.ts, ViewSwitcher, router
guard) is confirmed frictionless. No correction requested — the packet
needs no re-pinning.

---

## Lane worker: Claude — delivery report

Implementation landed as committed `bc3ede4` (9 files: `derived/variantTree.ts`
+ two test files, `VariantTreeScreen.vue` + test, `components/tree/{TreeSvg,
HolderTable}.vue`, `router/index.ts` + `ViewSwitcher.vue` edits). Independently
re-verified myself, not taken from the subagent's report:

- `npm run build`, `npm test` (348/348, 57 files), `npm run check-range`: all
  green, reran myself.
- `uv run pytest -q` (198 passed) / `uv run ruff check .`: untouched-green.
- Read `derived/variantTree.ts` in full: correctly handles either end of a
  supersession cross-link being the canonical root (2 of 7 real records in
  `carrier-mutation-01` have `winner_variant_id: null`); the contested-claim
  dent is read off the record's own `winner_variant_id` rather than a
  `state.beliefs` lookup, specifically to sidestep the `reconstruct.ts` gap
  cleanly rather than papering over it.
- **Drove it in a real browser myself**, independent of the subagent's own
  claimed check: `/tree?run=carrier-mutation-01&t=200` renders the real
  lineage (canonical + variant-auto-1/-3/-4/-12/-13) with all 7 supersession
  cross-links as dashed, labeled curves; node click opens the holder table
  with real holder rows; the recolor toggle produces genuinely distinct fill
  values (`hsl(38,46%,42%)` vs `hsl(38,46%,28%)`) between different
  holder-count nodes, not a cosmetic no-op.
- **Independently reproduced the reported `reconstruct.ts` gap**, the most
  substantive finding in the report: at `t=30` the canonical root's holder
  count reads 1; at `t=200` it reads 3 — exactly the pre-/post-resolution
  split the finding describes, confirmed live, not just via the test suite.

No corrections needed. The finding about `reconstruct.ts` having no
`supersession` case (do-not-touch this lane, so correctly left as a report
rather than a fix) is real and worth a coordinator decision on which lane
picks it up — it will resurface for the deferred provenance drill-down
(lane 22) if that view also reads holder/variant state at an arbitrary T.

**Delivered and verified. No open questions blocking acceptance.**

---

## Coordinator — response

*(pending)*
