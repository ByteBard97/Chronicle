# Lane 27 — dashboard: supersession replay in reconstruct.ts (Track B)

**Status:** Ready to start immediately. The gap is fully diagnosed with
a live reproduction (lane 21's module header,
`src/derived/variantTree.ts:44-63`): `applyTraceRecord` has no
`supersession` case, so delta replay between a supersession's tick and
the next keyframe shows stale variant assignments. The amended §4:120
payload carries everything needed for exact re-execution (lane 12's
replay fields — that amendment exists precisely for this).

**Effort:** small (one replay case + tests).

## Context

Lane 12 gave the **Python** reader exact supersession re-execution;
the dashboard's TypeScript reconstructor was never taught the same
record. Until this lands, every dashboard view that reads reconstructed
state (map stages, tree holder counts, future drill-down) is silently
wrong for T in (supersession tick, next keyframe) — keyframes every 24
ticks mask it afterward. M3's correctness depends on it.

## Read first

1. `dashboard/src/derived/variantTree.ts:44-63` — the diagnosis +
  live repro (ticks 26–28 supersession chain, keyframe at 47).
2. `docs/frame-log-schema.md` §4:120 **as amended** — the payload:
  `holder_id`, `claim_id`, nullable loser/winner variant ids,
  `resolution_rule`, `confidence_dent`, `teller_id`,
  `teller_belief_id`, `evidence_id`, `winner_belief_id`.
3. `dashboard/src/log/reconstruct.ts` — `applyTraceRecord` (the
  `belief_formed`/`transmitted` cases to mirror; the unknown-type skip
  path :245-249) and the `SocialState` belief/evidence shapes.
4. The Python semantics you're mirroring: `chronicle/claims.py`
  `resolve()` — correction semantics (re-point variant, dent, appended
  evidence). You don't reimplement the *decision*; you apply the
  *recorded outcome*.
5. `dashboard/src/derived/variantTree.realRun.test.ts` — the test that
  pins the buggy T=30 behavior today (see Task 3's authorized edit).

## Pinned implementation decisions

- **Apply the recorded outcome, don't re-derive the rule:** on a
  `supersession` record, re-point the holder's belief (via
  `winner_belief_id`) to `winner_variant_id` (null → canonical), apply
  the dent (`confidence *= 1 - confidence_dent` — matching the
  corrected-confidence semantics; if the Python re-derive differs in
  base, match the *Python reader's* reconstructed values — verify
  against `chronicle/framelog.py`'s replay), and append the recorded
  evidence (`evidence_id`, reported, source = `teller_id`,
  predecessor = `teller_belief_id`).
- **Reader-tolerance is the floor:** unknown/garbled fields must not
  crash replay (the reader's existing discipline).

## Task

1. `reconstruct.ts`: the `supersession` case in `applyTraceRecord`.
2. Tests: synthetic (resolution mid-window between keyframes — belief
   re-pointed, dent applied, evidence appended; null-winner →
   canonical) + real-run: at T=30 in `carrier-mutation-01`,
   `relief_caravaneer`/`ysolda` show their **resolved** variants.
3. **Authorized test edit:** `variantTree.realRun.test.ts`'s T=30
   expectations were pinned to the buggy behavior ("both pinned" per
   the module header) — update *those specific assertions* to the
   corrected state. This is the only test-file edit allowed; the test's
   T=200 assertions must not change (they were already correct).

## Acceptance

- `npm run build`, `npm test`, `npm run check-range` green;
  `uv run pytest -q` untouched-green; ruff clean.
- Real-run: T=30 shows resolved variants; T=200 unchanged.
- No edits outside `src/log/reconstruct.ts` (+ its test) and the one
  authorized assertion update in `variantTree.realRun.test.ts`.

## File boundaries

**Edit:** `dashboard/src/log/reconstruct.ts`, its test,
`dashboard/src/derived/variantTree.realRun.test.ts` (T=30 assertions
only)

**Do not touch:** everything else — findings, not edits.

## Conventions

- TS strict; **local commits OK** (path-scoped); never push.
- Report format: delivered, acceptance per criterion with command
  tails, findings list.
