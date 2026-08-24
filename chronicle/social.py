"""The social-state store -- layer 4 of the data-ownership model.

docs/decisions/0006-data-ownership-layers.md defines five ownership
layers over the canonical event log (chronicle/events.py, layer 1) and
the claim/variant/belief store (chronicle/claims.py, layers 2-3). This
module implements layer 4: sparse relationships, grudges, obligations,
and observer-local reputation.

Two rules are load-bearing enough to enforce at the type/validation
level rather than by convention alone:

  - the sparse-graph rule: a Relationship exists only via co-location,
    kinship, faction, or shared employer (docs/v0.1-spec.md rule 11) --
    never for an arbitrary pair, and never backed by a dense N x N
    structure. form_relationship() rejects any other basis.
  - rule 10, observer-local reputation: a Reputation is keyed
    (observer_id, subject_id, context) with Beta-distribution counts --
    never a single score per NPC. There is deliberately no
    "global reputation" constructor or query on this store.

A Grudge is derived from a belief, not from an event directly (rule 8:
"a grudge is created only when the holder has an existing relationship
edge to the victim") -- form_grudge() takes the caller's already-looked-up
Relationship (or None) explicitly, the same way claims.retell() takes an
already-looked-up parent_variant/teller_belief, so the caller can't
silently skip the lookup and the rule is enforced at the one place a
grudge comes into existence.

Obligations are created explicitly for v0.1 (rule 18: obligations,
grudges, and reputation stay three separate record kinds, never merged)
-- there is no auto-derivation path from beliefs yet; that is a
documented follow-up, not a v0.1 requirement.

Rules 15/16 (encounter-sampling from NPC schedules, and the rumor stage
machine unheard -> heard -> repeated -> dormant -> forgotten) are
explicitly out of scope for this module. v0.1 hand-seeds "colocation"
relationships in chronicle/fixtures/whiterun_relationships.py instead of
deriving them from schedules -- the store's basis vocabulary already
has room for "colocation" so that seam is ready when the math tier
implements real encounter sampling.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from chronicle.claims import _decay


def _require_unit_interval(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value!r}")


ALLOWED_RELATIONSHIP_BASES = {"colocation", "kinship", "faction", "shared_employer"}

# Grudge severity and reputation weighting, per docs/decisions/open-questions.md's
# "treat as a tunable to be set empirically" note -- placeholders until the math
# tier calibrates them against a scenario, same status as claims.py's retell/decay
# constants.
GRUDGE_EMOTIONAL_WEIGHT = 0.5
GRUDGE_EVIDENTIARY_WEIGHT = 0.5

REPUTATION_PRIOR_ALPHA = 1.0
REPUTATION_PRIOR_BETA = 1.0
REPUTATION_WEIGHT_BY_KIND = {
    "witnessed": 1.0,
    "corroborated": 0.75,
    "reported": 0.5,
}

# Grudge decay half-lives, in gamets/ticks (rule 13 -- the missing twin of
# belief decay, ruled 2026-08-23 under lane 18's R7). Same tunable-not-derived
# placeholder status as claims.py's decay constants (docs/decisions/
# open-questions.md); the *ordering* is the load-bearing part: emotional
# strength outlives evidentiary strength (the facts of a grievance fade faster
# than the feeling), and both outlive belief confidence
# (CONFIDENCE_DECAY_HALF_LIFE = 168) by a wide margin -- T3.2's assertable
# "grudge decays slower than the rumor" holds at the constants level.
GRUDGE_EMOTIONAL_HALF_LIFE = 672.0  # ticks: ~28 game-days (24*28) -- anger outlives the story.
GRUDGE_EVIDENTIARY_HALF_LIFE = 336.0  # ticks: ~14 game-days (24*14) -- between confidence (168) and gist (1440).


@dataclass(frozen=True)
class Relationship:
    """A sparse, directed social edge. Never a dense matrix row.

    Directed: a Relationship(from_id="hulda", to_id="ysolda", ...) says
    nothing about the reverse -- a fixture wanting a mutual bond creates
    both edges explicitly, rather than this store inferring symmetry.
    """

    id: str
    from_id: str
    to_id: str
    basis: str
    basis_id: str | None
    strength: float
    formed_at: float
    last_updated: float

    def __post_init__(self) -> None:
        if self.basis not in ALLOWED_RELATIONSHIP_BASES:
            raise ValueError(
                f"basis {self.basis!r} is not one of {sorted(ALLOWED_RELATIONSHIP_BASES)} -- "
                "relationships exist only via co-location, kinship, faction, or shared "
                "employer (docs/v0.1-spec.md rule 11), never for an arbitrary pair"
            )
        _require_unit_interval("strength", self.strength)


@dataclass(frozen=True)
class Grudge:
    """A lasting negative social debt, derived from a belief about harm to someone the holder cares about."""

    id: str
    holder_id: str
    target_id: str
    source_belief_id: str
    grievance_type: str
    severity: float
    emotional_strength: float
    evidentiary_strength: float
    last_rehearsed: float
    forgiveness_threshold: float

    def __post_init__(self) -> None:
        _require_unit_interval("severity", self.severity)
        _require_unit_interval("emotional_strength", self.emotional_strength)
        _require_unit_interval("evidentiary_strength", self.evidentiary_strength)
        _require_unit_interval("forgiveness_threshold", self.forgiveness_threshold)


@dataclass(frozen=True)
class Obligation:
    """A social debt: issuer expects debtor to perform an action under a condition.

    A separate record kind from Grudge/Reputation (rule 18) -- created
    explicitly via issue_obligation() for v0.1, not auto-derived from
    beliefs or grudges.
    """

    id: str
    issuer_id: str
    debtor_id: str
    beneficiary_id: str | None
    action: str
    condition: str | None
    deadline: float | None
    status: str  # "active" | "fulfilled" | "violated" | "expired" | "excused"
    witnesses: tuple[str, ...]
    sanctions: str | None
    excuse: str | None
    created_at: float
    fulfilled_at: float | None
    violated_at: float | None


@dataclass(frozen=True)
class Reputation:
    """An observer-local trust assessment in one context (rule 10).

    Keyed (observer_id, subject_id, context) -- there is no global score.
    alpha/beta are Beta-distribution success/failure counts starting from
    a uniform prior; direct_count/witness_count/certified_count record
    how that evidence was gathered, distinct from the Beta counts
    themselves so the provenance breakdown survives even as alpha/beta
    accumulate.
    """

    observer_id: str
    subject_id: str
    context: str
    alpha: float
    beta: float
    direct_count: int
    witness_count: int
    certified_count: int
    uncertainty: float
    last_updated: float

    def __post_init__(self) -> None:
        if self.alpha <= 0.0 or self.beta <= 0.0:
            raise ValueError("alpha/beta must be positive -- a Beta distribution's parameters")
        _require_unit_interval("uncertainty", self.uncertainty)

    @property
    def mean(self) -> float:
        """The Beta distribution's mean -- the point-estimate trust value."""
        return self.alpha / (self.alpha + self.beta)


