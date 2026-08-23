"""Scenario-ladder rung T2.2 (Mutate): seeded mutation of a spreading rumor.

Same shape as the Tier-2 spread run: a public death, a tavern full of
co-present NPCs, propagation driven purely by scheduled encounters through
the driver's tick loop -- nobody here picks who talks to whom. What T2.2
adds is the mutation machinery this rung exists to pin:

  - chronicle/driver.py's Tier-2 mutation policy (MUTATION_PROBABILITY
    gate, _decide_mutation): each encounter-driven retelling rolls
    mutation.slot (gate + slot pick, one draw) and mutation.value (pick
    from the caller-supplied candidate domain) per ADR-0009's keyed
    randomness, and evidences a fired mutation with a mutation_applied
    trace record (docs/frame-log-schema.md §4) before the transmitted
    record that carries the effect.
  - The candidate domains below are the caller-supplies-context seam:
    this scenario registers them; the engine stays domain-agnostic.

Asserts, per the rung: the EXACT mutated slot and value under the pinned
seed (golden regression values -- computed by running, then pinned; any
change to the roll keying, the policy, or the fixture that alters them is
a behavior change to explain, not a test to update blindly); the
predecessor chain intact (every mutated variant's parent_variant_id
resolves -- to a stored variant, or to the claim's original telling when
the teller was the witness); and no variant without a predecessor.
"""

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import NPCDied
from chronicle.framelog import FrameLogReader
from chronicle.schedule import ScheduleBlock

_SEED = "tier2-mutation"
_SAVE = "whiterun-save-1"
_TICKS = 240  # 10 game-days (ADR-0010: 1 tick = 1 game-hour)

# The witness plus seven tavern regulars, co-present for the whole run.
_CAST = ("irileth", "proventus", "hulda", "ysolda", "belethor", "nazeem", "carlotta", "mia")

# The candidate domains a mutation can substitute from, keyed
# (claim_kind, slot) -- the scenario-supplied context the engine's
# mutation.value roll picks uniformly from (current value excluded).
_MUTATION_CANDIDATES = {
    ("npc_death", "perpetrator"): ("the Thalmor", "a bandit chief", "the guard captain"),
    ("npc_death", "cause"): ("an accident", "a sudden illness"),
    ("npc_death", "location"): ("the market", "the plains district"),
}

# Golden regression values for seed "tier2-mutation" (computed by running
# this scenario, then pinned): the run's two mutation_applied records, in
# emission order, as (variant_id, slot, old_value, new_value, mutation_id,
# parent_variant_id).
_GOLDEN_MUTATIONS = [
    ("variant-auto-5", "perpetrator", "unknown", "a bandit chief", "mut-0d4901cb843a", "variant-auto-1"),
    ("variant-auto-6", "cause", "assassination", "a sudden illness", "mut-852ade7a1e84", None),
]


def test_tier2_mutation_rung():
    driver = Driver(
        run_id="scenario-tier2-mutation",
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=tuple(
            ScheduleBlock(npc_id=npc, location_id="bannered_mare", start_tick=0, end_tick=_TICKS)
            for npc in _CAST
        ),
        encounter_probability=1.0,
        mutation_candidates=_MUTATION_CANDIDATES,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_tier2_mutation"},
    )
    driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-irileth-death",
        evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=EventKey(_SAVE, 0, 1),
        witness_id="irileth",
        gamets=0.0,
    )
    driver.run(0, _TICKS)
    driver.close()

    reader = FrameLogReader(driver.writer.run_dir)
    trace = [r["payload"] for r in reader.records("trace")]
    mutations = [p for p in trace if p["record_type"] == "mutation_applied"]
    transmitted = [p for p in trace if p["record_type"] == "transmitted"]

    # Rung assertion 1: the exact mutated slot and value under the seed.
    # At least one mutation fired (the rung's premise), and the full set
    # matches the pinned goldens above.
    assert mutations, "T2.2 requires at least one mutation to fire under the pinned seed"
    actual = [
        (p["variant_id"], p["slot"], p["old_value"], p["new_value"], p["mutation_id"], p["parent_variant_id"])
        for p in mutations
    ]
    assert actual == _GOLDEN_MUTATIONS
    # The transmitted record carries the same mutation as its effect --
    # readers replay the effect via transmitted, not mutation_applied.
    by_variant = {p["variant"]["variant_id"]: p["variant"] for p in transmitted}
    for variant_id, slot, _old, new, _mid, _parent in _GOLDEN_MUTATIONS:
        assert by_variant[variant_id]["mutated_slot"] == slot
        assert by_variant[variant_id]["slots"][slot] == new

    # Rung assertion 2: the predecessor chain is intact. Every mutated
    # variant's parent_variant_id resolves -- to a stored variant, or (when
    # the teller was the witness holding the original telling) to None,
    # meaning the variant is rooted directly at the canonical claim.
    for _variant_id, _slot, _old, _new, _mid, parent_variant_id in _GOLDEN_MUTATIONS:
        if parent_variant_id is not None:
            parent = driver.variant(parent_variant_id)  # raises if unresolvable
            assert parent.claim_id == "claim-jarl-death"

    # Rung assertion 3: no variant without a predecessor -- across EVERY
    # variant the run produced, mutated or not. None roots at the claim's
    # original telling; anything else must resolve in the store.
    assert transmitted  # the story actually spread
    for p in transmitted:
        variant = p["variant"]
        if variant["parent_variant_id"] is not None:
            assert driver.variant(variant["parent_variant_id"]).id == variant["parent_variant_id"]
        # And every hearer's belief walks back through its evidence chain
        # to the witness's first-hand observation (ADR-0007).
        chain = driver.chain_for(p["hearer_belief_id"])
        assert chain[-1][1].evidence_type == "witnessed"
        assert chain[-1][0].holder_id == "irileth"
