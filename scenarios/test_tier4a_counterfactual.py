"""Scenario-ladder rung T4a.2 (Second-order counterfactual) -- the roll-identity proof.

Run A (with reroute) vs. Run B (fixture-frozen, no reroute), same seed,
keyed randomness (docs/scenario-ladder.md:84). The lane-33/37 pins in
force (docs/design/tier-4a-schedule-write-back.md §2 T4, §5 T7;
docs/work-packets/lane-37-t4a2-counterfactual.md):

  - Run B is Run A with ``disabled_rules=("schedule-write-back",)`` --
    not a hand-authored second fixture (T7): same seed_id, same base
    schedule, same everything else.
  - **Primary assertion: every roll outside the mourner's changed sites
    is identical across runs.** Precisely: for every ``encounter_rolled``
    record whose participants EXCLUDE the mourner, the record in A and
    the one in B at the same (tick, location_id, participants) are
    byte-identical in value/threshold/encountered (T4's exact wording --
    "per-pair, not per-site"). A pair that simply doesn't get rolled in
    one run (because the mourner isn't there to be paired with) is not a
    violation; it's the changed part.
  - **Companion narrative assertion:** the death rumor sven carries
    reaches the priest (at the mourning destination) before the market
    in Run A, and the reverse in Run B.

Fixture: sven (kin to the deceased) witnesses jarl_balgruuf's death at
tick 0 -- immediately overlaid to the temple in Run A. The priest lives
at the temple; a market regular lives at the market (sven's own base
site); camilla and delphine live at an unrelated tavern, present in
every one of this test's assertions as the "outside the mourner's
changed sites" control pair.
"""

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import NPCDied
from chronicle.framelog import FrameLogReader
from chronicle.rules import SCHEDULE_WRITE_BACK
from chronicle.schedule import ScheduleBlock

_SEED = "tier4a-counterfactual"
_SAVE = "whiterun-save-1"
_TICKS = 15  # well inside the mourning window -- sven never returns to market in Run A
_MOURNING_DURATION = 30

_DECEASED = "jarl_balgruuf"
_MOURNER = "sven"
_PRIEST = "priest"
_MARKET_NPC = "market_regular"
_CAMILLA = "camilla"
_DELPHINE = "delphine"

_MARKET = "market"
_TEMPLE = "temple"
_TAVERN = "tavern"

_CLAIM_ID = "claim-balgruuf-death"
_CLAIM_KIND = "npc_death"
_MOURNING_TRIGGERS = {_CLAIM_KIND: "deceased"}

_SCHEDULE = (
    ScheduleBlock(npc_id=_MOURNER, location_id=_MARKET, start_tick=0, end_tick=_TICKS),
    ScheduleBlock(npc_id=_MARKET_NPC, location_id=_MARKET, start_tick=0, end_tick=_TICKS),
    ScheduleBlock(npc_id=_PRIEST, location_id=_TEMPLE, start_tick=0, end_tick=_TICKS),
    # The control pair: present the whole run, never named by the
    # mourner's overlay, at a site the mourning mechanism never touches.
    ScheduleBlock(npc_id=_CAMILLA, location_id=_TAVERN, start_tick=0, end_tick=_TICKS),
    ScheduleBlock(npc_id=_DELPHINE, location_id=_TAVERN, start_tick=0, end_tick=_TICKS),
)


def _driver(run_id: str, *, disabled_rules: tuple[str, ...] = ()) -> Driver:
    return Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=_SCHEDULE,
        encounter_probability=1.0,
        mourning_triggers=_MOURNING_TRIGGERS,
        mourning_location=_TEMPLE,
        mourning_duration_ticks=_MOURNING_DURATION,
        disabled_rules=disabled_rules,
    )


def _records(driver: Driver, stream: str) -> list[dict]:
    try:
        driver.writer.flush()
    except ValueError:  # flush of closed file -- close() already flushed
        pass
    reader = FrameLogReader(driver.writer.run_dir)
    return [record["payload"] for record in reader.records(stream)]


