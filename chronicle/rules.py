"""The rule registry -- Tier 3's forced cross-cutting machinery.

docs/scenario-ladder.md §8 (consequence b): every named rule must exist in
the registry as a named, toggleable, trace-instrumented object. The ruled
design is docs/design/tier-3-rule-registry-and-tell-decision.md §1 (R1-R3)
and §7 (R12), with the coordinator's 2026-08-23 rulings (O1-O5):

  - A rule is a small object; the registry is per-run, constructed in
    Driver.__init__ alongside the stores (R1). Toggleable means
    construction-time only (Driver's disabled_rules) -- never mid-run.
  - Retro-registration of the ten implemented rules is BY WRAPPER (R2):
    behavior stays at the existing call sites in driver.py/claims.py; the
    Rule object records the evaluation. Nothing here refactors store
    internals.
  - Every evaluation of an enabled rule emits a rule_evaluated trace
    record (docs/frame-log-schema.md §4:122), fired or not, with current
    accumulator values in inputs (R3). A disabled rule emits nothing.
    inputs is caller-assembled context -- rules never query stores
    themselves (the T2.3 lesson, docs/scenario-ladder.md:60).
  - Unlanded rules register as disabled stubs from day one (R12): they
    exist by name so the registry lists all 20, but emit nothing and run
    nothing until their tier's lane lands. Rules 11 (accumulation-
    threshold, lane 24), 12 (grudge-creation, the standalone self-victim
    twin of rule 14's cascade), 13 (grudge-decay, read-path wrapper
    around social.grudge_at/grudge_cooled), 14 (obligation-lifecycle
    violation cascade, lane 25), 15 (tell-decision-policy, lane 23), 16
    (reputation-evidence-accumulation, lane 26), 17
    (schedule-write-back, lane 36), 18 (pairwise-encounter-weighting,
    lane 43), 19 (role-vacancy-succession, lane 48), and 20
    (trust-discounted-retelling, docs/design/trust-discounted-retelling.md)
    are live; no stubs remain.
  - Budget (O4 ruling): 9+10 are one state machine and 4 is
    schema-not-rule -- 18/20 against the ceiling, landing exactly at the
    ceiling with rule 20 (docs/scenario-ladder.md §8). The registry still
    lists all 20 names; the table below is the vocabulary, slugified from
    §8's leading tokens.

Two rule flavors fall out of R2's no-refactor ruling:

  - RecordedRule: the behavior happened at the driver call site; evaluate()
    is handed the outcome and records it. Disabling a RecordedRule
    suspends its INSTRUMENTATION; the underlying store mechanics are
    untouched (they were never the rule object's to suspend). The two
    driver-owned steps that ARE discrete rule behaviors -- the encounter
    sweep (rule 6) and the mutation decision (rule 7) -- are also gated
    behaviorally in driver.py, so disabling them is a real what-if probe.
  - Rule 20 (trust-discounted-retelling) is a third flavor: a real
    behavioral toggle like rules 6/7 above, not instrumentation-only, but
    with no natural fired/not-fired EVENT the way rules 12/15/17/18/19
    have -- every enabled encounter-driven retelling/resolution gets a
    trust value, never zero of them. Its ``fired`` names WHICH trust value:
    True when a qualifying relationship existed, False when the
    no-relationship default was used. See TrustDiscountedRetellingRule.
  - Read-path rules (2, 9, 10, 13): decay and the rumor stage machine are
    pure derivations evaluated at READ time (claims.decay / claims.
    stage_at / social.grudge_at / social.grudge_cooled), never during the
    run loop, so they emit nothing in-run -- the CLI/reconstruction read
    path must not write to the log. Their evaluate() wraps the pure
    function for off-log consumers (a future GM layer); the driver never
    calls it.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import NamedTuple, Protocol

from chronicle.claims import BeliefInstance, RumorState, decay, stage_at
from chronicle.social import Grudge, grudge_at, grudge_cooled

# The 19 rule names of docs/scenario-ladder.md §8's table, by introducing tier.
WITNESS_CREATES_BELIEF = "witness-creates-belief"  # 1, tier 0
BELIEF_DECAY = "belief-decay"  # 2, tier 0 (verbatim/gist curves)
CORROBORATION = "corroboration"  # 3, tier 0 (noisy-or, distinct-source)
SHARED_CLAIM_INVARIANT = "shared-claim-invariant"  # 4, tier 0 (one claim per canonical event)
TESTIMONY_TRANSFER = "testimony-transfer"  # 5, tier 1 (flat retell decay)
ENCOUNTER_SAMPLING = "encounter-sampling"  # 6, tier 1 (co-presence + keyed roll)
MUTATION_POLICY = "mutation-policy"  # 7, tier 2
VARIANT_RESOLUTION = "variant-resolution"  # 8, tier 2 (evidence-type ordering + tiebreak)
RUMOR_STAGE_TRANSITIONS = "rumor-stage-transitions"  # 9, tier 2 (5-state machine)
DORMANCY_REACTIVATION = "dormancy-reactivation"  # 10, tier 2
ACCUMULATION_THRESHOLD = "accumulation-threshold"  # 11, tier 3 (with hysteresis, doctrine 3)
GRUDGE_CREATION = "grudge-creation"  # 12, tier 3 (emotional/evidentiary split)
GRUDGE_DECAY = "grudge-decay"  # 13, tier 3
OBLIGATION_LIFECYCLE = "obligation-issue-fulfill-violate"  # 14, tier 3 (+violation wiring)
TELL_DECISION_POLICY = "tell-decision-policy"  # 15, tier 3 (privacy/motive gate)
REPUTATION_ACCUMULATION = "reputation-evidence-accumulation"  # 16, tier 3 (observer-local Beta)
SCHEDULE_WRITE_BACK = "schedule-write-back"  # 17, tier 4a
PAIRWISE_ENCOUNTER_WEIGHTING = "pairwise-encounter-weighting"  # 18, tier 4b
ROLE_VACANCY_SUCCESSION = "role-vacancy-succession"  # 19, tier 5
TRUST_DISCOUNTED_RETELLING = "trust-discounted-retelling"  # 20, tier 1 (docs/design/trust-discounted-retelling.md)


class RuleContext(NamedTuple):
    """The caller-assembled evaluation context (R3: rules never query stores).

    outcome is the call-site-determined result for RecordedRule wrappers;
    read-path rules compute from inputs instead and leave it None.
    """

    tick: int
    gamets: float
    inputs: Mapping[str, object]
    outcome: RuleResult | None = None


class RuleResult(NamedTuple):
    fired: bool
    result: Mapping[str, object] | None = None


class Rule(Protocol):
    """A named, toggleable, trace-instrumented rule (R1). name is the §8 table string."""

    name: str
    tier: int

    def evaluate(self, ctx: RuleContext) -> RuleResult: ...


@dataclass(frozen=True)
class RecordedRule:
    """A wrapper rule (R2): the behavior lives at the existing call site; evaluate() records its outcome."""

    name: str
    tier: int

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        if ctx.outcome is None:
            raise ValueError(f"recorded rule {self.name!r} must be handed its call-site outcome")
        return ctx.outcome


@dataclass(frozen=True)
class StubRule:
    """A rule whose tier has not landed: registered by name, never enabled, runs nothing (R12)."""

    name: str
    tier: int

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        raise NotImplementedError(f"rule {self.name!r} is a registered stub -- it lands with its tier's lane")


class BeliefDecayRule:
    """Rule 2, read-path: wraps claims.decay for off-log consumers. Never evaluated in-run."""

    name = BELIEF_DECAY
    tier = 0

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        belief = ctx.inputs["belief"]
        assert isinstance(belief, BeliefInstance)
        decayed = decay(belief, ctx.inputs["at_gamets"])  # type: ignore[arg-type]
        return RuleResult(
            fired=True,
            result={
                "confidence": decayed.confidence,
                "verbatim_strength": decayed.verbatim_strength,
                "gist_strength": decayed.gist_strength,
            },
        )


class GrudgeDecayRule:
    """Rule 13, read-path: wraps social.grudge_at/grudge_cooled. Never evaluated in-run.

    The decay math already exists and already runs, unconditionally, at
    read-time -- social.grudge_at() (docstringed "rule 13's decay-at-read")
    and social.grudge_cooled() are called directly from driver.py's pairwise-
    avoidance logic (rule 18, around lines 1587/1595), gated only by
    ``self.rules.enabled(PAIRWISE_ENCOUNTER_WEIGHTING)`` -- nothing anywhere
    checks ``registry.enabled(GRUDGE_DECAY)``. So this class, like
    BeliefDecayRule/RumorStageRule, is a registry-level acknowledgment that
    the mechanism is real; landing it changes no runtime behavior.
    """

    name = GRUDGE_DECAY
    tier = 3

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        grudge = ctx.inputs["grudge"]
        assert isinstance(grudge, Grudge)
        at_gamets = ctx.inputs["at_gamets"]
        decayed = grudge_at(grudge, at_gamets)  # type: ignore[arg-type]
        return RuleResult(
            fired=True,
            result={
                "severity": decayed.severity,
                "emotional_strength": decayed.emotional_strength,
                "evidentiary_strength": decayed.evidentiary_strength,
                "cooled": grudge_cooled(grudge, at_gamets),  # type: ignore[arg-type]
            },
        )


class RumorStageRule:
    """Rule 9, read-path: wraps claims.stage_at. Never evaluated in-run."""

    name = RUMOR_STAGE_TRANSITIONS
    tier = 2

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        rumor = ctx.inputs["rumor"]
        belief = ctx.inputs["belief"]
        assert isinstance(rumor, RumorState) and isinstance(belief, BeliefInstance)
        return RuleResult(fired=True, result={"stage": stage_at(rumor, belief, ctx.inputs["at_gamets"])})  # type: ignore[arg-type]


class DormancyReactivationRule:
    """Rule 10, read-path: the stage machine's dormancy half (O4: 9+10 are one machine).

    fired means the rumor is dormant (or beyond) at the evaluation moment;
    reactivation itself is observed through testimony-transfer (rule 5) on
    a dormant rumor, not through a separate evaluation.
    """

    name = DORMANCY_REACTIVATION
    tier = 2

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        rumor = ctx.inputs["rumor"]
        belief = ctx.inputs["belief"]
        assert isinstance(rumor, RumorState) and isinstance(belief, BeliefInstance)
        stage = stage_at(rumor, belief, ctx.inputs["at_gamets"])  # type: ignore[arg-type]
        return RuleResult(fired=stage in ("dormant", "forgotten"), result={"stage": stage})


class GrudgeCreationRule:
    """Rule 12, grudge-creation gate (ladder T3.2 "Humiliation"; the non-
    obligation twin of rule 14's obligation-violation cascade).

    A latch/gate rule, the same "fired = the rule's effect" convention as
    rules 15/17/18/19 -- there is no accumulator here, just "does a grudge
    already exist for this (holder, target) pair." ``already_exists`` is
    driver-derived (the T2.3 lesson: rules never query stores) from
    ``social.grudge(holder_id, target_id)``, the same store lookup
    ``SocialStateStore.add_grudge`` itself uses to enforce its one-grudge-
    per-pair invariant (social.py ~line 486) -- this rule restates that
    invariant as a visible, instrumented gate instead of a raised
    ValueError, so a repeat humiliation for an already-grudging pair is a
    logged non-fire, not a silent skip or a crash.

    fired means a grudge SHOULD be formed -- the driver's cascade
    (form_grudge + the grudge_formed trace record) runs only then.
    """

    name = GRUDGE_CREATION
    tier = 3

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        already_exists = ctx.inputs["already_exists"]
        assert isinstance(already_exists, bool)
        return RuleResult(fired=not already_exists)


class AccumulationThresholdRule:
    """Rule 11, accumulation-threshold escalation (ladder T3.1; design doc R4-R6, lane 24).

    The accumulator is DERIVED (R4): the driver counts the holder's beliefs
    whose claim kind matches a registered grievance kind and whose slots
    name the holder as victim, and hands the count in via inputs -- the rule
    never queries stores. fires when count >= threshold and the latch is
    clear. The latch (R5) is store-derived by the driver (the escalation
    belief's existence); since the accumulator is monotonic (beliefs are
    never un-learned), doctrine-3 hysteresis reduces to that latch.

    fired means the escalation TRIGGERED; the R6 cascade itself (event,
    witness, threshold_crossed record) is the driver's, evidenced by the
    threshold_crossed record (schema §4:123), so this rule's result stays
    None.
    """

    name = ACCUMULATION_THRESHOLD
    tier = 3

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        count = ctx.inputs["count"]
        threshold = ctx.inputs["threshold"]
        latched = ctx.inputs["latched"]
        assert isinstance(count, int) and isinstance(threshold, int) and isinstance(latched, bool)
        return RuleResult(fired=not latched and count >= threshold)


class TellDecisionRule:
    """Rule 15, the tell-decision gate (ladder T3.4; design doc R10, lane 23).

    Two stages, both driven by caller-assembled inputs (the rule never
    queries stores -- the T2.3 lesson):

      1. Deterministic motive decline: inputs["motive"] names a
         caller-found motive (e.g. "kin-motive") -- decline, always, no
         roll. The paired transmission_declined record carries
         roll_key=None for exactly this case (schema §4:121).
      2. Keyed roll: inputs["roll_value"] against inputs["threshold"]
         (the driver's tell_probability). value < threshold tells;
         otherwise the gate declines.

    fired means the gate DECLINED the transmission -- the rule's effect,
    not its evaluation (every evaluation emits rule_evaluated regardless,
    R3). O5: the sub-reason lives in result/inputs, never in the rule name.
    """

    name = TELL_DECISION_POLICY
    tier = 3

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        motive = ctx.inputs["motive"]
        if motive is not None:
            return RuleResult(fired=True, result={"reason": motive})
        roll_value = ctx.inputs["roll_value"]
        threshold = ctx.inputs["threshold"]
        assert isinstance(roll_value, float) and isinstance(threshold, float)
        declined = roll_value >= threshold
        return RuleResult(fired=declined, result={"reason": "roll"} if declined else None)


class ScheduleWriteBackRule:
    """Rule 17, schedule write-back (ladder T4a.1; design doc T1-T7, lane 33/36).

    The first rule where state writes back into behavior. Both inputs are
    caller-assembled booleans (the T2.3 lesson, restated for Tier 4a):
    ``kin`` -- the newly-informed holder has a kinship edge to the
    deceased (``social.relationship(holder_id, deceased_id, "kinship")``,
    looked up in the driver, never here) -- and ``already_mourning`` -- the
    R5-pattern log-derived latch (a ``schedule_rewrite`` event already
    exists for this exact (npc, trigger_event_key) pair, so a later
    corroboration of the same death can't re-insert the overlay).

    fired means the overlay WAS inserted -- the driver's cascade (the
    schedule_rewrite event + the overlay itself) runs only then, the same
    "fired = the rule's effect" convention as rule 15
    (``TellDecisionRule``). Real toggle, not instrumentation-only (lane-19
    precedent for driver-owned rules): disabling this rule must suppress
    the rewrite itself, because T4a.2's Run B is Run A with this rule
    disabled (design doc T7), not a second hand-authored fixture.
    """

    name = SCHEDULE_WRITE_BACK
    tier = 4

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        kin = ctx.inputs["kin"]
        already_mourning = ctx.inputs["already_mourning"]
        assert isinstance(kin, bool) and isinstance(already_mourning, bool)
        return RuleResult(fired=kin and not already_mourning)


class PairwiseEncounterWeightingRule:
    """Rule 18, pairwise encounter weighting / avoidance (ladder T4b.1; design doc W1-W5, lane 40/43).

    Both inputs are caller-assembled (the T2.3 lesson, restated again):
    ``severity`` -- the pair's decayed grudge severity
    (``social.grudge_at(...).severity``, and already gated by
    ``not grudge_cooled(...)`` before the driver even calls this --
    cooling isn't a separate boolean here the way rule 17's latch is,
    because there's no one-shot event to latch on; severity decaying
    below the threshold IS the "avoidance stops" signal, read fresh
    every tick) -- and ``threshold``
    (``AVOIDANCE_GRUDGE_THRESHOLD``, driver-owned).

    fired means avoidance is ACTIVE for this pair this tick -- the
    driver only overrides the pair's encounter threshold
    (``schedule.sample_encounters``'s ``pair_thresholds``) when this
    fires, the same "fired = the rule's effect" convention as rules
    15/17. Real toggle (lane-19 precedent for driver-owned rules):
    disabling this rule must suppress the override itself, since a
    disabled "avoidance" rule that still avoided would be a silent
    behavior change with no toggle to explain it.
    """

    name = PAIRWISE_ENCOUNTER_WEIGHTING
    tier = 4

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        severity = ctx.inputs["severity"]
        threshold = ctx.inputs["threshold"]
        assert isinstance(severity, float) and isinstance(threshold, float)
        fired = severity >= threshold
        result = (
            {"base_probability": ctx.inputs["base_probability"], "effective_probability": ctx.inputs["effective_probability"]}
            if fired
            else None
        )
        return RuleResult(fired=fired, result=result)


class RoleVacancySuccessionRule:
    """Rule 19, role-vacancy/succession resolution (ladder T5.2; design doc S5-S6, lane 44/48).

    The last of the 19 raw rule names. ``has_candidate`` is
    caller-assembled (the driver ranks candidates by institution-
    relationship strength, descending, ties broken by lower npc_id --
    never a roll, so "fixtures carry the counterfactual" holds
    exactly); this rule only asks whether the caller found one.

    fired means a successor WAS installed -- the driver's
    installation + the role_appointed status_changed event (S4's
    vocabulary) happen only then, the same "fired = the rule's effect"
    convention as rules 15/17/18. Real toggle (lane-19/43/47
    precedent for driver-owned rules): disabling this rule means roles
    never resolve a successor and stay vacant, not merely stop logging
    that they did.
    """

    name = ROLE_VACANCY_SUCCESSION
    tier = 5

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        has_candidate = ctx.inputs["has_candidate"]
        assert isinstance(has_candidate, bool)
        return RuleResult(fired=has_candidate)


class TrustDiscountedRetellingRule:
    """Rule 20, trust-discounted retelling (ladder row 20; design doc
    docs/design/trust-discounted-retelling.md, ruled and ready).

    A real behavioral toggle, in the rules-6/7 family this file's module
    docstring names (disabling it is a real what-if probe, not just
    suspended instrumentation): the driver only looks up the hearer's
    relationship to the teller and threads a trust float into
    retell()/resolve() when ``self.rules.enabled(TRUST_DISCOUNTED_RETELLING)``
    is true; disabled, both call sites pass trust=None, reproducing the
    pre-rule-20 flat RETELL_CONFIDENCE_DECAY behavior exactly (this is
    what keeps ladder T1.1's own flat-0.8 baseline intact when this rule
    is disabled for that fixture).

    Unlike rules 12/15/17/18/19, there is no natural "declined" outcome
    here -- every enabled encounter-driven retelling or resolution gets
    A trust value, never zero of them, so "fired = the rule's effect"
    doesn't fit. Instead fired names WHICH trust value was used: True
    when the driver found a qualifying relationship (basis in
    {kinship, faction, shared_employer}, max strength across bases --
    colocation excluded per the design doc's ruled basis filter) and
    used its strength; False when no such edge existed and the
    no-relationship default (trust=0.5) was used instead. Either way
    inputs/result carry the trust value applied, so a provenance
    drill-down can see the exact discount without re-deriving it
    (docs/architecture.md's inspectability doctrine).
    """

    name = TRUST_DISCOUNTED_RETELLING
    tier = 1

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        has_relationship = ctx.inputs["has_relationship"]
        trust = ctx.inputs["trust"]
        assert isinstance(has_relationship, bool) and isinstance(trust, float)
        return RuleResult(fired=has_relationship, result={"trust": trust})


def _default_rules() -> tuple[Rule, ...]:
    """All 20 §8 rules live: 1-20 are wrappers/read-path/real rules; no stubs remain."""
    return (
        RecordedRule(WITNESS_CREATES_BELIEF, 0),
        BeliefDecayRule(),
        RecordedRule(CORROBORATION, 0),
        RecordedRule(SHARED_CLAIM_INVARIANT, 0),
        RecordedRule(TESTIMONY_TRANSFER, 1),
        RecordedRule(ENCOUNTER_SAMPLING, 1),
        RecordedRule(MUTATION_POLICY, 2),
        RecordedRule(VARIANT_RESOLUTION, 2),
        RumorStageRule(),
        DormancyReactivationRule(),
        AccumulationThresholdRule(),
        GrudgeCreationRule(),
        GrudgeDecayRule(),
        RecordedRule(OBLIGATION_LIFECYCLE, 3),
        TellDecisionRule(),
        RecordedRule(REPUTATION_ACCUMULATION, 3),
        ScheduleWriteBackRule(),
        PairwiseEncounterWeightingRule(),
        RoleVacancySuccessionRule(),
        TrustDiscountedRetellingRule(),
    )


class RuleRegistry:
    """The per-run registry (R1): constructed by Driver.__init__, toggled at construction only."""

    def __init__(self, *, disabled: Collection[str] = ()) -> None:
        self._rules: dict[str, Rule] = {rule.name: rule for rule in _default_rules()}
        unknown = set(disabled) - set(self._rules)
        if unknown:
            raise ValueError(f"disabled_rules names unregistered rules: {sorted(unknown)}")
        self._disabled = frozenset(disabled)

    def get(self, name: str) -> Rule:
        return self._rules[name]

    def enabled(self, name: str) -> bool:
        """Whether the rule may evaluate. Stubs (none remain as of lane 26x) are never enabled until their tier's lane replaces the stub."""
        return name not in self._disabled and not isinstance(self._rules[name], StubRule)

    def names(self) -> tuple[str, ...]:
        return tuple(self._rules)
