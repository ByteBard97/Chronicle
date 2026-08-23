"""Scenario-ladder rung T2.3 (Conflicting variants): a holder of variant A hears variant B.

The frozen policy (docs/scenario-ladder.md §T2.3, v0.4): evidence-type
ordering (witnessed > reported) with a summed-strength tiebreak, the
challenger strictly stronger to displace (exact tie -> the incumbent
stands); supersession as a separate trace record (docs/frame-log-schema.md
§4, as amended 2026-08-23) naming loser/winner -- never a write onto the
losing variant; the winner takes the contested-claim confidence dent; and
resolution is a first-class ClaimStore write path (ClaimStore.resolve)
that enforces one-belief-per-(holder, claim) at the store.

Coordinator rulings of 2026-08-23 (docs/work-packets/reviews/2026-08-23-lane-12/)
pinned the semantics this file asserts: a supersession is a correction,
not a transmission (no new Variant; the loser adopts the winner's variant
as-held; exactly one Evidence -- the contested hearing -- appended to the
winner's belief); correction semantics composed from the existing
retell/corroborate constants; the dent constant itself
(CONTESTED_CLAIM_CONFIDENCE_DENT = 0.1).

Fixtures are scripted driver calls (witness/retell/corroborate/resolve)
plus one encounter-driven run proving the tick-loop wiring and arbitrary-T
reconstruction parity. All expected confidence values are computed from
the same module constants the engine uses -- the rung asserts the dent
matches the constant, never a magic number inline.
"""

import pytest

from chronicle.claims import (
    CONFIDENCE_DECAY_HALF_LIFE,
    CONTESTED_CLAIM_CONFIDENCE_DENT,
    RESOLUTION_RULE,
    RETELL_CONFIDENCE_DECAY,
    RETELL_GIST_DECAY,
    RETELL_VERBATIM_DECAY,
    WITNESS_CONFIDENCE,
    EventKey,
    decay,
)
from chronicle.driver import Driver
from chronicle.events import NPCDied
from chronicle.framelog import FrameLogReader
from chronicle.schedule import ScheduleBlock

_SAVE = "whiterun-save-1"
_DEATH_KEY = EventKey(_SAVE, 0, 1)
_CANONICAL_SLOTS = {"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"}
_MUTATED_VALUE = "a bandit chief"

# The supersession payload's field set, per docs/frame-log-schema.md §4 as
# amended 2026-08-23 (lane-12 pre-implementation review, findings 1-2).
_SUPERSESSION_FIELDS = {
    "record_type",
    "holder_id",
    "claim_id",
    "loser_variant_id",
    "winner_variant_id",
    "resolution_rule",
    "confidence_dent",
    "teller_id",
    "teller_belief_id",
    "evidence_id",
    "winner_belief_id",
}


def _driver(run_id: str, **kwargs: object) -> Driver:
    return Driver(run_id=run_id, seed_id="tier2-resolution", save_uuid=_SAVE, generation=0, **kwargs)  # type: ignore[arg-type]


def _witness_death(driver: Driver, *, witness_id: str, slots: dict[str, str] | None = None):
    """A witnessed jarl death at gamets 0: canonical event + belief_formed, T2.2's fixture shape."""
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_tier2_resolution"},
    )
    return driver.witness(
        claim_id="claim-jarl-death",
        belief_id=f"belief-{witness_id}-death",
        evidence_id=f"evidence-{witness_id}-death",
        kind="npc_death",
        slots=slots if slots is not None else dict(_CANONICAL_SLOTS),
        canonical_event_key=_DEATH_KEY,
        witness_id=witness_id,
        gamets=0.0,
    )


def _retell_with_mutation(driver: Driver, *, teller_id: str, hearer_id: str, variant_id: str, gamets: float):
    """A scripted retelling that mutates the perpetrator slot, so teller and hearer hold differing content."""
    claim = driver.claim("claim-jarl-death")
    teller_belief = driver.belief_of(teller_id, claim.id)
    return driver.retell(
        claim=claim,
        parent_variant=None,
        variant_id=variant_id,
        belief_id=f"belief-{hearer_id}-death",
        evidence_id=f"evidence-{hearer_id}-{variant_id}",
        teller_id=teller_id,
        teller_belief=teller_belief,
        hearer_id=hearer_id,
        gamets=gamets,
        mutate_slot="perpetrator",
        mutated_value=_MUTATED_VALUE,
    )


