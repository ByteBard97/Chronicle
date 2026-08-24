# Tier 4b design prep — pairwise encounter weighting (avoidance)

Status: design proposal for owner review (lane 40 deliverable). No code.
Every code/schema claim carries a file:line citation verified against
`5362cbc`. Structured so each **Decision** section lifts into an ADR,
same shape as the Tier-3/4a design docs; open points for the owner are
collected in §6. Decisions here are prefixed **W** (weighting) to keep
them distinct from Tier-4a's T-prefixed decisions.

Sources: `docs/scenario-ladder.md` Tier 4b intro + T4b.1 (lines 86–89),
§8 (line 152); `docs/design/tier-4a-schedule-write-back.md` §4 (the T6b
preview this doc verifies and makes precise); `chronicle/schedule.py`;
`chronicle/social.py`; `chronicle/driver.py` (lane 36's landed overlay
machinery); `chronicle/rules.py`; `docs/vision-v2.2.md` §2.

---

## 0. What Tier 4b actually asks for

One rung (`docs/scenario-ladder.md:86-89`): **T4b.1 Avoidance.** A
strong grudge between a pair. Assert: the pair's weight drops per the
named avoidance rule; encounters between them cease at the shared
tavern block; the weight delta is visible in the trace, not a hidden
multiplier.

The ladder's own framing draws the boundary against Tier 4a precisely:
*"4a changed who's at the table; 4b changes whether tablemates actually
talk"* — a different failure signature, split accordingly
(`docs/scenario-ladder.md:87`). Tier 4a's design doc already sketched
this as a preview (T6b, `tier-4a-schedule-write-back.md:225-250`)
specifically to name why it had to stay out of T4a's own rungs; this
doc verifies that preview against the now-landed 4a code and turns it
into a ruled design.

---

## 1. The override's exact mechanics (question 1)

### Decision W1 — a per-pair threshold REPLACEMENT, not a multiplier; computed by the driver, per tick

`sample_encounters` (`schedule.py:119-179`) rolls one keyed value per
co-present pair and compares it against a single scalar
`encounter_probability` (`schedule.py:124,177-178`:
`encountered=value < encounter_probability`). The roll itself
(`value`, line 155-162) never changes — the design doc's T6b preview
already established this and it holds: `value` is keyed on
`(seed_id, purpose, tick, site, participants, draw)`
(`rng.py:85-103`), and avoidance introduces none of those inputs.

The seam is `encounter_probability`. Proposed: `sample_encounters`
gains one new parameter, `pair_thresholds: Mapping[frozenset[str],
float] | None = None` — an unordered-pair-keyed override. For a pair
present in the mapping, its `threshold` is the override value instead
of the caller's `encounter_probability`; every other pair is
unaffected. `frozenset` (not a tuple) because a grudge is directional
(`Grudge.holder_id -> Grudge.target_id`, `social.py:117-118`) but the
roll and its threshold are about the *pair*, not the direction — the
override lookup must match regardless of which name `sample_encounters`
happens to sort first (`schedule.py:152`, `ordered = sorted(npc_ids)`).

**Replacement, not a multiplier.** A multiplier (`effective =
encounter_probability * factor`) is ambiguous at the edges (what factor
guarantees "cease" from an arbitrary base probability?) and introduces
a second tunable (the factor) on top of the override's own strength.
Nothing else in the codebase uses a multiplier for a probability
tunable — `ENCOUNTER_PROBABILITY`, `TELL_PROBABILITY`, and
`MOURNING_DURATION_TICKS` are all flat replacement values
(`schedule.py:34`, `driver.py:115,122`) — so a flat replacement is both
simpler and consistent with the existing tunable style. Proposed
constant: `AVOIDANCE_PROBABILITY = 0.0` (new, `driver.py`, same
placeholder-tunable status as its siblings). Zero is deliberate, not
just "very low": `encountered = value < threshold` with `threshold =
0.0` is **never** true regardless of `value` (`_rng.roll`'s range is
`[0, 1)`, `rng.py:94`) — this is what makes T4b.1's "encounters between
them cease" a hard guarantee the rung can assert exactly, not a
low-probability approximation that would make the rung's determinism
depend on run length or get flaky under a different seed.

