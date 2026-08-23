"""chronicle/cli.py: agent-debug CLI subcommand tests (docs/dashboard-build-plan.md §2 M1).

Each subcommand gets at least one test against a small hand-built run log,
built the same way chronicle/tests/test_framelog.py does (through
chronicle.driver.Driver, so the log looks like a real run's, not a
special-cased fixture format).
"""

from __future__ import annotations

import json

import pytest

from chronicle.claims import EventKey
from chronicle.cli import run as cli_run
from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed, NPCDied
from chronicle.framelog import serialize_state
from chronicle.social import form_grudge, form_relationship, issue_obligation

_SEED = "cli-test-seed"
_RUN_ID = "cli-test-run"
_SAVE_UUID = "cli-save-1"


def _build_run(tmp_path, run_id: str = _RUN_ID) -> None:
    driver = Driver(run_id=run_id, seed_id=_SEED, save_uuid=_SAVE_UUID, generation=0, runs_dir=tmp_path)

    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE_UUID, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_cli"},
    )
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid=_SAVE_UUID, generation=0, seq=2,
            gamets=0.0, wall_ts=1.0, witness_id="irileth",
            perpetrator_id="unknown", crime_type="murder", location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_cli"},
    )
    death_claim, irileth_belief, _ = driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-irileth-death",
        evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=EventKey(_SAVE_UUID, 0, 1),
        witness_id="irileth",
        gamets=0.0,
    )
    driver.retell(
        claim=death_claim,
        parent_variant=None,
        variant_id="variant-1",
        belief_id="belief-hulda",
        evidence_id="evidence-hulda",
        teller_id="irileth",
        teller_belief=irileth_belief,
        hearer_id="hulda",
        gamets=5.0,
        mutate_slot="perpetrator",
        mutated_value="the Thalmor",
        location_id="bannered_mare",
    )

    # Social layer: hand-seeded directly on the store, same as fixtures do
    # (docs/frame-log-schema.md §9's known gap -- no trace record type yet
    # for social mutations, so these only ever show up at the next
    # keyframe, which is exactly what this fixture exercises).
    rel = form_relationship(id="rel-1", from_id="hulda", to_id="jarl_balgruuf", basis="colocation", basis_id=None, strength=0.6, gamets=0.0)
    driver.social.add_relationship(rel)
    grudge = form_grudge(
        id="grudge-1", holder_id="hulda", victim_id="jarl_balgruuf", target_id="the_thalmor",
        grievance_type="murder", source_belief_id="belief-hulda", evidentiary_strength=0.4,
        relationship_to_victim=rel, gamets=5.0,
    )
    driver.social.add_grudge(grudge)
    obligation = issue_obligation(
        id="obligation-1", issuer_id="jarl_balgruuf", debtor_id="proventus", beneficiary_id=None,
        action="manage the treasury", condition=None, gamets=0.0,
    )
    driver.social.add_obligation(obligation)
    driver.social.update_reputation(observer_id="hulda", subject_id="proventus", context="stewardship", kind="witnessed", positive=True, gamets=5.0)

    driver.writer.write_keyframe(tick=10, state=serialize_state(driver.claims, driver.social, driver.schedule, tick=10))
    driver.writer.flush()
    driver.close()


@pytest.fixture
def run_dir(tmp_path):
    _build_run(tmp_path)
    return tmp_path


