# Next phases (as of 2026-08-26)

**Status:** working plan, not an ADR or a ladder amendment — informal
coordination doc, revise freely as work lands.

## 0. Landed this session

- Rules 12 (grudge-creation) and 13 (grudge-decay) — the scenario
  ladder's last two stubbed rules — are now real (`c6d047d`). All 19
  rules in `docs/scenario-ladder.md` §8 are live. `Driver.suffer_harm()`
  is the first grudge cascade that fires without a scenario/console
  script explicitly calling `form_grudge()`.
- `chronicle/sync.py` (ADR-0005's RESOLVE table, epoch fencing, dedup)
  and `chronicle sync-check <run_id> --manifest '<json>'`
  (`docs/design/chronicle-sync-cli-integration.md`) — `c5aa674`,
  `eea96c1`.
- `chronicle fork <run_id> --at-tick T` — on-disk fork support,
  copy-forward (`docs/design/fork-on-disk-support.md`, `d3f2e6c`). Caught
  a real bug in review: `cli._branch_identity()` used to trust a run's
  *first* record's envelope for its generation, which broke the moment a
  forked run's copied prefix legitimately carries the parent's
  generation on its earliest records — every fork's identity was
  silently misreported as its parent's. Fixed (registry-first, record
  fallback), regression test added.
- `sync-check --apply` (`c10c71a`) now actually calls `fork_run()` for
  FORK/ADOPT instead of only reporting them.

**This closes out the entire ADR-0005 sync-handshake thread as far as it
can go headlessly.** What's left there — the C++ shim side
(`g_isLoading`, co-save read/write, the two load hooks) and the
dashboard UI for triggering a fork (`ui-spec.md` §3.1) — needs the
Windows build machine, a live game, or dashboard-lane work respectively,
not this thread.

## 1. Open: trust-discounted retelling — blocked on two owner calls, not on scoping

`docs/design/trust-discounted-retelling.md` is fully written and has
been through two independent review passes (advisor, Kimi with a real
research pass) — the scoping work is done. What's blocking implementation
is two actual decisions, not missing design work:

1. **The stranger-discount question**, where the two reviews disagree:
   should a teller/hearer pair with *no* relationship edge at all take
   the flat, undiscounted `0.8` (advisor's position — "no trust data, no
   adjustment"), or a midpoint discount matching the doc's original
   `TRUST_FLOOR`-equivalent value (Kimi's position, backed by DeGroot/
   Friedkin-Johnsen trust-weighting and Granovetter's weak-ties research
   — `Relationship.strength` has no negative/distrust range at all, so a
   weak tie and no tie are the same *kind* of signal). Doc §3 lays out
   both sides in full; this is a real modeling-philosophy call.
2. **Whether to spend rule 19.** Corrected finding (Kimi, code-verified):
   rules 9/10 both wrap the identical `claims.stage_at()` call — a real
   merge, not ceiling-fudging — which drops the live count to 18/20
   before trust-discounted retelling is even added, landing it cleanly
   at 19/20. No rule-4 demotion or ceiling raise needed. Still requires
   amending the frozen `docs/scenario-ladder.md` §8 (recording the
   already-made O4 consolidation ruling that its own text never
   reflected, plus the new row) — a real frozen-doc edit, just a much
   smaller one than originally framed.

Three smaller implementation gaps the design doc's first draft missed
(also in doc §3, all need a ruling alongside the two above, not
separately): lookup direction (must be the *hearer's* trust in the
*teller* — `Relationship` is directed), what happens when a pair holds
multiple relationship bases at once, and a second independent hardcoded
use of `RETELL_CONFIDENCE_DECAY` in `claims.py`'s contested-resolution
path (~line 786) that the original inventory missed entirely.

**Not doing anything further here without the owner's answer to (1) and
(2).**

## 2. Flagged, not scheduled: v0.3's real remaining gaps

`docs/vision-v2.2.md` §6's "v0.3" is mostly already built — thresholds
(rule 11), hysteresis (doctrine 3), grudges (12/13), obligations (14),
and named relationships (`social.Relationship`) all exist and are
ladder-tested. What Kimi's independent review found still genuinely
open, if the owner ever wants to open a new rung:

- **Rule 11's latch is one-directional** — trips but never untrips. Fine
  for "four thefts escalate," not sufficient for CK-style relationship
  *demotion*, which needs separate entry/exit thresholds. No surveyed
  research or existing code solves two-way hysteresis; this is the
  hardest real open design problem beyond what's landed.
- **No inventory of NPC action verbs.** Avoidance (rule 18) is the only
  built "NPC acts differently because of accumulated social state"
  mechanism. Dialogue, package overrides, quest hooks are unresearched
  for this purpose.
- **A ready model to crib, not invent, for propensity scoring:**
  `docs/research/comparative-systems/ck-opinion-decay-and-threshold-tables.md`'s
  `ai_chance = base + Σ situational + Σ personality×coef` idiom.
- **Named-cast identity gap** (`HANDOFF-2026-08-25-1930.md`):
  live-observed Whiterun NPCs mostly aren't in the fixture cast, so any
  of the above is only demonstrable for the ~6 NPCs already fixtured.

This competes with §1 for rule 19/20's slot (or a future ceiling
decision) if the owner wants both eventually — not scheduled, no action
pending here.

## 3. Explicitly not being worked without owner sign-off

- Any edit to `docs/scenario-ladder.md`, `docs/ui-spec.md`, or
  `docs/ui-doctrines.md` (frozen, owner-review-only, `AGENTS.md`).
- Spending rule 19/20 on either §1 or §2 above.
- The ChronicleBridge C++ half of anything, or the named-cast identity
  gap's `IdentityMap.cpp` table (needs the Windows build machine + a
  live game to verify; not attemptable from this session alone).

## 4. Nothing else unblocked as of this update

Every headlessly-buildable, no-sign-off-needed thread scoped so far has
landed (§0). The only open item (§1) is waiting on the owner, not on
more design work. If picking this doc back up and nothing above has
moved, say so plainly rather than inventing a new lane to look busy.