**Where computed:** the driver, fresh every `_run_tick`, immediately
before the `sample_encounters` call (`driver.py`'s presence-computation
block, the same per-tick-consultation shape lane 36 established for
schedule overlays — `effective_schedule_at` is looked up fresh each
tick too, `driver.py`'s `_run_tick`). Proposed helper,
`_active_avoidance_pairs(tick) -> dict[frozenset[str], Grudge]`: scans
`self.social._grudges.values()` (the same private-dict-read precedent
`_evaluate_accumulation`/`_escalation_latched` already use against
`self.claims`, and the same one `cli.py`'s `trace`/`inspect` commands
use against `state.claims._beliefs` — there is no `grudges()` bulk
accessor on `SocialStateStore` today, only `grudges_of(holder_id)` and
`grudge(holder_id, target_id)`, `social.py:485-491`), and for each
grudge with `grudge_at(grudge, gamets).severity >=
AVOIDANCE_GRUDGE_THRESHOLD` and not `grudge_cooled(grudge, gamets)`
(`social.py:280-307`), maps `frozenset((grudge.holder_id,
grudge.target_id))` to that grudge. A mutual grudge (both sides holding
one against the other) collapses to the same key — no conflict, the
pair is either avoiding or it isn't.

**Interaction with `encounter_probability`:** purely additive. Unlisted
pairs get exactly the caller's `encounter_probability`, byte-identical
to today's behavior — migration-safe by construction, the same
guarantee every prior tier's caller-supplies-context mapping made (no
mapping/no qualifying grudge, zero behavior change).

---

## 2. The rung's exact assertions (question 2)

### Decision W2 — avoidance produces an ordinary `encounter_rolled` row with a visibly lower `threshold`, plus a paired `rule_evaluated` row naming the grudge

The pair is still co-present (avoidance is about *whether they talk*,
not *whether they're in the room* — Tier 4a's distinction, §0 above), so
`sample_encounters` still produces one `EncounterRoll`/`encounter_rolled`
record per tick they share a location, exactly like any other
rolled-against pair (ui-doctrines D7: negative results are first-class;
`schedule.py`'s `EncounterRoll` docstring makes the same point about
`encountered=False`). **No new record type is needed** — the existing
`encounter_rolled` row already carries `threshold`
(`docs/frame-log-schema.md:116`), so an avoiding pair's row is
self-evidently different from an ordinary rolled-against row: its
`threshold` reads `0.0` (or whatever `AVOIDANCE_PROBABILITY` is tuned
to) instead of the run's base `encounter_probability`. This is
literally "the weight delta is visible in the trace" — the delta is
`base_probability - threshold`, computable from the row alone if the
reader knows the run's configured base (which `runs/index.json` or a
fixture already records), and unambiguous either way since a normal
rolled-against row's `threshold` always equals the base.

That said, requiring a reader to know the run's base probability out of
band to *notice* the delta is a real gap for the "not a hidden
multiplier" requirement's spirit — a reader should see the WHY without
cross-referencing configuration. So: **rule 18 evaluates once per
avoiding pair, per tick they are rolled** (not once per tick globally,
unlike rule 6's per-tick-not-per-roll volume discipline
`docs/work-packets/reviews/README.md:85`, because rule 18's outcome is
inherently pair-specific — different pairs can have different
grudges). Paired with the `encounter_rolled` row, a `rule_evaluated`
row names the grudge directly:

```
inputs: {"npc_a": ..., "npc_b": ..., "grudge_id": ..., "severity": <grudge_at(...).severity>, "threshold": AVOIDANCE_GRUDGE_THRESHOLD}
fired: true
result: {"base_probability": <encounter_probability>, "effective_probability": AVOIDANCE_PROBABILITY}
```

`fired: true` means "avoidance is active for this roll" (the rule's
*effect*, the same convention as rules 15/17 — `rules.py`'s
`TellDecisionRule`/`ScheduleWriteBackRule` docstrings). **Rule 18 only
evaluates for pairs with a grudge between them at all** (mirroring how
rule 11/16/17 only evaluate for claim kinds/kins actually registered,
never a global sweep) — a grudge-free pair produces no rule-18 row,
bounding volume to (grudge count) × (co-present ticks), not
(all pairs) × (all ticks).