def _run(run_id: str, *, disabled_rules: tuple[str, ...] = ()) -> Driver:
    driver = _driver(run_id, disabled_rules=disabled_rules)
    driver.form_relationship(
        id="rel-sven-balgruuf", from_id=_MOURNER, to_id=_DECEASED,
        basis="kinship", basis_id=None, strength=0.9, gamets=0.0,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id=_DECEASED,
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_tier4a_counterfactual"},
    )
    driver.witness(
        claim_id=_CLAIM_ID,
        belief_id=f"belief-{_MOURNER}-balgruuf-death",
        evidence_id=f"evidence-{_MOURNER}-balgruuf-death",
        kind=_CLAIM_KIND,
        slots={"deceased": _DECEASED, "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=EventKey(_SAVE, 0, 1),
        witness_id=_MOURNER,
        gamets=0.0,
    )
    driver.run(0, _TICKS)
    driver.close()
    return driver


def _rolls(driver: Driver) -> list[dict]:
    return [p for p in _records(driver, "trace") if p.get("record_type") == "encounter_rolled"]


def _roll_key_tuple(payload: dict) -> tuple[int, str, frozenset[str]]:
    """(tick, location_id, participants) -- the merge-scan's join key.

    Reused verbatim by ``rolls_outside`` below; the dashboard's §3.9
    first-divergent-roll tool (ui-spec §3.9, design doc F4) should key its
    scan the same way, so the scenario-test definition of "outside the
    mourner's changed sites" and the tool's definition never drift apart.
    """
    return payload["roll_key"]["tick"], payload["location_id"], frozenset((payload["npc_a"], payload["npc_b"]))


def rolls_outside(rolls: list[dict], excluded_npc_id: str) -> dict[tuple[int, str, frozenset[str]], dict]:
    """Every roll whose participants exclude ``excluded_npc_id``, keyed for a merge-scan.

    This is the exact predicate T4a.2's roll-identity guarantee is about
    (design doc T4: "per-pair, not per-site") -- a pair that doesn't
    include the mourner is untouched by the reroute regardless of who
    else is or isn't present at its site. Intended to be shared with the
    dashboard's §3.9 run-comparison tool (design doc F4), not
    reimplemented per-caller.
    """
    return {
        _roll_key_tuple(payload): payload
        for payload in rolls
        if excluded_npc_id not in (payload["npc_a"], payload["npc_b"])
    }


def test_t4a2_every_roll_outside_the_mourners_pairs_is_byte_identical():
    a = _run("tier4a-counterfactual-a")
    b = _run("tier4a-counterfactual-b", disabled_rules=(SCHEDULE_WRITE_BACK,))

    outside_a = rolls_outside(_rolls(a), _MOURNER)
    outside_b = rolls_outside(_rolls(b), _MOURNER)

    # Non-vacuous: the control pair (camilla, delphine) at the tavern
    # actually produced rolls in both runs.
    assert outside_a
    assert any(_TAVERN == payload["location_id"] for payload in outside_a.values())

    # Same key set: every pair excluding the mourner is rolled at exactly
    # the same (tick, site) in both runs -- nothing about presence
    # elsewhere in the world shifted for them.
    assert set(outside_a) == set(outside_b)
    for key, payload_a in outside_a.items():
        payload_b = outside_b[key]
        assert payload_a["value"] == payload_b["value"]
        assert payload_a["threshold"] == payload_b["threshold"]
        assert payload_a["encountered"] == payload_b["encountered"]
        assert payload_a["roll_key"] == payload_b["roll_key"]


def test_t4a2_the_rumor_reaches_the_priest_before_the_market_in_a_and_the_reverse_in_b():
    a = _run("tier4a-counterfactual-a-narrative")
    b = _run("tier4a-counterfactual-b-narrative", disabled_rules=(SCHEDULE_WRITE_BACK,))

    priest_informed_a = a.belief_of(_PRIEST, _CLAIM_ID) is not None
    market_informed_a = a.belief_of(_MARKET_NPC, _CLAIM_ID) is not None
    priest_informed_b = b.belief_of(_PRIEST, _CLAIM_ID) is not None
    market_informed_b = b.belief_of(_MARKET_NPC, _CLAIM_ID) is not None

    # Run A: sven is overlaid to the temple from tick 0 -- he tells the
    # priest there and never returns to the market within this run's
    # (short, inside-the-mourning-window) span.
    assert priest_informed_a is True
    assert market_informed_a is False

    # Run B: rule 17 disabled -- sven never leaves the market, so the
    # reverse holds.
    assert priest_informed_b is False
    assert market_informed_b is True
