---
date: 2026-08-26
sources:
  - web research session (this pass) — control theory, opinion-dynamics
    literature, Dwarf Fortress/RimWorld/Sims prior art, Skyrim modding
    documentation, SkyrimNet Action Repository
topic: "v0.3 gap survey: two-way hysteresis for Grudge/Relationship state, and an NPC action-verb inventory beyond avoidance"
status: filed
---

# v0.3 Gap Survey: Two-Way Hysteresis and NPC Action Verbs

**Document File ID:** docs/research/23-v03-hysteresis-and-action-verbs.md
**Date:** 2026-08-26

## TL;DR

- **Part A**: no literature — not CK, not Dwarf Fortress, not RimWorld,
  not academic opinion-dynamics — publishes a two-way hysteresis model
  for social/relationship state with the specific rigor Chronicle needs.
  What *does* exist, robustly, is the generic control-theory pattern
  (separate rising/falling thresholds around a dead band) and one directly
  transferable game precedent with real published numbers: RimWorld's
  mental-break severity ladder, which additionally demonstrates the
  refractory-period technique Chronicle should combine with a dead band.
  **Recommendation**: build Chronicle's de-escalation as a Schmitt-trigger
  dead band (escalate at severity ≥ 0.6, de-escalate only once decayed
  severity ≤ 0.3) *plus* an explicit tick-count dwell requirement before
  the down-transition fires, modeled directly on `GrudgeDecayRule`'s
  existing `grudge_at`/`grudge_cooled` read-path — no new literature
  numbers are load-bearing here, the structure is what's borrowed.
- **Part B**: Skyrim's real, well-trodden action surface for
  state-driven NPC behavior beyond scheduling is narrower than it looks
  from outside — three mechanisms are genuinely load-bearing (dialogue
  conditions incl. `GetRelationshipRank`, AI package conditions on a
  global/quest variable, and vendor gold/price hooks), and everything
  richer (arrest, extortion, debt, brawls, combat initiation) that ships
  today is SkyrimNet/SeverActions LLM-conversation-triggered, not
  external-state-triggered, which is precisely the seam Chronicle would
  have to build itself if it wants one. **Top 3 recommendation**:
  (1) dialogue-gating on `GetRelationshipRank` [already targeted by
  `chronicle-bridge-hydration-out.md`], (2) grudge-driven vendor
  price/refuse-to-trade via barter script overrides, (3) an AI package
  condition keyed to a Chronicle-owned global (`avoid`/`hostile-greet`
  tier) — ranked in that order by mechanism safety, not by drama value.

---

## Part A — Two-way hysteresis / bidirectional threshold models

### Findings

