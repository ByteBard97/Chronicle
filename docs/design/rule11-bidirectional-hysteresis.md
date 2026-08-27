# Design prep — rule 11, bidirectional hysteresis (escalate/de-escalate)

**Design-ready, NOT approved for implementation** — spending the ladder's
last rule-budget slot (or amending rule 11 in place) needs the project
owner's explicit go-ahead before any code lands; this doc exists so that
decision can be made in one read.

**Status:** design-ready, unimplemented. No code changed to produce this
doc; `chronicle/rules.py`, `chronicle/driver.py`, `chronicle/social.py`
are read-only inputs, not touched.

Sources: `docs/research/23-v03-hysteresis-and-action-verbs.md` Part A
(the literature survey — no purpose-built bidirectional model exists
anywhere searched; the transferable pattern is generic control-theory
hysteresis, a dead band plus a dwell requirement); `docs/design/
next-phases-2026-08.md` §2 (the open problem statement: rule 11's latch
"trips but never untrips... needs separate entry/exit thresholds");
`chronicle/rules.py`'s `AccumulationThresholdRule` (rule 11's real,
current implementation, read in full); `chronicle/driver.py`'s
`_evaluate_accumulation`/`_escalation_latched` (rule 11's real call
site); `chronicle/claims.py`'s `decay()`/`RUMOR_FORGOTTEN_GIST_THRESHOLD`
(the decay-at-read idiom this design reuses); `chronicle/social.py`'s
`grudge_at`/`grudge_cooled`/`AVOIDANCE_GRUDGE_THRESHOLD` (rule 18's own,
already-shipped dead band, cited for its real numeric ratio);
`scenarios/test_tier3_accumulation.py` (T3.1, rule 11's only scenario
coverage, read in full); `docs/scenario-ladder.md` §8 (the rule-budget
table and the O4 9+10 consolidation precedent).

## 0. The premise this doc corrects before proposing anything

Two things read from the actual code change what "bidirectional
hysteresis on rule 11" can honestly mean. Getting these wrong would make
the rest of this doc unimplementable as written.

**(a) Rule 11's threshold is not a fixed constant to "match exactly."**
Unlike rule 18's `AVOIDANCE_GRUDGE_THRESHOLD = 0.5` (one constant, one
place), rule 11's threshold is caller-supplied per grievance kind via
`Driver`'s `accumulation_thresholds: Mapping[str, tuple[str, int]]`
(`driver.py:223`) — T3.1's fixture passes `{"theft": ("victim", 4)}`.
There is no single number to preserve; "the escalation threshold stays
as-is" means **the up-threshold stays exactly this caller-supplied
per-kind value, unchanged in meaning or type**, not that some named
constant gets frozen.

**(b) Rule 11's accumulator, as built today, is unconditional and
therefore monotonic — and that has to change to make de-escalation mean
anything.** `_evaluate_accumulation` counts *every* belief the holder has
whose claim kind matches and whose victim slot names the holder
(`driver.py:1516-1521`), with no decay check. Beliefs are never
un-learned, so this count never falls; the rule's own docstring says so
explicitly ("since the accumulator is monotonic ..., doctrine-3
hysteresis reduces to that latch"). A de-escalation threshold compared
against a quantity that structurally cannot decrease is not a design,
it's dead code — the count can never again drop below any positive
down-threshold.

The fix stays inside rule 11 and reuses machinery already in this
codebase, not new state: **redefine the accumulator, in bidirectional
mode only, as the count of contributing beliefs that have not yet
decayed to "forgotten."** `chronicle/claims.py`'s `decay(belief,
at_gamets)` and `RUMOR_FORGOTTEN_GIST_THRESHOLD = 0.05` already implement
exactly "has this belief's gist decayed below the forgotten floor" for
the rumor-stage machine (`stage_at`, `claims.py:292-307`) — this design
applies the same decayed-`gist_strength` check directly to each
contributing belief (no `RumorState` needed; grievance beliefs never
construct one, and requiring one would be new state, which this doc
rules out). Four old, half-forgotten thefts stop counting toward the
escalation the same way a five-year-old grudge stops gating avoidance —
same idiom, same file, same threshold constant, applied to a different
rule's read path. This is the one point where this design **must**
diverge from a literal "same accumulator, new threshold" reading of the
task, and the divergence is load-bearing: without it, there is nothing
for the de-escalation threshold to ever cross.

## 1. The exact mechanism

Bidirectional mode is opt-in, construction-time, per grievance kind —
`accumulation_thresholds`'s value type grows from `tuple[str, int]`
(victim slot, up-threshold) to a small frozen dataclass:

```python
@dataclass(frozen=True)
class AccumulationSpec:
    victim_slot: str
    up_threshold: int
    down_threshold: int | None = None   # None = today's one-directional latch, unchanged
    dwell_ticks: int = 0                # ignored unless down_threshold is set
