# Lane 45 delivery report — T6 north-star fixture design

**Delivered:** `3b950a6` — `docs/design/north-star-fixture.md`. No
code, no fixture code. Suite unchanged: 223 passed, ruff clean.

## Cover note

**Decided** (this doc's own recommendations, ready to build against):

- The fixture is an **extension** of the already-landed
  `chronicle/fixtures/carrier_schedule.py` and
  `whiterun_relationships.py`, not a fresh build. The cross-hold
  backbone (caravaneer, relief caravaneer, road, Markarth residents)
  and the court's succession-decidable relationship edges
  (proventus/irileth to `jarl_balgruuf` under `whiterun_court`) already
  exist and are already proven by `run_carrier_demo.py`'s own demo
  run — reusing them means the north-star fixture inherits machinery
  that's already been exercised rather than introducing fresh risk in
  the capstone.
- Six cast groups (household, court, market, carriers, temple,
  Markarth), ~18 NPCs total, comfortably inside the ladder's own
  25-NPC volume precedent.
- Tier 5's "fixtures carry the counterfactual" claim is made concrete,
  not just cited: the doc states the exact one-line relationship-
  strength change (proventus's edge from 0.85 to 0.97) that flips the
  successor from irileth to proventus, so the implementing lane has a
  literal recipe rather than an abstract requirement to reinvent.
- Every claim/event script the four vision beats need reuses a shape
  some earlier design doc already defined (deceased-naming slots,
  mutation candidates, privacy/reputation-relevance mappings) — this
  doc's contribution is assembly and citation, not new mechanism
  design, which matches Tier 6's own "no new mechanism" framing.

**Needs adjudication** (owner-visible, §7 in the doc):

- **O4** is the one worth flagging first: which role the vision's "the
  Jarl" actually maps to in Tier 5's model, and whether Proventus
  (already fixture-cast as steward-flavored via `shared_employer`) is
  a sitting steward, a succession candidate, or both. This doc assumes
  a `jarl_of_whiterun` role distinct from Tier 5's own steward rung
  example but doesn't resolve the overlap — a real casting decision
  for the implementing lane.
- **O1/O2** — whether to fold in an obligation-refusal (T3.3) or a
  second suspect-naming privacy (T3.4) beat. Neither is asked for by
  any of the four numbered vision beats; this doc recommends leaving
  both out unless the owner specifically wants broader tier coverage
  in the composition.
- **O3** — demo-run length vs. test-run length: the M7 walkthrough
  likely wants the full multi-day `carrier_schedule.py` timescale,
  while the T6 test itself may want a compressed version for CI speed.
  Left as an implementing-lane call.

**Surprises:**

1. How much of the north star is **already built**. Going in, I
   expected to be designing most of the cast and graph from scratch;
   instead, the cross-hold carrier machinery and the court's
   succession-relevant relationship data were already sitting in
   `chronicle/fixtures/`, exercised by an existing demo run. The actual
   gap was narrower than the packet's framing suggested — mostly
   household kinship edges and faction data, both explicitly named as
   missing by the ladder's own §9.
2. **T2.4 needs real engine work, not just fixture data** — the
   packet's question 5 ("whether this fixture's faction data finally
   exercises the placeholder") reads as though data alone might
   suffice. It doesn't: `_decide_mutation` has no teller-identity input
   today, so no fixture can make substitution allegiance-deterministic
   without a small code change. I named the minimal hook precisely
   (§5, Decision N4) but deliberately did NOT design it in full here —
   it's exactly the kind of focused, small change that's earned its
   own micro-lane in this series before (lane 39's `StatusChanged` is
   the size precedent), and bundling it into a fixture spec would blur
   who's reviewing what.
3. The read-only aggregate beat (guard cohesion / market confidence) is
   the one vision beat this doc genuinely can't fully specify from the
   engine side — it's a dashboard-side derived view over
   `reputation_updated`/belief state that doesn't exist as an engine
   concern yet. Named as a real scope boundary (F4) rather than
   glossed over.

Full detail — the six-group cast table, the concrete relationship
graph and its stated flip, the per-beat assertion outline, and every
citation — is in the doc itself.
