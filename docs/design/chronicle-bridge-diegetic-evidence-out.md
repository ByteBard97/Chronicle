# Design prep — ChronicleBridge, a seventh slice: diegetic evidence objects

Design proposal only. Nothing here is implemented. Mirrors the precedent
of `docs/design/chronicle-bridge-hydration-out.md`, `chronicle-bridge-
avoidance-mutagen-out.md`, and `chronicle-bridge-vendor-markup-out.md`
exactly: a Python-only first cut that computes and exposes already-
computed sim state over the established poll/ack HTTP protocol, no
game-side work in this pass. Produced from `docs/research/
31-diegetic-evidence-object-placement-spike.md` (read in full before
this doc — its F5 finding is the reason this slice is scoped the way it
is below) and `docs/design/kimi-architecture-delta-audit.md`'s origin
idea, corrected against the real code: the field is `chronicle/
claims.py`'s `Evidence.strength`, not `evidentiary_strength` (the
audit's paraphrase), and it lives on a per-belief record, not a per-NPC
or per-claim one.

## 0. What this is

The same "read state some rule already produces, don't touch the rule
itself" shape as every prior "Out" slice — hydration reads `Grudge`
state, avoidance reads `Grudge.severity`+`grudge_cooled` a second way,
vendor-markup reads `Grudge.severity` a third way. This slice reads
`chronicle.claims`' belief/evidence state a fourth way: when an NPC's
belief in some claim is well-enough evidenced, something physical
appears in the game world for that NPC — a dropped weapon, a bloodied
item, a torn note — using the exact mechanism `docs/research/
31-diegetic-evidence-object-placement-spike.md` verified is `[BUILD-ON]`
at zero reverse-engineering cost: `RE::TESObjectREFR::PlaceObjectAtMe()`,
called on an NPC's own already-resolved `Actor*` (the same resolution
chain `HydrationPoller` already established via `IdentityMap`), spawning
at that actor's own live position. Report 31's F5 finding is why this is
scoped to the believer's own position rather than "the scene of the
incident": Chronicle has no home/workplace/incident-location data for
any NPC anywhere in its identity or claims model, and inventing one is
an explicitly separate, deferred design question, not something this
slice smuggles in.

## 1. Which field actually drives this, and why it isn't a literal read of `Evidence.strength`