def form_relationship(
    *,
    id: str,
    from_id: str,
    to_id: str,
    basis: str,
    basis_id: str | None,
    strength: float,
    gamets: float,
) -> Relationship:
    """Construct a sparse relationship edge. Validation lives on Relationship itself."""
    return Relationship(
        id=id,
        from_id=from_id,
        to_id=to_id,
        basis=basis,
        basis_id=basis_id,
        strength=strength,
        formed_at=gamets,
        last_updated=gamets,
    )


def form_grudge(
    *,
    id: str,
    holder_id: str,
    victim_id: str,
    target_id: str,
    grievance_type: str,
    source_belief_id: str,
    evidentiary_strength: float,
    relationship_to_victim: Relationship | None,
    gamets: float,
    forgiveness_threshold: float = 0.2,
) -> Grudge:
    """Derive a Grudge from a belief about harm to victim_id -- rule 8's gate.

    relationship_to_victim must be the caller's own lookup of
    store.relationship(from_id=holder_id, to_id=victim_id, basis=...) (any
    basis) -- passing None means no such edge exists, and this raises
    rather than creating an unconditional grudge. This mirrors how
    claims.retell() takes an already-looked-up parent_variant: the check
    happens once, at construction, not scattered across callers.

    One ruled bypass (O3, 2026-08-23, lane 25): victim_id == holder_id
    skips the missing-edge raise. Harm-to-self is rule 8's BASE CASE, not
    an exception -- "someone the holder cares about" starts with the
    holder. No synthetic self-edge is created (no fake data); the bypass
    only skips the gate, and the emotional component is 1.0 because
    self-regard is total (there is no edge to draw it from).
    """
    if relationship_to_victim is None and victim_id != holder_id:
        raise ValueError(
            f"{holder_id!r} has no relationship edge to {victim_id!r} -- "
            "a grudge is created only when the holder has an existing relationship "
            "to the victim (docs/v0.1-spec.md rule 8), never unconditionally"
        )
    if relationship_to_victim is not None and (
        relationship_to_victim.from_id != holder_id or relationship_to_victim.to_id != victim_id
    ):
        raise ValueError(
            "relationship_to_victim must run holder_id -> victim_id -- "
            f"got {relationship_to_victim.from_id!r} -> {relationship_to_victim.to_id!r}"
        )
    _require_unit_interval("evidentiary_strength", evidentiary_strength)

    # The O3 self-victim bypass has no edge to read; self-regard is total.
    emotional_strength = relationship_to_victim.strength if relationship_to_victim is not None else 1.0
    severity = min(
        1.0,
        GRUDGE_EMOTIONAL_WEIGHT * emotional_strength + GRUDGE_EVIDENTIARY_WEIGHT * evidentiary_strength,
    )
    return Grudge(
        id=id,
        holder_id=holder_id,
        target_id=target_id,
        source_belief_id=source_belief_id,
        grievance_type=grievance_type,
        severity=severity,
        emotional_strength=emotional_strength,
        evidentiary_strength=evidentiary_strength,
        last_rehearsed=gamets,
        forgiveness_threshold=forgiveness_threshold,
    )


