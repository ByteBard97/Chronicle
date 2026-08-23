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
| 4 — M0 substrate | delivered (driver/framelog/rng + keyed schedule rework) | accepted — overseer verified: 75 pytest green, ruff clean, no scenario assertion changes, reconstruction + index-rebuild proofs present; all three findings reconciled into `docs/frame-log-schema.md` §7/§9 (keyframe seq rule formalized; social-mutation trace gap and `_rumor_sources` reconstruction documented as known M0-scope limitations, not bugs) |
| 5 — M1 scaffold | delivered + verified (npm ci/build clean, 27 vitest green, check-range 206 on both servers) | accepted |
| 6 — M1 reader + chrome | delivered, commit `0806811` | accepted — independently re-run: 24 test files/119 tests green, build clean, check-range 206 dev+preview |
| 7 — design system + M1 styling | delivered, commit `b080dd2` | accepted — independently re-run alongside lane 6 (same suite, above); self-fixed one bug (`--marker-halo` -> `--c-marker-halo`) before landing |
| 8 — map conversion + visual parity | in flight (overseer subagents 8a/8b; foundation 28b81d6) | — |
| 9 — M1 agent-debug CLI + pytest deep links | delivered, commit `f8e68f9` (packet renumbered from a collided "lane 8" — `docs/work-packets/lane-9-m1-cli-and-deep-links.md`) | needs coordinator decision, not yet accepted: `inject` was built to match `InjectionConsole.vue`'s flag names, but the console's default `EVENT_TYPES` (`claim_born`, `mutation`, `grudge_formed`, `threshold_crossed`) don't correspond to any real `events.py` event kind or existing trace-record type — the console's own affordance would be rejected by every subcommand call it composes. pytest and ruff green (independently re-verified: 93 passed, all checks passed) |
| design — M3 mockups | converged and frozen: token sheet delivered + vendored (`dashboard/design/`, c7f3d44) | Markarth label collision fix noted for the M3 build |
