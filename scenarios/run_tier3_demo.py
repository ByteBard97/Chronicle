"""Generate the Tier-3-rich demo run into runs/: all five rungs in one cast.

Not a test — a runnable demo producer (pytest ignores it: no test_ prefix).
Same idiom as scenarios/run_carrier_demo.py (lane 17), but with the Tier-3
opt-ins registered, so the run contains the records the M4 dashboard lanes
(diff panel + rule-firing log, ui-spec §3.7) are built against — no demo run
predating the registry has rule_evaluated / threshold_crossed /
transmission_declined / reputation_updated rows. One cast
(docs/work-packets/lane-29-tier-3-demo-run.md):

  - a kin-motivated secret: hulda (kin to the player) declines every
    telling to olfrid at the Bannered Mare (rule 15, transmission_declined
    rows), while ysolda spreads it freely at the market;
  - serial theft against belethor: four thefts, escalation at the fourth
    (rule 11, threshold_crossed + the escalation_warning event) — the
    first three thefts and every theft retell to a non-victim leave
    rule_evaluated fired:false rows (the diff panel's stuck counter);
  - an obligation refusal: adrianne's second favor over ulfberth refused
    in front of proventus (rule 14's cascade: grudge_formed + a witnessed
    reputation row), the first favor fulfilled clean;
  - a status proclamation: the player named Thane, witnessed by proventus
    and irileth, reported onward at encounters (rule 16: witnessed and
    reported reputation rows);
  - ordinary rumor/mutation traffic underneath: mutation candidates
    registered on three slots, so variants and supersessions emerge en
    route (the ruled T2.3 churn — welcome at this scale).

Deterministic: fixed seed, fixed wall_ts, same log
(chronicle/tests/test_determinism.py proves the property this script
relies on).

    uv run python scenarios/run_tier3_demo.py
"""

import json
from collections import Counter

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed, RumorHeard
from chronicle.framelog import default_runs_dir
from chronicle.schedule import ScheduleBlock, npcs_present_at

RUN_ID = "tier3-demo-01"
SEED = "tier3-demo"
SAVE_UUID = "whiterun-save-1"
END_TICK = 48  # two game-days (ADR-0010)

# `_scripted_setup` stamps beliefs with gamets up to 3.0 (the fourth theft,
# n=4 below) *before* the tick loop starts -- `driver.run` must not begin
# earlier than that, or its first tick's encounter propagation (gamets=0.0)
# would try to retell a belief whose last_rehearsed is already ahead of it
# (claims.py's "a retelling cannot precede the teller's last rehearsal"
# guard). One past the highest gamets any _scripted_setup call uses.
LOOP_START_TICK = 4

# The cast, by rung.
MERCHANT = "belethor"  # serial-theft victim (T3.1)
PEER = "carlotta"  # market regular: hears thefts second-hand
GOSSIP = "ysolda"  # unmotivated secret holder: spreads it
KEEPER = "hulda"  # kin-motivated secret holder (T3.4): declines
LISTENER = "olfrid"  # the keeper's ever-curious tablemate
ISSUER = "adrianne"  # the wronged favor-giver (T3.3)
DEBTOR = "ulfberth"
COURTIER = "proventus"  # proclamation witness + obligation-refusal witness
HOUSECARL = "irileth"  # proclamation witness who never leaves Dragonsreach
SUBJECT = "player"  # the Thane-to-be; the secret's subject

DRAGONSREACH = "dragonsreach"
WARMAIDENS = "warmaidens"
BANNERED_MARE = "bannered_mare"
MARKET = "whiterun_market"

