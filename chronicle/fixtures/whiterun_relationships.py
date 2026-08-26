"""Hand-seeded sparse relationship graph for v0.1's Whiterun cast.

docs/v0.1-spec.md rule 15 wants relationship candidates to come from
co-location/schedule overlap, not a hand-authored list -- but real
encounter sampling needs the math tier's schedule model, which doesn't
exist yet. This fixture is the deliberate stand-in: it seeds the same
"colocation"/"kinship"/"faction"/"shared_employer" bases the store
already validates, by hand, for the ~20-30 NPC Whiterun cast named in
docs/v0.1-spec.md §1. When schedule-driven encounter sampling lands, it
produces Relationship records through the same form_relationship() call
this fixture uses -- no schema change, just a different caller.

Only edges the v0.1 scenario suite actually exercises are seeded here;
this is not an attempt at a complete Whiterun social graph.

Two seeding paths over one shared edge list: seed_whiterun() writes
straight into a SocialStateStore (pre-frame-log callers), and
seed_whiterun_via_driver() goes through the Driver's form_relationship
wrapper so the formations also land in the frame log as
relationship_formed trace records (frame-log schema §4).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from chronicle.social import Relationship, SocialStateStore, form_relationship

if TYPE_CHECKING:
    from chronicle.driver import Driver

# The edge list, minus gamets (each seeder supplies its own). Field names
# mirror form_relationship()'s kwargs exactly.
_EDGE_SPECS: tuple[dict[str, Any], ...] = (
    # The Jarl's court: employed by/serving Balgruuf directly.
    {"id": "rel-proventus-balgruuf", "from_id": "proventus", "to_id": "jarl_balgruuf", "basis": "shared_employer", "basis_id": "whiterun_court", "strength": 0.85},
    {"id": "rel-irileth-balgruuf", "from_id": "irileth", "to_id": "jarl_balgruuf", "basis": "shared_employer", "basis_id": "whiterun_court", "strength": 0.95},
    # A rank-and-file guard: same faction as the Jarl's household guard,
    # but no personal closeness -- deliberately weaker than the court's edges,
    # for scenarios contrasting institutional loyalty with personal bond.
    {"id": "rel-guard-balgruuf", "from_id": "whiterun_guard_1", "to_id": "jarl_balgruuf", "basis": "faction", "basis_id": "whiterun_guard", "strength": 0.3},
    # Hulda and Ysolda are deliberately NOT connected to jarl_balgruuf --
    # they carry the rumor (scenarios/test_jarl_death_belief_cascade.py)
    # but have no relationship edge to the victim, so form_grudge() must
    # refuse to give either of them a grudge (rule 8). Co-location between
    # the tavern regulars themselves, unrelated to the Jarl's death:
    {"id": "rel-hulda-ysolda", "from_id": "hulda", "to_id": "ysolda", "basis": "colocation", "basis_id": "bannered_mare", "strength": 0.5},
    # 5 more edges added 2026-08-26, for the same 18-NPC growth pass as
    # whiterun_schedule.py -- deliberately conservative: only relationships
    # this well-established in vanilla Skyrim lore are seeded. NPCs with a
    # schedule block but no confident lore-backed relationship (Nazeem,
    # Danica Pure-Spring/Heimskr, Braith, Olava the Feeble,
    # Lillith Maiden-Loom, Brenuin, Anoriath) are left schedule-only, same
    # as whiterun_guard_1 above -- a schedule block alone still makes them
    # schedulable/encounterable, and an invented edge would be worse than
    # none.
    {"id": "rel-carlotta-lucia", "from_id": "carlotta_valentia", "to_id": "lucia", "basis": "kinship", "basis_id": "valentia_family", "strength": 0.9},
    {"id": "rel-amren-saffir", "from_id": "amren", "to_id": "saffir", "basis": "kinship", "basis_id": "amren_family", "strength": 0.9},
    {"id": "rel-fralia-olfina", "from_id": "fralia_gray_mane", "to_id": "olfina_gray_mane", "basis": "kinship", "basis_id": "gray_mane_family", "strength": 0.9},
    {"id": "rel-idolaf-lars", "from_id": "idolaf_battle_born", "to_id": "lars_battle_born", "basis": "kinship", "basis_id": "battle_born_family", "strength": 0.9},
    # Warmaiden's: Sigurd is Adrianne's forge assistant/employee.
    {"id": "rel-sigurd-adrianne", "from_id": "sigurd", "to_id": "adrianne_avenicci", "basis": "shared_employer", "basis_id": "warmaidens", "strength": 0.6},
)


def seed_whiterun(store: SocialStateStore, *, gamets: float = 0.0) -> tuple[Relationship, ...]:
    """Add the sparse relationship edges the v0.1 Whiterun cast needs. Returns what it added."""
    edges = tuple(form_relationship(**spec, gamets=gamets) for spec in _EDGE_SPECS)
    for edge in edges:
        store.add_relationship(edge)
    return edges


def seed_whiterun_via_driver(driver: Driver, *, gamets: float = 0.0) -> tuple[Relationship, ...]:
    """seed_whiterun through the Driver's wrapper, so the formations are traced (frame-log schema §4)."""
    return tuple(driver.form_relationship(**spec, gamets=gamets) for spec in _EDGE_SPECS)
