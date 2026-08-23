"""The tick loop: advance tick, sample encounters, apply retellings, emit records.

Chronicle's stores (events/claims/social) are pure-function modules; this
driver is what runs them as a simulation. Each tick it groups NPCs by
location from their schedules (chronicle.schedule.npcs_present_at), rolls
keyed co-presence encounters (sample_encounters, ADR-0009), propagates any
claim exactly one party of an encountered pair holds (chronicle.propagate
-> ClaimStore.retell), and emits the whole thing to the frame log
(chronicle.framelog): encounter rolls (fired and rolled-against),
transmissions, and nothing-salient rows to trace.jsonl; canonical events
and keyframes (every K ticks, K default one game-day per ADR-0010) to
events.jsonl; one flush per tick batch (the liveness contract, schema §1).

The driver is deliberately shaped for the deferred fork milestone
(docs/dashboard-build-plan.md §3): it accepts pre-populated stores (a
start-from-keyframe state, exactly what framelog.FrameLogReader.state_at()
produces) and canonical events can be injected at any tick with their
provenance recorded (inject_event's origin field, schema §3). Building the
fork path itself is not M0 scope.

Decay and thresholds are not tick-loop work here: claims.py's decay is
closed-form and applied at read time (rule 19), and Tier-3 threshold
machinery doesn't exist yet -- "apply retellings/decay/thresholds" at M0
means retellings only.

Tier 2 (docs/scenario-ladder.md T2.2) adds the mutation policy: an
encounter-driven retelling may mutate one slot of the story it carries
(_decide_mutation below), gated and keyed by ADR-0009 rolls and evidenced
by a mutation_applied trace record (frame-log schema §4) emitted just
before the transmitted record. Scripted retellings via driver.retell()
are unchanged -- explicit mutations stay caller-controlled.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NamedTuple, Self

from chronicle.claims import (
    BeliefInstance,
    Claim,
    ClaimStore,
    EventKey,
    Evidence,
    Variant,
)
from chronicle.events import Event, EventLog, NPCDied
from chronicle.framelog import (
    DEFAULT_KEYFRAME_INTERVAL,
    FrameLogWriter,
    event_payload,
    serialize_state,
)
from chronicle.propagate import teller_and_hearer
from chronicle.rng import MUTATION_SLOT, MUTATION_VALUE, roll, roll_key
from chronicle.schedule import (
    ENCOUNTER_PROBABILITY,
    ScheduleBlock,
    npcs_present_at,
    sample_encounters,
)
from chronicle.social import (
    Grudge,
    Obligation,
    Relationship,
    Reputation,
    SocialStateStore,
    form_grudge,
    form_relationship,
    issue_obligation,
)

# Tier-2 retelling mutation gate (docs/scenario-ladder.md T2.2): the
# probability that an encounter-driven retelling mutates one slot of the
# story it carries. Same tunable-not-derived status as claims.py's decay
# constants and schedule.py's ENCOUNTER_PROBABILITY -- a placeholder until
# the math tier calibrates it against a scenario, not derived from any
# source report.
MUTATION_PROBABILITY = 0.2


class _MutationDecision(NamedTuple):
    """What _decide_mutation settled for one encounter-driven retelling (ladder T2.2)."""

    slot: str
    old_value: str | None
    new_value: str
    mutation_id: str
    slot_roll_key: dict[str, object]
    slot_roll_value: float


class Driver:
    """Runs the sim over the stores and writes the frame log as it goes.

    Owns one frame-log writer (one run); use as a context manager or call
    close() so the run's registry entry is marked complete. Stores may be
    supplied pre-populated (start-from-keyframe shaping -- pass exactly
    what FrameLogReader.state_at() returns); they default to empty.
    NPCDied canonical events -- injected live or already present in a
    pre-populated event_log -- mark NPCs deceased, and the tick loop
    excludes the deceased from encounter sampling (ladder T1.2: death
    stops new propagation only; the dead keep their existing beliefs).

    Tier-2 mutation seam (ladder T2.2): mutation_probability gates how
    often an encounter-driven retelling mutates, and mutation_candidates
    supplies the values a mutation can substitute -- a Mapping keyed
    (claim_kind, slot) naming the candidate domain per slot. This is the
    caller-supplies-context pattern propagate.py already uses: fixtures
    and scenarios supply domains; the engine stays domain-agnostic. With
    no candidates registered (the default), encounter-driven retellings
    never mutate and no mutation_applied record is ever emitted.
    """

    def __init__(
        self,
        *,
        run_id: str,
        seed_id: str,
        save_uuid: str,
        generation: int = 0,
        schedule: Sequence[ScheduleBlock] = (),
        encounter_probability: float = ENCOUNTER_PROBABILITY,
        mutation_probability: float = MUTATION_PROBABILITY,
        mutation_candidates: Mapping[tuple[str, str], Sequence[str]] | None = None,
        keyframe_interval: int = DEFAULT_KEYFRAME_INTERVAL,
        runs_dir: Path | None = None,
        event_log: EventLog | None = None,
        claims: ClaimStore | None = None,
        social: SocialStateStore | None = None,
    ) -> None:
        self.seed_id = seed_id
        self.schedule = tuple(schedule)
        self.encounter_probability = encounter_probability
        self.mutation_probability = mutation_probability
        self.mutation_candidates = (
            {key: tuple(values) for key, values in mutation_candidates.items()}
            if mutation_candidates is not None
            else {}
        )
        self.keyframe_interval = keyframe_interval
        self.event_log = event_log if event_log is not None else EventLog()
        # Deceased NPCs (ladder T1.2): derived from NPCDied canonical events
        # -- including any already present in a pre-populated event_log, so
        # the start-from-keyframe path cannot resurrect the dead. inject_event
        # adds to this set as further deaths arrive.
        self._deceased: set[str] = {
            event.npc_id
            for event in self.event_log.lineage(save_uuid, generation)
            if isinstance(event, NPCDied)
        }
        self.claims = claims if claims is not None else ClaimStore()
        self.social = social if social is not None else SocialStateStore()
        self.writer = FrameLogWriter(
            run_id=run_id,
            seed_id=seed_id,
            save_uuid=save_uuid,
            generation=generation,
            runs_dir=runs_dir,
        )
        # Claims the tick loop tries to propagate on encounters. Populated
        # by witness() -- every claim the driver sees formed is a story that
        # can travel. Tier 3's tell-decision policy will gate this further.
        self._propagating_claims: list[str] = []
        self._auto_ids = itertools.count(1)

    # -- canonical events ---------------------------------------------------

    def inject_event(self, event: Event, *, origin: Mapping[str, str] | None = None) -> bool:
        """Append a canonical event and log it (schema §3). Returns False on an idempotent no-op duplicate.

        origin records how the event entered ({"kind": "scenario" |
        "console" | "adapter", "detail": ...}); None means engine-internal.
        Injected events are ordinary canonical events in every other
        respect -- this is the seam the fork milestone's injection path
        builds on.
        """
        if not self.event_log.append(event):
            return False
        if isinstance(event, NPCDied):
            self._deceased.add(event.npc_id)
        self.writer.write_event(tick=event.tick, seq=event.seq, payload=event_payload(event, origin=origin))
        return True

    # -- derivations (scripted) ----------------------------------------------
    # Thin wrappers over the store methods that ALSO emit the corresponding
    # trace record, so a hand-scripted scenario produces the same log shape
    # as encounter-driven derivation. Trace tick is int(gamets) -- ADR-0010
    # pins tick and gamets as the same clock, and M0 scenarios use integer
    # gamets.

    def witness(self, **kwargs: object) -> tuple[Claim, BeliefInstance, Evidence]:
        """Scripted first-hand observation; emits a belief_formed trace record (schema §4)."""
        claim, belief, evidence = self.claims.witness(**kwargs)  # type: ignore[arg-type]
        if claim.id not in self._propagating_claims:
            self._propagating_claims.append(claim.id)
        # canonical_event_key may arrive as a plain tuple from pre-ADR-0009
        # call sites; normalize for payload serialization.
        event_key = EventKey(*claim.canonical_event_key)
        self.writer.write_trace(
            tick=int(belief.first_learned),
            payload={
                "record_type": "belief_formed",
                "belief_id": belief.id,
                "claim_id": claim.id,
                "holder_id": belief.holder_id,
                "evidence_id": evidence.id,
                "claim_kind": claim.kind,
                "claim_slots": dict(claim.slots),
                "canonical_event_key": {
                    "save_uuid": event_key.save_uuid,
                    "generation": event_key.generation,
                    "seq": event_key.seq,
                },
            },
        )
        return claim, belief, evidence

    def retell(
        self,
        *,
        location_id: str | None = None,
        **kwargs: object,
    ) -> tuple[Variant, BeliefInstance, Evidence]:
        """Scripted retelling; emits a transmitted trace record (schema §4).

        location_id is trace-only context (claims.retell() has no use for
        it): the encounter's location when the tick loop drives the
        retelling, None for a hand-scripted one.
        """
        teller_belief: BeliefInstance = kwargs["teller_belief"]  # type: ignore[assignment]
        variant, belief, evidence = self.claims.retell(**kwargs)  # type: ignore[arg-type]
        self.writer.write_trace(
            tick=int(variant.gamets),
            payload={
                "record_type": "transmitted",
                "claim_id": variant.claim_id,
                "teller_id": evidence.source_id,
                "teller_belief_id": teller_belief.id,
                "hearer_id": belief.holder_id,
                "hearer_belief_id": belief.id,
                "evidence_id": evidence.id,
                "variant": {
                    "variant_id": variant.id,
                    "parent_variant_id": variant.parent_variant_id,
                    "slots": dict(variant.slots),
                    "mutated_slot": variant.mutated_slot,
                },
                "location_id": location_id,
            },
        )
        return variant, belief, evidence

    def corroborate(self, **kwargs: object) -> tuple[BeliefInstance, Evidence]:
        """Scripted corroboration (rule 7); emits a belief_corroborated trace record (schema §4)."""
        belief_id: str = kwargs["belief_id"]  # type: ignore[assignment]
        source_belief: BeliefInstance = kwargs["source_belief"]  # type: ignore[assignment]
        confidence_before = self.claims.chain_for(belief_id)[0][0].confidence
        updated, evidence = self.claims.corroborate(**kwargs)  # type: ignore[arg-type]
        self.writer.write_trace(
            tick=int(evidence.gamets),
            payload={
                "record_type": "belief_corroborated",
                "belief_id": belief_id,
                "source_belief_id": source_belief.id,
                "evidence_id": evidence.id,
                "confidence_before": confidence_before,
                "confidence_after": updated.confidence,
            },
        )
        return updated, evidence

    # -- derivations (scripted), layer 4: social mutations -------------------
    # The same wrapper contract as witness/retell/corroborate, for the
    # social store: thin store-mutation wrappers that also emit schema §4's
    # five social trace records, so layer-4 state reconstructs from the log
    # at arbitrary T, not just at keyframe granularity. Trace tick is
    # int(gamets), same clock discipline as the claims wrappers.

    def form_relationship(self, **kwargs: object) -> Relationship:
        """Scripted relationship formation; emits a relationship_formed trace record (schema §4)."""
        relationship = self.social.add_relationship(form_relationship(**kwargs))  # type: ignore[arg-type]
        self.writer.write_trace(
            tick=int(relationship.formed_at),
            payload={
                "record_type": "relationship_formed",
                "id": relationship.id,
                "from_id": relationship.from_id,
                "to_id": relationship.to_id,
                "basis": relationship.basis,
                "basis_id": relationship.basis_id,
                "strength": relationship.strength,
                "formed_at": relationship.formed_at,
            },
        )
        return relationship

    def form_grudge(self, **kwargs: object) -> Grudge:
        """Scripted grudge formation (rule 8's gate runs inside social.form_grudge); emits grudge_formed (schema §4).

        Takes the caller-looked-up relationship_to_victim exactly like
        social.form_grudge() does -- the lookup discipline is part of the
        rule, not something this wrapper can do for the caller.
        """
        grudge = self.social.add_grudge(form_grudge(**kwargs))  # type: ignore[arg-type]
        self.writer.write_trace(
            tick=int(grudge.last_rehearsed),
            payload={
                "record_type": "grudge_formed",
                "id": grudge.id,
                "holder_id": grudge.holder_id,
                "target_id": grudge.target_id,
                "source_belief_id": grudge.source_belief_id,
                "grievance_type": grudge.grievance_type,
                "severity": grudge.severity,
                "emotional_strength": grudge.emotional_strength,
                "evidentiary_strength": grudge.evidentiary_strength,
                "last_rehearsed": grudge.last_rehearsed,
                "forgiveness_threshold": grudge.forgiveness_threshold,
            },
        )
        return grudge

    def issue_obligation(self, **kwargs: object) -> Obligation:
        """Scripted obligation issuance; emits an obligation_issued trace record with the full Obligation fields (schema §4)."""
        obligation = self.social.add_obligation(issue_obligation(**kwargs))  # type: ignore[arg-type]
        self.writer.write_trace(
            tick=int(obligation.created_at),
            payload={
                "record_type": "obligation_issued",
                "id": obligation.id,
                "issuer_id": obligation.issuer_id,
                "debtor_id": obligation.debtor_id,
                "beneficiary_id": obligation.beneficiary_id,
                "action": obligation.action,
                "condition": obligation.condition,
                "deadline": obligation.deadline,
                "status": obligation.status,
                "witnesses": list(obligation.witnesses),
                "sanctions": obligation.sanctions,
                "excuse": obligation.excuse,
                "created_at": obligation.created_at,
                "fulfilled_at": obligation.fulfilled_at,
                "violated_at": obligation.violated_at,
            },
        )
        return obligation

    def fulfill_obligation(self, obligation_id: str, *, gamets: float) -> Obligation:
        """Scripted obligation fulfillment; emits an obligation_resolved trace record (schema §4)."""
        obligation = self.social.fulfill_obligation(obligation_id, gamets=gamets)
        self.writer.write_trace(
            tick=int(gamets),
            payload={
                "record_type": "obligation_resolved",
                "obligation_id": obligation.id,
                "status": "fulfilled",
                "gamets": gamets,
                "excuse": None,
            },
        )
        return obligation

    def violate_obligation(self, obligation_id: str, *, gamets: float, excuse: str | None = None) -> Obligation:
        """Scripted obligation violation; emits an obligation_resolved trace record (schema §4)."""
        obligation = self.social.violate_obligation(obligation_id, gamets=gamets, excuse=excuse)
        self.writer.write_trace(
            tick=int(gamets),
            payload={
                "record_type": "obligation_resolved",
                "obligation_id": obligation.id,
                "status": "violated",
                "gamets": gamets,
                "excuse": excuse,
            },
        )
        return obligation

    def update_reputation(self, **kwargs: object) -> Reputation:
        """Scripted reputation update (rule 10); emits a reputation_updated trace record -- inputs plus resulting values (schema §4)."""
        reputation = self.social.update_reputation(**kwargs)  # type: ignore[arg-type]
        self.writer.write_trace(
            tick=int(reputation.last_updated),
            payload={
                "record_type": "reputation_updated",
                "observer_id": reputation.observer_id,
                "subject_id": reputation.subject_id,
                "context": reputation.context,
                "kind": kwargs["kind"],
                "positive": kwargs["positive"],
                "alpha": reputation.alpha,
                "beta": reputation.beta,
                "direct_count": reputation.direct_count,
                "witness_count": reputation.witness_count,
                "certified_count": reputation.certified_count,
                "uncertainty": reputation.uncertainty,
                "last_updated": reputation.last_updated,
            },
        )
        return reputation

    # -- the tick loop ---------------------------------------------------------

    def run(self, start_tick: int, end_tick: int) -> None:
        """Run ticks [start_tick, end_tick): encounters, propagation, keyframes, one flush per tick."""
        for tick in range(start_tick, end_tick):
            self._run_tick(tick)
            if (tick + 1) % self.keyframe_interval == 0:
                self.writer.write_keyframe(
                    tick=tick,
                    state=serialize_state(self.claims, self.social, self.schedule, tick=tick),
                )
            # Writer order within a tick (schema §8): events, then trace,
            # then keyframe, one flush at the end of the batch.
            self.writer.flush()

    def _run_tick(self, tick: int) -> None:
        present = npcs_present_at(self.schedule, tick)
        if self._deceased:
            # The dead are not present to be met (ladder T1.2): drop them
            # before rolling. A location left with a lone survivor has no
            # pairs, so no roll -- and no encounter_rolled record -- ever
            # names the deceased.
            present = {
                location_id: tuple(npc for npc in npcs if npc not in self._deceased)
                for location_id, npcs in present.items()
            }
            present = {location_id: npcs for location_id, npcs in present.items() if len(npcs) >= 2}
        rolls = sample_encounters(
            present,
            seed_id=self.seed_id,
            tick=tick,
            encounter_probability=self.encounter_probability,
        )
        for encounter_roll in rolls:
            self.writer.write_trace(
                tick=tick,
                payload={
                    "record_type": "encounter_rolled",
                    "roll_key": dict(encounter_roll.roll_key),
                    "value": encounter_roll.value,
                    "threshold": encounter_roll.threshold,
                    "outcome": "encountered" if encounter_roll.encountered else "no_encounter",
                    "location_id": encounter_roll.location_id,
                    "npc_a": encounter_roll.npc_a,
                    "npc_b": encounter_roll.npc_b,
                    "encountered": encounter_roll.encountered,
                },
            )
            if not encounter_roll.encountered:
                continue
            self._propagate_on_encounter(
                tick=tick, location_id=encounter_roll.location_id, npc_a=encounter_roll.npc_a, npc_b=encounter_roll.npc_b
            )

    def _propagate_on_encounter(self, *, tick: int, location_id: str, npc_a: str, npc_b: str) -> None:
        if not self._propagating_claims:
            # An encounter with no story in play at all is still a record
            # (ui-doctrines D7: non-events are records).
            self._write_nothing_salient(tick=tick, location_id=location_id, npc_a=npc_a, npc_b=npc_b, claim_id=None, reason="neither-informed")
            return
        for claim_id in self._propagating_claims:
            resolved = teller_and_hearer(self.claims, claim_id=claim_id, npc_a=npc_a, npc_b=npc_b)
            if resolved is None:
                both = self.claims.belief_of(npc_a, claim_id) is not None and self.claims.belief_of(npc_b, claim_id) is not None
                self._write_nothing_salient(
                    tick=tick,
                    location_id=location_id,
                    npc_a=npc_a,
                    npc_b=npc_b,
                    claim_id=claim_id,
                    reason="both-informed" if both else "neither-informed",
                )
                continue
            teller_id, hearer_id = resolved
            teller_belief = self.claims.belief_of(teller_id, claim_id)
            assert teller_belief is not None  # teller_and_hearer() resolved it a line ago
            parent_variant = self.claims.variant(teller_belief.variant_id) if teller_belief.variant_id is not None else None
            n = next(self._auto_ids)
            variant_id = f"variant-auto-{n}"
            claim = self.claims.claim(claim_id)
            # Tier-2 mutation policy (ladder T2.2): encounter-driven
            # retellings may mutate one slot, decided by keyed rolls; the
            # mutation_applied record (schema §4) is the roll evidence and
            # is emitted BEFORE the transmitted record (the effect) below.
            mutation = self._decide_mutation(
                tick=tick, claim=claim, parent_variant=parent_variant,
                teller_id=teller_id, hearer_id=hearer_id,
            )
            if mutation is not None:
                self.writer.write_trace(
                    tick=tick,
                    payload={
                        "record_type": "mutation_applied",
                        "claim_id": claim_id,
                        "parent_variant_id": parent_variant.id if parent_variant is not None else None,
                        "variant_id": variant_id,
                        "slot": mutation.slot,
                        "old_value": mutation.old_value,
                        "new_value": mutation.new_value,
                        "mutation_id": mutation.mutation_id,
                        # The mutation.slot roll (schema §4's roll-bearing
                        # record shape: key plus value/threshold/outcome).
                        # The mutation.value roll's key differs only in
                        # purpose and is a pure function of it (ADR-0009),
                        # so no evidence is lost by embedding one key.
                        "roll_key": mutation.slot_roll_key,
                        "value": mutation.slot_roll_value,
                        "threshold": self.mutation_probability,
                        "outcome": "mutated",
                    },
                )
            self.retell(
                claim=claim,
                parent_variant=parent_variant,
                variant_id=variant_id,
                belief_id=f"belief-auto-{hearer_id}-{n}",
                evidence_id=f"evidence-auto-{n}",
                teller_id=teller_id,
                teller_belief=teller_belief,
                hearer_id=hearer_id,
                gamets=float(tick),
                location_id=location_id,
                mutate_slot=mutation.slot if mutation is not None else None,
                mutated_value=mutation.new_value if mutation is not None else None,
            )

    def _decide_mutation(
        self,
        *,
        tick: int,
        claim: Claim,
        parent_variant: Variant | None,
        teller_id: str,
        hearer_id: str,
    ) -> _MutationDecision | None:
        """The Tier-2 mutation policy for one encounter-driven retelling (ladder T2.2).

        Keyed rolls only (ADR-0009) -- a pure function of the run's seed
        and the retelling context, so replay is exact. Two rolls:

          - mutation.slot, draw=0: one roll both gates occurrence and picks
            the slot. value < mutation_probability gates the mutation on;
            conditioned on the gate, value / mutation_probability is still
            uniform on [0, 1), so scaling it by the slot count picks
            uniformly among the claim's slots. (Chosen over a separate
            gate draw and pick draw: one fewer roll site per retelling, and
            the record's roll_key then evidences occurrence and slot
            choice at once.)
          - mutation.value, draw=0: picks uniformly from the caller-
            supplied candidate domain for (claim.kind, slot), the current
            value excluded (claims.retell() rejects a no-op "mutation").

        Returns None -- no mutation, and no mutation_applied record -- when
        the gate fails, when no candidates are registered for the chosen
        (kind, slot), or when every registered candidate equals the current
        value. The schema's mutation_applied exists to record mutations
        that happened, so a declined mutation emits nothing.
        """
        slots = sorted(claim.slots)
        # ADR-0009's site for non-spatial rolls scopes to the claim id;
        # participants are the retelling's two parties.
        site = claim.id
        participants = (teller_id, hearer_id)
        gate = roll(
            seed_id=self.seed_id, purpose=MUTATION_SLOT, tick=tick,
            site=site, participants=participants, draw=0,
        )
        if gate >= self.mutation_probability:
            return None
        # gate / probability < 1 strictly; min() guards the float-rounding
        # edge where the division lands on exactly 1.0.
        slot = slots[min(int(gate / self.mutation_probability * len(slots)), len(slots) - 1)]
        base_slots = parent_variant.slots if parent_variant is not None else claim.slots
        old_value = base_slots[slot]
        candidates = [c for c in self.mutation_candidates.get((claim.kind, slot), ()) if c != old_value]
        if not candidates:
            return None
        pick = roll(
            seed_id=self.seed_id, purpose=MUTATION_VALUE, tick=tick,
            site=site, participants=participants, draw=0,
        )
        new_value = candidates[min(int(pick * len(candidates)), len(candidates) - 1)]
        # The seeded mutation id the variant tree labels edges with (schema
        # §4): a short hash of the value roll's key -- reproducible on
        # replay by construction, never a random uuid.
        value_key = roll_key(
            seed_id=self.seed_id, purpose=MUTATION_VALUE, tick=tick,
            site=site, participants=participants, draw=0,
        )
        mutation_id = "mut-" + hashlib.sha256(json.dumps(value_key, sort_keys=True).encode("utf-8")).hexdigest()[:12]
        return _MutationDecision(
            slot=slot,
            old_value=old_value,
            new_value=new_value,
            mutation_id=mutation_id,
            slot_roll_key=roll_key(
                seed_id=self.seed_id, purpose=MUTATION_SLOT, tick=tick,
                site=site, participants=participants, draw=0,
            ),
            slot_roll_value=gate,
        )

    def _write_nothing_salient(
        self,
        *,
        tick: int,
        location_id: str,
        npc_a: str,
        npc_b: str,
        claim_id: str | None,
        reason: str,
    ) -> None:
        self.writer.write_trace(
            tick=tick,
            payload={
                "record_type": "nothing_salient",
                "location_id": location_id,
                "npc_a": npc_a,
                "npc_b": npc_b,
                "claim_id": claim_id,
                "reason": reason,
            },
        )

    # -- store queries (read-through delegates) --------------------------------
    # The driver is the facade a scenario (or the M1 agent-debug CLI) queries;
    # these delegate to the claim store unchanged.

    def beliefs_of(self, holder_id: str) -> tuple[BeliefInstance, ...]:
        return self.claims.beliefs_of(holder_id)

    def belief_of(self, holder_id: str, claim_id: str) -> BeliefInstance | None:
        return self.claims.belief_of(holder_id, claim_id)

    def chain_for(self, belief_id: str) -> tuple[tuple[BeliefInstance, Evidence], ...]:
        return self.claims.chain_for(belief_id)

    def claim(self, claim_id: str) -> Claim:
        return self.claims.claim(claim_id)

    def variant(self, variant_id: str) -> Variant:
        return self.claims.variant(variant_id)

    # -- lifecycle ---------------------------------------------------------------

    def close(self) -> None:
        self.writer.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