def test_t23_eyewitness_shrugs_off_thirdhand_gossip():
    """Witnessed beats reported: the gossip's challenge fails, the eyewitness stands -- dented."""
    driver = _driver("scenario-tier2-resolution-repel")
    _witness_death(driver, witness_id="proventus")
    _retell_with_mutation(driver, teller_id="proventus", hearer_id="hulda", variant_id="variant-gossip", gamets=0.0)
    proventus_before = driver.belief_of("proventus", "claim-jarl-death")

    resolution = driver.resolve(
        claim=driver.claim("claim-jarl-death"),
        holder_id="proventus",
        teller_id="hulda",
        teller_belief=driver.belief_of("hulda", "claim-jarl-death"),
        evidence_id="evidence-proventus-challenged",
        gamets=2.0,
    )
    driver.close()

    # Rung assert: the named rule fires, and names itself in the record.
    assert resolution.resolution_rule == RESOLUTION_RULE
    # The eyewitness (witnessed) beats the rumor-holder (reported): the
    # incumbent stands. Winner = the claim's original telling (None -- the
    # amended schema's null-variant idiom); loser = the gossip's variant.
    assert resolution.winner_variant_id is None
    assert resolution.loser_variant_id == "variant-gossip"
    assert resolution.winner_belief_id == proventus_before.id
    # The winner shows exactly the constant dent on the decayed-to-now
    # confidence (repelled challenge: corroborate()-style decay, then dent).
    after = driver.belief_of("proventus", "claim-jarl-death")
    expected = decay(proventus_before, 2.0).confidence * (1 - CONTESTED_CLAIM_CONFIDENCE_DENT)
    assert after.confidence == pytest.approx(expected)
    assert after.variant_id is None  # never re-pointed; the story stands
    # Both encounters are in the winner's evidence chain: the original
    # witnessed grounding plus the contested hearing, appended.
    evidence = driver.claims.evidence_for(after.id)
    assert [e.evidence_type for e in evidence] == ["witnessed", "reported"]
    assert evidence[1].source_id == "hulda"
    # The emitted record matches the amended schema row field-for-field.
    trace = [r["payload"] for r in FrameLogReader(driver.writer.run_dir).records("trace")]
    supersessions = [p for p in trace if p["record_type"] == "supersession"]
    assert len(supersessions) == 1
    assert set(supersessions[0]) == _SUPERSESSION_FIELDS
    assert supersessions[0]["confidence_dent"] == CONTESTED_CLAIM_CONFIDENCE_DENT
    assert supersessions[0]["teller_belief_id"] == "belief-hulda-death"


def test_t23_rumor_holder_updates_when_the_witness_contradicts_them():
    """The flip: swap which side holds the eyewitness and the resolution flips -- the rumor-holder adopts."""
    driver = _driver("scenario-tier2-resolution-adopt")
    _witness_death(driver, witness_id="proventus")
    _retell_with_mutation(driver, teller_id="proventus", hearer_id="hulda", variant_id="variant-gossip", gamets=0.0)
    hulda_before = driver.belief_of("hulda", "claim-jarl-death")

    resolution = driver.resolve(
        claim=driver.claim("claim-jarl-death"),
        holder_id="hulda",
        teller_id="proventus",
        teller_belief=driver.belief_of("proventus", "claim-jarl-death"),
        evidence_id="evidence-hulda-corrected",
        gamets=2.0,
    )
    driver.close()

    # Direction flipped with the fixture: now the incoming side terminates
    # in witnessed evidence, so the challenger wins and hulda adopts the
    # eyewitness's telling -- the claim's original telling, variant None.
    assert resolution.winner_variant_id is None
    assert resolution.loser_variant_id == "variant-gossip"
    after = driver.belief_of("hulda", "claim-jarl-death")
    assert after.id == hulda_before.id  # the belief is re-pointed in place, not replaced
    assert after.variant_id is None
    # Adoption re-derives strengths from the teller's belief exactly as
    # retell() does, with the dent on confidence; first_learned survives.
    proventus = driver.belief_of("proventus", "claim-jarl-death")
    assert after.confidence == pytest.approx(
        proventus.confidence * RETELL_CONFIDENCE_DECAY * (1 - CONTESTED_CLAIM_CONFIDENCE_DENT)
    )
    assert after.verbatim_strength == pytest.approx(proventus.verbatim_strength * RETELL_VERBATIM_DECAY)
    assert after.gist_strength == pytest.approx(proventus.gist_strength * RETELL_GIST_DECAY)
    assert after.first_learned == hulda_before.first_learned
    assert after.last_rehearsed == 2.0
    # Both encounters in the winner's chain: her original hearing of the
    # gossip, then the contested hearing from the witness.
    evidence = driver.claims.evidence_for(after.id)
    assert [e.evidence_type for e in evidence] == ["reported", "reported"]
    assert evidence[0].source_id == "proventus"  # the original retelling
    assert evidence[1].source_id == "proventus"  # the correction
    assert evidence[1].strength == pytest.approx(proventus.confidence)  # testimony strength as given
    # The loser variant is a frozen lineage record: still in the store,
    # still saying what it said.
    assert driver.variant("variant-gossip").slots["perpetrator"] == _MUTATED_VALUE
    # ...and her rumor bookkeeping: she heard the eyewitness's telling
    # (the variant she now holds), he told his.
    rumor = driver.claims.rumor_state("hulda", "claim-jarl-death", None)
    assert rumor is not None and rumor.last_heard == 2.0


