"""The T6 north-star fixture: the Jarl assassination, composed (docs/design/north-star-fixture.md).

Tier 6 adds no new mechanism (docs/scenario-ladder.md, Tier 6 intro) --
this module composes fixtures that already exist rather than inventing
new ones (design doc N1/N5): `carrier_schedule()` (lane 13, the
cross-hold backbone) and `whiterun_relationships.py`'s court/tavern
edges (proventus/irileth/whiterun_guard_1/hulda/ysolda), extended with
exactly the two things the ladder's §9 named as missing --
household kin edges and a temple. No existing fixture file is edited;
this module only imports and adds.

One fixture, one run-length parameter (design doc O3, ruled): callers
pass `end_tick` -- a short window for the composition test, the full
multi-day `carrier_schedule.END_TICK` for the M7 demo producer.

Cast, by group (design doc N1):

  - Household (mourn + grudge): frothar, nelkir -- jarl_balgruuf's
    kin. NEW npcs, NEW kinship edges (the ladder §9 consequence: grudge
    rules gate on pre-existing edges, so these must exist for the
    household's grudge/mourning beats to fire at all).
  - Court (succession candidates): proventus, irileth, whiterun_guard_1
    -- their existing `whiterun_court`/`whiterun_guard` edges
    (`whiterun_relationships.py`) are reused unchanged; no new edges
    needed for succession to resolve (rule 19 already ranks by
    whatever's in the store).
  - Market/carriers/Markarth: `carrier_schedule()`'s existing cast,
    unchanged.
  - Temple: priest. NEW npc, NEW location -- the mourning destination.

Roles (design doc O4, ruled): TWO roles share the same institution
(`whiterun_court`) at two scales -- `steward_of_whiterun` (Proventus,
sitting, unaffected by this fixture's death) and `jarl_of_whiterun`
(jarl_balgruuf, who dies) -- so succession exercises the vision's own
big beat while the steward role demonstrates the mechanism composes at
a second scale without interference.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from chronicle.fixtures.carrier_schedule import (
    CARAVANEER_DEPARTURE,
    WHITERUN_MARKET,
    carrier_schedule,
)
from chronicle.fixtures.whiterun_relationships import seed_whiterun_via_driver
from chronicle.roles import Duty, Role
from chronicle.schedule import ScheduleBlock

if TYPE_CHECKING:
    from chronicle.driver import Driver

DECEASED = "jarl_balgruuf"
KILLER = "the_player"
STEWARD = "proventus"
HOUSECARL = "irileth"
GUARD = "whiterun_guard_1"
FROTHAR = "frothar"
NELKIR = "nelkir"
PRIEST = "priest"

DRAGONSREACH = "dragonsreach"
TEMPLE = "temple_of_kynareth"

STEWARD_ROLE = "steward_of_whiterun"
JARL_ROLE = "jarl_of_whiterun"
WHITERUN_COURT = "whiterun_court"

DEATH_CLAIM_ID = "claim-balgruuf-assassination"
DEATH_CLAIM_KIND = "npc_death"

# The caller-supplies-context seams every landed tier already defined
# the shape of (design doc N3) -- assembled here, nothing new designed.
MOURNING_TRIGGERS = {DEATH_CLAIM_KIND: "deceased"}
MOURNING_LOCATION = TEMPLE
# The stranger walkthrough's own example slot (docs/ui-spec.md:135,
# "drill provenance from belief to dagger through the mutation").
MUTATION_CANDIDATES = {
    (DEATH_CLAIM_KIND, "weapon"): ("a poisoned blade", "witchcraft", "a hired crossbow"),
}
# Reputation substrate for the ripple's aggregate (design doc F4: the
# aggregate ITSELF is a test-side/dashboard-side read, never fed back
# into a rule -- this mapping only produces the reputation_updated rows
# the read computes over).
REPUTATION_RELEVANCE = {DEATH_CLAIM_KIND: ("killer", False, "security")}


def north_star_schedule() -> tuple[ScheduleBlock, ...]:
    """`carrier_schedule()` (unedited) plus the household/court/temple blocks it doesn't carry.

    Household kin get no presence requirement at Dragonsreach -- they
    are witnessed in via a scripted `driver.witness()` call (the same
    "presence isn't required for a scripted witness" idiom every
    demo producer in this series uses), not an encounter-sampled one.
    Their base schedule is simply "at home" throughout; the mourning
    overlay (rule 17) overrides it the instant they're informed,
    regardless of what it says.
    """
    base = carrier_schedule()
    end_tick = max(block.end_tick for block in base)
    return base + (
        ScheduleBlock(npc_id=DECEASED, location_id=DRAGONSREACH, start_tick=0, end_tick=end_tick),
        ScheduleBlock(npc_id=HOUSECARL, location_id=DRAGONSREACH, start_tick=0, end_tick=end_tick),
        # Proventus bridges the court's news to the market -- without
        # him (or someone) making this trip, nothing ever reaches the
        # caravaneer and the whole cross-hold beat is unreachable.
        ScheduleBlock(npc_id=STEWARD, location_id=DRAGONSREACH, start_tick=0, end_tick=CARAVANEER_DEPARTURE // 2),
        ScheduleBlock(npc_id=STEWARD, location_id=WHITERUN_MARKET, start_tick=CARAVANEER_DEPARTURE // 2, end_tick=end_tick),
        ScheduleBlock(npc_id=GUARD, location_id=DRAGONSREACH, start_tick=0, end_tick=CARAVANEER_DEPARTURE // 2),
        ScheduleBlock(npc_id=GUARD, location_id=WHITERUN_MARKET, start_tick=CARAVANEER_DEPARTURE // 2, end_tick=end_tick),
        ScheduleBlock(npc_id=FROTHAR, location_id=DRAGONSREACH, start_tick=0, end_tick=end_tick),
        ScheduleBlock(npc_id=NELKIR, location_id=DRAGONSREACH, start_tick=0, end_tick=end_tick),
        ScheduleBlock(npc_id=PRIEST, location_id=TEMPLE, start_tick=0, end_tick=end_tick),
    )


def seed_relationships(driver: Driver, *, gamets: float = 0.0) -> None:
    """The existing court/tavern edges (unedited) plus the two new household kin edges."""
    seed_whiterun_via_driver(driver, gamets=gamets)
    for kin_id in (FROTHAR, NELKIR):
        driver.form_relationship(
            id=f"rel-{kin_id}-balgruuf", from_id=kin_id, to_id=DECEASED,
            basis="kinship", basis_id=None, strength=0.9, gamets=gamets,
        )


def install_roles(driver: Driver) -> None:
    driver.roles.install(
        Role(
            id=STEWARD_ROLE, title="Steward of Whiterun", institution_id=WHITERUN_COURT,
            duties=(Duty(name="collect_taxes", lapse_status_kind="duty_lapsed"),),
            holder_id=STEWARD, vacated_at=None,
        )
    )
    driver.roles.install(
        Role(
            id=JARL_ROLE, title="Jarl of Whiterun", institution_id=WHITERUN_COURT,
            duties=(Duty(name="hold_court", lapse_status_kind="duty_lapsed"),),
            holder_id=DECEASED, vacated_at=None,
        )
    )


def build_driver(run_id: str, seed_id: str, *, end_tick: int | None = None, runs_dir=None) -> Driver:
    """A fully-seeded driver: schedule, relationships, roles, and every caller-supplies-context mapping installed.

    end_tick is accepted but not itself used to trim the schedule --
    `north_star_schedule()`'s blocks already span the full
    `carrier_schedule()` window regardless of how many ticks the caller
    actually runs (design doc O3: one fixture, one run-length parameter
    supplied at `driver.run()` time, not two fixture variants).
    """
    from chronicle.driver import Driver

    driver = Driver(
        run_id=run_id,
        seed_id=seed_id,
        save_uuid="whiterun-save-1",
        generation=0,
        schedule=north_star_schedule(),
        encounter_probability=1.0,
        mutation_probability=0.9,
        mutation_candidates=MUTATION_CANDIDATES,
        mourning_triggers=MOURNING_TRIGGERS,
        mourning_location=MOURNING_LOCATION,
        reputation_relevance=REPUTATION_RELEVANCE,
        runs_dir=runs_dir,
    )
    seed_relationships(driver, gamets=0.0)
    install_roles(driver)
    return driver
