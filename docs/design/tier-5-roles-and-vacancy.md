# Tier 5 design prep — roles and vacancy

Status: design proposal for owner review (lane 44 deliverable). No code.
Every code/schema claim carries a file:line citation verified against
`e2b3672`. Structured so each **Decision** section lifts into an ADR,
same shape as the Tier-3/4a/4b design docs; open points for the owner
are collected in §6. Decisions here are prefixed **S** (roles), distinct
from the R/T/W prefixes of the earlier three docs.

Sources: `docs/scenario-ladder.md` Tier 5 intro + T5.1–T5.3, Tier 6
intro, §8 (rule 19); `docs/frame-log-schema.md` §3:92-97; `chronicle/social.py`;
`chronicle/fixtures/whiterun_relationships.py`; `chronicle/rules.py`;
`chronicle/driver.py`; `docs/ui-spec.md` §3.10; `docs/vision-v2.2.md` §2.

---

## 0. What Tier 5 actually asks for

The tier intro names one mechanism, and calls it the last one:
**roles as first-class entities** (`docs/scenario-ladder.md:93`). Three
rungs:

- **T5.1 Vacancy.** Steward killed. Assert: role vacant; duties lapse
  with defined effects; lapse effects are events propagating through
  Tiers 1–4 machinery.
- **T5.2 Succession.** Assert: successor resolves from
  relationship/faction state; varying the prior-relationship fixture
  while holding the seed produces a different successor — "fixtures
  carry the counterfactual, not seeds," a stronger determinism claim
  than any prior tier makes.
- **T5.3 No orphaned references.** Everything that pointed at the
  holder resolves through the role.

