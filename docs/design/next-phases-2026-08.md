# Next phases (as of 2026-08-26)

**Status:** working plan, not an ADR or a ladder amendment — informal
coordination doc, revise freely as work lands. Produced with independent
critique from Kimi and advisor (see session log); supersedes any
"v0.3 is undesigned" framing from earlier planning — see §3.

## 0. Just landed

Rules 12 (grudge-creation) and 13 (grudge-decay) — the scenario ladder's
last two stubbed rules — are now real (commit `c6d047d`). All 19 rules
in `docs/scenario-ladder.md` §8 are live; the ladder's rule-budget table
itself is stale on this point (still frozen/owner-review-only, not
edited here) and should be updated by the owner when convenient.

`Driver.suffer_harm()` is the new autonomous, self-victim grudge cascade
(`chronicle/driver.py`) — the first case of a grudge forming without a
scenario/console script explicitly calling `form_grudge()`.

## 0b. Also landed since this doc was first written

`chronicle/sync.py` (ADR-0005's RESOLVE table, epoch fencing, dedup —
§1 below) and `chronicle sync-check <run_id> --manifest '<json>'`
(`docs/design/chronicle-sync-cli-integration.md`) are both built and
tested (commits `c5aa674`, `eea96c1`). `sync-check` classifies a real
run's state fully for CONTINUE; FORK/ADOPT compute correctly but exit 3
with an explicit "no fork-on-disk mechanism exists yet" message, because
that finding turned out to be real: `chronicle/framelog.py`'s on-disk
format bakes in exactly one `(save_uuid, generation)` per run, and
`EventLog.fork()` (`chronicle/events.py`) has no on-disk counterpart.
**Fork-on-disk support is now the actual blocking dependency** for
finishing the sync handshake beyond the simple-reload case — it's real,
new, undesigned scope (nobody has specified what a forked branch's
directory/records/index layout looks like), not a small follow-up. See
§1b.

## 1. Highest-leverage next lane: ADR-0005's Python-side sync handshake