- **[RISK] No source — academic or game — publishes a two-way hysteresis
  model purpose-built for social/relationship state.** Direct queries
  against bounded-confidence and Hegselmann-Krause opinion-dynamics
  literature (survey: Bounded confidence opinion dynamics: A survey,
  ScienceDirect 2023, https://www.sciencedirect.com/science/article/pii/S0005109823004661;
  Opinion Dynamics Model with Bounded Confidence and the Sleeper Effect,
  PMC 2022, https://pmc.ncbi.nlm.nih.gov/articles/PMC9256380/) return
  models that are single-threshold and *symmetric* — the confidence
  bound determines whether opinions attract at all, and clustering
  outcomes are studied as an emergent property of that one threshold,
  not as an authored promotion/demotion pair for discrete relationship
  categories. Dwarf Fortress's own grudge-formation mechanics are
  publicly under-documented even for the *forming* half (DF Wiki:
  Grudge, https://dwarffortresswiki.org/index.php/DF2014:Grudge —
  "It is currently unknown how a grudge is formed" is the wiki's own
  caveat) so it cannot be cited for a de-escalation half either. This
  repo's own `ck-opinion-decay-and-threshold-tables.md` already
  establishes CK2/CK3 opinion decay is continuous and one-directional
  (modifiers expire or decay to zero; there is no separate, harder
  threshold to re-cross before a relation *category* like Rival
  reverts) — that finding is confirmed, not contradicted, by anything
  found in this pass.
- **[BUILD-ON] The control-theory pattern itself is exactly what
  Chronicle needs, and it is thoroughly documented outside game
  contexts.** A Schmitt trigger uses two thresholds around a dead band:
  crossing the *upper* threshold flips the output high, and only
  crossing the separate, lower threshold flips it back — the region
  between the two thresholds is "memory," the system's state depends on
  history, not just the current value (GeeksforGeeks, Schmitt Trigger,
  https://www.geeksforgeeks.org/electronics-engineering/schmitt-trigger/;
  general description of the up/down asymmetric-threshold pattern,
  Northumbria game-AI teaching material on hysteresis in FSMs,
  https://research.ncl.ac.uk/game/mastersdegree/gametechnologies/aitutorials/1state-basedai/AI%20-%20State%20Machines.pdf).
  The game-AI framing of this pattern is stated with an example directly
  usable as a template: "trigger the transition from state A to state B
  when a value becomes higher than 11m/s, and trigger the reverse
  transition when it becomes lower than 9m/s" — the same source names
  the resulting untouched interval a "dead band" where no switching
  occurs. This is structurally identical to what Chronicle needs for
  `AccumulationThresholdRule`/grudge severity: an *up* threshold that
  forms/escalates, and a distinct, lower *down* threshold that
  demotes/dissolves, with no oscillation possible for any value inside
  the gap.
- **[BUILD-ON] Ecological "alternative stable states" literature adds
  one structural nuance worth keeping: hysteresis loops in real systems
  are frequently *not* symmetric, and reversal can require sustained
  time below threshold, not just an instantaneous crossing.** "Once the
  system has crossed a tipping point, decreasing stress to the original
  value does not restore the system to the original state" — reversal
  needs either overshooting further past the original threshold, or
  dwelling there (Rethinking tipping points in spatial ecosystems, arXiv
  2306.13571, https://arxiv.org/pdf/2306.13571; Alternative Stable
  States, Nature Scitable, https://www.nature.com/scitable/knowledge/library/alternative-stable-states-78274277/).
  Applied to Chronicle: a single tick where decayed severity dips below
  the down-threshold should not be sufficient by itself to demote a
  Grudge — the literature's own qualitative lesson is that reversal
  needs *persistence*, not just a momentary crossing, which is exactly
  the "stays there for N ticks" framing this task's own prompt already
  guessed at. No source gives a numeric N; it is a tuning parameter, not
  a literature-derived constant.
- **[BUILD-ON] RimWorld's mental-break severity ladder is the single
  most directly transferable prior-art number set found, and it
  combines a graded threshold ladder with an explicit refractory
  period — worth borrowing the *shape*, not the numbers.** RimWorld
  computes three severity thresholds off one base stat: Minor at the
  full Mental Break Threshold value, Major at 4/7 of it, Extreme at 1/7
  of it (RimWorld Wiki, Mental Break Threshold,
  https://rimworldwiki.com/wiki/Mental_Break_Threshold), each mapped to
  a named mood band (Stressed/On edge/About to break) and a
  mean-time-to-break roll rather than an instant trigger (RimWorld Wiki,
  Mental break, https://rimworldwiki.com/wiki/Mental_break). Critically,
  once a break *fires*, mood is forcibly reset upward and breaks cannot
  re-fire immediately — this is a refractory/cooldown mechanism, a
  different but complementary technique to a dead band: it prevents
  oscillation not by requiring a harder threshold to reverse, but by
  making the up-transition itself temporarily un-repeatable. Chronicle's
  own `ScheduleWriteBackRule`/`already_mourning`-latch pattern already
  uses exactly this refractory idea for the escalation side (a
  log-derived latch prevents re-firing on repeat corroboration) — the
  new piece this report adds is applying the *same* latch discipline to
  a de-escalation direction that doesn't exist yet.
- **[RISK] The Sims' relationship decay is a useful negative example:
  its "bidirectional" behavior is between-Sims asymmetry (satisfaction
  can rise for one party while falling for the other), not a
  category-level up/down hysteresis mechanism** (Relationship
  Satisfaction, Waffle's Mix-Ins via Patreon,
  https://www.patreon.com/posts/relationship-it-116122721) — decay rate
  differs by current relationship tier (low tiers decay first; "good
  friends and soulmates decay very slowly") but there is no separate,
  harder threshold gating a category *downgrade* the way this task
  requires; a Sim's tier simply tracks the underlying scalar continuously.
  Not usable as structural precedent beyond confirming, again, that
  tier-decay-rate-by-level (slower decay once a relationship is
  "crystallized," matching this project's `Relationship` category idea)
  is a reasonable design knob independent of hysteresis itself.

### Recommendation — structural, for Chronicle's Grudge/Relationship machinery

No literature gives Chronicle numbers to import wholesale; what it gives
is a validated *shape*. Structurally:

1. **Escalation threshold (existing)**: `AccumulationThresholdRule`'s
   `count >= threshold` and `PairwiseEncounterWeightingRule`'s
   `severity >= threshold` stay as-is — this is the Schmitt trigger's
   "rising" edge and is already correctly a one-shot latch pattern
   (`GrudgeCreationRule`'s `already_exists` gate, `ScheduleWriteBackRule`'s
   `already_mourning` gate).
2. **De-escalation threshold (new)**: introduce a distinct, strictly
   lower threshold (e.g. `AVOIDANCE_GRUDGE_THRESHOLD` for up, a new
   `AVOIDANCE_GRUDGE_COOL_THRESHOLD` for down, with a documented gap —
   the dead band — between them) evaluated against the same
   `social.grudge_at(...).severity` read-path `GrudgeDecayRule` already
   wraps, never a new store field.
3. **Dwell requirement, not instantaneous crossing**: per the
   alternative-stable-states literature's qualitative lesson, gate the
   down-transition on the decayed severity having stayed at or below the
   cool threshold for N consecutive evaluation ticks (or since a
   recorded `gamets` watermark) — mirroring how `grudge_cooled()` already
   evaluates a decay function at a point in time, this just needs the
   *previous* evaluation's result carried forward by the driver (a
   caller-assembled boolean, per the T2.3 lesson every existing rule in
   this file follows — never a new store query inside the rule itself).
   N is a tuning constant, not a literature-derived one; this report
   does not recommend a specific value.
4. **Category demotion mirrors `RoleVacancySuccessionRule`'s "fired = the
   effect" convention**: a `RelationshipDemotionRule` (or extending
   `GrudgeDecayRule`'s tier) should fire only when a Relationship's
   *category* (not just its scalar) needs to step down one level, using
   the same log-derived latch idiom rules 12/15/17/18/19 already
   establish, so disabling it is a real behavioral toggle, not
   instrumentation-only.

This is the same rule-family idiom the ladder already uses end to end —
the addition is one new threshold constant and one new caller-tracked
dwell counter, not a new subsystem.

---

## Part B — NPC action-verb inventory for Skyrim

### Findings

- **[BUILD-ON] Dialogue-gating on `GetRelationshipRank` is a
  well-trodden, first-class vanilla mechanism — not something Chronicle
  would be pioneering.** `GetRelationshipRank` is a native dialogue/
  quest condition function usable directly in Creation Kit condition
  trees (e.g. `GetRelationshipRank == -1` for Rival-gated lines); modders
  already map story/quest-reward outcomes onto it via
  `SetRelationshipRank`/`player.setrelationshiprank` (UESP,
  Skyrim:Disposition, https://en.uesp.net/wiki/Skyrim:Disposition;
  community modding-help thread confirming the condition-tree usage,
  https://forums.nexusmods.com/topic/13497763-need-help-with-applying-condition-to-dialogue/).
  This directly corroborates and narrows the scope of
  `docs/design/chronicle-bridge-hydration-out.md`'s own claim (line ~93)
  that vanilla `GetRelationshipRank` conditions already make relationship
  rank changes dialogue-observable with zero new dialogue authoring —
  this pass finds no reason to doubt that claim and treats it as
  confirmed, not merely asserted.
- **[RISK] AI package conditions driven by a custom global/quest
  variable are architecturally real but not independently documented
  with the depth this task hoped for.** Web search surfaced only
  generic Creation Kit package-condition mechanics (package conditions
  gate execution; formlists can override Spectator/Combat AI —
  Beyond Skyrim's Arcane University: World Interactions,
  https://wiki.beyondskyrim.org/wiki/Arcane_University:World_Interactions)
  rather than a named mod demonstrating "package driven by an
  externally-written global at runtime" end to end. This is the same
  mechanism rule 18's avoidance override already uses in practice
  (`schedule.sample_encounters`'s `pair_thresholds`, per
  `PairwiseEncounterWeightingRule`'s own docstring) — the finding here
  is that this repo's *own* rule 18 is closer to the state of the art
  than anything independently documented elsewhere; there is no richer
  published pattern to build on beyond what Chronicle already ships.
- **[RISK] Vendor price/refuse-to-trade driven by reputation is not a
  shipped, documented mod pattern either** — search for exactly this
  (faction-reputation-gated barter refusal/markup) returned only
  generic trade-expansion mods (Trade and Barter, rewarding *positive*
  relationships with better prices via favors — Nexus Mods,
  https://www.nexusmods.com/skyrim/mods/34612) with no example of the
  negative/refusal direction. The underlying mechanism is real and
  already surveyed in this repo's own economy research (report 16/18:
  vendor gold caps, `fBarterBuyMin` price floor, barter-menu-open
  population timing) — the gap is that nobody has wired grudge/
  reputation state into it, which is an opportunity, not a wall.
- **[BUILD-ON] The richest documented "NPC action verb" inventory in the
  entire Skyrim modding ecosystem is SkyrimNet's Action Repository plus
  the community SeverActions plugin, and it is conversation-triggered,
  not external-state-triggered — a distinction load-bearing for this
  task.** The Action Repository documents actions including `SellItem`,
  `CreateDebt`/`CollectPayment`/`CreateRecurringDebt`, `ExtortGold`,
  `DeclineBrawl`/`ChallengeBrawl`, `RejectPersuasion`,
  `RejectEscortPlea`, `AdjustRelationship` (a numeric -15..+15 rapport/
  trust/loyalty delta), `SetCompanion`, `TransferOwnership`,
  `AttackTarget`, and `ThugAttack` (SkyrimNet Action Repository,
  https://goncalo22.github.io/SkyrimNet-GamePlugin/action-repository/;
  SeverActions README, 38-71 actions spanning combat/crafting/arrest/
  follower systems, https://github.com/Severause/SeverActions). Every
  one of these is invoked from the LLM's evaluation of live conversation
  context (the docs frame `ThugAttack` firing "only after player refusal
  or hostile action," i.e. dialogue-turn-gated), not from an external
  simulation tick pushing a global/quest variable the way Chronicle's
  own architecture requires (per this repo's own 03/19/20's
  hybrid-neurosymbolic doctrine: symbolic state must govern engine logic,
  LLM output restricted to framing/dispatch). **The actions themselves
  are a legitimate inventory of "verbs Skyrim NPCs can be made to
  perform" — `ExtortGold`, `DeclineBrawl`/`ChallengeBrawl`,
  `AdjustRelationship`, `AttackTarget`, and vendor/debt actions are all
  proof that the underlying Papyrus/SKSE hooks exist and work in
  production — but the trigger wiring (LLM-conversation vs.
  Chronicle-simulation-state) would have to be built fresh; nothing here
  is a drop-in adapter for Chronicle's own state.**
- **[RISK] No independent "nemesis"/persistent-grudge combat-initiation
  mod was found with published mechanics detail beyond gimmick mods.**
  "Nemesis Combat AI" and "Shadow of Skyrim" exist (Nexus Mods,
  https://www.nexusmods.com/skyrimspecialedition/mods/185305; PC Gamer
  coverage, https://www.pcgamer.com/this-skyrim-mod-recreates-the-best-part-of-shadow-of-mordor-the-nemesis-system/)
  but both are single-encounter/randomized promotion systems (whoever
  defeats the player becomes their nemesis) with no state feed from an
  external reputation/grudge system, and neither publishes a
  threshold model. `AttackTarget` from SkyrimNet's Action Repository
  remains the only documented, general-purpose "make this specific NPC
  hostile toward this specific actor" primitive found.

### Recommendation — ranked, buildable NPC action verbs for Chronicle

Ranked by (a) mechanism safety/well-trodden-ness and (b) fit to state
Chronicle already computes (`Reputation`, `Grudge.severity`,
`Relationship` category):

1. **Dialogue-gating on `GetRelationshipRank`.** Safest possible
   mechanism — pure vanilla condition-tree usage, zero new Papyrus,
   already the explicit target of
   `docs/design/chronicle-bridge-hydration-out.md`. Directly matches
   Chronicle's `Relationship` rank output with no translation layer.
   Effort is entirely on the authoring side (new dialogue topics/lines
   conditioned on rank), not the engine-hook side.
2. **Grudge-severity-driven vendor refusal/price markup.** Mechanism is
   well-trodden in the abstract (barter price calc and vendor gold caps
   are documented engine hooks per this repo's own reports 16/18) even
   though no existing mod wires reputation into it — this is a real gap
   Chronicle could fill first. Matches `Grudge.severity` almost exactly
   as-is (same scalar rule 18 already reads for avoidance), and is
   strictly lower-risk than combat or faction actions since it never
   changes hostility state, only a barter-menu price calculation.
3. **AI-package-condition override keyed to a Chronicle-owned global
   variable, for a small hostile-greeting/refuse-to-interact tier below
   full avoidance.** Same mechanism family as rule 18's existing
   avoidance override (`pair_thresholds`) — extending, not inventing.
   Matches `Grudge.severity` at a lower threshold than avoidance (a
   "cold shoulder" tier between neutral and active avoidance), which
   also gives the two-way-hysteresis machinery from Part A a second,
   independently-observable behavioral rung to demonstrate de-escalation
   against.
4. **(Lower priority, higher payoff if built) `AttackTarget`-style
   nemesis combat initiation, state-triggered rather than
   conversation-triggered.** The primitive is proven in production
   (SkyrimNet's `AttackTarget`) but every existing use is LLM-turn-
   triggered; Chronicle would have to build the state→trigger wiring
   itself (a Chronicle-simulation tick deciding "grudge severity crossed
   a combat-initiation threshold" and dispatching an SKSE call) with no
   prior-art adapter to lean on. Higher drama value than 1-3, but real
   new engineering, and carries the same off-screen-actor-can't-act
   absence-of-execution wall already documented in report 17 — only
   viable for loaded/nearby actors.
5. **(Not recommended near-term) Faction join/refusal driven by
   reputation.** No prior art at all was found for state-driven faction
   admission/refusal; Story Manager involvement (per report 19/20's own
   "bypass the Story Manager for anything macro" lesson) makes this the
   riskiest of the five candidates. Held out of the ranked top-3
   deliberately.

---

## Caveats

- This is a single web-research pass (no independent second pass or
  source-code read of SeverActions/SkyrimNet exists yet, matching the
  caveat pattern already used by reports 19/21) — treat the SkyrimNet
  Action Repository summary as one page's documentation, not
  independently verified against the plugin's own YAML/C++ source.
- Part A's literature search found what it found: an absence of
  purpose-built bidirectional-hysteresis social-simulation literature is
  itself the finding, not a search failure — three separate query
  angles (control theory, bounded-confidence opinion dynamics, named
  game systems) converged on the same gap.
- Numeric claims to flag explicitly as *not* transferable: RimWorld's
  4/7 and 1/7 severity fractions are cited only to illustrate the
  "graded ladder off one base stat" shape, not as values Chronicle
  should adopt for its own severity thresholds.
