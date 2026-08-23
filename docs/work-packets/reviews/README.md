# Reviews — overseer protocol and log

## Governance (owner-settled 2026-08-23)

**The owner has assigned a managing agent.** The primary planning agent
(the Kimi session lineage that produced `HANDOFF-2026-08-23-1325.md`,
Track B) is the project's planner/coordinator/reviewer. Its job:

- Plan what happens next and write lane packets.
- Portion work out to other agents (lane workers).
- Review delivered work against packet acceptance criteria, run the
  battery itself, integrate, and commit.

It is **not** a bulk code-editing role. All other sessions (Kimi, Claude,
or otherwise) are lane workers: check this board before starting, claim
lanes here first, stay inside packet file boundaries, and do not edit
this status table or assume the coordinator role. This supersedes the
"no managing agent" note in `HANDOFF-2026-08-23-1323.md` — that session
never received the assignment. The collisions of 2026-08-22/23 (ADR-0009
clobber, lane 8/9 numbering, mid-flight table edits) trace to that
ambiguity and are considered closed by this ruling.

**Commit policy (owner-settled 2026-08-23, second ruling):** local
commits are fine for everyone — lane workers may commit their own lane's
files directly (path-scoped, explicit adds, never `-a`/`-A`; the lane-11
and lane-14 pattern). Local history is easy to undo. What requires
explicit owner permission is **pushing to a remote** (GitHub) — no
worker or coordinator pushes without it. The coordinator still reviews
every delivered lane (post-commit where applicable) and can require
fixes or revert. This supersedes the "No `git commit` in any lane"
convention line in older packets and in `docs/work-packets/README.md`
rule 2.

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
| 8 — map conversion + visual parity | delivered (commits `28b81d6`…`dbdd1e2`; Kimi ran out of session usage partway through the follow-on Tier-2/mutation work, picked up and closed out in `da6785b`) | accepted — `make check` green (133 pytest + 1 xfail, ruff clean, dashboard build/132 vitest/check-range 206). One real integration bug found and fixed: `npm run visual-diff` was screenshotting the Vue app's root route ("/", Shell.vue's M1 chrome) against the M3 map mockup instead of `/map` (MapScreen.vue) — inflated the diff to 25.05%; pointed at the right route it's 4.84%, mostly font-rendering noise against a static HTML mockup. Map region itself is visually faithful |
| 9 — M1 agent-debug CLI + pytest deep links | delivered, commit `f8e68f9` (packet renumbered from a collided "lane 8" — `docs/work-packets/lane-9-m1-cli-and-deep-links.md`); the `EVENT_TYPES` bug it found was fixed in `575ca10` | accepted — `InjectionConsole.vue` now offers the three real Tier-0 event kinds and its CLI invocation matches `inject`'s flags exactly. pytest and ruff green |
| 10 — map/timeline component tests + coverage pass | delivered (packet `a50a64c`; tests `555b8e1` + coverage guards `cc9f2ab`/`a8e8c30`) | accepted — 175 pytest + 1 xfail, ruff clean, 132 vitest green (from `make check` battery, handoff 13:25); board row added post-hoc by the planning agent |
| 11 — M2 encounter-feed view | delivered, commit `3ef4745` | accepted — coordinator independently re-ran the battery: 237/237 vitest, build clean, check-range 206 dev+preview; zero new deps; file boundaries respected (two honest extras flagged in the report: `ViewSwitcher.vue` and a `view=` router guard fixing a real packet defect — the worked deep link would have silently rendered Shell). 2 pytest failures in the tree at review time are lane 12 mid-flight, not this lane (zero Python touched) |
| 12 — T2.3 conflicting-variant resolution | delivered + dispositions applied (overseer review in `reviews/2026-08-23-lane-12/`) | accepted — coordinator re-ran the battery: 183 passed / 0 failed / 0 xfailed, ruff clean; marker-only T0.4 edit verified byte-for-byte; re-hearing carve-out + two in-seam guard rails reviewed and accepted; schema §4:120/§4:117 amended by the coordinator with dated notes; T2.2 resolution-churn finding logged to the owner-review backlog; committed `6235a1a` |
| 13 — T2.6/T2.7 mobile carriers | delivered (report in `reviews/2026-08-23-lane-13/`) | accepted — coordinator re-ran the battery: 185 passed / 0 failed / 0 xfailed, ruff clean; zero engine changes verified (`git diff chronicle/` empty); rung assertions verified in-test (exact ticks 96/24/25/120, chain walks, zero-supersession + zero-road guards, kill-phasing anti-vacuity guard). Tier 2 executable surface closed except parked T2.4 |
| 14 — map → real data wiring (M3 prep) | delivered + worker-committed `8d82e8a` (pre-review commit, same as lane 11 — see governance note below) | accepted — coordinator re-ran the battery post-commit: 274/274 vitest, build clean, check-range 206, 185 pytest, ruff clean; boundaries clean (11 files, all in packet lists; lane-10 tests unedited). Two real packet defects caught + fixed by the worker, verified in `mapMarkers.ts`'s module header: cast enumeration extended with relationship endpoints + `npc_died` subjects (the packet's union silently dropped `jarl_balgruuf` — dies at tick 0, never believes, never a trace participant); the "locations static per run" framing was wrong (Proventus moves mid-run) — the pinned latest-observation-≤T rule handles it correctly |
| 15 — dashboard hygiene batch (Markarth label, RunPicker default, 416 backoff) | delivered + worker-committed `d5226d7` | accepted — coordinator re-ran the battery: 320/320 vitest, build clean, check-range 206, 196 pytest, ruff clean; backoff verified per packet spec (double-on-416, 10s cap, reset-on-progress, interface unchanged). **Markarth label collision retired: does not reproduce** — worker measured at 3 viewports incl. the harness's 1600×900 with the visual-diff tool, both salience variants; no fix invented for a bug that isn't there (correct discipline). Minor protocol note: no filed delivery report — captured from the worker's session summary |
| 16 — TimelineBar → real data (M3 timeline) | delivered + worker-committed `c268a8b` | accepted — coordinator re-ran the battery: 308/308 vitest, build clean, check-range 206, 186 pytest, ruff clean; boundaries clean (timeline components + derived module only; no MapScreen edit needed). Two jsdom-invisible bugs found by the worker's live-browser verification (playhead eating clicks; coincident markers unclickable — collapsed into combined-label nodes) — the browser-verification rule earns its keep again |
| 17 — carrier+mutation demo run + CLI polish | delivered + worker-committed `e558dfc` | accepted — coordinator spot-verified: 7 supersessions + 1 mutation in the trace (exact report match), Markarth belief via CLI at the pinned arrival tick, 186 passed / 0 failed / 0 xfailed, ruff clean. Run dir is local-only (`.gitignore:18` ignores `runs/` — worker's finding 2 corrects the packet's stale integration note). Finding 1 (CLI `trace` supersession filter under-reports once a loser variant is held by nobody) → future cli.py hygiene lane |
| 18 — Tier 3 design prep (rule registry + tell-decision design doc) | delivered, worker-committed `9de84de` | accepted — overseer review in `reviews/2026-08-23-lane-18/`; all citations spot-verified; F2 downgraded (escalation event type already reserved in schema §3:95 — coordinator fills fields at L-C). O1–O5 **ruled** (owner delegated): run-config → runs/index.json; grudge half-lives 672/336 tunables; victim==holder documented bypass; budget 17/20; rule name in `rule`, sub-reason in `inputs` |
| 19 — Tier 3 L-A: rule-registry core | delivered + worker-committed `8a83e41` | accepted — 196 passed, ruff clean; 190 pre-existing tests unedited with wiring live (no-behavior-change holds); replay tolerance of `rule_evaluated` rows verified by the worker via `state_at`. Judgment calls reviewed and accepted: toggle-suspends-instrumentation-only for wrapper rules (real toggles only for driver-owned rules 6/7 — honest R2 consequence, documented); rule 6 evaluates per tick-with-pairs not per roll (volume discipline); rule 4 flag driver-scoped; rule 3 covers scripted path only. +10–15% trace volume feeds the §1.1 backlog item |
| 20 — Tier 3 L-B: grudge decay | delivered + worker-committed `231aceb` | accepted — ruled constants present with placeholder comments; `grudge_at` pure decay-at-read; ordering asserts green; 4 new tests, no edits. Judgment call accepted: cooled-floor compares decayed severity composite (component-level gating deferred to T4b if wanted) |
| 21 — variant tree view (M3 §3.5) | delivered + worker-committed `bc3ede4` | accepted — coordinator re-ran the battery: 348/348 vitest, build clean, check-range 206, 198 pytest, ruff clean; pre-dispatch review came back fully clean (canonical-root-on-winner-end verified in tests). Surfaced one real gap, now a lane: dashboard `reconstruct.ts` doesn't replay `supersession` records (stale variants between supersession tick and next keyframe) → lane 27. Protocol note: pre-dispatch review should gate implementation (self-flagged by the worker); delivery reports should be filed on disk |
| 22 — provenance drill-down (M3 §3.6) | packet written; dispatchable in parallel with 21 (invocation points on landed screens only) | in flight |
| 23 — Tier 3 L-D: tell-decision gate | delivered + worker-committed `50e7357` | accepted — 198 passed, ruff clean; rung asserts verified (48/48 declines counted against encounter_rolled, not hardcoded; roll_key null on motive declines; T2.3 path untouched; only the two lane-19 stub assertions moved — flagged pre-build). `transmission_declined` has its producer — M4's fourth outcome state unblocked |
| 24 — Tier 3 L-C: accumulation-threshold | packet written; serial after lane 23 (driver.py) | queued |
| 25 — Tier 3 L-E: obligation violation cascade | packet written; serial after lane 24 | queued |
| 26 — Tier 3 L-F: observer-local reputation wiring | packet written; serial after lane 25 | queued |
| 27 — dashboard supersession replay (reconstruct.ts) | packet written (lane-21 finding); Track B, after lane 22 | pending dispatch |
| design — M3 mockups | converged and frozen: token sheet delivered + vendored (`dashboard/design/`, c7f3d44) | Markarth label collision fix noted for the M3 build |
