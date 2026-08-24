# Lane 53 — M7: the stranger walkthrough, release gate (Track B, QA)

**Status:** After **lanes 49 and 52** land (the north-star demo run +
the role inspector — the walkthrough's data and views). This is the
dashboard v1 release gate (build plan §M7). It is a **verification
lane, not a feature lane**: you execute the frozen walkthrough against
the real dashboard in a real browser and document what actually happens.

**Effort:** medium (careful, browser-driven verification + a findings
dossier).

## Context

The frozen acceptance test (ui-spec §5, verbatim):

> A person who has never seen the tool, given a completed Tier-6 run
> and one sentence ("the Jarl was assassinated — find out what
> Markarth believes and why it's wrong"), can within ten minutes and
> zero coaching: (1) find the assassination on the timeline; (2) scrub
> and watch the rumor overlay spread, including the carrier hop; (3)
> click a Markarth believer, read the belief, notice the variant badge;
> (4) open the variant tree, identify which slot changed at which hop;
> (5) drill provenance from belief to dagger through the mutation;
> (6) copy the URL and have it reproduce the view. Each step is a
> usability test case; **failure of any step is a spec bug, not a user
> error.**

Plus the developer twin (ui-spec §5): every ladder assertion type's
failure deep link lands within one click of the offending record,
including the named negative-row landing cases (T1.3 rolled-against,
T3.4 declined-by-rule, nothing-salient — all three now have producers).

## Read first (in order)

1. `docs/ui-spec.md` §5 (both walkthroughs, verbatim) and §0 (the
   doctrines a failure violates).
2. `runs/north-star-01/` (once lane 49 lands) — the walkthrough's run.
3. The views the steps exercise: timeline (16), map overlay (14/35),
   inspector (28), variant tree (21), drill-down (22), URL state (§1.2).
4. The developer-twin deep-link mechanism (lane 9's conftest fixture,
   lane 11's landing cases, lane 30's T3.4 case).
5. `docs/work-packets/reviews/README.md` — governance.

## Task

1. **The stranger walkthrough, executed for real:** a fresh browser
   profile, `runs/north-star-01` served, the one-sentence prompt. Do
   the six steps in order, unaided, timing the whole. Where you can't
   be a stranger (you know the tool), say so per step and note what
   you had to *already know* — that knowledge gap IS the finding.
2. **The developer-twin sweep:** for each named landing case (T1.3,
   T3.4, nothing-salient), emit the deep link from the failing
   assertion and verify it lands within one click of the offending
   record (and T3.4's rule name is readable without scrolling).
3. **The dossier** (`docs/work-packets/reviews/<date>-m7/`): per step,
   pass/fail + evidence (screenshot or URL), and every failure filed
   as a spec bug with the doctrine it violates and a proposed fix
   lane. **Any step failing = the gate fails** — report, don't patch.
4. If the gate passes cleanly: say so, with the evidence.

## Acceptance

- The dossier exists with per-step evidence and either (a) a clean
  pass, or (b) a complete spec-bug list with fix-lane proposals.
- No code changes in this lane (a step failing is a finding, not a
  fix — fixes are their own lanes).

## File boundaries

**Create:** `docs/work-packets/reviews/<date>-m7/` (the dossier)

**Do not touch:** code, fixtures, runs — this is verification only.

## Conventions

- **Local commits OK** (path-scoped, atomic `add && commit`); never push.
- Report format: the dossier + a cover note (gate: PASS/FAIL, the
  evidence, the spec-bug list if any).
