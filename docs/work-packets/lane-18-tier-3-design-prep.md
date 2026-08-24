# Lane 18 — Tier 3 design prep: rule registry + tell-decision (Track A, design doc)

**Status:** Ready to start immediately. This is a **design-doc lane — no
production code, no test edits**. The deliverable is one markdown
document for the owner's review; the owner promotes its decisions to
ADRs / frozen-doc amendments through the review cycle. Track B lanes
(15/16) are disjoint by construction.

**Effort:** medium (deep reading + one document).

## Context

Tier 2's executable surface is closed (T2.4 parked). Tier 3 (ladder
lines 68–84) introduces five rungs — T3.1 accumulation-threshold
escalation, T3.2 grudge creation + **grudge decay**, T3.3 obligation
violation wiring, T3.4 the **tell-decision gate**, T3.5 observer-local
reputation — and one piece of cross-cutting machinery the tier's own
tooling forces: the **rule registry** ("rules become named, toggleable,
instrumented objects… tiers 0–2 scenarios migrate onto it as regression
cases"). Ladder §8 is explicit: 19 named rules against a ~20 ceiling,
and *every* rule — including the ten already implemented — must exist in
the registry.

Some of the substrate pre-exists and the doc must build on it, not
redesign it: schema §4 already carries the tier-3 records
(`relationship_formed`, `grudge_formed`, `obligation_issued/resolved`,
`reputation_updated`, `rule_evaluated`, `threshold_crossed`, and the
reserved `transmission_declined`); `rng.py` already registers the
`tell_decision` roll purpose (ahead of machinery); `chronicle/social.py`
has the grudge/obligation/reputation write paths; the demo run already
emits `relationship_formed`. And vision v2.2 names the registry's
future second consumer: the GM/director layer sifts exactly this
surface — provenance-anchored intervention reads named, instrumented
rules. Design for that consumer now; it's cheap now and expensive to
retrofit.

## Read first (in order)

1. `docs/scenario-ladder.md` — Tier 3 intro + T3.1–T3.5 verbatim
   (`sed -n '68,84p' | fold -s`), §8's rule table and consequences
   (`sed -n '129,155p' | fold -s`). Frozen — findings to the
   coordinator.
2. `docs/frame-log-schema.md` §4 — the tier-3 record rows (119–128):
   what fields already exist; your design emits *these*, not new shapes,
   unless a gap is found (gaps are findings).
3. `chronicle/social.py` — the existing write paths and the
   caller-supplies-context discipline (`form_grudge` takes a
   caller-looked-up relationship, per the lane-12 research).
4. `chronicle/claims.py` — the decay constants + `_decay` (grudge decay
   needs its own constants, the "missing twin"); the tunables-block
   comment discipline.
5. `chronicle/rng.py` — the purpose registry (`tell_decision` is
   registered; nothing new may be added without an ADR-0009 change).
6. `chronicle/driver.py` — where rules would hook: the tick loop, the
   scripted wrappers, the trace-emission pattern.
7. `docs/decisions/` — the ADR format the owner's promotion step will
   use; your doc should be structured so its decisions lift cleanly.
8. `docs/vision-v2.2.md` §6 — the GM/director layer paragraph (the
   registry's future consumer).
9. `docs/work-packets/reviews/README.md` — governance. Commit policy:
   local commits fine (path-scoped); never push.

## Questions the doc must answer (the design surface)

1. **Rule registry shape.** How a rule becomes a named, toggleable,
   trace-instrumented object: registration API, where instances live
   (Driver-level? module-level?), what "toggleable" means (fixture/
   construction-time config — not mid-run), and how the ten already-
   implemented rules (§8 #1–10) retro-register without rewriting their
   internals (wrappers vs. refactoring). Include the `rule_evaluated`
   emission contract: every evaluation logs, fired or not, with current
   accumulator values (the ladder's "a counter stuck at 3-of-4 is
   visible, not silent").
2. **Accumulation-threshold with hysteresis (rule 11).** Accumulator
   state: per what key (holder? holder+subject+kind?), where stored
   (event-sourced how?), and T3.1's escalation pattern — the escalation
   materializes **as an event in the log first**, the warning claim
   hangs off that event's canonical key, propagation is encounters-only.
   Hysteresis per doctrine 3 (design-doctrines).
3. **Grudge machinery (rules 12–13).** The emotional/evidentiary split
   (schema fields exist), grudge decay constants (new tunables —
   propose magnitudes with the same placeholder-status comments as the
   belief decays), and how T3.2's "grudge decays slower than the rumor"
   becomes an assertion.
4. **Obligation violation wiring (rule 14).** T3.3's
   consume/refuse paths and the violation→grudge+reputation-evidence
   cascade for present observers.
5. **Tell-decision policy (rule 15).** The gate's inputs (privacy/
   motive — what data do they read? caller-supplies-context per the
   propagate.py discipline; NO social-state lookups leaking into claims
   operations — the T2.3 lesson), where it sits in the encounter path
   (before `teller_and_hearer`? after?), the keyed `tell_decision`
   roll's roll_key members, and `transmission_declined` emission
   (declining **by rule name** — T3.4's assert, and the M4 dashboard's
   fourth outcome-state producer).
6. **Observer-local reputation (rule 16).** The Beta accumulator
   (alpha/beta fields exist in the schema), which events feed evidence,
   and T3.5's tripwire (uninformed NPCs unchanged — no global jumps).
7. **Migration + rule-budget plan.** How tiers 0–2 scenarios migrate
   onto the registry as regression cases (mechanics, not a big-bang
   rewrite), and the budget accounting: 19/20 with the consolidation
   candidates §8 names (9+10 as one state machine; 4 as schema-not-
   rule). The doc recommends, the owner decides.
8. **Lane breakdown.** End with a proposed implementation-lane split
   (file boundaries, dependencies, rough effort) the coordinator can
   turn into packets.

## Acceptance

- One markdown deliverable:
  `docs/design/tier-3-rule-registry-and-tell-decision.md` (new dir OK).
- Every claim about existing code/schema verified (file:line citations
  throughout) — the coordinator will spot-check.
- Each question above answered with a recommendation **and** the
  alternatives considered; open points for the owner named explicitly
  (e.g. decay magnitudes, budget consolidation).
- `uv run pytest -q` / ruff untouched-green (you write no code — this
  should be trivially true; verify anyway).
- Structured so decisions lift into ADRs; findings list at the end.

## File boundaries

**Create:** `docs/design/tier-3-rule-registry-and-tell-decision.md`

**Do not touch:** everything else — no code, no test, no frozen-doc, no
schema edits. If the design *requires* a schema/ADR change, the doc
proposes it; the owner's review cycle decides.

## Conventions

- Match the repo's doc voice (see `docs/decisions/0009`/`0010`):
  decisions stated with rationale and named rejected alternatives.
- **Local commits OK** (path-scoped, explicit adds); never push.
- Report format: the doc, plus a short cover note: what's decided,
  what needs owner adjudication, what surprised you.
