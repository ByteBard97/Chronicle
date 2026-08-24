# Lane 59 — M7 release gate: formal re-run (Track B, QA)

**Status:** Ready to start immediately. All five fix lanes from the
first gate run (54, 55, 56, 57, 58) are landed and accepted. A
combined informal spot-check already passed steps 1–4 live and step 5
via diff-review rather than an interactive re-check (a Playwright
locator against the tree's SVG title elements hung and was abandoned).
This lane formally re-certifies the gate the same way lane 53 did, so
"the gate passed" is a verified record, not an inference from five
separate fix reviews plus a partial spot-check.

**Effort:** small-medium (re-run, not fresh discovery — the six steps
and the developer-twin cases are already known from lane 53's dossier;
this lane's job is to execute them again against the now-fixed
dashboard and produce the same kind of dossier).

## Context

`docs/work-packets/reviews/2026-08-24-m7/dossier.md` is the original
FAIL run. Read it first — it's your checklist. You don't need to
rediscover the six ui-spec §5 steps or the three developer-twin cases;
you need to re-execute them and see whether each now passes, with the
same evidentiary rigor (screenshots, specific verified claims, honest
distinction between "I confirmed this live" and "I inferred this from
a diff").

Per lane 53's own packet: **this is a verification lane, not a feature
lane** — no code changes here. If something still fails, file it as a
spec bug with a proposed fix lane, exactly like the first run; don't
patch it yourself.

## Read first (in order)

1. `docs/work-packets/reviews/2026-08-24-m7/dossier.md` — the original
   run and its five filed bugs, all in the same directory as this
   lane's own dossier will go.
2. `docs/work-packets/reviews/README.md`'s lane 54/55/56/57/58 rows —
   what each fix actually did, so you know what changed and why.
3. `docs/ui-spec.md` §5 (both walkthroughs, verbatim) — same source
   text lane 53 worked from.

## Task

1. Re-run the stranger walkthrough (six steps, `runs/north-star-01`,
   the same one-sentence prompt) for real, in a real browser. You may
   go in already knowing what changed (unlike lane 53's deliberately
   blind first attempt) — the point this time is confirming the fix,
   not discovering fresh usability gaps — but still narrate what you
   see and grade each step strictly pass/fail per §5's own rule.
2. Re-run the developer-twin sweep for T1.3, T3.4, and nothing-salient
   (same three cases lane 53 checked).
3. Produce a dossier in the same format as lane 53's, at
   `docs/work-packets/reviews/<date>-lane-59/dossier.md` (a fresh
   date-stamped directory, not overwriting lane 53's).
4. If everything passes: say so, with evidence for all six steps,
   including step 5 with a genuine live interaction (not a diff-review
   substitute) — this is the one gap the informal spot-check left
   open.
5. If something still fails (regression from a fix, or a fix that
   didn't fully close its bug): file it as a spec bug with a proposed
   fix lane, same discipline as before.

## Acceptance

- The dossier exists with per-step evidence for all six steps and the
  three developer-twin cases.
- Step 5 specifically has a genuine interactive confirmation (click
  through, not read-the-diff).
- Either a clean PASS with evidence, or a complete list of any
  remaining spec bugs with fix-lane proposals.

## File boundaries

**Create:** `docs/work-packets/reviews/<date>-lane-59/` (the dossier +
screenshots).

**Do not touch:** code, fixtures, `runs/` — verification only.

## Conventions

- **Local commits OK** (path-scoped); never push.
- Report format: the dossier + a short cover note (gate: PASS/FAIL,
  the evidence, the remaining spec-bug list if any).