SCHEDULE = (
    ScheduleBlock(npc_id=HOUSECARL, location_id=DRAGONSREACH, start_tick=0, end_tick=END_TICK),
    ScheduleBlock(npc_id=COURTIER, location_id=DRAGONSREACH, start_tick=0, end_tick=2),
    ScheduleBlock(npc_id=COURTIER, location_id=WARMAIDENS, start_tick=2, end_tick=END_TICK),
    ScheduleBlock(npc_id=ISSUER, location_id=WARMAIDENS, start_tick=0, end_tick=END_TICK),
    ScheduleBlock(npc_id=DEBTOR, location_id=WARMAIDENS, start_tick=0, end_tick=END_TICK),
    ScheduleBlock(npc_id=KEEPER, location_id=BANNERED_MARE, start_tick=0, end_tick=END_TICK),
    ScheduleBlock(npc_id=LISTENER, location_id=BANNERED_MARE, start_tick=0, end_tick=END_TICK),
    ScheduleBlock(npc_id=MERCHANT, location_id=MARKET, start_tick=0, end_tick=END_TICK),
    ScheduleBlock(npc_id=PEER, location_id=MARKET, start_tick=0, end_tick=END_TICK),
    ScheduleBlock(npc_id=GOSSIP, location_id=MARKET, start_tick=2, end_tick=END_TICK),
)

# The Tier-3 opt-in seams (all construction-time, the mutation_candidates
# idiom), one per rung:
THEFT_KIND = "theft"
SECRET_KIND = "player_secret"
STATUS_KIND = "status_change"
CLAIM_PRIVACY = {SECRET_KIND: "subject"}  # T3.4: the kind is private; the subject slot names whom to
ACCUMULATION_THRESHOLDS = {THEFT_KIND: ("victim", 4)}  # T3.1: four strikes against the same victim
REPUTATION_RELEVANCE = {STATUS_KIND: ("subject", True, "civic")}  # T3.5: positive civic standing
MUTATION_CANDIDATES = {
    (STATUS_KIND, "role"): ("thane_of_haafingar", "thane_of_the_rift"),
    (SECRET_KIND, "secret"): ("a stolen sweetroll", "a daedric pact"),
    (THEFT_KIND, "perpetrator"): ("a cave bear", "a rival merchant"),
}

THANE_CLAIM = "claim-thanehood"
SECRET_CLAIM = "claim-player-secret"
VIOLATION_EVIDENTIARY_STRENGTH = 0.6  # T3.3: caller-supplied, from the favor's sanctions


def _scripted_setup(driver: Driver) -> None:
    """All pre-run scripted writes; the tick loop then carries the rumors."""
    # Canonical anchors (the lane-23/26 precedent: an existing event class
    # anchors the claim; the claim kind carries the semantics). Seqs 1-6
    # are hand-numbered; the engine's escalation event takes seq 7 when
    # the fourth theft fires it (lane-24's seq discipline).
    driver.inject_event(
        RumorHeard(
            tick=0, save_uuid=SAVE_UUID, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, hearer_id=COURTIER,
            source_id="jarl_balgruuf", rumor_id="rumor-thanehood",
            content="the player is named Thane of Whiterun",
        ),
        origin={"kind": "scenario", "detail": "run_tier3_demo"},
    )
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid=SAVE_UUID, generation=0, seq=2,
            gamets=0.0, wall_ts=0.0, witness_id=KEEPER,
            perpetrator_id=SUBJECT, crime_type="trespass", location_id="the_hall_of_the_dead",
        ),
        origin={"kind": "scenario", "detail": "run_tier3_demo"},
    )
    for witness_id in (COURTIER, HOUSECARL):
        driver.witness(
            claim_id=THANE_CLAIM,
            belief_id=f"belief-{witness_id}-thane",
            evidence_id=f"evidence-{witness_id}-thane",
            kind=STATUS_KIND,
            slots={"subject": SUBJECT, "role": "thane_of_whiterun"},
            canonical_event_key=EventKey(SAVE_UUID, 0, 1),
            witness_id=witness_id,
            gamets=0.0,
        )
    for witness_id in (KEEPER, GOSSIP):
        driver.witness(
            claim_id=SECRET_CLAIM,
            belief_id=f"belief-{witness_id}-secret",
            evidence_id=f"evidence-{witness_id}-secret",
            kind=SECRET_KIND,
            slots={"subject": SUBJECT, "secret": "the player looted the hall of the dead"},
            canonical_event_key=EventKey(SAVE_UUID, 0, 2),
            witness_id=witness_id,
            gamets=0.0,
        )
    # The motive (rule 15 stage 1 reads this caller-looked-up edge).
    driver.form_relationship(
        id="rel-keeper-player", from_id=KEEPER, to_id=SUBJECT,
        basis="kinship", basis_id=None, strength=0.9, gamets=0.0,
    )
    # The favor ledger (T3.3): one fulfilled clean, one refused in front
    # of whoever is actually at warmaiden's at tick 2 (the courtier,
    # arrived that tick).
    driver.issue_obligation(
        id="obl-favor-1", issuer_id=ISSUER, debtor_id=DEBTOR, beneficiary_id=None,
        action="return the borrowed steel", condition=None, gamets=0.0,
    )
    driver.issue_obligation(
        id="obl-favor-2", issuer_id=ISSUER, debtor_id=DEBTOR, beneficiary_id=None,
        action="forge a replacement blade", condition=None, gamets=0.0,
        witnesses=(COURTIER,),
    )
    driver.fulfill_obligation("obl-favor-1", gamets=1.0)
    driver.violate_obligation(
        "obl-favor-2",
        gamets=2.0,
        violation_evidentiary_strength=VIOLATION_EVIDENTIARY_STRENGTH,
        present_npc_ids=npcs_present_at(SCHEDULE, 2)[WARMAIDENS],
    )
    # Serial theft (T3.1): four thefts the merchant witnesses first-hand;
    # the fourth crosses the registered threshold and escalates.
    for n in (1, 2, 3, 4):
        gamets = float(n - 1)
        driver.inject_event(
            CrimeWitnessed(
                tick=int(gamets), save_uuid=SAVE_UUID, generation=0, seq=n + 2,
                gamets=gamets, wall_ts=0.0, witness_id=MERCHANT,
                perpetrator_id="a pickpocket", crime_type="theft", location_id=MARKET,
            ),
            origin={"kind": "scenario", "detail": "run_tier3_demo"},
        )
        driver.witness(
            claim_id=f"claim-theft-{n}",
            belief_id=f"belief-merchant-theft-{n}",
            evidence_id=f"evidence-merchant-theft-{n}",
            kind=THEFT_KIND,
            slots={"perpetrator": "a pickpocket", "victim": MERCHANT, "location": MARKET},
            canonical_event_key=EventKey(SAVE_UUID, 0, n + 2),
            witness_id=MERCHANT,
            gamets=gamets,
        )