def grudge_at(grudge: Grudge, at_gamets: float) -> Grudge:
    """The grudge as of a moment in time -- rule 13's decay-at-read.

    Pure derivation, the same pattern as claims.py's stage_at(): emotional
    and evidentiary strengths decay from last_rehearsed via claims._decay
    with their own half-lives, and severity recomputes from the decayed
    strengths with the formation-time weights. The stored record is never
    mutated (event-sourcing discipline: state is derived, not destroyed).
    """
    elapsed = max(0.0, at_gamets - grudge.last_rehearsed)
    emotional = _decay(grudge.emotional_strength, elapsed, GRUDGE_EMOTIONAL_HALF_LIFE)
    evidentiary = _decay(grudge.evidentiary_strength, elapsed, GRUDGE_EVIDENTIARY_HALF_LIFE)
    return replace(
        grudge,
        severity=min(1.0, GRUDGE_EMOTIONAL_WEIGHT * emotional + GRUDGE_EVIDENTIARY_WEIGHT * evidentiary),
        emotional_strength=emotional,
        evidentiary_strength=evidentiary,
    )


def grudge_cooled(grudge: Grudge, at_gamets: float) -> bool:
    """Whether the decayed grudge has fallen below its forgiveness threshold.

    A cooled grudge no longer gates behavior rules (Tier 4b's avoidance);
    it is never deleted. The comparison is against decayed severity -- the
    record's composite strength.
    """
    return grudge_at(grudge, at_gamets).severity < grudge.forgiveness_threshold


def issue_obligation(
    *,
    id: str,
    issuer_id: str,
    debtor_id: str,
    beneficiary_id: str | None,
    action: str,
    condition: str | None,
    gamets: float,
    deadline: float | None = None,
    witnesses: tuple[str, ...] = (),
    sanctions: str | None = None,
) -> Obligation:
    return Obligation(
        id=id,
        issuer_id=issuer_id,
        debtor_id=debtor_id,
        beneficiary_id=beneficiary_id,
        action=action,
        condition=condition,
        deadline=deadline,
        status="active",
        witnesses=witnesses,
        sanctions=sanctions,
        excuse=None,
        created_at=gamets,
        fulfilled_at=None,
        violated_at=None,
    )