Rule 19 (`role-vacancy/succession resolution`,
`docs/scenario-ladder.md:152`) is the registry's last stub
(`rules.py:335`, `StubRule(ROLE_VACANCY_SUCCESSION, 5)`). Tooling
forced downstream: the role inspector (`docs/ui-spec.md:122`, "Role,
holder (linked), duties with lapse state, vacancy history, succession
record drill-down-able") and role rows joining the diff panel — both
M6/Tier-5-era, out of this doc's scope to design.

Tier 6 lurks immediately behind this one: the north star needs
succession to *work*, not just exist — "different prior relationships
produce a different Jarl" (`docs/vision-v2.2.md:20`). This doc's lane
breakdown (§5) is written to end at that doorstep.

---

## 1. The role model (question 1)

### Decision S1 — a new module, `chronicle/roles.py`; a `Role` owns its own duties, vacancy history, and succession record

**Where it lives.** `chronicle/social.py`'s docstring enumerates layer
4 precisely: "sparse relationships, grudges, obligations, and
observer-local reputation" (`social.py:6-7`) — four kinds, each with
its own dataclass and store methods, no fifth kind implied anywhere in
that module's design. Roles are a genuinely different axis of state
(an office that persists across holders, not a fact about one NPC or
one pair), and every other store module in this codebase owns exactly
one coherent concern (`claims.py`, `social.py`, `schedule.py`,
`events.py`). Proposed: a new module, `chronicle/roles.py`, with its
own `RoleStore`, held on the driver as `self.roles: RoleStore` — the
same compositional pattern as `self.claims`/`self.social`
(`driver.py`'s `__init__`, `self.claims = ... ; self.social = ...`).
**Rejected alternative:** growing `SocialStateStore` with a fifth
`_roles` dict. Rejected because it would make `social.py` responsible
for reading `claims`-adjacent state (a role's vacancy detection reads
the canonical event log, §2 below) that has nothing to do with
relationships/grudges/obligations/reputation's shared "derived from a
belief/relationship" character.

**Shape.**

```
@dataclass(frozen=True)
class Duty:
    name: str                     # e.g. "collect_taxes"
    lapse_status_kind: str        # the status_changed status_kind emitted on lapse

@dataclass(frozen=True)
class Role:
    id: str                       # e.g. "steward_of_whiterun"
    title: str                    # display name
    institution_id: str           # the faction/court this role belongs to -- the
                                   # same basis_id vocabulary Relationship already
                                   # uses (social.py:97, "faction"/"shared_employer"
                                   # edges carry a basis_id like "whiterun_court")
    duties: tuple[Duty, ...]
    holder_id: str | None         # None means vacant
    vacated_at: float | None      # gamets of the most recent vacancy, or None
```

`RoleStore` mirrors `SocialStateStore`'s shape: `install(role)`,
`role(role_id) -> Role | None`, `holder_of(role_id) -> str | None`,
`roles_held_by(npc_id) -> tuple[Role, ...]` (the reverse index T5.2's
"don't double-cast a successor already holding another role" concern,
§6 O4, would query). All mutations return a new frozen `Role` via
`dataclasses.replace`, the same immutable-record discipline
`claims.py`/`social.py` already use throughout.

### Decision S2 — T5.3 is satisfied by construction, not by retrofitting existing stores

The ladder's exact wording — "everything that pointed at the holder
resolves through the role" — reads, at first pass, like it demands that
`Relationship`/`Obligation`/`Grudge` records "about the steward" survive
a succession by re-pointing at the new holder automatically. That would
require a new `role_id` field on some subset of those frozen dataclasses
(a real schema change to three already-shipped record types) and a
read-time resolution rule for when to follow `role_id` vs. trust the
stored `to_id`/`debtor_id` directly — a much larger surface than this
tier's "last new mechanism" framing suggests, and nothing in `docs/
frame-log-schema.md`'s existing `relationship_formed`/`grudge_formed`/
`obligation_issued` rows (§4:124-127) reserves room for it.

**Proposed scope, instead:** T5.3 holds by construction because
role-owned state (`Role.holder_id`, `duties`, vacancy history,
succession record) is **never mirrored onto the holder** in the first
place — it lives exclusively on the `Role` object, keyed by `role_id`,
so there is nothing on the *NPC* side to go stale when the holder
changes. `RoleStore.holder_of(role_id)` is always the live answer, by
definition, the instant `install()` runs. Existing layer-4 records
(`social.obligations_involving(npc_id)`, `social.py:514-516`;
`grudges_of`/`grudge`, `:485-491`; `Relationship` edges) continue to
name NPCs directly, exactly as today — a `succession` doesn't rewrite
them, and this doc does not propose that it should. **This is a real
scope decision, not a implementation detail** — flagged as open point
O1 (§6) because "no orphaned references" could be read more broadly,
and the owner should confirm this narrower reading is what the ladder
intended before an implementing lane builds against it.

---

## 2. Vacancy + lapse (question 2)

### Decision S3 — vacancy is objective, detected at `inject_event`, not belief-gated

Every other Tier-3/4 trigger (rules 11/16/17/18) evaluates at **belief
acquisition** — an NPC has to learn something before a rule reacts.
Vacancy is different in kind: a role becomes vacant the instant its
holder dies, a fact about the world (layer 1), independent of who has
heard about it yet. `docs/scenario-ladder.md:93`'s "duties lapse with
defined effects; lapse effects are events propagating through Tiers
1–4" reads the same way — the LAPSE'S CONSEQUENCES propagate normally
(as beliefs, through the existing machinery), but the vacancy fact
itself is immediate, the same way `_deceased` is updated the instant
`inject_event` appends an `NPCDied` (`driver.py:284-286`
`if isinstance(event, NPCDied): self._deceased.add(event.npc_id)`),
not when someone first witnesses it.

Proposed: `inject_event` gains one more `isinstance` branch, alongside
the `_deceased` update — on `NPCDied`, look up
`self.roles.roles_held_by(event.npc_id)` and vacate each one
(`RoleStore` mutation, no trace record of its own — vacancy is derived
state the same way `_deceased` is, reconstructible from the log by
replaying `NPCDied` events, no keyframe/schema entry needed). This is
the one place this design's trigger shape genuinely differs from every
prior tier's rule, and it's worth the owner's eyes as a real pattern
choice, not an oversight (open point O2).

### Decision S4 — duty lapse reuses `status_changed` (schema §3:97), anchored on the vacancy

Each of a role's `Duty` records carries a `lapse_status_kind`
(§1). On vacancy, for every duty the just-vacated role had, the driver
injects one `StatusChanged` event
(`events.py`'s dataclass, landed lane 39; schema row filled at
`docs/frame-log-schema.md:97`): `npc_id` = the former holder (the
duty's natural anchor even though they're dead — the same "a dead NPC
can still be a canonical anchor" precedent `NPCDied` itself sets, and
the one `escalation_warning`/`schedule_rewrite` events already
establish for engine-internal, non-belief-gated events), `status_kind`
= the duty's `lapse_status_kind` (e.g. `"duty_lapsed"`), `detail` = the
duty's `name`. **No new event type.** `status_changed`'s own docstring
(lane 39) already names `"role_appointed"` as an example `status_kind`
— this doc's `"duty_lapsed"`/succession's eventual `"role_appointed"`
are exactly the vocabulary that field was built for. Rejected
alternative: a dedicated `role_lapse` event
(`docs/frame-log-schema.md:98`, already reserved for tier 5!) — the
schema literally holds a slot for this
("`role_lapse` | 5 — reserved | duty-lapse effects as events (ladder
T5.1). Fields defined with roles"). Recommend the owner **retire that
reservation** in favor of `status_changed`, the same "reuse before
growing schema" move every prior design doc in this series has made
(Tier-3's escalation event was the one genuine exception, and even that
reused an existing reserved slot rather than inventing a new one) —
flagged as O3 since it means *not* filling a row the schema already set
aside, which deserves an explicit owner call rather than silent
reuse.

From there, propagation is ordinary: the lapse event is witnessed
off its own canonical key by whoever's positioned to notice
(a `claim_kind` the caller registers, same `witness()` call site
pattern every prior tier uses) and spreads through Tiers 1–4 exactly
like any other claim — no new propagation machinery, matching the
ladder's own "propagating through Tiers 1–4 machinery" phrasing
literally.

---

## 3. Succession (question 3)

### Decision S5 — deterministic ranking over relationship strength; no roll, no new RNG purpose

The packet's own steer is the right one: T5.2's counterfactual is
"fixtures carry the counterfactual, not seeds" — a **stronger**
determinism claim than a keyed roll would give. A roll would need a new
RNG purpose (an ADR-0009 conversation the packet explicitly wants
avoided) and, more importantly, would make "varying the fixture
produces a different successor" merely *probable*, not *guaranteed* —
exactly the weaker claim doctrine-adjacent reasoning throughout this
series has consistently rejected in favor of exact assertions
(Tier-4a's `AVOIDANCE_PROBABILITY = 0.0` is the same instinct: prefer a
hard guarantee over a well-tuned probability).

**Resolution rule:** among NPCs holding a `Relationship` edge to the
vacant role's `institution_id` (any basis whose `basis_id` matches --
`whiterun_relationships.py:38,40`'s existing `"whiterun_court"`/
`"whiterun_guard"` fixture data is exactly this vocabulary, already
seeded), rank by edge `strength` descending; the highest-strength edge
succeeds. **Tie-break: lower `npc_id` string, lexicographic** — cheap,
deterministic, and it's what a tie-break needs to be here since there's
no principled "who's more deserving" signal at equal strength (proposed
over "earliest `formed_at`," which would silently favor whoever a
fixture happens to introduce first — a fixture-authoring accident, not
a modeled fact). A role with zero qualifying edges has no successor
(stays vacant) — a real, assertable outcome, not an error: "the office
goes unfilled" is itself information.

**Inputs are caller-assembled**, per the by-now-standard discipline:
the driver reads `self.social`'s relationship edges (a bulk scan,
mirroring rule 18's `_grudge_severities` shape — one new
`SocialStateStore.relationships_to(basis_id)`-style accessor, the
`grudges()` precedent from lane 43's O3 ruling) and hands the ranked
candidate list to the rule; the rule itself only picks the head of an
already-sorted list, never queries `self.social` directly (the T2.3
lesson, restated once more).

**How the counterfactual is asserted:** two scenario tests sharing one
`seed_id`, differing only in which fixture relationship edge has the
higher `strength` — assert the successor differs between them. No
driver-config flag is needed the way lane 37's `disabled_rules` toggle
was for T4a.2 (rule 19 isn't being turned on/off between the two runs,
its *input data* is); the two runs are simply two different
`Driver(...)` constructions with different relationship fixtures.

---

## 4. Registry + budget (question 4)

### Decision S6 — rule 19 registers as the last raw-19 stub; real toggle; budget unchanged at 17/20

- **Registration**: `RoleVacancySuccessionRule` replaces
  `StubRule(ROLE_VACANCY_SUCCESSION, 5)` (`rules.py:335`). Shape:
  `evaluate()` receives the caller-assembled candidate ranking (already
  sorted) and a `vacant: bool` flag; `fired` means a successor was
  installed (vacancy alone, or a vacancy with no qualifying candidate,
  is a distinct outcome the caller records separately — vacancy
  detection itself, per S3, isn't gated by this rule at all, so the
  rule's own `fired` is specifically about *succession happening*, not
  about the vacancy existing).
- **Real toggle**, same lane-19/43 precedent for driver-owned rules:
  disabling rule 19 must mean roles never resolve a successor (they'd
  stay vacant forever), not merely stop logging that they did.
- **Budget**: rule 19 is the 19th of the ladder's raw-19 names
  (`docs/scenario-ladder.md:152`) and was already counted inside R13's
  17/20 effective math (Tier-3 doc §7) — landing it fills the
  registry's *last* stub slot. All 19 raw names are now live; the
  effective count stays 17/20, confirming the packet's own claim of
  three slots of headroom for v0.3's social-action rules. Nothing here
  proposes a 20th rule.
- **RNG**: no new purpose (§3, Decision S5).

---

## 5. Proposed implementation-lane split (question 5)

| Lane | Scope | Files | Depends on | Effort |
|---|---|---|---|---|
| L-I | Role model core + vacancy + duty lapse: `chronicle/roles.py` (new), `driver.py` (`self.roles`, the `inject_event` vacancy branch, `status_changed` lapse-event injection), T5.1 rung | `chronicle/roles.py`, `chronicle/driver.py`, new scenario test | — | medium |
| L-J | Succession resolution + T5.2/T5.3: `rules.py` (`RoleVacancySuccessionRule` replacing the stub), `social.py` (the relationship-bulk-scan accessor), `driver.py` (ranking + installation wiring), the fixture-variation counterfactual test, the T5.3 no-orphaned-references rung | `chronicle/rules.py`, `chronicle/social.py`, `chronicle/driver.py`, new scenario tests | L-I | medium |

Two lanes, split by rung (T5.1 vs. T5.2+T5.3) — the same shape as
Tier 4a's L-G/L-H split, and for the same reason: L-I's pieces (role
object, vacancy detection, lapse events) are one coupled mechanism that
doesn't split usefully; L-J is a clean second phase once a `Role` object
and vacancy exist to succeed *into*. **This is the last mechanism
lane-set before Tier 6** — once L-J lands, the north-star composition
test (already the subject of a separate fixture-design lane) has every
mechanism it needs: succession (this doc), grief/grudge (Tier 3/4a),
city-wide propagation with mutation (Tier 2), and the read-only
aggregate view (Tier 6 itself, no new engine mechanism). No further
design-prep lane is anticipated after L-J besides Tier 6's own.

---

## 6. Open points for the owner

- **O1 — T5.3's scope** (§1, Decision S2). This doc reads "no orphaned
  references" narrowly (role-owned state never mirrors onto the
  holder, so nothing to orphan) rather than broadly (existing
  relationship/obligation/grudge records retroactively re-pointing
  through a role). The narrow reading needs no schema change; the
  broad reading is a real, larger feature. Recommend the narrow
  reading for v0.1, with the broad one named explicitly as a documented
  follow-up (the same status obligations' "no auto-derivation from
  beliefs" limitation already carries, `social.py:29-32`).
- **O2 — vacancy's objective (not belief-gated) trigger site** (§2,
  Decision S3). A genuine pattern departure from rules 16/17/18; worth
  the owner's explicit sign-off since it sets precedent for any future
  "fact about the world, not about anyone's knowledge of it" mechanism.
- **O3 — retiring the `role_lapse` reserved schema row** (§2, Decision
  S4) in favor of reusing `status_changed`. The schema currently
  reserves `role_lapse` by name (`docs/frame-log-schema.md:98`); this
  doc recommends never filling it. An explicit "not needed, superseded
  by status_changed" note is cleaner than a permanently-unfilled
  reservation.
- **O4 — double-role-holding.** Nothing in S1/S5 prevents a resolved
  successor from already holding a different role (e.g., a Housecarl
  succeeding to Steward while remaining Housecarl). `roles_held_by`
  (§1) is proposed as the accessor a future refinement would use to
  exclude or flag this, but no rung in this tier's ladder text asks for
  it — flagged so it's a deliberate deferral, not an oversight.

## 7. Findings

- **F1 — none of the packet's premises were wrong.** The rule-19 stub
  citation, the `status_changed` schema row and its
  `"role_appointed"` example, the `role_lapse` reservation, the
  existing `whiterun_court`/`whiterun_guard` faction fixture data, and
  `obligations_involving`'s existence all check out as described.
- **F2 — the schema already half-anticipated this design.** Lane 39's
  `status_changed` `status_kind` example (`"role_appointed"`) and the
  still-reserved `role_lapse` row together show the ladder's authors
  expected roles to need *some* event vocabulary; this doc's
  contribution is choosing which of the two to actually use (reuse
  `status_changed`, retire `role_lapse`) and why.
- **F3 — T5.3 is the one rung whose literal wording is broader than
  what this doc proposes to build**, and that gap is named explicitly
  (O1) rather than quietly resolved in the doc's own favor — the
  owner should read Decision S2 as a scope proposal, not a foregone
  conclusion.
