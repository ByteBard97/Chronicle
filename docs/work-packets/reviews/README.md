# Reviews — overseer protocol and log

The overseer agent (planner/reviewer) evaluates lane deliverables against
their packet's acceptance criteria before anything is committed. One
subdirectory per review round: `reviews/<date>-<lane>/` containing the
agent's report, the overseer's findings, and the verdict
(accepted / accepted-with-fixes / returned).

## What every delivered lane must include

1. **The report** (per packet rule 5): what was delivered, acceptance
   status per criterion, and a findings list.
2. **The diff** — the overseer reviews files, not summaries.
3. **Test evidence**: `uv run pytest` and `uv run ruff check .` output
   for code lanes (paste the tail).

## Overseer checklist per delivery

- [ ] Every factual claim about existing code/docs verified against the
      repo (file + line), not trusted from the report.
- [ ] Acceptance criteria from the packet checked one by one.
- [ ] File boundaries respected (packet's create/edit/do-not-touch).
- [ ] No edits to frozen docs (`ui-spec.md`, `scenario-ladder.md`,
      `ui-doctrines.md`) — findings about them route to a review cycle.
- [ ] No test-assertion edits; no commits by the lane agent.
- [ ] Consistency across documents: if the delivery changes an interface
      another lane depends on (RNG keys, schema fields, constants), the
      dependent packets still describe reality.
- [ ] Then: overseer runs the test suite itself, commits with the
      project's message conventions, and updates the status table.

## Lane status

| Lane | State | Review |
|------|-------|--------|
| 1 — keyed-randomness ADR | delivered + overseer-aligned to schema (`roll_key` members, purpose strings) | accepted — flipped to `status: accepted` |
| 2 — frame-log schema | delivered (v1, 226 lines) | accepted — field names verified against code; tier discipline correct |
| 3 — tick quantum | delivered (ADR-0010 + claims.py rebaseline, commit 5b168e7) | accepted — overseer re-verified: 52 pytest green, ruff clean, unit+derivation+rule comments present |
| 4 — M0 substrate | **unblocked** (1–2 landed; 3 parallel-safe) | — |
| 5 — M1 scaffold | delivered + verified (npm ci/build clean, 27 vitest green, check-range 206 on both servers) | accepted |
| 6 — M1 reader + chrome | packet ready | — |
| 7 — design system + M1 styling | packet ready (design vendored at `dashboard/design/`) | — |
| design — M3 mockups | converged: merged register, both salience modes, docked-LIVE, storyboard all approved | pending token sheet + Markarth label fix, then frozen |