**Why this one first:** every future ChronicleBridge extraction slice
(crimes, dialogue, quest stages — `adapters/skyrim/README.md`'s charter)
writes events into *some* branch. Right now nothing enforces that it's
the *correct* branch — the death-extraction slice
(`docs/design/chronicle-bridge-death-extraction.md` §1) named this gap
explicitly and deliberately didn't solve it. `docs/decisions/
0005-sync-handshake.md` already fully specifies the protocol (co-save
manifest schema, HELLO/RESOLVE/ACK, a six-way RESOLVE decision table,
epoch fencing) — nothing of the Python-side "RESOLVE" logic exists in
the repo yet, and `scenarios/sync/*.md` (12 files) are prose risk
scenarios only, no implementation, no tests.

Unlike the C++ shim half (needs the Windows build machine + a live game
to test at all), the RESOLVE-table logic is pure branch-key arithmetic
against `chronicle/events.py`'s existing `EventLog`/`BranchKey`/
`lineage()` — fully headless, fully unit-testable today.

**Scope for the first lane:** a new `chronicle/sync.py` module implementing:
- The manifest dataclass (`docs/decisions/0005-sync-handshake.md`'s
  co-save manifest table: `format_version`, `save_uuid`, `generation`,
  `parent_generation`, `head_seq`, `gamets`, `wall_ts`).
- A pure `resolve(manifest, branch_state) -> Decision` function
  implementing the six-way table (CONTINUE / FORK / ADOPT / NEW TIMELINE
  / LEGACY IMPORT / DEGRADED) verbatim from the ADR.
- Epoch fencing: an `epoch_id` counter and a `mutation_admissible(epoch,
  current_epoch) -> bool` gate (ADR-0005 point 4).
- Idempotency dedup keyed on `(save_uuid, generation, event_seq)` (ADR
  point 7) — likely already close to what `EventLog.append()`'s existing
  idempotency does; check for reuse before adding a second mechanism.
- Test coverage: one test per applicable `scenarios/sync/*.md` risk
  scenario, plus the six RESOLVE branches individually.

**Explicitly out of scope for the first lane:** wiring this into
`adapters/skyrim/listener/listener.py` (a real integration decision —
where the manifest actually arrives from, e.g. a new endpoint — needs
its own design-prep doc first, same discipline as the two existing
ChronicleBridge slices); the C++ shim side (`g_isLoading`, the co-save
read/write, the two load hooks) — needs the Windows machine and a live
game, not attemptable headless.

## 1c. Landed: fork-on-disk support

`chronicle fork <run_id> --at-tick T` (commit `d3f2e6c`) — copy-forward
per §1b's ruling. Caught one real bug in review before committing:
`cli._branch_identity()` (used by `inject`/`sync-check`) used to trust a
run's first record's envelope for its generation, which broke the moment
a forked run's copied prefix legitimately carries the *parent's*
generation on its earliest records — every forked run's own identity was
silently misreported as its parent's. Fixed (registry-first, record
fallback) with a regression test. Also landed: `sync-check --apply`
(commit `c10c71a`) now actually calls `fork_run()` for FORK/ADOPT
instead of only reporting them; without `--apply` it still just reports
(exit 3), the prior default unchanged. This closes out the ADR-0005
sync-handshake thread as far as it can go headlessly — everything left
(the C++ shim side, the dashboard UI for triggering a fork per ui-spec
§3.1) needs the Windows machine, a live game, or dashboard-lane work,
not this thread.

## 1b. New candidate: fork-on-disk support (superseded by §1c above)

What §0b surfaced. Needed before `sync-check`'s FORK/ADOPT paths (or any
real reload-to-an-earlier-save case) can do anything but report. Not yet
scoped at all — open questions a design-prep doc would need to answer:
how a forked branch's run directory/records/index actually look on disk
(a new directory? a second `(save_uuid, generation)` inside the existing
one, mirroring `EventLog`'s in-memory shape?); how `chronicle inject`'s
existing historical-tick refusal (`_inject_write`, "fork territory, a
deliberately deferred milestone") changes once fork *is* built; whether
the dashboard's run-registry/index needs to learn about multiple
generations per `save_uuid`. This is real, undesigned scope — worth a
design-prep doc of its own before any code, same discipline as
everything else in this doc.

## 2. Second candidate: trust-discounted retelling design-prep

`docs/scenario-ladder.md` §6 names this as the one deliberately deferred
mechanism that "feeds social state into claims and deserves its own
rung when wanted" — the ladder's last open rule-budget slot (19/20 used;
completing rules 12/13 didn't spend it, they were already counted). T2.3
names the exact pattern to build on: "the caller-supplies-context pattern
`propagate.py` already uses" (`chronicle/propagate.py`'s
`teller_and_hearer`/`conflicting_pair` functions).

This needs a design-prep doc (`docs/design/trust-discounted-retelling.md`,
modeled on the two ChronicleBridge design docs) before any code, since it
spends the ladder's last rule slot — that's an owner-review point per the
ladder's own frozen-document convention, not something to decide
unilaterally mid-lane.

## 3. Corrected finding: v0.3's headline features are NOT undesigned

Earlier planning in this session assumed v0.3 ("NPC-initiated social
actions with CK-style thresholds, hysteresis, crystallized named
relationships," `docs/vision-v2.2.md` §6) was an unstarted tier needing a
from-scratch design doc. That was wrong: thresholds (rule 11), hysteresis
(doctrine 3), grudges (12/13, now real), obligations (14), and named
relationships (`social.Relationship`) are already built and
ladder-tested. What's actually still open, per Kimi's independent review:

- **Rule 11's latch is one-directional.** It can trip but never untrip —
  fine for "four thefts escalate," not sufficient for CK-style
  relationship *demotion*, which needs separate entry/exit thresholds.
  No surveyed research (`docs/research/comparative-systems/`) or existing
  code solves two-way hysteresis. This is the hardest real open design
  problem for anything beyond what's landed.
- **No inventory of NPC action verbs.** Avoidance (rule 18) is the only
  built "NPC acts differently because of accumulated social state"
  mechanism. Dialogue, package overrides, quest hooks are unresearched
  for this purpose (research/19-21 cover GM-layer quest injection, a
  different consumer).
- **Propensity scoring has a ready model to crib, not invent:**
  `docs/research/comparative-systems/ck-opinion-decay-and-threshold-tables.md`'s
  `ai_chance = base + Σ situational + Σ personality×coef` idiom.
- Named-cast identity gap (`HANDOFF-2026-08-25-1930.md`): live-observed
  Whiterun NPCs mostly aren't in the fixture cast yet, so any of this is
  currently only demonstrable for the ~6 NPCs the fixtures already know.

None of §3 is scheduled — it's flagged for whenever the owner wants to
open a genuinely new rung, and it plainly requires the ladder's last
rule-budget slot (in competition with §2 above) or a consolidation
ruling (§8's own suggestion: merge rules 9+10, or reclassify 4 as
schema-not-rule).

## 4. Explicitly not being worked without owner sign-off

- Any edit to `docs/scenario-ladder.md` itself (frozen, owner-review-only
  per the project's governance convention).
- Spending the ladder's last rule-budget slot on either §2 or §3.
- The ChronicleBridge C++ half of anything (needs the Windows build
  machine + a live game; not attemptable from this session alone).
