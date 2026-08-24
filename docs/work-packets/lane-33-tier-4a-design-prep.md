# Lane 33 — Tier 4a design prep: schedule write-back (Track A, design doc)

**Status:** Ready after **lane 32** (quick predecessor). This is a
**design-doc lane — no production code**, the same shape as lane 18
(which produced the Tier-3 design: read its structure and its overseer
review first — that loop is the model). The deliverable is one markdown
document for owner review.

**Effort:** medium (deep reading + one document).

## Context

Tier 4a (ladder, `docs/scenario-ladder.md:80-84`) is the first tier
where **state writes back into behavior** — the vision's "grief
reroutes a mourner's days":

- **T4a.1 Mourning.** Kin dies. Assert: mourning block inserted
  (temple, N days); original schedule restored after; the rewrite is
  itself an event causally linked to the death.
- **T4a.2 Second-order counterfactual.** Run A (with reroute) vs. Run
  B (fixture-frozen), same seed, keyed randomness. Assert: the rumor
  reaches the priest before the market in A and the reverse in B — and
  **every roll outside the mourner's changed sites is identical across
  runs** (the keyed-randomness guarantee, asserted directly).

Rules 17 (schedule write-back) and 18 (pairwise encounter weighting —
avoidance, tier 4b) are the registry stubs this design brings to life.
Tooling forced downstream: schedule diff (ui-spec §3.8, M5) and run
comparison (§3.9, M5) — informational, but the design should not close
their doors.

## Read first (in order)

1. `docs/design/tier-3-rule-registry-and-tell-decision.md` + its
   overseer review (`reviews/2026-08-23-lane-18/`) — the model for
   structure, decision/ruling separation, and the findings idiom.
2. `docs/scenario-ladder.md:80-84` (Tier 4a, verbatim via fold) and §8
   (rules 17/18).
3. `chronicle/schedule.py` — `ScheduleBlock`, the sampler, what
   "insert a block" and "restore" mean mechanically.
4. `chronicle/driver.py` — the tick loop's schedule use; what a mid-run
   schedule change would touch (the `_deceased` precedent for mid-run
   state).
5. `chronicle/rng.py` — ADR-0009's keyed rolls: why T4a.2's
   "identical rolls outside changed sites" holds by construction (the
   site is a roll_key member) — and what breaks if a block insertion
   changes pairings at *unchanged* sites (the real design risk).
6. `docs/frame-log-schema.md` §3 — the event vocabulary; a
   schedule-rewrite event type is likely a schema amendment (propose;
   the owner/coordinator amends).
7. `chronicle/social.py` — grudges/relationships (what gates mourning:
   kin edges; what gates avoidance: grudge above threshold + cooled
   floor from `grudge_at`, lane 20).
8. `docs/vision-v2.2.md` — the mourning/grudge beats of the north
   star (§2).
9. `docs/work-packets/reviews/README.md` — governance.

## Questions the doc must answer

1. **The write-back mechanism.** How a schedule block insertion works
   mid-run (schedule is fixed at construction today — lane 13's
   relief-carrier pin): mutation vs. overlay, and how the rewrite is
   "itself an event causally linked to the death" (new event type?
   fields?). Restoration semantics (restore the *original* blocks, or
   resume from the insertion point?).
2. **T4a.2's roll-identity guarantee.** Prove (on paper, with
   roll_key mechanics) which rolls a block insertion perturbs: pairings
   at unchanged sites must be identical across A/B — is that automatic
   (site+participants keying) or does the insertion change co-presence
   groupings and therefore which rolls exist at all? Design the
   assertion's exact meaning.
3. **Mourning rule (17→rule-17 registration).** Trigger (kin edge +
   death belief), parameters (location, duration — tunables with the
   placeholder-comment discipline), hysteresis (doctrine 3), and the
   cooled/restoration path.
4. **Avoidance weighting (18, tier 4b preview).** How a grudge above
   threshold re-weights encounter pairings (sampler-side), the cooled
   floor's role (`grudge_at`), and why this stays out of T4a.1/T4a.2.
5. **Migration + budget.** Rules 17/18 registration plan against the
   17/20 count (post-O4 consolidation); any new RNG purposes (should be
   none — weighting consumes existing rolls; if a new purpose is
   needed, that's an ADR-0009 conversation).
6. **Lane breakdown.** Proposed implementation-lane split with file
   boundaries and dependencies (mind: `driver.py`/`schedule.py`
   contention, and the Track-B §3.8/§3.9 views that eventually consume
   this).

## Acceptance

- One markdown deliverable:
  `docs/design/tier-4a-schedule-write-back.md`.
- file:line citations throughout; recommendations + named alternatives;
  open points for the owner collected at the end; findings list.
- Suite untouched-green (no code written).

## File boundaries

**Create:** `docs/design/tier-4a-schedule-write-back.md`

**Do not touch:** everything else.

## Conventions

- Match the Tier-3 design doc's voice and structure.
- **Local commits OK** (path-scoped); never push.
- Report format: the doc + a cover note (decided / needs adjudication /
  surprises).