**Distinguishing avoided from ordinary rolled-against, precisely:**
`encounter_rolled.threshold == AVOIDANCE_PROBABILITY` (or, more
robustly for the rung: `< encounter_probability`, in case a future
tuning makes avoidance a genuine reduction rather than a hard zero) AND
a same-tick `rule_evaluated` row (rule 18) naming that pair with
`fired: true`. An ordinary rolled-against pair has `threshold ==
encounter_probability` and no rule-18 row at all (not `fired: false` —
per W1/§0, rule 18 doesn't evaluate for grudge-free pairs).

**Rung fixture, concretely (T4b.1):** two NPCs (say Adrianne and
Ulfberth) share the tavern block for the whole run
(`ScheduleBlock`, the shared "bannered_mare"-style fixture convention
every prior tier's tavern rung uses); a grudge above
`AVOIDANCE_GRUDGE_THRESHOLD` exists between them from tick 0. Assert:
every `encounter_rolled` row for their pair has `encountered: false`
and `threshold == AVOIDANCE_PROBABILITY`; a same-tick rule-18
`rule_evaluated` row exists for each one; a **control pair** at the same
tavern block with no grudge encounters normally (`threshold ==
encounter_probability`, `encountered` varies with the roll) — proving
avoidance is per-pair, not a location-wide effect.

---

## 3. Cooling/reheating dynamics (question 3)

### Decision W3 — no separate transition record; the same read-time-derivation discipline as everything else in this tier

`grudge_at`/`grudge_cooled` are pure functions of `gamets`
(`social.py:280-307`) — nothing is stored about "is this pair currently
avoiding." Each tick's `_active_avoidance_pairs` call re-derives the
answer from scratch. A cooling transition is therefore not a special
case: severity decays every tick (`grudge_at`'s `_decay` calls,
`social.py:290-291`), and once it drops below
`AVOIDANCE_GRUDGE_THRESHOLD` (avoidance stops, but the grudge itself
persists — it isn't `grudge_cooled` yet, since that floor is
`forgiveness_threshold`, a *separate*, lower bar, `social.py:307` vs.
this doc's new `AVOIDANCE_GRUDGE_THRESHOLD`), the pair simply stops
appearing in `pair_thresholds` on some later tick and rolls resume at
the base probability — visible in the trace as the `rule_evaluated`
rows for that pair simply stopping (no more `fired: true` rows), the
same "the absence of a row IS the signal" pattern rule 11's latch and
rule 17's restoration both already use (§1/§3 of the Tier-4a doc).

**A three-stage severity progression falls out for free**, worth naming
explicitly since it clarifies why two different thresholds exist on the
same `Grudge`:

| Severity range | Behavior |
|---|---|
| `>= AVOIDANCE_GRUDGE_THRESHOLD` | Avoiding: rule 18 fires, encounters cease |
| `< AVOIDANCE_GRUDGE_THRESHOLD`, `>= forgiveness_threshold` | Cooling: no avoidance, but the grudge is still "live" (still counts for whatever future T4b/T5 machinery reads it) |
| `< forgiveness_threshold` (`grudge_cooled`, `social.py:300-307`) | Forgiven: never gated behavior again, never deleted |

Proposed `AVOIDANCE_GRUDGE_THRESHOLD = 0.5` (new tunable,
`driver.py`, placeholder magnitude) — comfortably above the default
`forgiveness_threshold = 0.2` (`social.py:227`), so the three stages are
reachable in order as severity decays rather than avoidance and cooling
being indistinguishable. Reheating (a fresh grievance re-raises
severity, e.g. via `form_grudge` being called again or a future
"grudge reinforcement" mechanism not yet designed) is not a new
mechanism either — it would just be a new/updated `Grudge` record
crossing back above the threshold, which `_active_avoidance_pairs`
picks up on its next per-tick read with no code change. Whether the
current one-`Grudge`-per-(holder,target) store shape
(`social.py:489-491`, `grudge(holder_id, target_id)` implies at most one
per ordered pair) supports "reinforcement" at all is out of this doc's
scope — no rung needs it.

---

## 4. Rule budget + registry (question 4)

### Decision W4 — rule 18 registers exactly like rule 17: real toggle, no budget change, no new RNG purpose

- **Registration**: `PairwiseEncounterWeightingRule` replaces the
  `StubRule(PAIRWISE_ENCOUNTER_WEIGHTING, 4)` stub (`rules.py:265` as of
  lane 36's edit) — same shape as `ScheduleWriteBackRule`
  (`rules.py`'s current class): `evaluate()` receives caller-assembled
  `severity`/`threshold` and returns `fired = severity >= threshold`
  (the "not `grudge_cooled`" gate is folded into whether
  `_active_avoidance_pairs` includes the pair at all — it never reaches
  the rule as a separate boolean the way rule 17's `already_mourning`
  does, since there's no *latch* here to distinguish from the raw
  gate — cooling is continuous decay, not a one-shot event).
- **Real toggle** (not instrumentation-only), same lane-19 precedent
  cited for rule 17: disabling rule 18 must suppress the override
  itself, not just its `rule_evaluated` row, because otherwise a
  disabled "avoidance" rule would still silently avoid — the driver-
  owned-rule discipline (`docs/work-packets/reviews/README.md:85`)
  applies identically here.
- **Budget**: rule 18 is already counted in the ladder's raw 19
  (`docs/scenario-ladder.md:152`) and in the Tier-3 doc's R13
  consolidation math (17/20 effective,
  `tier-3-rule-registry-and-tell-decision.md:371`) — landing it fills
  the registry's last Tier-4 stub slot (`PAIRWISE_ENCOUNTER_WEIGHTING`);
  nothing here proposes a 20th rule.
- **RNG**: no new purpose. The roll is `ENCOUNTER_CO_PRESENCE`
  unchanged (`rng.py:41`); avoidance only changes what the driver
  compares the roll's value against, exactly as the Tier-4a preview
  argued and this doc reconfirms against the landed `sample_encounters`
  signature (`schedule.py:119-124`).

---

## 5. Interaction with lane 37's roll-identity guarantee (question 5)

### Decision W5 — currently a non-issue by construction; a methodological note for future reuse of the T4a.2 pattern

T4a.2's guarantee (`tier-4a-schedule-write-back.md` §2, Decision T4) is
that every `encounter_rolled` record outside the mourner's changed
sites is **byte-identical** between Run A and Run B, including
`threshold`. Lane 37's fixture
(`scenarios/test_tier4a_counterfactual.py`) forms no grudges at all —
`git grep form_grudge scenarios/test_tier4a_counterfactual.py` finds
nothing — so `_active_avoidance_pairs` would return an empty mapping in
both runs regardless of whether rule 18 is enabled, and the guarantee
holds trivially today. This isn't luck: no T4a fixture has a reason to
form a grudge, since Tier 4a's own mechanism (schedule write-back) is
triggered by kinship + death, not grievance.

**The real risk is forward-looking**, for whoever eventually builds a
*combined* Tier 4a+4b counterfactual (the vision's north-star
composition, `docs/vision-v2.2.md:12`, eventually needs both mourning
and avoidance active together). Recommendation, for that future lane's
packet: if a grudge is present in a shared A/B fixture, it must be
**identical in both runs** (same severity, same formation tick) for the
roll-identity comparison to mean anything — an avoidance effect that
differs between A and B (e.g., because the mourning reroute itself
somehow changed who could form a grudge against whom, which nothing in
this design does, but a future mechanism might) would be a second,
uncontrolled variable contaminating the "outside the mourner's changed
sites" comparison. Concretely: keep `disabled_rules` for such a test
symmetric on rule 18 (either enabled in both A and B, with identical
grudge fixtures, or disabled in both) — never disable it in only one
side the way T7 deliberately does for rule 17. This is a note for a
future packet, not a change to lane 37's delivered work.

---

## 6. Open points for the owner

- **O1 — `AVOIDANCE_PROBABILITY = 0.0`** (§1, W1). Zero (a hard
  guarantee) vs. a small nonzero placeholder (a "still possible but
  vanishingly rare" flavor). Recommend zero: the rung's "encounters...
  cease" wording reads as an absolute, and zero is what makes the
  assertion exact rather than probabilistic-and-flaky.
- **O2 — `AVOIDANCE_GRUDGE_THRESHOLD = 0.5`** (§3, W3). Placeholder;
  the ordering requirement (strictly above `forgiveness_threshold`'s
  default 0.2, so the three-stage progression is reachable) is
  load-bearing, the number isn't — same status as every other Tier-3/4a
  tunable table.
- **O3 — no bulk `grudges()` accessor on `SocialStateStore`.** The
  driver reading `self.social._grudges.values()` directly follows an
  existing precedent (cli.py, `_evaluate_accumulation`) but is a private
  attribute read from outside `social.py`; whether `SocialStateStore`
  should grow a public `grudges()` iterator (a small, generically useful
  addition, not Tier-4b-specific) is worth a line in the implementing
  lane's packet rather than silently reaching for `_grudges` again.
- **O4 — mutual-grudge collapse.** W1 folds a two-directional grudge
  (both sides holding one against the other) into one avoidance key
  with no special handling. No rung needs the distinction, but it's
  worth the owner's eyes since it's a real modeling simplification
  (asymmetric grudges produce symmetric avoidance).

## 7. Findings

- **F1 — none of the packet's premises were wrong.** All citations
  checked against the lane-36-landed code: `sample_encounters`'s
  signature and roll loop, `grudge_at`/`grudge_cooled`'s existence and
  behavior, the rule-18 stub's current registration, and lane 37's
  fixture genuinely forming no grudges.
- **F2 — no new record type needed for T4b.1**, contrary to what a
  first read of "the weight delta is visible in the trace" might
  suggest. The existing `encounter_rolled.threshold` field already
  carries exactly the information needed; the paired `rule_evaluated`
  row (§2, W2) is what makes the *reason* visible without requiring a
  schema change — matching the Tier-3/4a pattern of reusing
  `rule_evaluated`'s existing shape rather than growing the schema per
  rule.
- **F3 — the T4a.2 roll-identity interaction (§5) surfaced a
  methodological note, not a defect.** Nothing in the landed Tier-4a
  code or lane 37's fixture is at risk; the note is for whoever designs
  the eventual Tier 4a+4b combined counterfactual, so it doesn't have to
  rediscover the "keep the third variable identical across A/B" concern
  from scratch.
