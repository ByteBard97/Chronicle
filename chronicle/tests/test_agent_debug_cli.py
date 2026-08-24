"""chronicle/cli.py: the M1 agent-debug CLI's positional invocation forms and the inject write path.

Lane 9's flag-form subcommands and compose-only inject are covered by
chronicle/tests/test_cli.py; this file covers the positional forms
(``inspect <run_id> <npc_id> --at <tick>``, ``trace <run_id> <claim_id>``,
``feed <run_id> ...``), the ``--at`` default, the unknown-entity refusals,
and ``inject <run_id> --event '<json>'`` -- the write path the dashboard's
injection console composes. Runs are built with the real Driver in a tmp
CHRONICLE_RUNS_DIR (the one env var shared by pytest and the dashboard,
ui-spec §1.2), the same pattern as chronicle/tests/test_driver.py.
"""

from __future__ import annotations

import json

import pytest

from chronicle.claims import EventKey, decay
from chronicle.cli import _FEED_RECORD_TYPES, main
from chronicle.driver import Driver
from chronicle.events import NPCDied
from chronicle.framelog import FrameLogReader
from chronicle.schedule import ScheduleBlock

_SEED = "agent-cli-seed"
_RUN = "agent-cli-run"
_SAVE_UUID = "save-1"
_TICKS = 30  # the run's max tick is therefore 29


@pytest.fixture()
def run_dir(tmp_path, monkeypatch):
    """A small real Driver run in a tmp CHRONICLE_RUNS_DIR: one witnessed death, encounter-driven spread."""
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    driver = Driver(
        run_id=_RUN,
        seed_id=_SEED,
        save_uuid=_SAVE_UUID,
        generation=0,
        schedule=tuple(
            ScheduleBlock(npc_id=npc, location_id="bannered_mare", start_tick=0, end_tick=50)
            for npc in ("irileth", "proventus", "hulda")
        ),
        encounter_probability=1.0,
        runs_dir=tmp_path,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE_UUID, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="bannered_mare",
        ),
        origin={"kind": "scenario", "detail": "test_agent_debug_cli"},
    )
    driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-irileth-death",
        evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "bannered_mare"},
        canonical_event_key=EventKey(_SAVE_UUID, 0, 1),
        witness_id="irileth",
        gamets=0.0,
    )
    driver.run(0, _TICKS)
    driver.close()
    return tmp_path / _RUN


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