def test_t23_strength_tiebreak_summed_evidence_including_corroboration():
    """Reported vs reported: higher summed evidence strength wins -- and corroboration counts toward the sum."""
    driver = _driver("scenario-tier2-resolution-tiebreak")
    _witness_death(driver, witness_id="irileth")
    claim = driver.claim("claim-jarl-death")
    # hulda hears the story unmutated; nazeem hears a mutated telling.
    # Both ground in reported evidence of strength 0.95 -- a type AND sum
    # tie until nazeem's belief picks up corroboration from ysolda.
    driver.retell(
        claim=claim, parent_variant=None, variant_id="variant-canonical",
        belief_id="belief-hulda-death", evidence_id="evidence-hulda-canonical",
        teller_id="irileth", teller_belief=driver.belief_of("irileth", claim.id),
        hearer_id="hulda", gamets=0.0,
    )
    _retell_with_mutation(driver, teller_id="irileth", hearer_id="nazeem", variant_id="variant-gossip", gamets=0.0)
    driver.retell(
        claim=claim, parent_variant=None, variant_id="variant-canonical-2",
        belief_id="belief-ysolda-death", evidence_id="evidence-ysolda-canonical",
        teller_id="irileth", teller_belief=driver.belief_of("irileth", claim.id),
        hearer_id="ysolda", gamets=0.0,
    )
    driver.corroborate(
        belief_id="belief-nazeem-death",
        source_belief=driver.belief_of("ysolda", claim.id),
        evidence_id="evidence-nazeem-corroborated",
        gamets=1.0,
    )

    resolution = driver.resolve(
        claim=claim,
        holder_id="hulda",
        teller_id="nazeem",
        teller_belief=driver.belief_of("nazeem", claim.id),
        evidence_id="evidence-hulda-outweighed",
        gamets=2.0,
    )
    driver.close()

    # nazeem's side sums 0.95 (grounding) + ysolda's corroboration strength;
    # hulda's sums 0.95 alone -- strictly stronger, so the challenger wins
    # on the tiebreak even though both terminate in reported evidence.
    assert resolution.winner_variant_id == "variant-gossip"
    assert resolution.loser_variant_id == "variant-canonical"
    after = driver.belief_of("hulda", claim.id)
    assert after.variant_id == "variant-gossip"
    nazeem = driver.belief_of("nazeem", claim.id)
    assert after.confidence == pytest.approx(
        nazeem.confidence * RETELL_CONFIDENCE_DECAY * (1 - CONTESTED_CLAIM_CONFIDENCE_DENT)
    )
    # All three of hulda's evidence records are visible: her grounding and
    # the contested hearing -- and nazeem's sum included his corroboration.
    assert len(driver.claims.evidence_for(after.id)) == 2
    assert len(driver.claims.evidence_for(nazeem.id)) == 2


def test_t23_exact_tie_two_eyewitnesses_incumbent_stands():
    """The post-T0.4 default case: two eyewitnesses, 1.0 vs 1.0 -- a shrug, not a coin flip."""
    driver = _driver("scenario-tier2-resolution-exact-tie")
    _witness_death(driver, witness_id="proventus")
    # Irileth witnessed the same event but disagrees about the perpetrator
    # (ladder T0.4, closed by this lane): a Variant of the shared Claim.
    driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-irileth-death",
        evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={**_CANONICAL_SLOTS, "perpetrator": "a thalmor justiciar"},
        canonical_event_key=_DEATH_KEY,
        witness_id="irileth",
        gamets=0.0,
    )
    proventus_before = driver.belief_of("proventus", "claim-jarl-death")

    resolution = driver.resolve(
        claim=driver.claim("claim-jarl-death"),
        holder_id="proventus",
        teller_id="irileth",
        teller_belief=driver.belief_of("irileth", "claim-jarl-death"),
        evidence_id="evidence-proventus-standoff",
        gamets=1.0,
    )
    driver.close()

    # Both ground in witnessed evidence at strength 1.0: the challenger must
    # be STRICTLY stronger, so the incumbent stands -- and still takes the
    # dent (a challenged belief is held less certainly even when nothing
    # changes hands). The record fires either way.
    assert resolution.winner_variant_id is None
    assert resolution.loser_variant_id == "claim-jarl-death-witness-disagreement-irileth"
    after = driver.belief_of("proventus", "claim-jarl-death")
    expected = decay(proventus_before, 1.0).confidence * (1 - CONTESTED_CLAIM_CONFIDENCE_DENT)
    assert after.confidence == pytest.approx(expected)
    # The loser's belief is untouched -- losers never mutate.
    irileth = driver.belief_of("irileth", "claim-jarl-death")
    assert irileth.variant_id == "claim-jarl-death-witness-disagreement-irileth"
    assert irileth.confidence == WITNESS_CONFIDENCE


