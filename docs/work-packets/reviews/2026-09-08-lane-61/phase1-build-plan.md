# Phase 1 build plan — lane dispatch, post lane-61 rulings

Status: **reviewed (Kimi + advisor, 2026-09-10) — dispatch-ready modulo
the two owner items below (O4, and the two long-carried loose ends noted
in the handoff).** Built directly from `social-mechanics-v3-foundation.md`
§10's proposed lane split, **revised 2026-09-10 to match `rulings.md`**
(written 2026-09-09, a day after this plan's first draft) rather than the
ruling sheet's original recommendations — the first draft had drifted from
what was actually ruled on O7, the `driver.py` claimant count, sequencing,
O6's mechanism, and O4/lane 6's status. See `rulings.md` for the rulings
themselves; O1/O2/O3/O5/O6/O7 are settled there (Kimi already cross-checked
them, task `kfdgwusze`) and are not up for re-litigation in this review —
this plan is what's under review, specifically the lane boundaries, the
lane 1↔2 mutual-dependency resolution, and `driver.py` sequencing under
four claimants.

## What changed from §10's original split

- **O3 (Dread folds into `crystallization.py`):** lane 4 is gone as a
  separate lane. Dread ships inside lane 1's module.
- **O4 (STC ladder) — still blocked, not unblocked.** O4 recommends
  splitting menu construction (Phase 1) from line-rendering call shape
  (Phase 2), but `rulings.md` is explicit that this recommendation has
  **not been ruled on** — it's an ADR-0011 §3 amendment, an owner-signature
  item, not something this session or a build plan can authorize. Lane 6
  is drafted below on the assumption the split is eventually adopted, but
  it does not start until that ruling lands.
- **O2 (predicate grammar decided) + O6 (rate-limit state, caller-
  assembled):** fold into lane 2's scope as concrete field/format
  decisions. O6's mechanism, corrected from this plan's first draft: as
  ruled, `last_fired` is a **pre-filter `Driver` applies before a
  candidate reaction reaches the registry**, not a field passed into
  `ReactionContext` — the registry never sees rate-limited-out candidates
  at all. It also needs a save/load keyframe entry (no underlying store
  to recompute it from, unlike `_grudge_severities`/`_avoidance_
  thresholds`).
- **O1, O5:** no lane-count change, concrete algorithm/field decisions
  inside lane 1.
- **O7, corrected:** the ruling sheet's "nothing to build" conclusion was
  wrong (rulings.md, Kimi finding). Lane 1 must add a
  `Driver.form_fondness()` wrapper mirroring `Driver.form_grudge()`
  (`driver.py:844`) that emits a `fondness_formed` trace record, including
  its `driver.py` call site(s) (mirroring `:922`/`:1070`). This makes lane
  1's file boundary `chronicle/crystallization.py` **plus** a `driver.py`
  touch, not just the one file.
- **`driver.py` contention now has four claimants, not three**: lane 1's
  new `form_fondness()` call site (see O7 above), lane 2's registry call
  site + `last_fired` writeback, lane 3 (gossip-writeback + kin routing),
  and lane 5 (pacing director's per-tick sweep hook). All four need
  explicit sequencing — see the sequencing section below.
- **Separately, a lane 1↔2 mutual dependency is still unresolved**
  (`rulings.md` dispatch blocker #1): lane 1 needs lane 2's `temperament`
  static fixture for Dread's valence conversion; lane 2 needs lane 1's
  `sentiment_label` output shape. This is a design-sequencing question,
  distinct from the `driver.py` file-contention question above — "any
  serialization order is correct" (below) applies only to the `driver.py`
  touch-point ordering, not to this cycle. **RULED, see rulings.md's
  2026-09-10 addendum:** lane 2 owns the `ReactionContext` contract, so
  it also owns specifying the `sentiment_label`/`sentiment_source_
  belief_id` shape, frozen at the same time as the `temperament`
  fixture; lane 1's `crystallize()` conforms to that frozen shape.

## Lanes

1. **Sentiment/Crystallization + Dread** — `chronicle/crystallization.py`
   **plus a `driver.py` touch (see O7 below — this is a real file-boundary
   addition, not optional).**
   - `Fondness` record + constructor, with O5's field-shape decision:
     constructor allows `holder_id == target_id` (mirrors `form_grudge()`'s
     existing self-victim bypass). No `Guilty` semantics designed —
     field-shape only.
   - `crystallize()` derived labeling with O1's hysteresis rule: a pair
     must decay through neutral before flipping Friend↔Rival (opposing
     row's decayed value must fall below its own threshold first).
   - Dread as a derived-label function over the same `{Grudge, Fondness}`
     stores, same module, per O3.
   - **O7, corrected:** no `FondnessFormed` *Event* subclass, matching the
     (lack of) `GrudgeFormed` precedent — but grudge formation *is* logged
     as a trace record, not an Event, and Fondness needs the same. Add
     `Driver.form_fondness()` mirroring `Driver.form_grudge()`
     (`driver.py:844`) that emits a `fondness_formed` trace record
     (mirrors `driver.py:855`, consumed by `framelog.py:931`), plus its
     `driver.py` call site(s) mirroring `form_grudge()`'s
     (`driver.py:922`, `:1070`). This is a required deliverable of this
     lane, not an optional nice-to-have.
   - No reaction rendering yet — that's lane 2's job.
   - **Dependency, corrected:** Dread's valence conversion reads
     `temperament.boldness` (lane 2's X3 static fixture data). Folding
     Dread into lane 1 (O3) moved this dependency, it didn't remove it —
     lane 1 still depends on lane 2 for Dread specifically, even though
     Crystallization proper does not.

2. **Reaction-context contract + registry core** —
   `chronicle/reactions.py`.
   - `ReactionContext`/`ReactionResult`/`Reaction` protocol/
     `ReactionRegistry`, temperament as static fixture data, external
     data-file loading.
   - O2's predicate grammar: flat implicitly-ANDed clause list over
     `event.*`/`sentiment_label`/`temperament.*`/`mood.*`, `eq/neq/gt/
     gte/lt/lte` on numerics, equality-only on strings/enums, one
     non-recursive `any_of` OR-block per rule, required integer
     `priority` field (validated at load, no inferred specificity),
     tiebreak priority-desc → file load order → rule name. Loud logged
     validation failure on any unresolvable field reference (e.g. a
     `mood.*` reference, since mood ships always-empty in v1) — never a
     silent fallback. **File enumeration at load time must be explicitly
     sorted alphabetically by filename** (rulings.md O2, Kimi finding) —
     left to directory-listing order, the load-order tiebreak becomes
     platform-dependent, which collides with the byte-identical-logs
     doctrine.
   - **O6's rate-limit state, corrected — this is a pre-filter, not a
     context field.** `last_fired: Mapping[tuple[str,str], float]`
     (keyed by ordered `(observer_id, subject_id)`, not a symmetric
     `frozenset` pair) is read by `Driver` to gate whether a pair is even
     eligible for reaction evaluation this tick — it is never passed into
     `ReactionContext` as an evaluable field, and the registry stays pure.
     `last_fired` must also round-trip through save/load — **ruled
     required in rulings.md O6, not optional.** Precedent framing
     corrected (Kimi review, checked `framelog.py:234-279` directly):
     it's the **first Driver-owned field** in the keyframe, not an
     instance of an existing convention — today's `serialize_state`/
     `load_state` only serialize *store* state (claims/social/schedule),
     so this is a genuine signature extension, not a copy-paste of a
     precedent. (Kimi separately noted post-keyframe `last_fired` values
     are also reconstructible on replay from `reaction_evaluated` fired
     records — the same reason `_grudge_severities`/`_avoidance_
     thresholds` skip the keyframe — which is *why* the "no store to
     recompute from" rationale needed the correction above; it doesn't
     reopen the keyframe requirement itself, which stands as ruled.)
   - **File boundary, corrected — this is bigger than "reactions.py"
     alone:** §2 X2 requires every evaluated reaction to emit a
     `reaction_evaluated` trace mirroring `Driver._evaluate_rule()`
     (`driver.py:366-401`), which means `Driver` must invoke the
     registry per tick *and* write back `last_fired` when a reaction
     fires. That call site and writeback are lane 2's responsibility,
     not a separately-assignable "sweep" — there's no `last_fired` sweep
     to write until lane 2's registry exists to populate it from. Lane
     2's file boundary is `chronicle/reactions.py` **plus** the
     `Driver`-side call site/writeback in `driver.py`.
   - Depends on lane 1 for the `sentiment_label`/`sentiment_source_
     belief_id` input shape.

3. **Gossip-writeback + kin-priority routing** — one lane,
   `chronicle/propagate.py` + `driver.py`'s trust-discount path.
   Independent of lanes 1-2. **`driver.py` contention: see sequencing
   note below.**

4. **Secrets/Hooks leverage** — `chronicle/leverage.py`, `Hook` record
   only. Depends on lanes 1-2 for detonation effects; the record itself
   can start independently.

5. **World-event pacing director** — `chronicle/pacing.py`. Independent
   of lanes 1-4; needs its own `rng.py` purpose and a new per-tick sweep
   hook wired into `Driver.__init__`/`_run_tick`. **`driver.py`
   contention: see sequencing note below.**

6. **STC conversational ladder (deterministic menu construction only)** —
   **still blocked, not unblocked.** O4 only *recommends* splitting menu
   construction (Phase 1, this lane) from line-rendering call shape
   (Phase 2, ADR-0011's actual concern) — it doesn't authorize the split.
   Scope, if/when unblocked, is strictly piece (1): a deterministic engine
   query over parameterized intents (`confront, rumor_id=X`,
   `boast, quest_id=Y`) that produces the player's menu, no LLM call, no
   line-rendering call shape. **Blocked on:** ADR-0011 §3 being formally
   amended first — an owner-level ruling, not a pre-lane chore — this lane
   doesn't start writing code, let alone get dispatched, before that
   lands.

## `driver.py` sequencing (four claimants, not three)

Lane 1's new `form_fondness()` call site (O7), lane 2's own `Driver`
wiring block (registry call site + `last_fired` writeback — not a
standalone "sweep," it can't land on its own since there's nothing to
populate `last_fired` from until lane 2's registry exists), lane 3
(gossip-writeback), and lane 5 (pacing) all touch `driver.py`. There are
no dependency edges between these four touch-points *as `driver.py`
edits* (gossip-writeback is independent of lanes 1-2; pacing is
independent of lanes 1-4) — so *at the file-contention level* any
serialization order is correct, this is purely a conflict-minimization
choice, the same pattern lanes 19→26 used. This does **not** resolve the
separate lane 1↔2 design dependency noted above (lane 2 needs lane 1's
`sentiment_label` shape regardless of which `driver.py` edit lands first)
— that's a design-sequencing question, not a merge-conflict one.

Recommended order: lane 1's `form_fondness()` call site first (lane 2
already depends on lane 1's output shape regardless of `driver.py`
contention, so landing lane 1 first is a design requirement, not just a
tie-break), then gossip-writeback (lane 3, self-contained), then lane 2's
Driver wiring block, then pacing (lane 5, largest, benefits from a clean
base).

## Before any lane starts

1. **Done, 2026-09-10:** sent to Kimi for a technical pass (verified
   against `driver.py`/`events.py`/`framelog.py`/`social.py` directly,
   not just the documents) plus an advisor pass. Findings folded in above
   and in `rulings.md`'s addendum. Kimi confirmed the lane split, file
   boundaries, and four-claimant `driver.py` sequencing sound against the
   real code (dispatch blocker #3, closed) and caught three real gaps,
   all fixed in this document: O2's missing sorted-load-order requirement,
   dispatch blocker #4's dropped event/trace leftovers, and an
   overstated persistence precedent on `last_fired`. The lane 1↔2 cycle
   (dispatch blocker #1) is now ruled — see `rulings.md`'s addendum.
2. **O4 is still the owner's to rule on** (ADR-0011 §3 amendment) — lane 6
   stays blocked until then; nothing else in this plan depends on it.

## Still needs an owner ruling, not just a lane assignment

- **Amending ADR-0011 §3** (O4's premise for lane 6 existing at all) is
  itself an owner-level decision, not a pre-lane chore this plan can
  just schedule — O4 *recommends* the amendment, it doesn't authorize
  it. Lane 6 is blocked on that ruling, not on someone doing the edit.

## Not resolved by this plan (unchanged from §10/ruling sheet)

- STC ladder's Phase-2 half (line-rendering call shape, confirm-vs-
  autoplay, free-form input) — deliberately deferred, not this plan's
  job.
- Body-model / embodiment work — Phase 2/3, unrelated to this plan
  (see report 57 / the Countenance repo for that thread; not part of
  Phase 1 dispatch).
- **`rulings.md` dispatch blocker #4 — §8's event/RNG table leftovers.**
  `HookCreated`/`HookSpent` (lane 4), `OffScreenEventFired`/`Suppressed`
  and a possible `DREAD_REPORT_DECISION` (lane 1/5), and
  `PACING_BUDGET_SPEND` (lane 5) are explicitly *not* ruled yet — fine to
  rule per-lane when lanes 1, 4, and 5 are actually dispatched, but flagged
  here (Kimi review caught this list missing from this plan entirely) so
  whoever picks up those lanes doesn't read lane 4/5's text below as
  fully specified. It isn't — the event/trace shape for those items still
  needs a ruling at dispatch time.
