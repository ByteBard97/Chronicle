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
    exist by name so the registry lists all 19, but emit nothing and run
    nothing until their tier's lane lands. Rules 11 (accumulation-
    threshold, lane 24), 14 (obligation-lifecycle violation cascade,
    lane 25), and 15 (tell-decision-policy, lane 23) are live;
    the stub set is now 12-13 and 16-19.
  - Budget (O4 ruling): 9+10 are one state machine and 4 is
    schema-not-rule -- 17/20 against the ceiling. The registry still lists
    all 19 names; the table below is the vocabulary, slugified from §8's
    leading tokens.

Two rule flavors fall out of R2's no-refactor ruling:

  - RecordedRule: the behavior happened at the driver call site; evaluate()
    is handed the outcome and records it. Disabling a RecordedRule
    suspends its INSTRUMENTATION; the underlying store mechanics are
    untouched (they were never the rule object's to suspend). The two
    driver-owned steps that ARE discrete rule behaviors -- the encounter
    sweep (rule 6) and the mutation decision (rule 7) -- are also gated
    behaviorally in driver.py, so disabling them is a real what-if probe.
  - Read-path rules (2, 9, 10): decay and the rumor stage machine are
    pure derivations evaluated at READ time (claims.decay / claims.
    stage_at), never during the run loop, so they emit nothing in-run --
    the CLI/reconstruction read path must not write to the log. Their
    evaluate() wraps the pure function for off-log consumers (a future GM
    layer); the driver never calls it.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import NamedTuple, Protocol

from chronicle.claims import BeliefInstance, RumorState, decay, stage_at

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


def _default_rules() -> tuple[Rule, ...]:
    """The 19 §8 rules: 1-10 enabled (wrappers/read-path), 11/14/15 live, the rest disabled stubs."""
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
        StubRule(GRUDGE_CREATION, 3),
        StubRule(GRUDGE_DECAY, 3),
        RecordedRule(OBLIGATION_LIFECYCLE, 3),
        TellDecisionRule(),
        StubRule(REPUTATION_ACCUMULATION, 3),
        StubRule(SCHEDULE_WRITE_BACK, 4),
        StubRule(PAIRWISE_ENCOUNTER_WEIGHTING, 4),
        StubRule(ROLE_VACANCY_SUCCESSION, 5),
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
        """Whether the rule may evaluate. Stubs (11-19) are never enabled until their tier's lane replaces the stub."""
        return name not in self._disabled and not isinstance(self._rules[name], StubRule)

    def names(self) -> tuple[str, ...]:
        return tuple(self._rules)
