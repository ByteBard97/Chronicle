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
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path
from typing import NamedTuple, Self

from chronicle.claims import (
    BeliefInstance,
    Claim,
    ClaimStore,
    EventKey,
    Evidence,
    Resolution,
    Variant,
)
from chronicle.events import (
    EscalationWarning,
    Event,
    EventLog,
    NPCDied,
    ScheduleRewrite,
)
from chronicle.framelog import (
    DEFAULT_KEYFRAME_INTERVAL,
    FrameLogWriter,
    event_payload,
    serialize_state,
)
from chronicle.propagate import conflicting_pair, teller_and_hearer
from chronicle.rng import MUTATION_SLOT, MUTATION_VALUE, TELL_DECISION, roll, roll_key
from chronicle.rules import (
    ACCUMULATION_THRESHOLD,
    CORROBORATION,
    ENCOUNTER_SAMPLING,
    MUTATION_POLICY,
    OBLIGATION_LIFECYCLE,
    PAIRWISE_ENCOUNTER_WEIGHTING,
    REPUTATION_ACCUMULATION,
    SCHEDULE_WRITE_BACK,
    SHARED_CLAIM_INVARIANT,
    TELL_DECISION_POLICY,
    TESTIMONY_TRANSFER,
    VARIANT_RESOLUTION,
    WITNESS_CREATES_BELIEF,
    RuleContext,
    RuleRegistry,
    RuleResult,
)
from chronicle.schedule import (
    ENCOUNTER_PROBABILITY,
    ScheduleBlock,
    effective_schedule_at,
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
    grudge_at,
    grudge_cooled,
    issue_obligation,
)

# Tier-2 retelling mutation gate (docs/scenario-ladder.md T2.2): the
# probability that an encounter-driven retelling mutates one slot of the
# story it carries. Same tunable-not-derived status as claims.py's decay
# constants and schedule.py's ENCOUNTER_PROBABILITY -- a placeholder until
# the math tier calibrates it against a scenario, not derived from any
# source report.
MUTATION_PROBABILITY = 0.2

# Tier-3 tell-decision gate (ladder T3.4, rule 15; design doc R10): the
# probability that an unmotivated, resolved teller tells at all. 1.0 is the
# migration-safe default -- with no privacy mappings and this threshold,
# behavior is identical to pre-gate runs (the 196-test battery is the
# regression proof); fixtures lower it per-run at construction time.
TELL_PROBABILITY = 1.0

# Tier-4a schedule write-back (ladder T4a.1, rule 17; design doc T6): how
# long a mourning overlay lasts, in ticks. Placeholder magnitude (3
# game-days) -- the ladder names "N days" without pinning N; the ordering
# requirement (observable, non-trivial duration) is load-bearing, not this
# number (design doc O2, coordinator-ruled 2026-08-23).
MOURNING_DURATION_TICKS = 72

# Tier-4b pairwise encounter weighting (ladder T4b.1, rule 18; design doc
# W1): the threshold an avoiding pair's roll compares against, replacing
# encounter_probability for that pair only. Zero is deliberate, not a
# placeholder magnitude to be tuned later -- `encountered = value <
# threshold` with threshold 0.0 is never true regardless of the roll's
# value (rng.roll's range is [0, 1)), which is what makes T4b.1's
# "encounters... cease" an exact guarantee rather than a probabilistic
# approximation (design doc O1, coordinator-ruled 2026-08-23).
AVOIDANCE_PROBABILITY = 0.0

# The decayed grudge severity (social.grudge_at) at or above which a pair
# avoids each other. Placeholder magnitude, strictly above
# forgiveness_threshold's default (0.2, social.py) so a grudge passes
# through three stages as it decays: avoiding, cooling (still live, no
# longer gating), forgiven (social.grudge_cooled) -- the ordering is
# load-bearing, not this number (design doc O2, coordinator-ruled
# 2026-08-23).
AVOIDANCE_GRUDGE_THRESHOLD = 0.5