def main() -> None:
    driver = Driver(
        run_id=RUN_ID,
        seed_id=SEED,
        save_uuid=SAVE_UUID,
        generation=0,
        schedule=SCHEDULE,
        encounter_probability=1.0,  # the decline stream must be guaranteed, not rolled for
        claim_privacy=CLAIM_PRIVACY,
        accumulation_thresholds=ACCUMULATION_THRESHOLDS,
        reputation_relevance=REPUTATION_RELEVANCE,
        mutation_candidates=MUTATION_CANDIDATES,
    )
    _scripted_setup(driver)
    driver.run(LOOP_START_TICK, END_TICK)
    driver.close()

    run_dir = default_runs_dir() / RUN_ID
    counts: Counter[str] = Counter()
    fired_counts: Counter[bool] = Counter()
    for stream, type_field in (("events.jsonl", "event_type"), ("trace.jsonl", "record_type")):
        for line in (run_dir / stream).open():
            payload = json.loads(line)["payload"]
            record_type = payload.get(type_field) or payload.get("record_type", "?")
            counts[f"{stream}:{record_type}"] += 1
            if record_type == "rule_evaluated":
                fired_counts[bool(payload["fired"])] += 1
    for key, count in sorted(counts.items()):
        print(f"{key}: {count}")
    print(f"rule_evaluated fired: true={fired_counts[True]} false={fired_counts[False]}")

    # The lane's smoke facts: all five Tier-3 record types present, plus
    # negative rule rows (the diff panel's stuck counter).
    required = (
        "trace.jsonl:rule_evaluated",
        "trace.jsonl:threshold_crossed",
        "trace.jsonl:transmission_declined",
        "trace.jsonl:reputation_updated",
        "trace.jsonl:grudge_formed",
        "events.jsonl:escalation_warning",
    )
    missing = [key for key in required if counts[key] == 0]
    print(f"smoke: {'OK' if not missing and fired_counts[False] > 0 else f'MISSING {missing}'}")
    print(f"run written: {run_dir}")


if __name__ == "__main__":
    main()
