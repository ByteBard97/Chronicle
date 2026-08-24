# Lane 44 — Tier 5 design prep: roles & vacancy (Track A, design doc)

**Status:** After **lane 43** lands (Tier 4b completes Tier 4). This is
a **design-doc lane — no production code**, same shape as lanes 18/33/40
(read those docs' structure and their overseer reviews first — that
loop is the model). The deliverable is one markdown document for owner
review.

**Effort:** medium (deep reading + one document).

## Context

Tier 5 (ladder, `docs/scenario-ladder.md`): **roles as first-class
entities — the last new sim mechanism.** Rule 19
(role-vacancy/succession resolution) is the registry's final stub.
Three rungs:

- **T5.1 Vacancy.** Steward killed. Assert: role vacant; duties lapse
  with defined effects; lapse effects are events propagating through
  Tiers 1–4 machinery.
- **T5.2 Succession.** Assert: successor resolves from
  relationship/faction state; **varying the prior-relationship fixture
  while holding the seed produces a different successor** (fixtures
  carry the counterfactual, not seeds — the stronger determinism
  claim).
- **T5.3 No orphaned references.** Everything that pointed at the
  holder resolves through the role.

Tooling forced downstream: the role inspector (ui-spec §3.10, M6) and
role rows in the diff panel (lane 30's view, Tier-5-era). And Tier 6
lurks: the north-star composition test needs succession to *work* —
"different prior relationships produce a different Jarl"
(`docs/vision-v2.2.md:20`).

## Read first (in order)

1. `docs/scenario-ladder.md` Tier 5 (T5.1–T5.3) + Tier 6 intro, §8
   (rule 19, the budget's last slot).
2. The three accepted design docs (`docs/design/`) — structure, the
   decision/ruling split, the findings idiom.
3. `chronicle/social.py` — relationships/factions (what succession
   resolves *from*: which edges exist today, what's missing).
4. `chronicle/rules.py` — the rule-19 stub; the real-rule idiom.
5. `docs/frame-log-schema.md` §3/§4 — what a role/vacancy/succession
   event or record needs (likely a schema amendment — propose; the
   coordinator amends). `status_changed` (§3:97, lane 39) is directly
   relevant — succession is a status change with machinery around it.
6. `docs/vision-v2.2.md` §2 (succession beat of the north star).
7. `docs/work-packets/reviews/README.md` — governance.

## Questions the doc must answer

1. **The role model.** What a Role *is* in the store (first-class
   entity: id, duties, holder, vacancy state), where it lives
   (social.py? new module?), and how references work (T5.3: what
   "everything that pointed at the holder" means mechanically —
   relationships? obligations? claims naming the role-holder?).
2. **Vacancy + lapse (T5.1).** What triggers vacancy detection (a
   death belief? the NPCDied event? rule 19 evaluating on belief
   acquisition per the rule-16/17 pattern), what "duties lapse with
   defined effects" concretely means for a steward (fixture-defined
   duties with lapse consequences), and how lapse effects become
   *events* that propagate through the existing machinery.
3. **Succession (T5.2).** The resolution rule's inputs
   (relationship/faction state — caller-supplied per the T2.3
   discipline), its determinism (rolled or ranked? if rolled: a new
   RNG purpose is an ADR-0009 conversation — prefer deterministic
   ranking over fixture state, since T5.2's counterfactual is
   *fixture-carried*), and how "varying the fixture varies the
   successor" is asserted.
4. **Registry + budget.** Rule 19 registration (the last stub), the
   real-toggle question, and the rule-budget consequence (17/20 with
   19 landed = three slots of headroom for v0.3's social actions —
   confirm the math).
5. **Lane breakdown.** Implementation lanes with file boundaries and
   dependencies (mind: this is the last mechanism before the T6
   composition test — the breakdown should end at T6's doorstep).

## Acceptance

- One markdown deliverable: `docs/design/tier-5-roles-and-vacancy.md`.
- file:line citations; recommendations + named alternatives; open
  points for the owner; findings list.
- Suite untouched-green (no code written).

## File boundaries

**Create:** `docs/design/tier-5-roles-and-vacancy.md`

**Do not touch:** everything else.

## Conventions

- Match the design-doc series' voice and structure.
- **Local commits OK** (path-scoped); never push.
- Report format: the doc + a cover note (decided / needs adjudication /
  surprises).