# The warning claim's kind matches the escalation_warning event type
# (schema §3:95): the claim is the belief-layer shadow of that event, and
# the kind equality is what lets rule 11's latch find it (R5/R6).
ESCALATION_WARNING_CLAIM_KIND = "escalation_warning"


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
        tell_probability: float = TELL_PROBABILITY,
        claim_privacy: Mapping[str, str] | None = None,
        accumulation_thresholds: Mapping[str, tuple[str, int]] | None = None,
        reputation_relevance: Mapping[str, tuple[str, bool, str]] | None = None,
        mourning_triggers: Mapping[str, str] | None = None,
        mourning_location: str | None = None,
        mourning_duration_ticks: int = MOURNING_DURATION_TICKS,
        avoidance_probability: float = AVOIDANCE_PROBABILITY,
        avoidance_grudge_threshold: float = AVOIDANCE_GRUDGE_THRESHOLD,
        keyframe_interval: int = DEFAULT_KEYFRAME_INTERVAL,
        runs_dir: Path | None = None,
        event_log: EventLog | None = None,
        claims: ClaimStore | None = None,
        social: SocialStateStore | None = None,
        disabled_rules: Collection[str] = (),
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
        self.tell_probability = tell_probability
        # The tell-decision gate's privacy classification (rule 15 stage 1):
        # claim_kind -> the slot naming the claim's subject. Presence in the
        # mapping classifies the kind as private; the motive check itself
        # looks up the teller's kinship edge to that subject. Same
        # caller-supplies-context idiom as mutation_candidates above.
        self.claim_privacy = dict(claim_privacy) if claim_privacy is not None else {}
        # Rule 11's accumulating kinds (R4): claim_kind -> (victim_slot,
        # threshold). The victim slot names which slot holds the aggrieved
        # party's id; the threshold is per-kind, caller-supplied (never a
        # global). Same caller-supplies-context idiom as above.
        self.accumulation_thresholds = dict(accumulation_thresholds) if accumulation_thresholds is not None else {}
        # Rule 16's reputation-relevant kinds (R11): claim_kind ->
        # (subject_slot, positive, context). The subject slot names which
        # slot holds the observed party's id; the evidence kind comes from
        # the acquisition path, never from the mapping. Same
        # caller-supplies-context idiom as above; no mapping registered
        # means zero reputation rows -- behavior identical to pre-lane-26.
        self.reputation_relevance = dict(reputation_relevance) if reputation_relevance is not None else {}
        # Rule 17's mourning-eligible kinds (design doc T5, O1): claim_kind
        # -> the slot naming the deceased. Unlike rule 11/16's victim/
        # subject slots, no fixture names the deceased in an npc_death
        # claim's own slots today (only perpetrator/cause/location) -- a
        # scenario author must add e.g. slots={"deceased": npc_id, ...}
        # explicitly for a death claim to be mourning-eligible. Same
        # caller-supplies-context idiom as above; no mapping registered
        # means zero mourning overlays -- behavior identical to pre-lane-36.
        self.mourning_triggers = dict(mourning_triggers) if mourning_triggers is not None else {}
        # The overlay's destination (design doc T6, O5): one construction-
        # time location per run. None disables rule 17 regardless of
        # mourning_triggers -- there is nowhere to send the mourner.
        # Per-household destinations are a fixture-design question deferred
        # past T4a.1 (O5, coordinator-ruled).
        self.mourning_location = mourning_location
        self.mourning_duration_ticks = mourning_duration_ticks
        # Rule 18's avoidance seam (design doc W1): the threshold an
        # avoiding pair's roll compares against, and the decayed-severity
        # floor that makes a pair avoiding at all. Both driver-owned
        # tunables, not caller-supplied mappings -- every pair with a
        # qualifying grudge avoids the same way, there is no per-kind
        # variation the way claim_privacy/accumulation_thresholds have.
        self.avoidance_probability = avoidance_probability
        self.avoidance_grudge_threshold = avoidance_grudge_threshold
        self.save_uuid = save_uuid
        self.generation = generation
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
        # Rule 17's overlays (design doc T1): derived from schedule_rewrite
        # canonical events, same start-from-keyframe-safe pattern as
        # _deceased above -- a pre-populated event_log's rewrites are
        # already in effect, not re-triggered.
        self._schedule_overlays: list[ScheduleBlock] = [
            ScheduleBlock(
                npc_id=event.npc_id,
                location_id=event.location_id,
                start_tick=event.start_tick,
                end_tick=event.end_tick,
            )
            for event in self.event_log.lineage(save_uuid, generation)
            if isinstance(event, ScheduleRewrite)
        ]
        self.claims = claims if claims is not None else ClaimStore()
        self.social = social if social is not None else SocialStateStore()
        self.writer = FrameLogWriter(
            run_id=run_id,
            seed_id=seed_id,
            save_uuid=save_uuid,
            generation=generation,
            runs_dir=runs_dir,
        )
        # The Tier-3 rule registry (docs/scenario-ladder.md §8 consequence
        # b; design doc R1): per-run, construction-time toggled only.
        # Default all-on, so tiers 0-2 migrate as regression cases with no
        # behavior change (R12). Rules 11-19 are registered disabled stubs.
        self.rules = RuleRegistry(disabled=disabled_rules)
        # Claims the tick loop tries to propagate on encounters. Populated
        # by witness() -- every claim the driver sees formed is a story that
        # can travel. Tier 3's tell-decision policy will gate this further.
        self._propagating_claims: list[str] = []
        self._auto_ids = itertools.count(1)

    # -- rule evaluation (Tier 3, design doc R3) ------------------------------

    def _evaluate_rule(
        self,
        name: str,
        *,
        tick: int,
        inputs: Mapping[str, object],
        outcome: RuleResult | None = None,
    ) -> RuleResult | None:
        """Evaluate a registered rule and emit its rule_evaluated record (schema §4:122).

        The ruled contract: every evaluation of an enabled rule logs, fired
        or not, with the caller-assembled inputs (accumulator values and
        entity refs) attached -- a counter stuck at 3-of-4 is visible, not
        silent. A disabled rule emits nothing and returns None. Rules never
        query stores; the caller assembles everything the row carries.

        outcome is the call-site-determined result for RecordedRule
        wrappers; computing rules (tell-decision, the read-path rules)
        derive their own and are called with outcome=None.
        """
        if not self.rules.enabled(name):
            return None
        result = self.rules.get(name).evaluate(
            RuleContext(tick=tick, gamets=float(tick), inputs=inputs, outcome=outcome)
        )
        self.writer.write_trace(
            tick=tick,
            payload={
                "record_type": "rule_evaluated",
                "rule": name,
                "inputs": dict(inputs),
                "fired": result.fired,
                "result": dict(result.result) if result.result is not None else None,
            },
        )
        return result

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
        """Scripted first-hand observation; emits a belief_formed trace record (schema §4).

        claim_slots carries the slots AS THE WITNESS REPORTED THEM (kwargs),
        not the stored claim's: identical for an agreeing witness, but for a
        disagreeing second witness (ladder T0.4) it is what lets the reader
        re-execute witness()'s disagreement branch -- synthesized variant id
        and all -- and keep reconstruction exact without a schema change.
        """
        reported_slots = dict(kwargs["slots"])  # type: ignore[arg-type]
        # Rule 4 (shared-claim invariant) context, driver-scoped: whether
        # this witness attaches to a claim the driver has already seen
        # formed (claims.py enforces the invariant itself at the store --
        # R2 wraps, never refactors).
        pre_existing = kwargs["claim_id"] in self._propagating_claims
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
                "claim_slots": reported_slots,
                "canonical_event_key": {
                    "save_uuid": event_key.save_uuid,
                    "generation": event_key.generation,
                    "seq": event_key.seq,
                },
            },
        )
        tick = int(belief.first_learned)
        self._evaluate_rule(
            WITNESS_CREATES_BELIEF,
            tick=tick,
            inputs={"claim_id": claim.id, "witness_id": belief.holder_id, "claim_kind": claim.kind},
            outcome=RuleResult(fired=True, result={"belief_id": belief.id, "evidence_id": evidence.id}),
        )
        self._evaluate_rule(
            SHARED_CLAIM_INVARIANT,
            tick=tick,
            inputs={"claim_id": claim.id, "canonical_event_key": f"{event_key.save_uuid}/{event_key.generation}/{event_key.seq}"},
            outcome=RuleResult(fired=True, result={"claim_id": claim.id, "pre_existing": pre_existing}),
        )
        # Rule 11 evaluates exactly here, where a belief forms (R5).
        self._evaluate_accumulation(holder_id=belief.holder_id, claim=claim, tick=tick, gamets=belief.first_learned)
        # Rule 16: first-hand observation is "witnessed" reputation evidence (R11).
        self._apply_reputation(holder_id=belief.holder_id, claim=claim, kind="witnessed", tick=tick, gamets=belief.first_learned)
        # Rule 17: witnessing a mourning-eligible death is belief acquisition too.
        self._evaluate_mourning(holder_id=belief.holder_id, claim=claim, tick=tick, gamets=belief.first_learned)
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

        A scripted re-hearing (ladder T2.3 conflict-2 disposition: the hearer
        already holds the same content) mints nothing; the store returns the
        EXISTING records and this wrapper's transmitted record references
        those same ids. The one unruled corner -- re-hearing content the
        hearer holds as the claim's un-varianted original telling (variant
        None) -- has no variant to reference, so it raises rather than emit a
        record the schema can't shape.
        """
        teller_belief: BeliefInstance = kwargs["teller_belief"]  # type: ignore[assignment]
        # Rule 11's hook needs to know whether this retelling FORMS the
        # hearer's belief -- a re-hearing (the T2.3 conflict-2 carve-out)
        # mints nothing, so no accumulator can change.
        hearer_already_held = self.claims.belief_of(kwargs["hearer_id"], kwargs["claim"].id) is not None  # type: ignore[union-attr, arg-type]
        result = self.claims.retell(**kwargs)  # type: ignore[arg-type]
        if isinstance(result, Resolution):
            # The store routed a scripted retell into conflict resolution
            # (hearer holds differing content). The trace is the artifact --
            # a resolution without its supersession record breaks the log
            # discipline, so the caller must go through driver.resolve().
            raise TypeError(
                "scripted retell routed to conflict resolution (hearer holds differing "
                "content) -- call driver.resolve() instead, so the supersession trace "
                "record is emitted"
            )
        variant, belief, evidence = result
        if variant is None:
            raise ValueError(
                "a scripted re-hearing of the claim's un-varianted original telling has no "
                "variant id to reference in a transmitted record -- no ruled trace shape "
                "(surface as a finding if a scenario needs it)"
            )
        # Trace tick is the telling's own gamets (kwargs) -- NOT
        # variant.gamets, which for a re-hearing is the existing variant's
        # creation tick, not this hearing's.
        self.writer.write_trace(
            tick=int(kwargs["gamets"]),  # type: ignore[arg-type]
            payload={
                "record_type": "transmitted",
                "claim_id": variant.claim_id,
                "teller_id": teller_belief.holder_id,
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
        self._evaluate_rule(
            TESTIMONY_TRANSFER,
            tick=int(kwargs["gamets"]),  # type: ignore[arg-type]
            inputs={
                "claim_id": variant.claim_id,
                "teller_id": teller_belief.holder_id,
                "hearer_id": belief.holder_id,
            },
            outcome=RuleResult(
                fired=True,
                result={"variant_id": variant.id, "hearer_belief_id": belief.id, "evidence_id": evidence.id},
            ),
        )
        if not hearer_already_held:
            # Rule 11 evaluates exactly here, where a belief forms (R5).
            self._evaluate_accumulation(
                holder_id=belief.holder_id,
                claim=self.claims.claim(variant.claim_id),
                tick=int(kwargs["gamets"]),  # type: ignore[arg-type]
                gamets=float(kwargs["gamets"]),  # type: ignore[arg-type]
            )
            # Rule 16: a telling the hearer hadn't held is "reported"
            # reputation evidence (R11). A re-hearing mints nothing, so no
            # reputation row can come of it either.
            self._apply_reputation(
                holder_id=belief.holder_id,
                claim=self.claims.claim(variant.claim_id),
                kind="reported",
                tick=int(kwargs["gamets"]),  # type: ignore[arg-type]
                gamets=float(kwargs["gamets"]),  # type: ignore[arg-type]
            )
            # Rule 17: hearing of a mourning-eligible death for the first
            # time is belief acquisition too -- a re-hearing mints nothing.
            self._evaluate_mourning(
                holder_id=belief.holder_id,
                claim=self.claims.claim(variant.claim_id),
                tick=int(kwargs["gamets"]),  # type: ignore[arg-type]
                gamets=float(kwargs["gamets"]),  # type: ignore[arg-type]
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
        self._evaluate_rule(
            CORROBORATION,
            tick=int(evidence.gamets),
            inputs={"belief_id": belief_id, "source_belief_id": source_belief.id},
            outcome=RuleResult(
                fired=True,
                result={"confidence_before": confidence_before, "confidence_after": updated.confidence},
            ),
        )
        # Rule 16: independent corroborating testimony is "corroborated"
        # reputation evidence (R11).
        self._apply_reputation(
            holder_id=updated.holder_id,
            claim=self.claims.claim(updated.claim_id),
            kind="corroborated",
            tick=int(evidence.gamets),
            gamets=evidence.gamets,
        )
        # Rule 17: corroborating testimony is belief acquisition too (rule
        # 16's exact call-site pattern) -- in practice usually latch-blocked
        # (the holder was already informed to have something to corroborate
        # against), but a kinship edge formed after first learning is a real
        # case this catches.
        self._evaluate_mourning(
            holder_id=updated.holder_id,
            claim=self.claims.claim(updated.claim_id),
            tick=int(evidence.gamets),
            gamets=evidence.gamets,
        )
        return updated, evidence

    def resolve(self, **kwargs: object) -> Resolution:
        """Scripted conflicting-variant resolution (ladder T2.3); emits a supersession trace record (schema §4, as amended 2026-08-23).

        The Resolution's field names match the schema row exactly, so the
        payload is the record type plus the resolution spread verbatim --
        no location_id: unlike transmitted, the §4 supersession row carries
        none, and the payload matches the schema field-for-field.
        """
        gamets: float = kwargs["gamets"]  # type: ignore[assignment]
        resolution = self.claims.resolve(**kwargs)  # type: ignore[arg-type]
        self.writer.write_trace(
            tick=int(gamets),
            payload={"record_type": "supersession", **resolution._asdict()},
        )
        self._evaluate_rule(
            VARIANT_RESOLUTION,
            tick=int(gamets),
            inputs={
                "claim_id": resolution.claim_id,
                "holder_id": resolution.holder_id,
                "teller_id": resolution.teller_id,
            },
            outcome=RuleResult(
                fired=True,
                result={
                    "loser_variant_id": resolution.loser_variant_id,
                    "winner_variant_id": resolution.winner_variant_id,
                    "resolution_rule": resolution.resolution_rule,
                },
            ),
        )
        return resolution

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

    def violate_obligation(
        self,
        obligation_id: str,
        *,
        gamets: float,
        excuse: str | None = None,
        violation_evidentiary_strength: float | None = None,
        present_npc_ids: Collection[str] = (),
    ) -> Obligation:
        """Scripted obligation violation; emits obligation_resolved (schema §4), then rule 14's violation cascade.

        The cascade (lane 25, design doc R8) fires only when the caller
        supplies violation_evidentiary_strength -- the ruling's
        "caller-supplied" severity, from the obligation's
        sanctions/severity. Without it the wrapper is exactly the
        pre-lane-25 behavior (the resolution record alone), so existing
        scripted violations are untouched. With it, after the
        obligation_resolved write:

          - one grudge, issuer against debtor, grievance_type
            "obligation_violated" -- the issuer is the wronged party, so
            this is form_grudge's ruled O3 self-victim bypass (victim_id
            == holder_id, no synthetic self-edge);
          - one witnessed, negative reputation row per PRESENT observer:
            obligation.witnesses intersected with the caller-supplied
            co-located presence set (npcs_present_at), subject the
            debtor, context the obligation's action;

        all recorded under one rule-14 rule_evaluated row. Rule 14
        disabled at construction suspends the cascade entirely (a
        behavioral gate, the rule-11 idiom); the obligation_resolved
        write itself predates the registry and always happens.
        """
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
        if violation_evidentiary_strength is None or not self.rules.enabled(OBLIGATION_LIFECYCLE):
            return obligation
        n = next(self._auto_ids)
        grudge = self.form_grudge(
            id=f"grudge-violation-auto-{n}",
            holder_id=obligation.issuer_id,
            victim_id=obligation.issuer_id,  # O3: the issuer is the wronged party (harm-to-self)
            target_id=obligation.debtor_id,
            grievance_type="obligation_violated",
            # No belief exists on the violation path; the obligation record
            # is the grievance's source, so its id fills source_belief_id.
            source_belief_id=obligation.id,
            evidentiary_strength=violation_evidentiary_strength,
            relationship_to_victim=None,
            gamets=gamets,
        )
        # Witnesses intersected with caller-supplied presence, in the
        # obligation's witness order (deterministic, fixture-meaningful).
        observer_ids = [witness for witness in obligation.witnesses if witness in present_npc_ids]
        for observer_id in observer_ids:
            self.update_reputation(
                observer_id=observer_id,
                subject_id=obligation.debtor_id,
                context=obligation.action,
                kind="witnessed",
                positive=False,
                gamets=gamets,
            )
        self._evaluate_rule(
            OBLIGATION_LIFECYCLE,
            tick=int(gamets),
            inputs={
                "obligation_id": obligation.id,
                "issuer_id": obligation.issuer_id,
                "debtor_id": obligation.debtor_id,
                "evidentiary_strength": violation_evidentiary_strength,
                "present_observers": observer_ids,
            },
            outcome=RuleResult(
                fired=True,
                result={"grudge_id": grudge.id, "reputation_observer_ids": observer_ids},
            ),
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
        # Rule 17's overlay override happens here (design doc T1/T4): the
        # base schedule is never mutated, so this is the one place "who is
        # actually present" differs from "what the base schedule says."
        present = npcs_present_at(effective_schedule_at(self.schedule, self._schedule_overlays, tick), tick)
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
        # Rule 18's override happens here (design doc W1): a real toggle,
        # not instrumentation-only -- disabled means no grudge, however
        # severe, ever changes a threshold.
        grudge_severities = self._grudge_severities(tick) if self.rules.enabled(PAIRWISE_ENCOUNTER_WEIGHTING) else {}
        avoidance_thresholds = self._avoidance_thresholds(grudge_severities, tick) if grudge_severities else {}
        if self.rules.enabled(ENCOUNTER_SAMPLING):
            rolls = sample_encounters(
                present,
                seed_id=self.seed_id,
                tick=tick,
                encounter_probability=self.encounter_probability,
                pair_thresholds=avoidance_thresholds or None,
            )
        else:
            # Rule 6 toggled off (construction-time): the sweep does not
            # run -- no rolls, no encounter_rolled rows, no propagation.
            rolls = ()
        if rolls:
            # Rule 6's evaluation row: one per tick that had pairs to roll
            # (a tick with no co-present pairs is an empty world, not a
            # stuck counter). Per-pair outcomes stay in encounter_rolled.
            self._evaluate_rule(
                ENCOUNTER_SAMPLING,
                tick=tick,
                inputs={
                    "pairs_rolled": len(rolls),
                    "encountered": sum(1 for encounter_roll in rolls if encounter_roll.encountered),
                },
                outcome=RuleResult(fired=any(encounter_roll.encountered for encounter_roll in rolls)),
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
            if grudge_severities:
                self._evaluate_avoidance(
                    tick=tick, npc_a=encounter_roll.npc_a, npc_b=encounter_roll.npc_b, grudge_severities=grudge_severities
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
        for claim_ordinal, claim_id in enumerate(self._propagating_claims):
            resolved = teller_and_hearer(self.claims, claim_id=claim_id, npc_a=npc_a, npc_b=npc_b)
            if resolved is None:
                both = self.claims.belief_of(npc_a, claim_id) is not None and self.claims.belief_of(npc_b, claim_id) is not None
                if both:
                    # Ladder T2.3: both informed is a decline only while their
                    # content agrees. Differing variants are a contested hearing
                    # -- the store's resolution write path settles it and the
                    # supersession trace record (schema §4) is its evidence.
                    conflict = conflicting_pair(self.claims, claim_id=claim_id, npc_a=npc_a, npc_b=npc_b)
                    if conflict is not None:
                        teller_id, hearer_id = conflict
                        teller_belief = self.claims.belief_of(teller_id, claim_id)
                        assert teller_belief is not None  # conflicting_pair() resolved it a line ago
                        n = next(self._auto_ids)
                        self.resolve(
                            claim=self.claims.claim(claim_id),
                            holder_id=hearer_id,
                            teller_id=teller_id,
                            teller_belief=teller_belief,
                            evidence_id=f"evidence-auto-{n}",
                            gamets=float(tick),
                        )
                        continue
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
            claim = self.claims.claim(claim_id)
            # Rule 15, the tell-decision gate (ladder T3.4; design doc R9):
            # after teller_and_hearer resolves a real transmission pair,
            # before the mutation decision -- and never on T2.3's
            # resolution path (a contested hearing is not a telling). The
            # gate decides from caller-assembled context; declining emits
            # transmission_declined (schema §4:121) and ends the claim's
            # turn in this encounter.
            if self.rules.enabled(TELL_DECISION_POLICY):
                motive = self._tell_decline_motive(claim, teller_id)
                tell_roll_key = None
                tell_roll_value = None
                if motive is None:
                    # Stage 2 (R10): the keyed roll. draw is the claim's
                    # ordinal in this loop, keeping two claims told in the
                    # same tick/site/pair distinct (ADR-0009).
                    tell_roll_key = roll_key(
                        seed_id=self.seed_id, purpose=TELL_DECISION, tick=tick,
                        site=location_id, participants=(teller_id, hearer_id), draw=claim_ordinal,
                    )
                    tell_roll_value = roll(
                        seed_id=self.seed_id, purpose=TELL_DECISION, tick=tick,
                        site=location_id, participants=(teller_id, hearer_id), draw=claim_ordinal,
                    )
                decision = self._evaluate_rule(
                    TELL_DECISION_POLICY,
                    tick=tick,
                    inputs={
                        "claim_id": claim_id,
                        "teller_id": teller_id,
                        "hearer_id": hearer_id,
                        "location_id": location_id,
                        "motive": motive,
                        "roll_value": tell_roll_value,
                        "threshold": self.tell_probability,
                    },
                )
                if decision is not None and decision.fired:
                    self._write_transmission_declined(
                        tick=tick, claim_id=claim_id, teller_id=teller_id, hearer_id=hearer_id,
                        location_id=location_id,
                        roll_key=tell_roll_key if motive is None else None,
                    )
                    continue
            n = next(self._auto_ids)
            variant_id = f"variant-auto-{n}"
            # Tier-2 mutation policy (ladder T2.2): encounter-driven
            # retellings may mutate one slot, decided by keyed rolls; the
            # mutation_applied record (schema §4) is the roll evidence and
            # is emitted AFTER the rule_evaluated row (evaluation precedes
            # effect) and BEFORE the transmitted record (the effect) below.
            # Rule 7 toggled off skips the decision entirely: retellings
            # proceed unmutated and nothing is emitted.
            mutation = None
            if self.rules.enabled(MUTATION_POLICY):
                mutation = self._decide_mutation(
                    tick=tick, claim=claim, parent_variant=parent_variant,
                    teller_id=teller_id, hearer_id=hearer_id,
                )
                self._evaluate_rule(
                    MUTATION_POLICY,
                    tick=tick,
                    inputs={"claim_id": claim_id, "teller_id": teller_id, "hearer_id": hearer_id},
                    outcome=RuleResult(
                        fired=mutation is not None,
                        result=(
                            {"slot": mutation.slot, "old_value": mutation.old_value, "new_value": mutation.new_value, "variant_id": variant_id}
                            if mutation is not None
                            else None
                        ),
                    ),
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

    def _tell_decline_motive(self, claim: Claim, teller_id: str) -> str | None:
        """Rule 15 stage 1 (R10): the deterministic motive check, caller-assembled.

        Reads the construction-time claim_privacy mapping (claim kind -> the
        slot naming its subject); a private claim whose subject the teller
        is kin to is kept, always. The social lookup happens HERE, in the
        driver -- never inside a claims operation (the T2.3 lesson). Returns
        the sub-reason string for the rule_evaluated inputs (O5), or None.
        """
        subject_slot = self.claim_privacy.get(claim.kind)
        if subject_slot is None:
            return None
        subject = claim.slots.get(subject_slot)
        if subject is None:
            return None
        if self.social.relationship(teller_id, subject, "kinship") is not None:
            return "kin-motive"
        return None

    def _write_transmission_declined(
        self,
        *,
        tick: int,
        claim_id: str,
        teller_id: str,
        hearer_id: str,
        location_id: str,
        roll_key: dict[str, object] | None,
    ) -> None:
        """The gate's decline record (schema §4:121, field-for-field).

        roll_key is the stage-2 roll's key, or None for a stage-1
        deterministic (motive) decline -- the schema's null-roll_key case.
        """
        self.writer.write_trace(
            tick=tick,
            payload={
                "record_type": "transmission_declined",
                "claim_id": claim_id,
                "teller_id": teller_id,
                "hearer_id": hearer_id,
                "location_id": location_id,
                "rule": TELL_DECISION_POLICY,
                "roll_key": roll_key,
            },
        )

    # -- rule 11: accumulation-threshold escalation (ladder T3.1; design R4-R6) --

    def _escalation_latched(self, holder_id: str, grievance_kind: str) -> bool:
        """The R5 latch, store-derived: the holder already holds a belief on an
        escalation-warning claim for this grievance kind.

        Store state IS log-derived (beliefs reconstruct from the trace at any
        T), so a start-from-keyframe driver can't double-fire -- reading the
        threshold_crossed trace record directly would miss unflushed
        same-phase records and doesn't carry into a from-keyframe run.
        """
        for belief in self.claims.beliefs_of(holder_id):
            claim = self.claims.claim(belief.claim_id)
            if claim.kind == ESCALATION_WARNING_CLAIM_KIND and claim.slots.get("grievance_kind") == grievance_kind:
                return True
        return False

    def _evaluate_accumulation(self, *, holder_id: str, claim: Claim, tick: int, gamets: float) -> None:
        """Rule 11's evaluation hook: runs exactly where a matching belief forms (R5), never per-tick.

        No-op unless the claim's kind is registered in the
        construction-time accumulation_thresholds mapping. The accumulator
        is a pure ClaimStore read (R4); the rule object decides; on firing
        the driver runs the R6 cascade: the escalation_warning EVENT enters
        the log first, the warning claim is witnessed off its canonical key
        (the holder witnesses their own escalation -- no orphan beliefs, no
        broadcast), and threshold_crossed (schema §4:123) is the artifact.
        """
        spec = self.accumulation_thresholds.get(claim.kind)
        if spec is None or not self.rules.enabled(ACCUMULATION_THRESHOLD):
            return
        victim_slot, threshold = spec
        # R4's derived accumulator: the holder's beliefs whose claim kind
        # matches and whose victim slot names the holder.
        contributing = [
            belief
            for belief in self.claims.beliefs_of(holder_id)
            if (belief_claim := self.claims.claim(belief.claim_id)).kind == claim.kind
            and belief_claim.slots.get(victim_slot) == holder_id
        ]
        count = len(contributing)
        latched = self._escalation_latched(holder_id, claim.kind)
        result = self._evaluate_rule(
            ACCUMULATION_THRESHOLD,
            tick=tick,
            inputs={
                "holder_id": holder_id,
                "grievance_kind": claim.kind,
                "count": count,
                "threshold": threshold,
                "latched": latched,
                "belief_ids": [belief.id for belief in contributing],
            },
        )
        if result is None or not result.fired:
            return
        # The R6 cascade. The event is engine-internal (origin None, schema
        # §3); its seq continues the branch's monotone sequence.
        seq = max((event.seq for event in self.event_log.lineage(self.save_uuid, self.generation)), default=0) + 1
        n = next(self._auto_ids)
        self.inject_event(
            EscalationWarning(
                tick=tick, save_uuid=self.save_uuid, generation=self.generation, seq=seq,
                gamets=gamets, wall_ts=0.0,
                holder_id=holder_id, grievance_kind=claim.kind, count=count, threshold=threshold,
            )
        )
        warning_claim_id = f"claim-escalation-auto-{n}"
        self.witness(
            claim_id=warning_claim_id,
            belief_id=f"belief-escalation-{holder_id}-auto-{n}",
            evidence_id=f"evidence-escalation-auto-{n}",
            kind=ESCALATION_WARNING_CLAIM_KIND,
            slots={"grievance_kind": claim.kind, "victim": holder_id},
            canonical_event_key=EventKey(self.save_uuid, self.generation, seq),
            witness_id=holder_id,
            gamets=gamets,
        )
        self.writer.write_trace(
            tick=tick,
            payload={
                "record_type": "threshold_crossed",
                "rule": ACCUMULATION_THRESHOLD,
                "accumulator": {
                    "holder_id": holder_id,
                    "grievance_kind": claim.kind,
                    "count": count,
                    "belief_ids": [belief.id for belief in contributing],
                },
                "threshold": threshold,
                "produced": {
                    "event_key": {"save_uuid": self.save_uuid, "generation": self.generation, "seq": seq},
                    "claim_id": warning_claim_id,
                },
            },
        )

    def _apply_reputation(self, *, holder_id: str, claim: Claim, kind: str, tick: int, gamets: float) -> None:
        """Rule 16's hook: runs exactly where a belief is acquired or corroborated (R11), never per-tick.

        No-op unless the claim's kind is registered in the construction-
        time reputation_relevance mapping. The evidence kind names the
        acquisition path (witnessed / reported / corroborated); subject,
        positive, and context come from the mapping applied to the claim's
        slots -- never a global flag, so T3.5's observer-locality tripwire
        (no acquisition, no update) holds structurally. The update itself
        goes through the ordinary update_reputation wrapper, so the
        reputation_updated record (schema §4:128) is emitted
        field-for-field; one rule_evaluated row pairs with each update.
        """
        spec = self.reputation_relevance.get(claim.kind)
        if spec is None or not self.rules.enabled(REPUTATION_ACCUMULATION):
            return
        subject_slot, positive, context = spec
        subject_id = claim.slots[subject_slot]
        reputation = self.update_reputation(
            observer_id=holder_id,
            subject_id=subject_id,
            context=context,
            kind=kind,
            positive=positive,
            gamets=gamets,
        )
        self._evaluate_rule(
            REPUTATION_ACCUMULATION,
            tick=tick,
            inputs={
                "claim_id": claim.id,
                "observer_id": holder_id,
                "subject_id": subject_id,
                "context": context,
                "kind": kind,
                "positive": positive,
            },
            outcome=RuleResult(
                fired=True,
                result={"alpha": reputation.alpha, "beta": reputation.beta, "uncertainty": reputation.uncertainty},
            ),
        )

    # -- rule 17: schedule write-back (ladder T4a.1; design doc T1-T7) --------

    def _mourning_already_triggered(self, npc_id: str, trigger_event_key: EventKey) -> bool:
        """The R5-pattern latch (design doc T6): log-derived, from the event log itself.

        A schedule_rewrite event already naming this exact (npc,
        trigger_event_key) pair means the overlay was already inserted --
        surviving reconstruction and a start-from-keyframe resume the same
        way _deceased/_schedule_overlays are derived at __init__, rather
        than an in-memory flag that a fresh Driver wouldn't know about.
        """
        return any(
            isinstance(event, ScheduleRewrite)
            and event.npc_id == npc_id
            and (event.trigger_save_uuid, event.trigger_generation, event.trigger_seq) == tuple(trigger_event_key)
            for event in self.event_log.lineage(self.save_uuid, self.generation)
        )

    def _evaluate_mourning(self, *, holder_id: str, claim: Claim, tick: int, gamets: float) -> None:
        """Rule 17's hook: runs at belief acquisition, the same call sites as rule 16 (R11's pattern), never a per-tick sweep.

        No-op unless the claim's kind is registered in the
        construction-time mourning_triggers mapping AND a mourning_location
        is configured. The kinship lookup happens HERE, in the driver --
        never inside a rule (the T2.3 lesson, same as rule 15's motive
        check, driver.py:1039-ish _tell_decline_motive). fired means the
        rule 17 gate decided to insert the overlay; the cascade (the
        schedule_rewrite event + the overlay itself) is the driver's,
        evidenced by that event, so the rule's own result stays None (the
        AccumulationThresholdRule precedent).
        """
        deceased_slot = self.mourning_triggers.get(claim.kind)
        if deceased_slot is None or self.mourning_location is None or not self.rules.enabled(SCHEDULE_WRITE_BACK):
            return
        deceased_id = claim.slots.get(deceased_slot)
        if deceased_id is None:
            return
        trigger_event_key = EventKey(*claim.canonical_event_key)
        kin = self.social.relationship(holder_id, deceased_id, "kinship") is not None
        already_mourning = kin and self._mourning_already_triggered(holder_id, trigger_event_key)
        result = self._evaluate_rule(
            SCHEDULE_WRITE_BACK,
            tick=tick,
            inputs={
                "npc_id": holder_id,
                "deceased_id": deceased_id,
                "kin": kin,
                "already_mourning": already_mourning,
            },
        )
        if result is None or not result.fired:
            return
        # The cascade: the event enters the log first (engine-internal,
        # origin None, schema §3 -- same convention as rule 11's
        # escalation_warning), then the overlay itself (design doc T1) --
        # both driver-side, evidenced by the event, never inside the rule.
        seq = max((event.seq for event in self.event_log.lineage(self.save_uuid, self.generation)), default=0) + 1
        start_tick = tick
        end_tick = tick + self.mourning_duration_ticks
        self.inject_event(
            ScheduleRewrite(
                tick=tick, save_uuid=self.save_uuid, generation=self.generation, seq=seq,
                gamets=gamets, wall_ts=0.0,
                npc_id=holder_id, location_id=self.mourning_location,
                start_tick=start_tick, end_tick=end_tick, cause="mourning",
                trigger_save_uuid=trigger_event_key.save_uuid,
                trigger_generation=trigger_event_key.generation,
                trigger_seq=trigger_event_key.seq,
                rule=SCHEDULE_WRITE_BACK,
            )
        )
        self._schedule_overlays.append(
            ScheduleBlock(
                npc_id=holder_id,
                location_id=self.mourning_location,
                start_tick=start_tick,
                end_tick=end_tick,
            )
        )

    # -- rule 18: pairwise encounter weighting / avoidance (ladder T4b.1; design doc W1-W5) --

    def _grudge_severities(self, tick: int) -> dict[frozenset[str], tuple[Grudge, float]]:
        """Every pair with a grudge between them (either direction), decayed severity as of `tick` (W1/W3).

        Not gated by threshold here -- whether it fires is the rule's
        job (doctrine 3: a cooling grudge's fired:false rows stay
        visible, not silent, the same way a stuck accumulator does).
        Mutual grudges (both sides holding one against the other)
        collapse to one key -- avoidance is about the pair, not the
        direction (O4).
        """
        severities: dict[frozenset[str], tuple[Grudge, float]] = {}
        for grudge in self.social.grudges():
            key = frozenset((grudge.holder_id, grudge.target_id))
            severities[key] = (grudge, grudge_at(grudge, float(tick)).severity)
        return severities

    def _avoidance_thresholds(self, grudge_severities: Mapping[frozenset[str], tuple[Grudge, float]], tick: int) -> dict[frozenset[str], float]:
        """The W1 override mapping: pairs whose decayed severity clears the avoidance floor and aren't cooled."""
        return {
            pair: self.avoidance_probability
            for pair, (grudge, severity) in grudge_severities.items()
            if severity >= self.avoidance_grudge_threshold and not grudge_cooled(grudge, float(tick))
        }

    def _evaluate_avoidance(self, *, tick: int, npc_a: str, npc_b: str, grudge_severities: Mapping[frozenset[str], tuple[Grudge, float]]) -> None:
        """Rule 18's per-roll evaluation, paired with that pair's encounter_rolled row (W2).

        No-op for a pair with no grudge between them at all -- bounds
        volume to (grudge count) x (co-present ticks), never a global
        sweep over every rolled pair.
        """
        pair = frozenset((npc_a, npc_b))
        entry = grudge_severities.get(pair)
        if entry is None:
            return
        grudge, severity = entry
        self._evaluate_rule(
            PAIRWISE_ENCOUNTER_WEIGHTING,
            tick=tick,
            inputs={
                "npc_a": npc_a,
                "npc_b": npc_b,
                "grudge_id": grudge.id,
                "severity": severity,
                "threshold": self.avoidance_grudge_threshold,
                "base_probability": self.encounter_probability,
                "effective_probability": self.avoidance_probability,
            },
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
