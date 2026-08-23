"""The claim/variant/belief store -- layers 2-3 of the data-ownership model.

docs/decisions/0006-data-ownership-layers.md defines five ownership
layers over the canonical event log (chronicle/events.py, layer 1).
This module implements layers 2 and 3:

  - layer 2, claim/variant store: a Claim is a typed, structured fact
    derived from exactly one canonical event. Claims never mutate once
    created -- a retelling that changes the story produces a new Variant
    linked to its predecessor, never an edit in place.
  - layer 3, subjective belief store: a BeliefInstance records what one
    NPC believes -- which claim, which variant (if any retelling has
    reached them), confidence, and the verbatim/gist split fuzzy-trace
    theory uses to model memory decay (docs/architecture.md).

Every BeliefInstance is required to resolve to an Evidence record naming
its source and, transitively through the claim/variant chain, back to
the canonical event that grounded it -- this is what makes ADR-0007's
"since when, from what evidence, through whom" query answerable from the
schema rather than bolted on after the fact. See docs/v0.1-spec.md rules
1, 3, 4, 6, 7, 13, and 19 for the scenarios this module exists to satisfy.

Claims are keyed to their originating event via (save_uuid, generation,
seq) -- the same idempotency key EventLog.append() already establishes
-- rather than a separate event id, since Event carries no id of its own.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import NamedTuple


class EventKey(NamedTuple):
    """Identifies one canonical Event: its EventLog idempotency key."""

    save_uuid: str
    generation: int
    seq: int

# Retelling decay, per docs/decisions/open-questions.md's "treat as a tunable
# to be set empirically" note -- placeholders until the math tier calibrates
# them against a scenario, not derived from any source report.
RETELL_CONFIDENCE_DECAY = 0.8
RETELL_VERBATIM_DECAY = 0.7
RETELL_GIST_DECAY = 0.95
WITNESS_CONFIDENCE = 0.95

# Time-decay half-lives, in gamets units (rule 6). docs/decisions/0010-tick-
# quantum.md pins the unit: 1 gamets = 1 tick = 1 game-hour, 24 gamets = 1
# game-day. Verbatim strength decays faster than gist strength -- fuzzy-trace
# theory's central claim, per docs/architecture.md's bounded-memory item --
# so a rehearsed-but-fading memory keeps its gist ("something bad happened to
# the Jarl") long after the exact wording is gone. Still placeholder
# magnitudes, same tunable-not-derived status as the retell constants above
# (0010 rebaselines their units, not their epistemic status).
CONFIDENCE_DECAY_HALF_LIFE = 168.0  # ticks: ~7 game-days (24*7), rule 6.
VERBATIM_DECAY_HALF_LIFE = 72.0  # ticks: ~3 game-days (24*3), fastest of the three, rule 5.
GIST_DECAY_HALF_LIFE = 1440.0  # ticks: ~60 game-days (24*60), slowest, rule 5's central claim.

# Rumor stage machine thresholds (rule 16), same tunable-not-derived status
# as the decay half-lives above. RUMOR_DORMANT_AFTER is gamets elapsed since
# the holder last heard or told the story with no activity in between;
# RUMOR_FORGOTTEN_GIST_THRESHOLD is the gist_strength floor below which the
# story is functionally gone even though the record itself is never deleted
# (event-sourcing discipline: state is derived, not destroyed).
# ~45 quiet game-days (24*45), per docs/decisions/0010-tick-quantum.md: sits
# between the scenario-ladder's T0.2 anchor (30 quiet days must read as "not
# dormant yet") and its T2.5 anchor (90 quiet days must have reached dormant
# well before the window closes).
RUMOR_DORMANT_AFTER = 1080.0  # ticks: ~45 quiet game-days (24*45), rule 16.
RUMOR_FORGOTTEN_GIST_THRESHOLD = 0.05  # dimensionless gist-strength floor, rule 16; not a time constant.


def _decay(value: float, elapsed: float, half_life: float) -> float:
    return value * 0.5 ** (elapsed / half_life)


def _frozen_slots(slots: Mapping[str, str | None]) -> Mapping[str, str | None]:
    return MappingProxyType(dict(slots))


def _require_unit_interval(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value!r}")


@dataclass(frozen=True)
class Claim:
    """A typed fact derived from one canonical event. Immutable once created."""

    id: str
    kind: str
    slots: Mapping[str, str | None]
    canonical_event_key: EventKey
    truth_status: str = "unconfirmed"

    def __post_init__(self) -> None:
        object.__setattr__(self, "slots", _frozen_slots(self.slots))


@dataclass(frozen=True)
class Variant:
    """A retelling of a Claim with exactly one slot mutated from its predecessor."""

    id: str
    claim_id: str
    parent_variant_id: str | None
    slots: Mapping[str, str | None]
    mutated_slot: str | None
    gamets: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "slots", _frozen_slots(self.slots))


@dataclass(frozen=True)
class Evidence:
    """Names the source and grounds of one BeliefInstance.

    predecessor_belief_id links a "reported" Evidence back to the
    teller's own BeliefInstance -- None for "witnessed" Evidence, which
    grounds directly in the canonical event via its Claim instead. This
    is what lets ClaimStore.chain_for() walk a belief back through every
    intermediate teller to the original witness (ADR-0007).
    """

    id: str
    belief_id: str
    evidence_type: str  # "witnessed" | "reported"
    source_id: str
    predecessor_belief_id: str | None
    gamets: float
    strength: float


@dataclass(frozen=True)
class BeliefInstance:
    """What one NPC believes: which claim, which variant, and how strongly."""

    id: str
    holder_id: str
    claim_id: str
    variant_id: str | None
    confidence: float
    verbatim_strength: float
    gist_strength: float
    first_learned: float
    last_rehearsed: float


@dataclass(frozen=True)
class RumorState:
    """One NPC's propagation-stage tracking for one claim/variant (rule 16).

    stage is only ever stored as "heard" or "repeated" -- "unheard" is the
    absence of a RumorState (nobody constructs one until the NPC has heard
    something), and "dormant"/"forgotten" are never written here. They are
    time/decay-derived at query time by stage_at(), the same lazy-derivation
    discipline decay() already uses for confidence (rule 19): a story going
    quiet doesn't require a tick loop to notice, and a later retelling can
    reactivate a "dormant" rumor without this record needing to have
    predicted that in advance.
    """

    npc_id: str
    claim_id: str
    variant_id: str | None
    stage: str  # "heard" | "repeated"
    first_heard: float
    last_heard: float
    last_told: float | None
    exposure_count: int
    distinct_source_count: int


def hear(
    *,
    npc_id: str,
    claim_id: str,
    variant_id: str | None,
    gamets: float,
) -> RumorState:
    """First exposure: an NPC has heard (or witnessed) a claim/variant. Stage starts at "heard"."""
    return RumorState(
        npc_id=npc_id,
        claim_id=claim_id,
        variant_id=variant_id,
        stage="heard",
        first_heard=gamets,
        last_heard=gamets,
        last_told=None,
        exposure_count=1,
        distinct_source_count=1,
    )


def hear_again(existing: RumorState, *, is_new_source: bool, gamets: float) -> RumorState:
    """A further exposure to the same claim/variant -- rule 7's spirit applied to exposure counting.

    is_new_source must come from the caller checking whether this source
    already contributed to this NPC's exposure (ClaimStore tracks that),
    the same explicit-lookup discipline claims.retell()/form_grudge() use
    elsewhere in this codebase -- repetition from the same source doesn't
    grow distinct_source_count, only exposure_count.
    """
    return replace(
        existing,
        last_heard=gamets,
        exposure_count=existing.exposure_count + 1,
        distinct_source_count=existing.distinct_source_count + (1 if is_new_source else 0),
    )


def tell(existing: RumorState, *, gamets: float) -> RumorState:
    """The NPC has retold this claim/variant to someone else -- stage advances to "repeated"."""
    return replace(existing, stage="repeated", last_told=gamets)


def stage_at(rumor: RumorState, belief: BeliefInstance, at_gamets: float) -> str:
    """The rumor's stage as of at_gamets, deriving "dormant"/"forgotten" lazily (rule 19).

    belief must be the BeliefInstance this RumorState tracks propagation
    for -- "forgotten" is keyed off the belief's decayed gist_strength
    (fuzzy-trace theory's claim that gist outlives verbatim detail, so gist
    going below threshold is a stronger "truly gone" signal than confidence
    alone) rather than a separate, independently-drifting clock.
    """
    decayed = decay(belief, at_gamets)
    if decayed.gist_strength < RUMOR_FORGOTTEN_GIST_THRESHOLD:
        return "forgotten"
    last_activity = rumor.last_told if rumor.last_told is not None else rumor.last_heard
    if at_gamets - last_activity > RUMOR_DORMANT_AFTER:
        return "dormant"
    return rumor.stage


def witness(
    *,
    claim_id: str,
    belief_id: str,
    evidence_id: str,
    kind: str,
    slots: dict[str, str | None],
    canonical_event_key: EventKey,
    witness_id: str,
    gamets: float,
) -> tuple[Claim, BeliefInstance, Evidence]:
    """First-hand observation: a Claim, a high-confidence BeliefInstance, and its witnessed Evidence."""
    claim = Claim(id=claim_id, kind=kind, slots=slots, canonical_event_key=canonical_event_key)
    belief = BeliefInstance(
        id=belief_id,
        holder_id=witness_id,
        claim_id=claim.id,
        variant_id=None,
        confidence=WITNESS_CONFIDENCE,
        verbatim_strength=1.0,
        gist_strength=1.0,
        first_learned=gamets,
        last_rehearsed=gamets,
    )
    evidence = Evidence(
        id=evidence_id,
        belief_id=belief.id,
        evidence_type="witnessed",
        source_id=witness_id,
        predecessor_belief_id=None,
        gamets=gamets,
        strength=1.0,
    )
    return claim, belief, evidence


def retell(
    *,
    claim: Claim,
    parent_variant: Variant | None,
    variant_id: str,
    belief_id: str,
    evidence_id: str,
    teller_id: str,
    teller_belief: BeliefInstance,
    hearer_id: str,
    gamets: float,
    mutate_slot: str | None = None,
    mutated_value: str | None = None,
) -> tuple[Variant, BeliefInstance, Evidence]:
    """A retelling: at most one slot mutates (rule 4), confidence decays from the teller's.

    Passing mutate_slot=None carries the story on unmutated -- the
    Variant record still exists so the hearer's belief links to a
    specific retelling, distinct from a claim's original telling.
    """
    _require_unit_interval("teller_belief.confidence", teller_belief.confidence)
    _require_unit_interval("teller_belief.verbatim_strength", teller_belief.verbatim_strength)
    _require_unit_interval("teller_belief.gist_strength", teller_belief.gist_strength)

    expected_variant_id = parent_variant.id if parent_variant is not None else None
    if teller_belief.claim_id != claim.id or teller_belief.variant_id != expected_variant_id:
        raise ValueError(
            "teller_belief does not hold the given claim/variant -- "
            "retelling would silently break the evidence chain"
        )
    if gamets < teller_belief.last_rehearsed:
        raise ValueError("a retelling cannot precede the teller's last rehearsal of it")

    base_slots = parent_variant.slots if parent_variant is not None else claim.slots
    slots = dict(base_slots)
    if mutate_slot is not None:
        if mutate_slot not in slots:
            raise ValueError(f"{mutate_slot!r} is not a slot on claim kind {claim.kind!r}")
        if slots[mutate_slot] == mutated_value:
            raise ValueError("mutated_value is identical to the current slot value -- not a mutation")
        slots[mutate_slot] = mutated_value

    variant = Variant(
        id=variant_id,
        claim_id=claim.id,
        parent_variant_id=parent_variant.id if parent_variant is not None else None,
        slots=slots,
        mutated_slot=mutate_slot,
        gamets=gamets,
    )
    belief = BeliefInstance(
        id=belief_id,
        holder_id=hearer_id,
        claim_id=claim.id,
        variant_id=variant.id,
        confidence=teller_belief.confidence * RETELL_CONFIDENCE_DECAY,
        verbatim_strength=teller_belief.verbatim_strength * RETELL_VERBATIM_DECAY,
        gist_strength=teller_belief.gist_strength * RETELL_GIST_DECAY,
        first_learned=gamets,
        last_rehearsed=gamets,
    )
    evidence = Evidence(
        id=evidence_id,
        belief_id=belief.id,
        evidence_type="reported",
        source_id=teller_id,
        predecessor_belief_id=teller_belief.id,
        gamets=gamets,
        # Deliberately the teller's pre-decay confidence, not the hearer's post-decay
        # belief.confidence -- this is the strength of the testimony as given, which
        # is what an inspector re-judging the chain needs, not a duplicate of the effect.
        strength=teller_belief.confidence,
    )
    return variant, belief, evidence


def decay(belief: BeliefInstance, at_gamets: float) -> BeliefInstance:
    """Fuzzy-trace decay (rule 6): erode confidence/verbatim/gist by elapsed time.

    A read-time computation, not a store mutation (rule 19: derivation is
    lazy, not eagerly maintained every tick) -- the stored BeliefInstance
    keeps recording its strength as of last_rehearsed; callers needing
    "how strong is this belief right now" call decay() at query time
    instead of a tick loop writing decayed values back.
    """
    elapsed = at_gamets - belief.last_rehearsed
    if elapsed <= 0:
        return belief
    return replace(
        belief,
        confidence=_decay(belief.confidence, elapsed, CONFIDENCE_DECAY_HALF_LIFE),
        verbatim_strength=_decay(belief.verbatim_strength, elapsed, VERBATIM_DECAY_HALF_LIFE),
        gist_strength=_decay(belief.gist_strength, elapsed, GIST_DECAY_HALF_LIFE),
    )


class ClaimStore:
    """The queryable claim/variant/belief store ADR-0006 names -- materialized.

    witness()/retell() above are pure constructors; this indexes their
    output so a consumer (a scenario assertion, the dashboard) can ask
    "what does NPC X believe" and "walk this belief's evidence chain"
    without holding onto every intermediate return value by hand.
    """

    def __init__(self) -> None:
        self._claims: dict[str, Claim] = {}
        self._claim_id_by_event: dict[EventKey, str] = {}
        self._variants: dict[str, Variant] = {}
        self._beliefs: dict[str, BeliefInstance] = {}
        # One belief can accumulate multiple Evidence records (corroboration,
        # rule 7) -- index [0] is always the belief's original grounding
        # evidence, which is what chain_for() walks; later entries are
        # corroborating testimony that raises confidence without displacing
        # the original provenance link.
        self._evidence_by_belief: dict[str, list[Evidence]] = {}
        # Rumor stage machine (rule 16), keyed the same way as ADR-0006's
        # RumorState.claim_variant_id: one entry per (holder, claim, variant)
        # a given NPC has heard. _rumor_sources tracks which source_ids have
        # already contributed to that NPC's exposure count, mirroring
        # corroborate()'s already_counted set above for the same
        # distinct-source-not-repetition reasoning (rule 7's spirit).
        self._rumors: dict[tuple[str, str, str | None], RumorState] = {}
        self._rumor_sources: dict[tuple[str, str, str | None], set[str]] = {}

    def _record_hearing(
        self, *, npc_id: str, claim_id: str, variant_id: str | None, source_id: str, gamets: float
    ) -> RumorState:
        key = (npc_id, claim_id, variant_id)
        sources = self._rumor_sources.setdefault(key, set())
        is_new_source = source_id not in sources
        sources.add(source_id)

        existing = self._rumors.get(key)
        state = (
            hear(npc_id=npc_id, claim_id=claim_id, variant_id=variant_id, gamets=gamets)
            if existing is None
            else hear_again(existing, is_new_source=is_new_source, gamets=gamets)
        )
        self._rumors[key] = state
        return state

    def _record_telling(self, *, npc_id: str, claim_id: str, variant_id: str | None, gamets: float) -> RumorState:
        key = (npc_id, claim_id, variant_id)
        existing = self._rumors.get(key)
        if existing is None:
            raise ValueError(
                f"{npc_id!r} cannot tell claim {claim_id!r} variant {variant_id!r} without having heard it first"
            )
        state = tell(existing, gamets=gamets)
        self._rumors[key] = state
        return state

    def rumor_state(self, npc_id: str, claim_id: str, variant_id: str | None) -> RumorState | None:
        return self._rumors.get((npc_id, claim_id, variant_id))

    def rumor_stage_now(self, npc_id: str, claim_id: str, variant_id: str | None, at_gamets: float) -> str:
        """The rumor's current stage, deriving "dormant"/"forgotten" lazily (rule 19) -- see stage_at()."""
        state = self._rumors[(npc_id, claim_id, variant_id)]
        belief = next(
            b for b in self._beliefs.values()
            if b.holder_id == npc_id and b.claim_id == claim_id and b.variant_id == variant_id
        )
        return stage_at(state, belief, at_gamets)

    def witness(self, **kwargs: object) -> tuple[Claim, BeliefInstance, Evidence]:
        claim, belief, evidence = witness(**kwargs)  # type: ignore[arg-type]

        existing_claim_id = self._claim_id_by_event.get(claim.canonical_event_key)
        if existing_claim_id is not None and existing_claim_id != claim.id:
            raise ValueError(
                f"event {claim.canonical_event_key} already has claim {existing_claim_id!r} -- "
                "a second independent witness reuses that claim_id, it doesn't create a new claim "
                "for the same canonical event"
            )

        existing_claim = self._claims.get(claim.id)
        if existing_claim is not None and existing_claim != claim:
            # Rule 12/21: a canonical claim never mutates in place -- two
            # witnesses to the same event must agree on the claim's
            # content, since every belief already pointing at this
            # claim_id (via chain_for) would otherwise retroactively
            # resolve to different content.
            raise ValueError(
                f"claim {claim.id!r} already exists with different content -- "
                "a second witness to the same event must report identical claim slots/kind, "
                "since claims never mutate in place (any disagreement belongs on a Variant instead)"
            )

        self._claim_id_by_event[claim.canonical_event_key] = claim.id
        self._claims[claim.id] = claim
        self._beliefs[belief.id] = belief
        self._evidence_by_belief[belief.id] = [evidence]
        # Witnessing is the story's first hearing for this NPC, self-sourced --
        # consistent with witness()'s Evidence.source_id also being the witness.
        self._record_hearing(
            npc_id=belief.holder_id, claim_id=claim.id, variant_id=None,
            source_id=belief.holder_id, gamets=belief.first_learned,
        )
        return claim, belief, evidence

    def retell(self, **kwargs: object) -> tuple[Variant, BeliefInstance, Evidence]:
        variant, belief, evidence = retell(**kwargs)  # type: ignore[arg-type]
        self._variants[variant.id] = variant
        self._beliefs[belief.id] = belief
        self._evidence_by_belief[belief.id] = [evidence]
        # The hearer heard this variant from the teller; the teller, by the
        # act of retelling, advances their own rumor stage to "repeated" for
        # whatever variant they held at the time (teller_belief.variant_id --
        # the same value retell()'s own validation checks against parent_variant).
        teller_belief: BeliefInstance = kwargs["teller_belief"]  # type: ignore[assignment]
        self._record_hearing(
            npc_id=belief.holder_id, claim_id=variant.claim_id, variant_id=variant.id,
            source_id=evidence.source_id, gamets=belief.first_learned,
        )
        self._record_telling(
            npc_id=evidence.source_id, claim_id=variant.claim_id,
            variant_id=teller_belief.variant_id, gamets=evidence.gamets,
        )
        return variant, belief, evidence

    def corroborate(
        self,
        *,
        belief_id: str,
        source_belief: BeliefInstance,
        evidence_id: str,
        gamets: float,
    ) -> tuple[BeliefInstance, Evidence]:
        """Independent corroborating testimony (rule 7): confidence rises, repetition doesn't.

        source_belief must be the current version of a belief already in
        this store (not a stale copy captured before an earlier call
        replaced that id), about the same claim, held by an NPC other
        than belief_id's own holder, who hasn't already corroborated
        belief_id -- a second telling from the *same* source is not
        corroboration (rule 7's "distinct source count, not repetition").
        Both beliefs are decayed to `gamets` (rule 19) before combining --
        corroborating testimony nobody has thought about in a long time
        shouldn't count at its original, un-decayed strength. Combines
        confidence via noisy-or (1 - product of disbelief), which is
        monotonically non-decreasing in both (decayed) inputs.
        """
        existing = self._beliefs[belief_id]
        if source_belief.claim_id != existing.claim_id:
            raise ValueError("source_belief must be about the same claim as the belief it corroborates")
        if source_belief.holder_id == existing.holder_id:
            raise ValueError("a belief cannot corroborate itself")
        if self._beliefs.get(source_belief.id) != source_belief:
            raise ValueError("source_belief is stale -- fetch the current version from the store")
        if gamets < existing.last_rehearsed or gamets < source_belief.last_rehearsed:
            raise ValueError("corroboration cannot precede either belief's last rehearsal")

        already_counted = {e.source_id for e in self._evidence_by_belief[belief_id]}
        if source_belief.holder_id in already_counted:
            raise ValueError(
                f"{source_belief.holder_id!r} already corroborated {belief_id!r} -- "
                "repetition from the same source doesn't raise confidence (rule 7)"
            )

        decayed_existing = decay(existing, gamets)
        decayed_source = decay(source_belief, gamets)
        updated = replace(
            existing,
            confidence=1 - (1 - decayed_existing.confidence) * (1 - decayed_source.confidence),
            verbatim_strength=decayed_existing.verbatim_strength,
            gist_strength=decayed_existing.gist_strength,
            last_rehearsed=gamets,
        )
        evidence = Evidence(
            id=evidence_id,
            belief_id=belief_id,
            evidence_type="corroborated",
            source_id=source_belief.holder_id,
            predecessor_belief_id=source_belief.id,
            gamets=gamets,
            strength=source_belief.confidence,
        )
        self._beliefs[belief_id] = updated
        self._evidence_by_belief[belief_id].append(evidence)
        return updated, evidence

    def beliefs_of(self, holder_id: str) -> tuple[BeliefInstance, ...]:
        """Every belief a given NPC holds, across every claim."""
        return tuple(b for b in self._beliefs.values() if b.holder_id == holder_id)

    def evidence_for(self, belief_id: str) -> tuple[Evidence, ...]:
        """Every Evidence record grounding one belief -- its original witness/report plus any corroboration."""
        return tuple(self._evidence_by_belief[belief_id])

    def chain_for(self, belief_id: str) -> tuple[tuple[BeliefInstance, Evidence], ...]:
        """Walk one belief back through its original-grounding predecessors to its witness.

        Returns (belief, evidence) pairs ordered from the queried belief
        back to the witness -- ADR-0007's "since when, from what
        evidence, through whom" as data, not hand-held references. Walks
        each belief's *original* grounding evidence (index 0); use
        evidence_for() to see corroborating evidence too.
        """
        chain: list[tuple[BeliefInstance, Evidence]] = []
        current: str | None = belief_id
        while current is not None:
            belief = self._beliefs[current]
            evidence = self._evidence_by_belief[current][0]
            chain.append((belief, evidence))
            current = evidence.predecessor_belief_id
        return tuple(chain)

    def claim(self, claim_id: str) -> Claim:
        return self._claims[claim_id]

    def variant(self, variant_id: str) -> Variant:
        return self._variants[variant_id]

    def belief_of(self, holder_id: str, claim_id: str) -> BeliefInstance | None:
        """The one belief holder_id holds about claim_id, or None if they don't hold one yet.

        Used by chronicle.propagate to decide whether an encounter has
        anything to propagate: exactly one belief per (holder, claim) can
        exist at a time (witness()/retell() enforce this by construction),
        so there's no ambiguity about which one this returns.
        """
        return next((b for b in self._beliefs.values() if b.holder_id == holder_id and b.claim_id == claim_id), None)
