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
| 1 — keyed-randomness ADR | drafted by overseer (ADR-0009, `status: proposed`) | awaiting owner adjudication |
| 2 — frame-log schema | dispatched | — |
| 3 — tick quantum | dispatched | — |
| 4 — M0 substrate | blocked on 1–3 | — |
| 5 — M1 scaffold | dispatched | — |
| design — M3 mockups | converged: merged register, both salience modes, docked-LIVE, storyboard all approved | pending token sheet + Markarth label fix, then frozen |