`chronicle/claims.py`'s `Evidence` dataclass is `id, belief_id,
evidence_type, source_id, predecessor_belief_id, gamets, strength` — a
per-belief record naming one grounding or corroborating fact, not a
per-claim or per-NPC scalar. `strength` is set once at creation
(`1.0` for a fresh witness, or the teller's `confidence` for a report/
corroboration/contested-hearing) and never decays; `ClaimStore` keeps
zero or more `Evidence` records per belief in `_evidence_by_belief`,
exposed read-only via `evidence_for(belief_id)`. The aggregation itself
is not unprecedented — `resolve()`'s frozen T2.3 strength-tiebreak policy
already computes `sum(e.strength for e in
self._evidence_by_belief[...])` (claims.py:806-807) — but that sum is
explicitly, by its own docstring, "summed as-stored... decay is a
read-time concern, rule 19": a one-off tiebreak snapshot, not a
maintained or decayable quantity. There is no `evidence_strength_at()`
analogous to `chronicle.social.grudge_at` — no existing read-time-decayed
form of that sum for this slice to reuse. Building one would mean
inventing a new decay formula for `Evidence.strength` chronicle doesn't
already compute, the exact kind of invention `chronicle/hydration.py`'s
own docstring refused to do for combining `Reputation` into its rank
bucketing ("no clean combination was found... say so explicitly rather
than inventing a combination formula").

The field that already *is* a decaying, already-aggregated read of "how
well-evidenced is this belief" is `BeliefInstance.confidence`:
`witness()` sets it from `WITNESS_CONFIDENCE`, `retell()`/`resolve()`
discount it through the trust/retelling machinery, and — the load-
bearing fact for this slice — `corroborate()` (rule 7) already combines
multiple `Evidence` records' contribution into `confidence` via a
noisy-or update (`1 - (1 - decayed_existing.confidence) * (1 -
decayed_source.confidence)`), and `chronicle.claims.decay(belief,
at_gamets)` already gives it the exact same read-time, half-life-based
decay treatment `grudge_at` gives `Grudge.severity`. This slice therefore
reads **`BeliefInstance.confidence`, decayed via the existing public
`chronicle.claims.decay()`**, as its threshold signal — not a raw sum of
`Evidence.strength`. This is a deliberate substitution, named explicitly
rather than silently made: it is the "how strongly is this NPC convinced,
right now" scalar chronicle already maintains, and `Evidence` records
remain exactly what they've always been — the provenance chain
`chain_for()`/`evidence_for()` expose, feeding `confidence` rather than
being read directly by this slice.

## 2. Scope for the first (Python-only) cut

- **New module, `chronicle/diegetic_evidence.py`**, headless, no adapter
  dependency — the same "chronicle/ never imports adapter-specific
  concerns" boundary `hydration.py`/`avoidance.py`/`vendor_markup.py`
  all follow, and a new module for the same reason `avoidance.py`'s and
  `vendor_markup.py`'s own docstrings each gave for not reusing
  `hydration.py`: this reads a `BeliefInstance`, not a `Grudge`, and
  produces a plain boolean gate, not a rank bucket or a continuous
  multiplier — reusing any of the other three modules' scope would
  misdescribe what's here.
  - `should_reveal_evidence(belief: BeliefInstance, *, at_gamets: float, threshold: float = EVIDENCE_CONFIDENCE_THRESHOLD) -> bool`:
    decays `belief` via `chronicle.claims.decay(belief, at_gamets)` and
    returns whether decayed `confidence` has cleared `threshold`. A
    placeholder constant, `EVIDENCE_CONFIDENCE_THRESHOLD` (e.g. `0.6`) —
    not load-bearing precision, same tunable-not-derived status as every
    other threshold in this codebase (`hydration.py`'s
    `MILD_SEVERITY_THRESHOLD`/`SEVERE_SEVERITY_THRESHOLD`,
    `vendor_markup.py`'s `MARKUP_SEVERITY_FLOOR`). Unlike `Grudge`, a
    `BeliefInstance` has no `_cooled`-equivalent forgiveness concept, so
    there is no second condition to check here beyond the decayed
    threshold — this function is one comparison, deliberately simpler in
    shape than `is_avoiding`/`relationship_rank_for`/
    `markup_multiplier_for`, all of which also check a cooldown.
  - No change to `chronicle/claims.py` itself: `beliefs_of(holder_id)`,
    `evidence_for(belief_id)`, and `decay()` are all already public on
    `ClaimStore`/the module and already exactly what this needs — this
    slice is a pure external read, same posture as `hydration.py`
    reading `chronicle.social.grudge_at` rather than adding a method to
    `Grudge` itself. Unlike the hydration doc's own §3b, which had to add
    `SocialStateStore.reputations()` because no store-wide grudge-style
    enumerator existed for reputations, `ClaimStore` has no `beliefs()`
    equivalent to `grudges()` either — only the per-holder
    `beliefs_of(holder_id)`. This is a deliberate choice, not an
    oversight, unlike the other three slices' single `for grudge in
    state.social.grudges()` scan-and-filter: `GET /whiterun/evidence`
    instead loops `NAMED_CAST_NPC_IDS` and calls `beliefs_of(holder_id)`
    per NPC (at most 19 calls, the same named-cast size every other
    slice already bounds itself to) rather than adding a store-wide
    `beliefs()` enumerator to `ClaimStore` that nothing else needs yet.
- **New endpoints on the listener** (`adapters/skyrim/listener/
  listener.py`), gated identically to the other three (`503` without
  `--live-run`, same shared-secret auth, same `NAMED_CAST_NPC_IDS`
  restriction — only named-cast NPCs have a resolvable `Actor*` for a
  C++ consumer to call `PlaceObjectAtMe` on, exactly the same reasoning
  `_hydration_pairs`/`_avoidance_pairs`/`_vendor_markup_pairs` already
  apply):
  - **`GET /whiterun/evidence`**: for each named-cast NPC's beliefs
    (`ClaimStore.beliefs_of(holder_id)`, filtered to
    `holder_id in NAMED_CAST_NPC_IDS`), computes
    `should_reveal_evidence` at the run's current max tick and returns
    the beliefs that just crossed the threshold, diffed against a
    per-entry state machine exactly like the other three slices'
    `_HydrationPairState`/`_AvoidancePairState`/`_VendorMarkupPairState`
    (in-memory, closure-scoped, `_AWAITING_ACK_TIMEOUT_SECONDS` reused
    unchanged rather than a second copy). Response shape:
    `[{"holder_id": str, "belief_id": str, "claim_id": str}]` —
    `belief_id` is the dedupe/state key (paired with `holder_id`, which
    is redundant with the belief's own `holder_id` field but included
    for the same reason every other route's response is self-contained
    rather than requiring the C++ side to hold a side table); `claim_id`
    is included for logging/future object-kind selection even though
    the first cut's C++ consumer (out of scope here) is expected to
    spawn one fixed base object regardless of claim kind, per report
    31's recommendation 2.
  - **`POST /whiterun/evidence/ack`**: body `[{"holder_id": str,
    "belief_id": str, "outcome": "applied" | "retry"}]`. **Two-outcome,
    like avoidance/vendor-markup, not hydration's three** — a
    `PlaceObjectAtMe` call has no `no_relationship`-equivalent permanent-
    failure mode the way hydration's `BGSRelationship::GetRelationship()`
    lookup does (report 31's F1/F2 confirm both `PlaceObjectAtMe` and
    `Enable`/`Disable` are plain, unconditional, documented calls, not
    calls that can structurally fail against a specific NPC pair the way
    "no authored vanilla relationship exists" can). `applied` means the
    actor resolved and the spawn was attempted; `retry` means the actor
    was unresolvable or no game was active — the same "always temporary,
    never permanent" shape vendor-markup's own ack already established
    for the identical reason.
  - **Neither directed nor symmetric — single-key, unlike all three
    prior slices.** Hydration and vendor-markup key on a directed
    `(holder_id, target_id)` pair; avoidance keys on a symmetric,
    canonicalized pair. Evidence keys on **one NPC's one belief**
    (`(holder_id, belief_id)`) — there is no second party, per report
    31's own framing ("near the NPC it's about") resolved concretely
    here as "near the NPC who now believes it," not "near the claim's
    subject" (see §3's non-goal on this — `Claim.slots` has no
    standardized "subject" field across claim kinds, so resolving a
    claim's subject NPC generically isn't a cheap or even well-defined
    operation today; the believer's own identity and live position are
    always well-defined, which is the entire reason report 31
    recommended spawning at the NPC's own position over any
    location-modeling alternative).
  - **State machine is one-shot, with no re-offer on decay.** Unlike
    hydration's rank re-offered whenever it changes (up or down) and
    avoidance's boolean re-evaluated every poll, a `PlaceObjectAtMe`
    spawn has no natural retraction in this cut — there is no `Enable`/
    `Disable` toggle wired up here (that's report 31's *other*
    mechanism, pre-place-and-toggle, explicitly deferred, §3). So a
    `(holder_id, belief_id)` entry has exactly three states: not-yet-
    offered (absent) → `awaiting_ack` (served, timing out and re-offered
    per the existing `_AWAITING_ACK_TIMEOUT_SECONDS` convention on a
    dropped ack) → `applied` (terminal — never re-offered again, even if
    the belief's confidence later decays back below threshold; see §3).
    A `retry` ack, like the other three slices, simply forgets the entry
    so it's re-evaluated fresh next poll.
- **Tests**: `should_reveal_evidence`'s threshold boundary and decay-
  awareness (a belief whose stored confidence was once high but has
  since decayed below threshold returns `False`); the endpoint's diff/
  dedupe/timeout behavior, mirroring the other three slices' test
  suites' own fixture/style patterns exactly.

## 3. Non-goals

- **No C++ work in this cut.** The eventual consumer (`EvidencePoller.
  {h,cpp}`, presumably, following `HydrationPoller`'s exact shape and
  reusing its `IdentityMap`-based `Actor*` resolution) is real future
  work, not assumed or scaffolded here.
- **No new Mutagen content.** Report 31's recommendation 1 is exactly
  why: spawn-at-runtime via `PlaceObjectAtMe` needs no pre-authored
  `PlacedObject` record, only an existing or newly-authored base
  `MISC`/`WEAP` item to pass as the object to spawn — and even that
  choice belongs to the eventual C++/authoring pass, not this one.
- **No arbitrary-location placement.** Only NPC-live-position spawning
  (an NPC's own resolved `Actor*`'s current position, via the same
  `GetPosition()`/`PlaceObjectAtMe` combination report 31's F2/F3
  verified). Binding evidence to "the scene of the incident" is blocked
  on a real, separate, deferred data-modeling question (report 31's F5:
  Chronicle has no home/workplace/incident-location concept anywhere)
  and is not attempted here even partially.
- **No retraction/un-reveal mechanism, and no re-fire either.** Once a
  `(holder_id, belief_id)` entry reaches `applied`, this cut has no path
  back — a belief that later decays below threshold still has its
  spawned object sitting in the world, and if its confidence later rises
  back above threshold (fresh corroboration, a retelling), nothing
  spawns a second time. `applied` is a true terminal state: one object
  per belief, ever, by design, not a side effect of the state machine
  left unconsidered. This is a real, named limitation, not an oversight: fixing
  it needs the `Enable`/`Disable` toggle report 31 scoped as the
  separate pre-place-and-toggle mechanism, which this slice deliberately
  does not build (see report 31's own recommendation 3 on why that
  mechanism is blocked on location data this project doesn't have,
  independent of the retraction question).
- **No per-claim-kind object variety.** One fixed evidence object for
  the first cut (report 31's recommendation 2) — `claim_id` is exposed
  in the response for future use, not consumed by anything yet.
- **No change to `chronicle/claims.py`, `chronicle/rules.py`, or any
  existing rule.** See §4.

## 4. Rule-budget check: no new rule needed, confirmed by reading `chronicle/rules.py`

Checked directly, per this doc's own instruction not to force a
no-new-rule framing without verifying it: `chronicle/rules.py` already
registers `REPUTATION_ACCUMULATION` (rule 16, "reputation-evidence-
accumulation") as the rule that produces/consumes `Evidence` and
`BeliefInstance` state today, and `ClaimStore.witness()`/`retell()`/
`corroborate()`/`resolve()` already maintain `confidence` exactly as
described in §1 — nothing this slice needs is missing. This slice adds
**zero new rules**: it is a pure external read of `BeliefInstance.
confidence` (via the already-public `decay()`) and `beliefs_of()`,
computed the same way `hydration.py`/`avoidance.py`/`vendor_markup.py`
each read `Grudge` state without touching rule 18 or adding a rule of
their own. The project's rule budget currently sits at 19 named
rule-slots against `docs/scenario-ladder.md` §8's ~20-slot ceiling — one
slot still open (the one `docs/design/rule11-bidirectional-hysteresis.md`
would spend, pending owner sign-off) — and this slice does not touch
that count at all, spending zero of either the used or the remaining
slots. Needs no owner sign-off on rule-budget grounds, the same "zero
new rules, zero rule-budget spend" position `docs/design/
next-phases-2026-08.md` already established for its own registered-
primitives work.

## 5. Build order, once this Python half lands

1. This doc's `chronicle/diegetic_evidence.py` + listener endpoints,
   headless, buildable and testable today.
2. A short authoring decision (not a full research pass — report 31
   already verified the mechanism): pick or author the single fixed
   evidence base object (§3).
3. `EvidencePoller.h/.cpp` on the Windows build machine, following
   `HydrationPoller`'s exact pattern (main-thread task hop via
   `SKSE::GetTaskInterface()->AddTask()`, same `IdentityMap`-based
   `Actor*` resolution, same ack-POST-from-a-non-main-thread discipline)
   — real future work, not started here.
