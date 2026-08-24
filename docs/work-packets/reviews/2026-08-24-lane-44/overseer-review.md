# Lane 44 — overseer review and rulings (Tier 5 design doc)

**Date:** 2026-08-24 · **Overseer:** planning agent · **Re:**
`docs/design/tier-5-roles-and-vacancy.md` (`94a6d5c`)

## Verdict: **accepted.** The design is disciplined, minimal, and honest
about its one real scope question.

Decisions worth affirming explicitly: S1 (a `roles.py` module — roles
are a different axis of state, and the module-per-concern discipline
holds); S3 (objective vacancy at `inject_event` — correct: the roster
is a layer-1 fact like `_deceased`, and the ladder's "lapse effects
propagate through Tiers 1–4" only makes sense with an objective lapse
whose *consequences* propagate); S4 (lapse via `status_changed` — the
vocabulary lane 39 built for); S5 (deterministic strength-ranking with
lexicographic tie-break — "fixtures carry the counterfactual" as an
exact guarantee, the same instinct as Tier 4's hard-zero tunables);
S6 (budget confirmed at 17/20 with the last stub filled).

## Rulings on the open points (coordinator authority, owner-delegated)

- **O1 — T5.3 narrow reading: accepted.** Role-owned state lives only
  on the `Role` keyed by `role_id`; nothing mirrors onto the holder,
  so nothing orphans. The broad reading (retroactive re-pointing of
  `Relationship`/`Obligation`/`Grudge` records) is a real, larger
  feature — named as a documented follow-up, not built. The design
  rule that falls out and which packets must enforce: **anything
  needing the *current* holder asks `holder_of(role_id)`; nothing
  stores the holder's npc id as a proxy for the role.**
- **O2 — objective vacancy trigger: accepted, with the precedent
  named.** Facts about the world (death, vacancy) are layer-1 and
  objective; facts about knowledge are belief-gated. This is the
  correct line and the right place to draw it.
- **O3 — `role_lapse` reservation retired: accepted and executed.**
  Schema §3:98 now reads "superseded, will not be filled" with the
  `status_changed` mapping (coordinator edit, dated).
- **O4 — double-role-holding: deferral accepted.** No rung asks;
  `roles_held_by` exists for the future refinement.

## Dispatch

Lane 47 (L-I: role model + vacancy + lapse, T5.1) and lane 48 (L-J:
succession + T5.2/T5.3) packetized per the doc's split; 48 queues
behind 47. After 48 lands, every ladder mechanism exists — the path to
T6 runs through lane 45's fixture design and the T6 composition lane.
