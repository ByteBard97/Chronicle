# Lane 44 delivery report — Tier 5 design prep (roles and vacancy)

**Delivered:** `94a6d5c` — `docs/design/tier-5-roles-and-vacancy.md`.
No code. Suite unchanged: 223 passed, ruff clean.

## Cover note

**Decided** (this doc's own recommendations, ready to build against):

- A new module, `chronicle/roles.py`, rather than growing
  `social.py`'s four-kind scope to five — roles are a genuinely
  different axis of state (an office outliving its holders), and every
  other store module here owns exactly one concern.
- Vacancy detection is **objective**, wired at `inject_event`'s
  existing `NPCDied` branch (the same site `_deceased` already
  updates) — not belief-gated like rules 16/17/18. A role becomes
  vacant the instant its holder dies, independent of who's heard.
- Duty lapse reuses `status_changed` (already landed, lane 39) rather
  than filling the schema's still-reserved `role_lapse` row — that
  row's own field comment ("fields defined with roles") makes it look
  load-bearing, but `status_changed`'s own docstring already named
  `"role_appointed"` as an example `status_kind`, so the vocabulary
  this tier needs already exists.
- Succession is **deterministic ranking by relationship strength**
  (tie-break: lower `npc_id`, lexicographic) — no roll, no new RNG
  purpose. This makes "fixtures carry the counterfactual, not seeds"
  an exact guarantee rather than a well-tuned probability, the same
  instinct behind Tier 4a/4b's hard-zero tunables.
- Rule 19 registers as the registry's last raw-19 stub with a real
  (driver-owned) toggle; the effective budget stays 17/20 — confirmed,
  not just asserted, by re-deriving the count from R13's original
  consolidation math.

**Needs adjudication** (owner-visible, §6 in the doc):

- **O1 — T5.3's scope**, the one point genuinely worth debate. The
  ladder's literal wording ("everything that pointed at the holder
  resolves through the role") could mean existing
  `Relationship`/`Obligation`/`Grudge` records retroactively re-point
  through a role indirection — a real schema change to three
  already-shipped record types. This doc proposes a narrower reading
  (role-owned state never mirrors onto the holder, so nothing
  orphans) and names the broader reading explicitly as a deferred
  follow-up rather than silently picking the easier answer.
- **O2 — vacancy's objective trigger site.** A genuine departure from
  every prior tier's belief-acquisition-gated pattern; worth explicit
  sign-off since it sets precedent.
- **O3 — retiring the `role_lapse` schema reservation** in favor of
  `status_changed`. Means recommending the owner leave a named schema
  slot permanently unfilled, which deserves a decision on record rather
  than silent supersession.
- **O4 — double-role-holding** is left unaddressed (a resolved
  successor could already hold a different role) — flagged as a
  deliberate deferral, since no rung in this tier's ladder text asks
  for the exclusion.

**Surprises:**

1. The schema had already half-anticipated this design: lane 39's
   `status_changed` example `status_kind` (`"role_appointed"`) and the
   still-reserved `role_lapse` row together show the ladder's authors
   expected *some* role-event vocabulary to be needed. This doc's real
   contribution turned out to be choosing between the two options
   already sitting in the schema, not inventing a new one.
2. T5.3 is the one rung whose plain-English wording is genuinely
   broader than what seemed buildable at this tier's scope. Rather than
   resolve that quietly in the doc's own favor, I wrote up both
   readings and flagged the gap (O1) — this is the one place in the
   doc where I'm least confident the owner will agree with my proposed
   scope.
3. Confirming the rule-19 budget math (17/20 unchanged) required
   re-deriving it from scratch rather than trusting the packet's own
   claim at face value — it checked out, but it's the kind of thing
   worth actually recomputing rather than repeating.

Lane breakdown proposed: L-I (role model + vacancy + duty lapse, T5.1)
then L-J (succession + T5.2's fixture-variation counterfactual + T5.3,
depends on L-I). This is explicitly the last mechanism-lane pair before
Tier 6's north-star composition test — no further design-prep lane is
anticipated after L-J besides Tier 6's own. Full detail, dependencies,
and file lists in §5 of the doc.
