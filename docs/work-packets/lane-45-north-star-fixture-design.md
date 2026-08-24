# Lane 45 — T6 north-star fixture design (Track A, design doc)

**Status:** After **lane 44** (Tier 5 design prep) — the composition
fixture must be designed against the final Tier 5 role model. This is a
**design-doc lane — no production code, no fixture code**: it produces
the fixture *specification* the north-star composition test (T6) and
its demo run are built from. Same shape as lanes 18/33/40/44.

**Effort:** medium-large (this is the capstone fixture — every landed
tier's authoring discipline converges on it).

## Context

The north star (`docs/vision-v2.2.md` §2, the acceptance test for the
whole architecture): the player assassinates Jarl Balgruuf. Succession
resolves through actual relationship/faction state; his household
mourns on their calendars and holds grudges with the killing as
evidence; the rumor mutates across holds (a Markarth merchant greets
you with a confidently-wrong thirdhand version); guard cohesion,
market confidence, and faction posture shift as **aggregates over what
individuals believe** — never as global flags. Tier 6 adds **no new
mechanism** (ladder): if the fixture can't express the cascade, the
mechanisms don't compose.

The ladder's §9 fixture consequences (line 160) are explicit: carrier
NPCs (T2.6 — landed) and **the victim's kin relationship edges**
("grudge rules gate on pre-existing edges — the north star's 'his
children hold grudges' fails for a boring reason if Balgruuf's
household edges aren't seeded"). This doc names every such requirement
so the fixture build (a later lane) is mechanical.

## Read first (in order)

1. `docs/vision-v2.2.md` §2 (the north-star beats, verbatim) and §6
   (T6's place on the road).
2. `docs/scenario-ladder.md` Tier 6 intro (composition; the read-only
   aggregate discipline: **collective fear is a derived view, never an
   input to any behavior decision**), plus §9's fixture consequences.
3. The authoring disciplines each landed tier demands of this fixture:
   - deceased-naming claim slots (lane 33's F3/O1 — mourning-eligible
     death claims),
   - kinship edges for mourning + grudge (lanes 25, 36),
   - **faction allegiance data** — T2.4's unpark prerequisite AND
     succession's resolution input (Tier 5),
   - carriers and road locations (lane 13's fixture),
   - reputation-relevance mappings (lane 26) for the ripple beats,
   - privacy/motive mappings for tell-decision (lane 23) — the
     assassination is exactly the kind of secret some holders keep.
4. The demo-run producers (`scenarios/run_*.py`) — the fixture will
   also drive the stranger-walkthrough demo (M7), so its spec must be
   producer-consumable, not just test-consumable.
5. `chronicle/fixtures/` — the fixture-module idiom.
6. `docs/work-packets/reviews/README.md` — governance.

## Questions the doc must answer

1. **The cast.** Household (who grieves, who grudges), court
   (succession candidates with the relationship/faction state that
   makes T5.2's "different fixture → different Jarl" demonstrable),
   market (propagation density), carriers (the Markarth/Riften beats),
   a priest + temple (T4a), guards + merchants (the ripple
   aggregates). Sizes per group, with the ladder's 25-NPC precedents
   as the scale guide.
2. **The relationship/faction graph.** Which edges are seeded
   (kinship, faction, rivalry, obligation) and what data model
   expresses them (relationships fixture — the lane-17 seeding
   idiom). Succession must be *decidable from the graph* — the doc
   should be able to say "with these edges, X succeeds; with those,
   Y" to prove the fixture-carried counterfactual.
3. **The claim/event scripts.** The assassination event itself (and
   its witnesses, incl. the disagreeing one — T0.4's variant path,
   exercised in anger), the deceased-naming slots, the private-claim
   mappings (who's kin-motivated to keep the secret), the
   reputation-relevance mappings for guard-cohesion/market-confidence
   aggregates.
4. **The assertion outline.** What T6 asserts per beat (succession,
   mourning reroutes, grudge-holding kin, the mutated variant
   surviving to Markarth, the read-only aggregate correct and
   drillable) — an outline, not test code (that's the T6 lane after
   Tier 5 lands).
5. **T2.4's unpark.** Whether this fixture's faction data finally
   exercises the motivated-mutation placeholder — and if so, the
   rung's assertion shape.
6. **The demo-run twin.** The same fixture as the stranger
   walkthrough's run (ui-spec §5): what the walkthrough's ten-minute
   path needs present in the data.

## Acceptance

- One markdown deliverable: `docs/design/north-star-fixture.md`.
- Every fixture requirement traces to a landed mechanism (rule/test
  citations); open points for the owner; findings list.
- Suite untouched-green (no code written).

## File boundaries

**Create:** `docs/design/north-star-fixture.md`

**Do not touch:** everything else.

## Conventions

- Match the design-doc series' voice and structure.
- **Local commits OK** (path-scoped); never push.
- Report format: the doc + a cover note (decided / needs adjudication /
  surprises).