def _resolve_obligation(obligation: Obligation, *, status: str, gamets: float, excuse: str | None = None) -> Obligation:
    if obligation.status != "active":
        raise ValueError(f"obligation {obligation.id!r} is {obligation.status!r}, not active -- cannot resolve twice")
    if status == "fulfilled":
        return replace(obligation, status=status, fulfilled_at=gamets)
    if status == "violated":
        return replace(obligation, status=status, violated_at=gamets, excuse=excuse)
    raise ValueError(f"unsupported resolution status {status!r}")


def update_reputation(
    existing: Reputation | None,
    *,
    observer_id: str,
    subject_id: str,
    context: str,
    kind: str,
    positive: bool,
    gamets: float,
) -> Reputation:
    """Fold one observation into an observer-local Reputation (rule 10).

    kind selects both the evidence-provenance bucket (direct/witness/
    certified count) and the Beta-update weight -- a witnessed act moves
    the estimate more than secondhand testimony (REPUTATION_WEIGHT_BY_KIND),
    the same "distinct source, weighted by directness" spirit as claims.py's
    corroboration (rule 7), applied to a running trust estimate instead of
    a single belief's confidence.
    """
    if kind not in REPUTATION_WEIGHT_BY_KIND:
        raise ValueError(f"kind must be one of {sorted(REPUTATION_WEIGHT_BY_KIND)}, got {kind!r}")

    weight = REPUTATION_WEIGHT_BY_KIND[kind]
    alpha = existing.alpha if existing is not None else REPUTATION_PRIOR_ALPHA
    beta = existing.beta if existing is not None else REPUTATION_PRIOR_BETA
    direct_count = existing.direct_count if existing is not None else 0
    witness_count = existing.witness_count if existing is not None else 0
    certified_count = existing.certified_count if existing is not None else 0

    if positive:
        alpha += weight
    else:
        beta += weight

    if kind == "witnessed":
        direct_count += 1
    elif kind == "certified":  # pragma: no cover -- no v0.1 caller yet, shape reserved
        certified_count += 1
    else:
        witness_count += 1

    total_evidence = direct_count + witness_count + certified_count
    uncertainty = 1.0 / (1.0 + total_evidence)

    return Reputation(
        observer_id=observer_id,
        subject_id=subject_id,
        context=context,
        alpha=alpha,
        beta=beta,
        direct_count=direct_count,
        witness_count=witness_count,
        certified_count=certified_count,
        uncertainty=uncertainty,
        last_updated=gamets,
    )