```

Existing callers passing `("victim", 4)` keep working unchanged only if
the driver accepts the old tuple shape as sugar for
`AccumulationSpec(victim_slot="victim", up_threshold=4)` — a thin
normalization at construction time, not a breaking API change. This
mirrors `retell()`'s `trust: float | None = None` idiom (rule 20):
omitting the new fields reproduces exactly today's behavior.

**Escalation threshold — unchanged in meaning.** `up_threshold` is
whatever the caller already supplies today (4 for the T3.1 theft
fixture). No new number is proposed here; this is deliberate, since
T3.1's every assertion is pinned to the existing accumulation semantics
at `up_threshold=4` (see §4).

**De-escalation threshold — `down_threshold`, recommended caller-supplied
value `max(1, round(0.4 * up_threshold))`.** The dataclass field itself
defaults to `None` (one-directional, today's exact behavior, §2's feature
gate) — this formula is not an automatic fallback the driver computes,
it is the recommended value for a caller opting a grievance kind into
bidirectional mode to pass explicitly, the same way `AVOIDANCE_GRUDGE_THRESHOLD`
is a named recommended constant rather than something `Driver` derives on
its own. For `up_threshold=4` this gives `down_threshold=2`. The 0.4 ratio is not invented for this doc: it is
rule 18's own already-shipped dead band, read directly from
`chronicle/social.py` and `chronicle/driver.py` — `AVOIDANCE_GRUDGE_THRESHOLD
= 0.5` (up) vs. `forgiveness_threshold`'s default `0.2` (down) is a
0.2/0.5 = 0.4 ratio, and `docs/design/tier-4b-avoidance.md`/lane-43's
work packet record the "strictly above forgiveness_threshold" ordering
as load-bearing for that rule. Reusing the one dead-band ratio this
project has already shipped and tuned, rather than inventing a second
one, is the reasoning; `max(1, ...)` exists so `down_threshold` is never
0 — 0 would mean "never de-escalate until every single grievance belief
is fully forgotten," which collapses the dwell mechanism into "wait
forever" for any kind with a slow gist half-life, and is a degenerate,
not a conservative, choice.

**Dwell requirement — proposed `dwell_ticks=24` (one game-day; 1 tick =
1 game-hour, ADR-0010).** Chosen relative to the one other named
duration constant in this exact subsystem, `MOURNING_DURATION_TICKS = 72`
(`driver.py:131`, three game-days): dwell should be shorter than a
full narrative schedule-rewrite block (mourning is an authored,
multi-day state), but long enough that ordinary encounter-timing noise
— the fixture's own `encounter_probability` roll — can't produce a
single lucky quiet tick that instantly untrips a latch formed over
multiple thefts. Not a literature-derived number (research/23 §"BUILD-ON"
explicitly declines to supply one: "N is a tuning constant, not a
literature-derived one"); this is the same "documented placeholder,
real reasoning, not load-bearing precision" status `social.py`'s own
grudge half-lives and `forgiveness_threshold` carry.

**The evaluation-trigger problem, and the ruling that resolves it.**
`_evaluate_accumulation` runs *exactly where a matching belief forms*
(R5; `driver.py:1499`'s own docstring: "never per-tick"). That is fine
for the up-direction — a new theft is exactly the event that should
re-check escalation. It is fatal for the down-direction: nothing about
elapsed time alone triggers a re-evaluation, so if no new grievance
belief of that kind ever forms again, a dwell-counted release can never
fire — the mechanism would be unreachable as designed.

Two candidates were considered:

1. **Per-tick evaluation, bidirectional mode only.** Add a tick-loop hook
   (`_run_tick`, `driver.py:1101`) that, only for grievance kinds with
   `down_threshold` set and an active latch, recomputes the not-yet-forgotten
   count and increments/resets a per-(holder, grievance_kind) dwell
   counter. Release fires (and the latch clears) once the counter reaches
   `dwell_ticks` consecutive ticks at or below `down_threshold`. This
   literally implements "how many ticks below the de-escalation threshold
   before the latch releases," matching the task's own framing, at the
   cost of breaking R5's "never per-tick" invariant — but **only for
   rules with `down_threshold` set**; the existing one-directional kinds
   (and every kind with the flag off) keep the exact current
   formation-triggered-only evaluation.
2. **Lazy watermark, evaluated at read time** (the `grudge_cooled`/
   `stage_at` idiom, gestured at by research/23 §"BUILD-ON": "since a
   recorded `gamets` watermark"). Record the gamets of the last
   formation-time evaluation where the recomputed count was still above
   `down_threshold`; release is a pure function of `at_gamets - watermark
   >= dwell_ticks * TICK_HOURS` computed on read, no tick-loop hook at
   all. This preserves R5 exactly (still only evaluated at formation, or
   on demand) but changes "dwell" from a literal tick count to a duration
   threshold, and — because the down-crossing itself happens continuously
   via decay, not at a formation event — computing the *watermark itself*
   exactly would require inverting the exponential decay curve
   (`elapsed = half_life * log2(gist_0 / RUMOR_FORGOTTEN_GIST_THRESHOLD)`)
   rather than reading a recorded fact, which is a materially more
   complex derivation than every other decay-at-read function in this
   codebase (`grudge_at`, `decay`, `stage_at` all decay a *stored* value
   forward, none of them solve for a crossing time).

**Ruling: option 1 (per-tick, bidirectional-mode-only).** It is simpler,
matches the task's literal "dwell count... consecutive ticks" framing,
and its R5 violation is narrowly scoped (opt-in, per-kind, and the
existing one-directional path is provably untouched — see §4). Option 2
is recorded, not chosen, because its exact implementation is
disproportionately more complex for a placeholder-tunable dwell value
that isn't claiming precision in the first place.

## 2. Where this lives in the codebase

**In rule 11, in place — not a new rule.** This is the second premise
correction: this design does not add a new named mechanism. It extends
`AccumulationThresholdRule.evaluate()` to accept an optional second
input shape (a `down_threshold`/`dwell_count` pair alongside the
existing `count`/`threshold`/`latched`), and extends
`_evaluate_accumulation`'s driver-side hook to (a) redefine the
accumulator per §0(b) only when `down_threshold` is set, and (b) add the
per-tick release check per §1 only when `down_threshold` is set. No new
`record_type`, no new event kind, no new rule `name` or `tier` constant
— `ACCUMULATION_THRESHOLD` stays the one rule name, the registry still
lists exactly the same 20 entries. This mirrors rule 20's own shape
(`retell()` gaining an optional `trust` parameter, disabled-by-default,
`None` reproducing prior behavior exactly — `docs/design/
trust-discounted-retelling.md` §2) at the parameter level, but is closer
in *rule-budget kind* to the O4 ruling: 9 and 10 stayed one registered
rule name because they wrap the same underlying mechanism
(`claims.stage_at()`) end to end; here, escalate and de-escalate are two
directions of literally the same accumulator/latch, evaluated by the
same rule object, under the same name. A new rule would mean a second
`ACCUMULATION_THRESHOLD`-shaped entity competing for the ladder's last
slot alone, which this design does not need and should not claim.

The feature gate is the existing `accumulation_thresholds` mapping
itself (§1): a grievance kind with `down_threshold=None` (or using the
old bare-tuple sugar) reproduces today's exact one-directional behavior;
bidirectionality is opt-in per kind, matching this project's own
established pattern for every prior optional-rule extension (rule 20's
`disabled_rules`/`trust=None` default; rule 18's `pair_thresholds`
override defaulting to the plain `AVOIDANCE_GRUDGE_THRESHOLD`).

## 3. Rule-budget accounting

**No ceiling raise. This is "rule 11, amended," landing at the existing
18/20 slot rule 11 already occupies** (`docs/scenario-ladder.md` §8's
table, with the O4-recorded 9+10 merge already accounted for and rule 20
landing at the ceiling per `docs/design/trust-discounted-retelling.md`
§3). The precedent to cite is O4 itself: rules 9 and 10 stayed one
registered rule name because both wrap the same underlying mechanism
(`stage_at()`) — the same reasoning applies here, more directly, since
this doesn't even merge two previously-distinct rules, it adds a second
*direction* of evaluation to one rule that already exists, under its
existing name. `docs/scenario-ladder.md` §8's own closing line —
"any proposed rule not on this table is a scope discussion, not a
commit" — is precisely the reason to be explicit that this proposal adds
**no row** to that table; rule 11's existing row's semantics grow, its
identity does not change.

The contrast worth naming: rule 20 (trust-discounted retelling) *was* a
new rule name landing exactly at the ceiling, so despite the similar
`Optional[...] = None`, disabled-by-default parameter shape, it is not
the precedent for a "no new slot" argument — it's the precedent for the
default-preserving-parameter *idiom*, not the budget accounting. The O4
merge is the budget precedent.

## 4. Test/regression plan

**Existing coverage, read in full:**

- `scenarios/test_tier3_accumulation.py::test_t31_serial_theft_escalates_exactly_once_and_only_via_encounters`
  — asserts (a) `rule_evaluated` rows' `inputs["count"]` == `[1, 2, 3]`
  exactly on thefts one through three (line 129); (b) `fired=False` on
  all three (line 130); (c) exactly one `escalation_warning` event and
  one `threshold_crossed` trace record on the fourth theft, with
  `count == threshold == 4` (lines 136-150); (d) after the tick loop
  runs (48 ticks) and a fifth theft is injected, the latch holds —
  `inputs["count"] == 5`, `inputs["latched"] is True`, `fired is False`
  (lines 173-176); (e) propagation to the peer merchant happens only via
  encounters, never a broadcast.
- `scenarios/test_tier3_accumulation.py::test_t31_reconstruction_parity_no_double_fire_on_replay`
  — asserts replay from a keyframe reconstructs exactly one escalation
  claim, never a second one, and that the reconstructed peer's belief
  survives replay.
- `chronicle/tests/test_rules.py` — has exactly one
  `ACCUMULATION_THRESHOLD`-touching assertion, `assert
  registry.enabled(ACCUMULATION_THRESHOLD)` (line 98), which only checks
  registry construction, not `evaluate()`'s input shape. A repo-wide grep
  (`grep -rln "AccumulationThresholdRule" chronicle/tests/ scenarios/`)
  found no test anywhere that constructs `AccumulationThresholdRule`
  directly or calls `.evaluate()` with a hand-built `RuleContext` —
  **finding, not a TODO for the implementer**: nothing outside
  `_evaluate_accumulation`'s own driver call site depends on
  `evaluate()`'s current three-key (`count`/`threshold`/`latched`) input
  shape, so widening it with optional `down_threshold`/`dwell_count`
  keys cannot break an existing unit test — only the two scenario tests
  above (which go through the driver, not `evaluate()` directly) are live
  regression surface.

**Backward-compatibility discipline — two separate gated changes, both
required, matching this project's "`None` byte-identical to before"
standard (rule 20's own precedent):**

1. **The accumulator definition itself must stay gated.** With
   `down_threshold=None` (T3.1's fixture, unchanged), `_evaluate_accumulation`
   must keep counting *every* matching belief unconditionally — the
   not-yet-forgotten filter from §0(b) applies **only** when
   `down_threshold` is set. This is the more easily missed of the two
   gates: T3.1's fifth-theft assertion (`count == 5` at tick 24,
   line 174) would become sensitive to `GIST_DECAY_HALF_LIFE` (1440
   ticks) if the not-yet-forgotten filter applied unconditionally — it
   doesn't fail today only because 24 ticks is far short of the
   half-life, which is exactly the kind of latent, timing-dependent
   coupling "gate the accumulator, not just the release path" is meant
   to prevent.
2. **The release/dwell path must stay gated.** With `down_threshold=None`,
   no per-tick hook runs at all for that grievance kind — the tick loop's
   added work is skip-checked per kind, not merely a no-op inside the
   loop, so T3.1's tick-by-tick trace shape (which rows appear, in what
   order) is unaffected byte-for-byte.

**New scenario tests this design requires before landing (not written by
this doc — a proposal for the implementing pass), with fixture timing
that actually exercises the band (see §5's arithmetic — this is not
optional tuning, a naively-spaced fixture would be vacuous):**

- A T3.1-twin fixture whose four contributing thefts are seeded at
  gamets staggered by half-life-scale gaps (e.g. 0 / 2000 / 4000 / 6000,
  against `GIST_DECAY_HALF_LIFE = 1440`), not T3.1's original ~1-tick
  spacing, so beliefs cross the forgotten floor one at a time rather than
  within hours of each other (§5). With `down_threshold=2`,
  `dwell_ticks=24`: assert the not-yet-forgotten count steps 4 → 3 → 2
  at the expected gamets, the latch stays set through the count==3
  interval, dwell starts only once count reaches 2 (~gamets 8220), and
  the latch actually releases ~24 ticks later with no new theft in that
  window. A sixth theft after release must be able to re-trigger a fresh
  escalation (proving the latch is genuinely bidirectional, not merely
  delayed). Seeding via explicit staggered gamets (or a chain of
  `retell()`-derived beliefs, which start `gist_strength` at ×0.95) is
  necessary — running ~8000 real tick-loop iterations to reach this
  arithmetically is not a reasonable test runtime.
- A dwell-interruption test, using the same staggered fixture: once count
  reaches `down_threshold` and the dwell counter has advanced partway
  (`dwell_ticks - 1` ticks), inject one more theft. Assert the
  not-yet-forgotten count jumps back above `down_threshold` and the
  dwell counter resets to zero (not merely pauses) — the exact
  band-occupied-then-interrupted scenario §5 walks through.
- A regression run of the full existing suite (T3.1's two tests plus the
  `test_rules.py` registry check) with `down_threshold=None` on every
  existing `accumulation_thresholds` entry, asserting trace output is
  byte-identical to pre-change output — the same discipline `docs/design/
  trust-discounted-retelling.md`'s landed commit used (312/312 passing,
  disabled-by-default reproducing exact prior behavior).

## 5. Minimal concrete example: the flicker de-escalation must not introduce

**Today's code cannot flicker — that is not the bug being fixed.**
Today's accumulator is unconditional and monotonic (§0(b)): it only ever
counts up, the latch only ever trips once, and it stays tripped forever.
There is no oscillation to fix in the shipped code. The risk this
section is about is a different one: **the band and dwell are what make
it *safe to add* de-escalation at all** — a naive single-threshold
de-escalation (release the instant the not-yet-forgotten count drops
back to `< up_threshold`, no separate down-threshold, no dwell) would
introduce exactly the flicker bug bidirectional hysteresis exists to
prevent. This section walks the real mechanism, corrected from an
earlier draft that wrongly modeled the integer count as a decaying float
and wrongly assumed decay alone could push the count back up (it can't —
`_decay` runs strictly downward from a stored value; only a **new**
belief forming can raise the count; between formation events the count
is monotone non-increasing).

**The naive single-threshold failure mode.** Suppose de-escalation were
built as "release when not-yet-forgotten count `< 4`, re-escalate when it
reaches 4 again" — no separate down-threshold, no dwell. A merchant's
count decays from 4 to 3 (one old theft belief crosses the forgotten
floor) — release fires. The same recurring thief strikes once more —
count returns to 4 — re-escalation fires. That single new theft alone is
enough to flip the latch, because the release boundary and the
escalation boundary are the *same* number: one theft is exactly the gap
between them. Each occurrence of "one theft, sometime after one old
belief decays out" toggles the latch again, each toggle emitting a fresh
`threshold_crossed` record and a fresh `escalation_warning` claim
propagated to the peer merchant on the next encounter — real, visible
behavioral noise for one continuous grievance history.

**Why the proposed values (`up_threshold=4`, `down_threshold=2`,
`dwell_ticks=24`) prevent it.** The dead band means release requires
falling *two* steps below the escalation point (4 → 2), not one — a
single new theft (count 2 → 3) cannot by itself cross back up to 4, so
it cannot alone re-trigger escalation, and because it also can't push
the count as far as `down_threshold` on its own from below, one theft
near the release boundary no longer toggles anything. `dwell_ticks`
covers the remaining case the band alone doesn't: a theft landing
*while* the count is already sitting at `down_threshold`, shortly before
release would otherwise fire — the 24-tick dwell requirement means that
theft (which raises the count back above 2) resets the dwell counter to
zero rather than merely arriving too late to matter, so a determined
adversary can't game a near-boundary count into oscillating even at the
band's edge.

**Making the band actually reachable — the fixture consequence.** This
only works if the not-yet-forgotten count actually spends time sitting
at 2 rather than stepping straight past it. Run the real numbers for
T3.1's fixture as originally spaced (four thefts roughly one tick
apart): `GIST_DECAY_HALF_LIFE = 1440` ticks, floor
`RUMOR_FORGOTTEN_GIST_THRESHOLD = 0.05`, so a belief crosses the floor at
elapsed ≈ 1440 · log₂(1/0.05) ≈ 6220 ticks after formation. Four beliefs
formed within an hour of each other all cross that floor within roughly
the same hour of each other too — the count steps straight 4 → 0, never
touching `down_threshold=2` at all, and the dwell counter never gets a
chance to start or reset. **The band only does anything for grievance
histories whose contributing beliefs are staggered by roughly
half-life-scale gaps** — which is realistic for genuine "recurring
grievance over weeks" cases (the CK-demotion scenario this design
targets) but means §4's new regression fixture cannot reuse T3.1's
tight ~1-tick spacing; it must seed beliefs at gamets spread by
thousands of ticks (e.g. 0 / 2000 / 4000 / 6000) to actually occupy the
band, exactly as §4 now specifies.

With that staggered fixture: count crosses to 3 at ~gamets 6220, to 2 at
~gamets 8220 — dwell starts here. If a fifth theft lands before gamets
8244 (dwell_ticks=24 later), the count returns to 3, the dwell counter
resets to zero, and the latch stays set — no release, no flicker,
exactly what the dwell-interruption test in §4 asserts. If no new theft
arrives, the latch releases cleanly at ~gamets 8244, and a later,
genuinely new theft is then free to re-trigger a fresh escalation from
scratch (a new `threshold_crossed` record, a new warning claim) — the
CK-style "the grievance can genuinely cool, and can genuinely flare up
again" behavior `docs/design/next-phases-2026-08.md` §2 asks for,
delivered without the naive scheme's one-theft toggle.

## 6. Non-goals for this doc

- Rule 18's avoidance dead band (`AVOIDANCE_GRUDGE_THRESHOLD`/
  `forgiveness_threshold`) is not changed by this proposal — it already
  has a form of hysteresis (an up-threshold and a separate, lower
  per-grudge floor) and is cited here only as the numeric precedent for
  §1's 0.4 ratio, never as something this doc modifies.
- No change to `chronicle/social.py`'s `Grudge`/`grudge_at`/
  `grudge_cooled` — this design's bidirectional accumulator is built
  entirely from `chronicle/claims.py`'s existing belief-decay primitives
  (`decay()`, `RUMOR_FORGOTTEN_GIST_THRESHOLD`), not from grudge state,
  because rule 11 operates on witnessed-belief counts, not grudge
  severity; the two mechanisms stay structurally independent, matching
  `docs/v0.1-spec.md` rule 18's "obligations, grudges, and reputation
  stay three separate record kinds" discipline extended to "grievance
  accumulation and grudge severity stay two separate signals."
- Any relationship-*category* label (Friend/Rival/Nemesis-style
  crystallization) — `docs/design/trust-discounted-retelling.md` §4
  already named this out of scope for that doc, and it stays out of
  scope here too; this design only makes rule 11's own latch releasable,
  it does not introduce a category system for a downstream consumer to
  read.
- Implementation. This doc is research/design-prep only, per this task's
  explicit charter — no code in `chronicle/rules.py`, `chronicle/driver.py`,
  or anywhere else was touched to produce it, and none should be until
  the project owner has read and approved (or rejected) this doc.