def test_t23_store_raises_on_every_duplicate_creating_path():
    """The one-belief invariant lives at the store now, not in driver courtesy."""
    driver = _driver("scenario-tier2-resolution-invariant")
    _witness_death(driver, witness_id="irileth")
    claim = driver.claim("claim-jarl-death")
    irileth = driver.belief_of("irileth", claim.id)
    driver.retell(
        claim=claim, parent_variant=None, variant_id="variant-1",
        belief_id="belief-hulda-death", evidence_id="evidence-hulda-1",
        teller_id="irileth", teller_belief=irileth, hearer_id="hulda", gamets=0.0,
    )

    # Witness-after-rumor: hulda holds the rumor; she cannot ALSO record a
    # first-hand witnessing through witness() (follow-up rung candidate).
    with pytest.raises(ValueError, match="already holds a belief"):
        driver.witness(
            claim_id="claim-jarl-death",
            belief_id="belief-hulda-witness", evidence_id="evidence-hulda-witness",
            kind="npc_death", slots=dict(_CANONICAL_SLOTS),
            canonical_event_key=_DEATH_KEY, witness_id="hulda", gamets=1.0,
        )
    # Multi-slot witness disagreement has no Variant representation.
    with pytest.raises(ValueError, match="multi-slot"):
        driver.witness(
            claim_id="claim-jarl-death",
            belief_id="belief-belethor-death", evidence_id="evidence-belethor-death",
            kind="npc_death",
            slots={"perpetrator": "a thalmor justiciar", "cause": "an accident", "location": "dragonsreach"},
            canonical_event_key=_DEATH_KEY, witness_id="belethor", gamets=1.0,
        )
    # resolve() without an incumbent belief is a caller error -- an
    # uncontested hearing is retell().
    with pytest.raises(ValueError, match="no belief"):
        driver.claims.resolve(
            claim=claim, holder_id="belethor", teller_id="irileth",
            teller_belief=irileth, evidence_id="evidence-nowhere", gamets=1.0,
        )
    driver.close()


def test_t23_same_content_retell_is_a_rehearing():
    """Same-content re-tell to an informed hearer (conflict-2 disposition, 2026-08-23):
    a re-hearing -- nothing minted, the hearing recorded (rule 7's exposure and
    distinct-source counting stay alive), the existing records returned, and the
    scripted transmitted record references those same ids.
    """
    driver = _driver("scenario-tier2-resolution-rehearing")
    _witness_death(driver, witness_id="irileth")
    claim = driver.claim("claim-jarl-death")
    # A second, agreeing witness gives hulda a distinct second source.
    driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-proventus-death", evidence_id="evidence-proventus-death",
        kind="npc_death", slots=dict(_CANONICAL_SLOTS),
        canonical_event_key=_DEATH_KEY, witness_id="proventus", gamets=0.0,
    )
    _, hulda_belief, _ = driver.retell(
        claim=claim, parent_variant=None, variant_id="variant-1",
        belief_id="belief-hulda-death", evidence_id="evidence-hulda-1",
        teller_id="irileth", teller_belief=driver.belief_of("irileth", claim.id),
        hearer_id="hulda", gamets=0.0,
    )

    # Repetition from the same source: exposure grows, distinct sources don't.
    variant, belief, evidence = driver.retell(
        claim=claim, parent_variant=None, variant_id="variant-ignored-2",
        belief_id="belief-hulda-ignored", evidence_id="evidence-hulda-ignored",
        teller_id="irileth", teller_belief=driver.belief_of("irileth", claim.id),
        hearer_id="hulda", gamets=1.0,
    )
    # A distinct second source re-tells the same content.
    driver.retell(
        claim=claim, parent_variant=None, variant_id="variant-ignored-3",
        belief_id="belief-hulda-ignored-3", evidence_id="evidence-hulda-ignored-3",
        teller_id="proventus", teller_belief=driver.belief_of("proventus", claim.id),
        hearer_id="hulda", gamets=2.0,
    )
    driver.close()

    # Nothing minted: the store returns the EXISTING records, the proposed new
    # ids exist nowhere, and hulda still holds exactly one belief.
    assert variant.id == "variant-1"
    assert belief is driver.belief_of("hulda", claim.id)
    assert belief.id == hulda_belief.id
    assert evidence.belief_id == hulda_belief.id
    with pytest.raises(KeyError):
        driver.variant("variant-ignored-2")
    assert len(driver.beliefs_of("hulda")) == 1
    # The hearings were recorded: exposure 3, distinct sources 2 (rule 7).
    rumor = driver.claims.rumor_state("hulda", claim.id, "variant-1")
    assert (rumor.exposure_count, rumor.distinct_source_count) == (3, 2)
    # The scripted re-hearings' transmitted records reference the existing
    # variant and hearer-belief ids (schema §4:117's amended gloss).
    trace = [r["payload"] for r in FrameLogReader(driver.writer.run_dir).records("trace")]
    transmitted = [p for p in trace if p["record_type"] == "transmitted"]
    assert len(transmitted) == 3
    for payload in transmitted[1:]:
        assert payload["variant"]["variant_id"] == "variant-1"
        assert payload["hearer_belief_id"] == "belief-hulda-death"
    assert transmitted[2]["teller_id"] == "proventus"