class SocialStateStore:
    """The queryable social-state store ADR-0006's layer 4 names -- materialized.

    Mirrors ClaimStore's shape: pure constructor functions above build
    records, this store indexes them for query. Every index is keyed by
    the sparse edges actually created -- there is no code path here that
    iterates "all NPCs" or "all pairs" (the sparse-graph rule extends to
    the store's own implementation, not just its inputs).
    """

    def __init__(self) -> None:
        self._relationships: dict[str, Relationship] = {}
        self._relationships_by_from: dict[str, set[str]] = {}
        self._relationship_key: dict[tuple[str, str, str], str] = {}

        self._grudges: dict[str, Grudge] = {}
        self._grudges_by_holder: dict[str, set[str]] = {}
        self._grudge_key: dict[tuple[str, str], str] = {}

        self._obligations: dict[str, Obligation] = {}
        self._obligations_by_npc: dict[str, set[str]] = {}

        self._reputations: dict[tuple[str, str, str], Reputation] = {}

    # -- relationships --------------------------------------------------

    def add_relationship(self, relationship: Relationship) -> Relationship:
        key = (relationship.from_id, relationship.to_id, relationship.basis)
        existing_id = self._relationship_key.get(key)
        if existing_id is not None and existing_id != relationship.id:
            raise ValueError(
                f"a relationship already exists for {key} -- update it via its existing "
                f"id {existing_id!r} rather than creating a second edge for the same triple"
            )
        self._relationships[relationship.id] = relationship
        self._relationships_by_from.setdefault(relationship.from_id, set()).add(relationship.id)
        self._relationship_key[key] = relationship.id
        return relationship

    def relationships_from(self, from_id: str) -> tuple[Relationship, ...]:
        ids = self._relationships_by_from.get(from_id, ())
        return tuple(self._relationships[i] for i in ids)

    def relationship(self, from_id: str, to_id: str, basis: str) -> Relationship | None:
        rel_id = self._relationship_key.get((from_id, to_id, basis))
        return self._relationships[rel_id] if rel_id is not None else None

    def any_relationship(self, from_id: str, to_id: str) -> Relationship | None:
        """The first relationship edge from_id -> to_id regardless of basis, or None.

        form_grudge() only needs *a* qualifying edge to exist (rule 8
        doesn't name a required basis) -- this is the lookup a caller
        does before calling form_grudge(), not a bypass of the
        basis-restricted relationship() query above.
        """
        for rel_id in self._relationships_by_from.get(from_id, ()):
            rel = self._relationships[rel_id]
            if rel.to_id == to_id:
                return rel
        return None

    # -- grudges ----------------------------------------------------------

    def add_grudge(self, grudge: Grudge) -> Grudge:
        key = (grudge.holder_id, grudge.target_id)
        existing_id = self._grudge_key.get(key)
        if existing_id is not None and existing_id != grudge.id:
            raise ValueError(
                f"a grudge already exists for {key} -- update it via its existing "
                f"id {existing_id!r} rather than creating a second grudge for the same pair"
            )
        self._grudges[grudge.id] = grudge
        self._grudges_by_holder.setdefault(grudge.holder_id, set()).add(grudge.id)
        self._grudge_key[key] = grudge.id
        return grudge

    def grudges_of(self, holder_id: str) -> tuple[Grudge, ...]:
        ids = self._grudges_by_holder.get(holder_id, ())
        return tuple(self._grudges[i] for i in ids)

    def grudge(self, holder_id: str, target_id: str) -> Grudge | None:
        grudge_id = self._grudge_key.get((holder_id, target_id))
        return self._grudges[grudge_id] if grudge_id is not None else None

    # -- obligations --------------------------------------------------------

    def add_obligation(self, obligation: Obligation) -> Obligation:
        self._obligations[obligation.id] = obligation
        for npc_id in {obligation.issuer_id, obligation.debtor_id, *( [obligation.beneficiary_id] if obligation.beneficiary_id else [])}:
            self._obligations_by_npc.setdefault(npc_id, set()).add(obligation.id)
        return obligation

    def obligations_involving(self, npc_id: str) -> tuple[Obligation, ...]:
        ids = self._obligations_by_npc.get(npc_id, ())
        return tuple(self._obligations[i] for i in ids)

    def active_obligations_of(self, debtor_id: str) -> tuple[Obligation, ...]:
        return tuple(o for o in self.obligations_involving(debtor_id) if o.debtor_id == debtor_id and o.status == "active")

    def fulfill_obligation(self, obligation_id: str, *, gamets: float) -> Obligation:
        updated = _resolve_obligation(self._obligations[obligation_id], status="fulfilled", gamets=gamets)
        self._obligations[obligation_id] = updated
        return updated

    def violate_obligation(self, obligation_id: str, *, gamets: float, excuse: str | None = None) -> Obligation:
        updated = _resolve_obligation(self._obligations[obligation_id], status="violated", gamets=gamets, excuse=excuse)
        self._obligations[obligation_id] = updated
        return updated

    # -- reputation -----------------------------------------------------

    def update_reputation(
        self,
        *,
        observer_id: str,
        subject_id: str,
        context: str,
        kind: str,
        positive: bool,
        gamets: float,
    ) -> Reputation:
        key = (observer_id, subject_id, context)
        updated = update_reputation(
            self._reputations.get(key),
            observer_id=observer_id,
            subject_id=subject_id,
            context=context,
            kind=kind,
            positive=positive,
            gamets=gamets,
        )
        self._reputations[key] = updated
        return updated

    def reputation(self, observer_id: str, subject_id: str, context: str) -> Reputation | None:
        return self._reputations.get((observer_id, subject_id, context))