def test_inspect_positional_form_shows_decayed_beliefs_and_rumor_stage(run_dir, capsys):
    rc = main(["inspect", _RUN, "irileth", "--at", "29"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "=== irileth @ tick 29" in out
    assert "claim-jarl-death" in out
    assert "npc_death" in out
    assert "rumor stage : repeated" in out  # irileth retold the story during the run
    # Rule 19: the printed confidence has read-time decay applied -- it is
    # decay(belief, 29), never the stored as-of-last-rehearsed 0.95.
    belief = FrameLogReader(run_dir).state_at(29).claims.belief_of("irileth", "claim-jarl-death")
    expected = decay(belief, 29.0)
    assert f"confidence  : {expected.confidence:.4f}" in out
    assert "confidence  : 0.9500 " not in out  # the stored value appears only parenthetically


def test_inspect_at_defaults_to_the_runs_max_tick(run_dir, capsys):
    rc = main(["inspect", _RUN, "irileth"])
    out = capsys.readouterr().out
    assert rc == 0
    assert f"@ tick {_TICKS - 1}" in out


def test_inspect_unknown_npc_exits_nonzero(run_dir, capsys):
    rc = main(["inspect", _RUN, "nazeem"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "unknown npc" in captured.err


def test_unknown_run_exits_nonzero(run_dir, capsys):
    rc = main(["inspect", "no-such-run", "irileth", "--at", "1"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "no such run" in captured.err


# ---------------------------------------------------------------------------
# trace
# ---------------------------------------------------------------------------


def test_trace_positional_form_lists_touching_records_in_seq_order_and_variant_lineage(run_dir, capsys):
    rc = main(["trace", _RUN, "claim-jarl-death"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "-- trace records touching this claim" in out
    assert "belief_formed" in out
    assert "transmitted" in out
    assert "nothing_salient" in out  # both-informed rows once everyone holds the claim
    section = out.split("-- trace records touching this claim")[1]
    seqs = [int(line.split("seq")[1].split()[0]) for line in section.splitlines() if line.strip().startswith("tick ")]
    assert seqs == sorted(seqs)  # seq order
    assert "-- variant lineage" in out
    assert "variant-auto-" in out
    # Lane 9's chain view is still part of the output.
    assert "holder irileth" in out


def test_trace_unknown_claim_exits_nonzero(run_dir, capsys):
    rc = main(["trace", _RUN, "claim-nope"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "no claim" in captured.err


def test_trace_supersession_renders_a_null_variant_id_as_the_original_telling(tmp_path, monkeypatch, capsys):
    """A repelled challenge's winner is the un-varianted original telling --
    null in the supersession record (amended schema §4:120). trace renders
    that as ``(original telling)``, not Python's None (lane-12 finding 6)."""
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    driver = Driver(
        run_id=_RUN,
        seed_id=_SEED,
        save_uuid=_SAVE_UUID,
        generation=0,
        schedule=tuple(
            ScheduleBlock(npc_id=npc, location_id="bannered_mare", start_tick=0, end_tick=50)
            for npc in ("proventus", "hulda")
        ),
        encounter_probability=1.0,
        runs_dir=tmp_path,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE_UUID, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="bannered_mare",
        ),
        origin={"kind": "scenario", "detail": "test_agent_debug_cli"},
    )
    driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-proventus-death",
        evidence_id="evidence-proventus-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "bannered_mare"},
        canonical_event_key=EventKey(_SAVE_UUID, 0, 1),
        witness_id="proventus",
        gamets=0.0,
    )
    # A scripted mutated retelling, then the eyewitness repels the gossip's
    # challenge: winner_variant_id is None (the original telling stands).
    driver.retell(
        claim=driver.claim("claim-jarl-death"),
        parent_variant=None,
        variant_id="variant-gossip",
        belief_id="belief-hulda-death",
        evidence_id="evidence-hulda-variant-gossip",
        teller_id="proventus",
        teller_belief=driver.belief_of("proventus", "claim-jarl-death"),
        hearer_id="hulda",
        gamets=0.0,
        mutate_slot="perpetrator",
        mutated_value="the Thalmor",
    )
    driver.resolve(
        claim=driver.claim("claim-jarl-death"),
        holder_id="proventus",
        teller_id="hulda",
        teller_belief=driver.belief_of("hulda", "claim-jarl-death"),
        evidence_id="evidence-proventus-challenged",
        gamets=2.0,
    )
    driver.close()

    rc = main(["trace", _RUN, "claim-jarl-death"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "variant-gossip superseded by (original telling)" in out
    assert "None" not in out


def test_trace_lists_a_supersession_whose_loser_is_held_by_nobody(tmp_path, monkeypatch, capsys):
    """lane-17 finding 1: cli.py's old supersession filter was built from
    *currently-held* variants, so a loser that gets re-pointed away from by
    its only holder vanished from the listing at every ``--at``. The fix
    (lane 32) unions over the claim's full variant lineage instead."""
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    driver = Driver(
        run_id=_RUN,
        seed_id=_SEED,
        save_uuid=_SAVE_UUID,
        generation=0,
        schedule=tuple(
            ScheduleBlock(npc_id=npc, location_id="bannered_mare", start_tick=0, end_tick=50)
            for npc in ("irileth", "hulda")
        ),
        encounter_probability=1.0,
        runs_dir=tmp_path,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE_UUID, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="bannered_mare",
        ),
        origin={"kind": "scenario", "detail": "test_agent_debug_cli"},
    )
    driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-irileth-death",
        evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "bannered_mare"},
        canonical_event_key=EventKey(_SAVE_UUID, 0, 1),
        witness_id="irileth",
        gamets=0.0,
    )
    # hulda hears a mutated (weaker, "reported") variant first -- the only
    # holder of variant-mutated.
    driver.retell(
        claim=driver.claim("claim-jarl-death"),
        parent_variant=None,
        variant_id="variant-mutated",
        belief_id="belief-hulda-death",
        evidence_id="evidence-hulda-variant-mutated",
        teller_id="irileth",
        teller_belief=driver.belief_of("irileth", "claim-jarl-death"),
        hearer_id="hulda",
        gamets=0.0,
        mutate_slot="perpetrator",
        mutated_value="the Thalmor",
    )
    # irileth's stronger "witnessed" telling then challenges hulda directly
    # and wins: hulda's belief re-points to the original telling (winner
    # variant_id None), so variant-mutated is left held by nobody.
    driver.resolve(
        claim=driver.claim("claim-jarl-death"),
        holder_id="hulda",
        teller_id="irileth",
        teller_belief=driver.belief_of("irileth", "claim-jarl-death"),
        evidence_id="evidence-hulda-challenged",
        gamets=2.0,
    )
    driver.close()

    rc = main(["trace", _RUN, "claim-jarl-death"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "variant-mutated superseded by (original telling)" in out


# ---------------------------------------------------------------------------
# feed
# ---------------------------------------------------------------------------


def _feed_lines(out: str) -> list[str]:
    return [line for line in out.splitlines() if line.startswith("tick ")]


def test_feed_positional_form_filters_by_npc_and_limit(run_dir, capsys):
    rc = main(["feed", _RUN, "--npc", "hulda", "--limit", "5"])
    out = capsys.readouterr().out
    assert rc == 0
    lines = _feed_lines(out)
    assert len(lines) == 5
    assert all("hulda" in line for line in lines)
    ticks = [int(line.split()[1]) for line in lines]
    assert ticks == sorted(ticks)


def test_feed_filters_by_location_and_at(run_dir, capsys):
    rc = main(["feed", _RUN, "--location", "bannered_mare", "--at", "2", "--limit", "0"])
    out = capsys.readouterr().out
    assert rc == 0
    lines = _feed_lines(out)
    assert lines
    assert all("bannered_mare" in line for line in lines)
    assert max(int(line.split()[1]) for line in lines) <= 2


def test_feed_only_shows_the_feed_vocabulary(run_dir, capsys):
    """This run's cast opts into no Tier-3 mappings, so its actual vocabulary
    is Tier-0/1/3-wrapper rows (rule_evaluated/encounter_rolled/transmitted/
    nothing_salient); the assertion checks against the full lane-32
    vocabulary (``_FEED_RECORD_TYPES``) rather than hardcoding that subset,
    so it doesn't go stale the next time a lane adds a producer."""
    rc = main(["feed", _RUN, "--limit", "0"])
    out = capsys.readouterr().out
    assert rc == 0
    lines = _feed_lines(out)
    assert lines
    assert all(any(record_type in line for record_type in _FEED_RECORD_TYPES) for line in lines)
    # belief_formed/belief_corroborated are claim-layer rows, visible via
    # `trace`, deliberately excluded from the encounter feed.
    assert not any("belief_formed" in line for line in lines)


# ---------------------------------------------------------------------------
# inject (the write path)
# ---------------------------------------------------------------------------


def test_inject_event_appends_a_console_origin_record(run_dir, capsys):
    event = {"event_type": "npc_died", "gamets": 30, "npc_id": "nazeem", "cause": "fell off the Skyforge", "location_id": "whiterun"}
    rc = main(["inject", _RUN, "--event", json.dumps(event)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "injected npc_died" in out

    reader = FrameLogReader(run_dir)
    events = [r for r in reader.records("events") if r["payload"].get("event_type") == "npc_died"]
    last = events[-1]
    assert last["tick"] == 30  # gamets-derived
    assert last["payload"]["npc_id"] == "nazeem"
    assert last["payload"]["origin"] == {"kind": "console", "detail": "chronicle inject"}  # schema §3
    # The writer machinery kept the sidecar index current (the liveness
    # contract, schema §1), and the log still reconstructs afterwards.
    assert "30" in reader.read_index()["streams"]["events"]["tick_offsets"]
    reader.state_at(30)


def test_inject_at_the_current_max_tick_is_allowed(run_dir, capsys):
    event = {"event_type": "npc_died", "tick": _TICKS - 1, "npc_id": "nazeem", "cause": "test"}
    rc = main(["inject", _RUN, "--event", json.dumps(event)])
    assert rc == 0, capsys.readouterr().err


def test_inject_refuses_a_historical_tick_as_fork_territory(run_dir, capsys):
    event = {"event_type": "npc_died", "tick": 5, "npc_id": "nazeem", "cause": "test"}
    rc = main(["inject", _RUN, "--event", json.dumps(event)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "fork territory" in captured.err
    assert "deferred" in captured.err
    # nothing was appended
    reader = FrameLogReader(run_dir)
    assert all(r["payload"].get("npc_id") != "nazeem" for r in reader.records("events"))


def test_inject_rejects_invalid_json(run_dir, capsys):
    rc = main(["inject", _RUN, "--event", "{not json"])
    assert rc == 1
    assert "not valid JSON" in capsys.readouterr().err


def test_inject_rejects_a_reserved_event_type(run_dir, capsys):
    rc = main(["inject", _RUN, "--event", json.dumps({"event_type": "role_lapse", "tick": 30})])
    assert rc == 1
    assert "reserved" in capsys.readouterr().err


def test_inject_rejects_missing_required_fields(run_dir, capsys):
    rc = main(["inject", _RUN, "--event", json.dumps({"event_type": "npc_died", "tick": 30})])
    assert rc == 1
    assert "missing required field" in capsys.readouterr().err


def test_inject_rejects_a_duplicate_seq(run_dir, capsys):
    event = {"event_type": "npc_died", "tick": 30, "seq": 1, "npc_id": "nazeem", "cause": "test"}
    rc = main(["inject", _RUN, "--event", json.dumps(event)])
    assert rc == 1
    assert "idempotency" in capsys.readouterr().err