def test_t23_encounter_driven_resolution_reconstructs_at_arbitrary_t():
    """The tick loop resolves conflicts on its own, and the reader replays them exactly -- keyframe boundary included."""
    ticks = 4
    driver = _driver(
        "scenario-tier2-resolution-encounter",
        schedule=tuple(
            ScheduleBlock(npc_id=npc, location_id="bannered_mare", start_tick=0, end_tick=ticks)
            for npc in ("hulda", "proventus")
        ),
        encounter_probability=1.0,
        keyframe_interval=2,  # a keyframe falls mid-run, before later supersessions
    )
    _witness_death(driver, witness_id="proventus")
    _retell_with_mutation(driver, teller_id="proventus", hearer_id="hulda", variant_id="variant-gossip", gamets=0.0)
    driver.run(1, ticks)
    driver.close()

    reader = FrameLogReader(driver.writer.run_dir)
    trace = [r["payload"] for r in reader.records("trace")]
    supersessions = [p for p in trace if p["record_type"] == "supersession"]
    # The two are co-present every tick and never agree: one contested
    # hearing per tick, each one a record. The driver's deterministic
    # direction has hulda (lexicographically smaller) telling proventus,
    # who as the eyewitness stands every time.
    assert len(supersessions) == ticks - 1
    for payload in supersessions:
        assert set(payload) == _SUPERSESSION_FIELDS
        assert payload["teller_id"] == "hulda"
        assert payload["holder_id"] == "proventus"
        assert payload["winner_variant_id"] is None
        assert payload["loser_variant_id"] == "variant-gossip"
        assert payload["resolution_rule"] == RESOLUTION_RULE

    # Arbitrary-T reconstruction, past a keyframe boundary, matches the
    # in-memory run exactly -- the replay re-executes resolve() from the
    # amended payload, it doesn't approximate it. Per tick: the eyewitness's
    # belief keeps the original telling and accumulates one appended
    # contested-hearing Evidence per supersession.
    for tick in range(1, ticks):
        rebuilt = reader.state_at(tick).claims.belief_of("proventus", "claim-jarl-death")
        assert rebuilt is not None
        assert rebuilt.variant_id is None
        assert len(reader.state_at(tick).claims.evidence_for(rebuilt.id)) == 1 + tick

    # The end-of-run live store and the final-tick reconstruction agree
    # field-for-field, dented confidence included.
    live_final = driver.belief_of("proventus", "claim-jarl-death")
    rebuilt_final = reader.state_at(ticks).claims.belief_of("proventus", "claim-jarl-death")
    assert rebuilt_final == live_final
    # And the dent is visibly compounding: one challenge per tick from
    # tick 1 to ticks-1 (run()'s end is exclusive), each decaying the
    # incumbent to that tick then multiplying by (1 - dent).
    challenges = ticks - 1
    assert live_final.confidence == pytest.approx(
        WITNESS_CONFIDENCE
        * 0.5 ** (challenges / CONFIDENCE_DECAY_HALF_LIFE)
        * (1 - CONTESTED_CLAIM_CONFIDENCE_DENT) ** challenges
    )
