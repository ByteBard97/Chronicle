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

# Time-decay half-lives, in gamets units (rule 6). Verbatim strength decays
# faster than gist strength -- fuzzy-trace theory's central claim, per
# docs/architecture.md's bounded-memory item -- so a rehearsed-but-fading
# memory keeps its gist ("something bad happened to the Jarl") long after
# the exact wording is gone. Placeholder magnitudes, same tunable-not-derived
# status as the retell constants above.
CONFIDENCE_DECAY_HALF_LIFE = 500.0
VERBATIM_DECAY_HALF_LIFE = 200.0
GIST_DECAY_HALF_LIFE = 2000.0


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
        return claim, belief, evidence

    def retell(self, **kwargs: object) -> tuple[Variant, BeliefInstance, Evidence]:
        variant, belief, evidence = retell(**kwargs)  # type: ignore[arg-type]
        self._variants[variant.id] = variant
        self._beliefs[belief.id] = belief
        self._evidence_by_belief[belief.id] = [evidence]
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
