# Next phases (as of 2026-08-26)

**Status:** working plan, not an ADR or a ladder amendment — informal
coordination doc, revise freely as work lands.

## 0. Landed

- Rules 12 (grudge-creation) and 13 (grudge-decay) — the scenario
  ladder's last two stubbed rules — are now real (`c6d047d`).
  `Driver.suffer_harm()` is the first grudge cascade that fires without
  a scenario/console script explicitly calling `form_grudge()`.
- `chronicle/sync.py` (ADR-0005's RESOLVE table, epoch fencing, dedup)
  and `chronicle sync-check <run_id> --manifest '<json>'`
  (`docs/design/chronicle-sync-cli-integration.md`) — `c5aa674`,
  `eea96c1`.
- `chronicle fork <run_id> --at-tick T` — on-disk fork support,
  copy-forward (`docs/design/fork-on-disk-support.md`, `d3f2e6c`). Caught
  a real bug in review: `cli._branch_identity()` used to trust a run's
  *first* record's envelope for its generation, which broke the moment a
  forked run's copied prefix legitimately carries the parent's
  generation on its earliest records. Fixed (registry-first, record
  fallback), regression test added.
- `sync-check --apply` (`c10c71a`) now actually calls `fork_run()` for
  FORK/ADOPT instead of only reporting them.

**This closes out the entire ADR-0005 sync-handshake thread as far as it
can go headlessly.** What's left there — the C++ shim side and the
dashboard UI for triggering a fork (`ui-spec.md` §3.1) — needs the
Windows build machine, a live game, or dashboard-lane work respectively.

## 1. Landed: trust-discounted retelling (rule 20, `472f3f8`)

Every design question is ruled — via Kimi + advisor, code-verified, not
owner opinion (session policy: a domain/tuning disagreement gets
resolved by consulting them and verifying the discriminating fact in
code, not bounced back to the owner — `docs/loop-playbook.md`):

- No-relationship pairs get `trust=0.5`, not the undiscounted flat `0.8`
  — verified `Relationship.strength` has no distrust range at all
  (`[0,1]`, hard-gated; distrust lives only in `Grudge`), so a weak tie
  and no tie are the same kind of signal, not neutral-vs-distrusted.
- Trust discounts confidence only, never `verbatim_strength`/
  `gist_strength` — the two axes are deliberately orthogonal (source
  credibility vs. memory precision).
- `colocation` is excluded from the trust lookup (kinship/faction/
  shared_employer only, max strength across bases) — verified colocation
  edges are hand-seeded fixture constants that never update, tracking no
  real signal.
- The contested-resolution path (`claims.py`'s T2.3 challenger-wins
  branch) inherits the same discount, applied consistently.

`docs/scenario-ladder.md` §8 is amended (`c251f36`): the O4 consolidation
ruling it never absorbed (rules 9+10 are one rule, per `chronicle/
rules.py`'s own docstring) is now recorded, and rule 20 lands exactly at
the ~20 ceiling with no further consolidation or ceiling raise needed.

Reviewed and committed. `claims.py`'s `retell()`/`resolve()` take an
optional `trust` (confidence only, `None` byte-identical to before);
`driver.py` gates the relationship lookup on the new rule, disabled by
default reproducing exact prior behavior; T1.1's fixture explicitly
disables rule 20, preserving its flat-0.8 assertion. The implementing
agent also caught and fixed a real bug on its own: `framelog.py`'s
post-keyframe replay path wasn't forwarding `trust_applied`, which would
have silently diverged live-vs-replayed confidence values. 312/312 tests
pass. This is the ladder's 20th and last rule at the current ~20
ceiling — any future new mechanism needs a fresh consolidation ruling or
an explicit ceiling raise.

## 2. Flagged, not scheduled: v0.3's real remaining gaps

`docs/vision-v2.2.md` §6's "v0.3" is mostly already built — thresholds
(rule 11), hysteresis (doctrine 3), grudges (12/13), obligations (14),
and named relationships (`social.Relationship`) all exist and are
ladder-tested. What's still genuinely open, if a new rung ever gets
opened:

- **Rule 11's latch is one-directional** — trips but never untrips. Fine
  for "four thefts escalate," not sufficient for CK-style relationship
  *demotion*, which needs separate entry/exit thresholds. No surveyed
  research or existing code solves two-way hysteresis — the hardest real
  open design problem beyond what's landed.
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

This would need its own rule-budget slot (the ceiling is now exactly at
20 once rule 20 lands — a future mechanism here needs a fresh
consolidation ruling or an explicit ceiling raise) and its own
design-prep doc. Not scheduled; no action pending.

## 3. Genuinely stops the loop (irreversible or preference, not domain/tuning)

- `git push` to the remote — always ask first, no exception.
- The ChronicleBridge C++ half of anything, or the named-cast identity
  gap's `IdentityMap.cpp` table — needs the Windows build machine and a
  live game to even test; not attemptable from this session.
- Opening a genuinely new tier/rung of scope (§2) versus staying within
  what's already ladder-scoped — a real product-direction call, not a
  tuning question.

Frozen documents (`docs/ui-spec.md`, `docs/scenario-ladder.md`,
`docs/ui-doctrines.md`) are not automatically in this list — see §1's
rule-20 amendment for the standard: a reviewed design doc that rules
cleanly on its own questions may amend a frozen doc's stale content,
reported afterward rather than asked about first.