def _run_cli(capsys, argv: list[str]) -> tuple[int, str, str]:
    code = cli_run(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


def test_inspect_reports_beliefs_and_social_standing(run_dir, capsys):
    code, out, _err = _run_cli(capsys, ["--runs-dir", str(run_dir), "inspect", "hulda", "--run", _RUN_ID, "--at", "10"])
    assert code == 0
    assert "belief hulda" in out or "belief-hulda" in out
    assert "claim-jarl-death" in out
    assert "the Thalmor" in out  # hulda's mutated variant
    assert "rumor stage" in out
    # social layer: hulda holds a relationship to the jarl, a grudge against
    # the Thalmor, and a reputation assessment of Proventus.
    assert "relationships held (1)" in out
    assert "jarl_balgruuf" in out
    assert "grudges held (1)" in out
    assert "the_thalmor" in out
    assert "reputations held (as observer) (1)" in out
    assert "proventus" in out


def test_inspect_on_unknown_run_fails_clearly(tmp_path, capsys):
    with pytest.raises(SystemExit):
        cli_run(["--runs-dir", str(tmp_path), "inspect", "hulda", "--run", "no-such-run", "--at", "0"])


# ---------------------------------------------------------------------------
# trace
# ---------------------------------------------------------------------------


def test_trace_walks_the_evidence_chain_back_to_the_witness(run_dir, capsys):
    code, out, _err = _run_cli(capsys, ["--runs-dir", str(run_dir), "trace", "claim-jarl-death", "--run", _RUN_ID, "--at", "10"])
    assert code == 0
    assert "claim claim-jarl-death" in out
    assert "holder irileth" in out
    assert "holder hulda" in out
    assert "witnessed via irileth" in out
    assert "reported via irileth" in out


def test_trace_on_unknown_claim_reports_an_error(run_dir, capsys):
    code, _out, err = _run_cli(capsys, ["--runs-dir", str(run_dir), "trace", "claim-nonexistent", "--run", _RUN_ID, "--at", "10"])
    assert code == 1
    assert "no claim" in err


# ---------------------------------------------------------------------------
# feed
# ---------------------------------------------------------------------------


def test_feed_filters_by_npc_and_prints_matching_records_in_tick_order(run_dir, capsys):
    code, out, _err = _run_cli(capsys, ["--runs-dir", str(run_dir), "feed", "--run", _RUN_ID, "--npc", "hulda"])
    assert code == 0
    lines = [line for line in out.splitlines() if line.startswith("tick ")]
    assert lines  # at least the transmitted record naming hulda as hearer
    assert any("transmitted" in line for line in lines)
    ticks = [int(line.split()[1]) for line in lines]
    assert ticks == sorted(ticks)


def test_feed_sorts_by_tick_even_when_the_log_is_not_written_in_tick_order(tmp_path, capsys):
    """A hand-scripted scenario can write trace records out of tick order --
    scenarios/test_jarl_death_belief_cascade.py does exactly this (a later
    witness() call at an earlier gamets than a retell() that preceded it in
    the file). FrameLogReader.records() yields file order; feed must not
    trust that as tick order (see feed_command's docstring)."""
    run_id = "cli-out-of-order-run"
    driver = Driver(run_id=run_id, seed_id=_SEED, save_uuid=_SAVE_UUID, generation=0, runs_dir=tmp_path)
    # Written to the file in this order: tick 50, then tick 10, then tick 30.
    driver.writer.write_trace(tick=50, payload={"record_type": "nothing_salient", "location_id": "x", "npc_a": "a", "npc_b": "b", "claim_id": None, "reason": "neither-informed"})
    driver.writer.write_trace(tick=10, payload={"record_type": "nothing_salient", "location_id": "x", "npc_a": "a", "npc_b": "b", "claim_id": None, "reason": "neither-informed"})
    driver.writer.write_trace(tick=30, payload={"record_type": "nothing_salient", "location_id": "x", "npc_a": "a", "npc_b": "b", "claim_id": None, "reason": "neither-informed"})
    driver.writer.flush()
    driver.close()

    code, out, _err = _run_cli(capsys, ["--runs-dir", str(tmp_path), "feed", "--run", run_id])
    assert code == 0
    lines = [line for line in out.splitlines() if line.startswith("tick ")]
    ticks = [int(line.split()[1]) for line in lines]
    assert ticks == [10, 30, 50]  # sorted, not file order (50, 10, 30)


def test_feed_filters_by_tick_range(run_dir, capsys):
    code, out, _err = _run_cli(capsys, ["--runs-dir", str(run_dir), "feed", "--run", _RUN_ID, "--from-tick", "6", "--to-tick", "10"])
    assert code == 0
    lines = [line for line in out.splitlines() if line.startswith("tick ")]
    for line in lines:
        tick = int(line.split()[1])
        assert 6 <= tick <= 10


# ---------------------------------------------------------------------------
# inject
# ---------------------------------------------------------------------------


def test_inject_composes_canonical_event_json_for_a_known_type(capsys):
    code, out, _err = _run_cli(
        capsys,
        [
            "inject", "--run", _RUN_ID, "--at", "42", "--type", "npc_died",
            "--payload", json.dumps({"npc_id": "sven", "cause": "brawl"}),
        ],
    )
    assert code == 0
    assert "NOT written to the run's log" in out
    body = "\n".join(out.splitlines()[1:])
    composed = json.loads(body)
    assert composed["event_type"] == "npc_died"
    assert composed["tick"] == 42
    assert composed["npc_id"] == "sven"
    assert composed["cause"] == "brawl"
    assert composed["killer_id"] is None
    assert composed["location_id"] is None
    assert "origin" in composed and composed["origin"]["kind"] == "console"


def test_inject_merges_actor_into_the_type_specific_field(capsys):
    code, out, _err = _run_cli(
        capsys,
        [
            "inject", "--run", _RUN_ID, "--at", "1", "--type", "crime_witnessed", "--actor", "irileth",
            "--payload", json.dumps({"perpetrator_id": "unknown", "crime_type": "theft"}),
        ],
    )
    assert code == 0
    body = "\n".join(out.splitlines()[1:])
    composed = json.loads(body)
    assert composed["witness_id"] == "irileth"


def test_inject_rejects_an_unknown_event_type(capsys):
    code, _out, err = _run_cli(capsys, ["inject", "--run", _RUN_ID, "--at", "1", "--type", "not_a_real_kind"])
    assert code == 1
    assert "unknown event type" in err


def test_inject_rejects_a_reserved_not_yet_producing_event_type(capsys):
    """escalation_warning is a real, schema-committed canonical event_type
    (docs/frame-log-schema.md §3) but reserved for Tier 3 -- "writers must
    not emit them before their tier." inject must reject it with a message
    naming the owning tier, not silently accept it. (Separately: the
    console's own EVENT_TYPES list -- claim_born/mutation/grudge_formed/
    threshold_crossed -- doesn't match any canonical event_type at all, see
    this lane's report; that's a different, sharper finding than this
    reserved-kind case.)"""
    code, _out, err = _run_cli(capsys, ["inject", "--run", _RUN_ID, "--at", "1", "--type", "escalation_warning"])
    assert code == 1
    assert "reserved" in err


def test_inject_rejects_missing_required_fields(capsys):
    code, _out, err = _run_cli(capsys, ["inject", "--run", _RUN_ID, "--at", "1", "--type", "rumor_heard", "--payload", "{}"])
    assert code == 1
    assert "missing required field" in err


def test_inject_rejects_invalid_json_payload(capsys):
    code, _out, err = _run_cli(capsys, ["inject", "--run", _RUN_ID, "--at", "1", "--type", "npc_died", "--payload", "{not json"])
    assert code == 1
    assert "not valid JSON" in err
