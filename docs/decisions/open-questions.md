# Open questions

Tensions surfaced by research that contradict an existing decision record or
another report. Resolving one means proposing an ADR update and getting
explicit sign-off before marking it resolved here.

**Status (2026-08-20): research phase complete.** Every item below is
resolved or closed except the deferred economy tier, which is deliberately
out of scope, not unresolved. See `docs/research/00-index.md`.

The project has since moved past research into six *design* (not
research) decisions gating the v0.1 build — see `docs/v0.1-spec.md`,
accepted 2026-08-20. `chronicle/claims.py` (the layer 2/3 claim/variant/
belief store) is the first code built against it; revisit a decision
only if a scenario disproves it, not preemptively.

## Resolved by direct repo verification (2026-08-20)

Three factual disagreements between the two `01-skyrim-modding-substrate.md`
source reports were repo-checkable rather than genuinely ambiguous, so they
were resolved directly against GitHub instead of re-researched:

- **MinAI status** — confirmed **deprecated**. `MinLL/MinAI`'s README leads
  with an explicit deprecation banner redirecting users to SkyrimNet; no
  `LICENSE` file in the repo; latest release `2.1.3` published 2025-04-23.
  (The "active, open source" claim in the gemini-sourced report was stale.)
- **Mantella latest release** — confirmed **v0.14, published 2026-04-21**
  (`art-from-the-machine/Mantella`). The compass-sourced report's April 2026
  date was correct; the gemini-sourced report's "December 2025" was stale.
- **CHIM/HerikaServer license** — confirmed **MIT** (`abeiro/HerikaServer`
  ships a top-level `MIT-LICENSE` file; GitHub's detected SPDX license is
  `MIT`). The "GPL-3.0 lineage" claim in the compass-sourced report was
  wrong; the gemini-sourced report's "MIT" was correct.

`docs/research/01-skyrim-modding-substrate.md` has been corrected in place
to reflect these facts.

## Closed: SkyrimNet — build-on or study-only? (2026-08-20, amended 2026-08-20)

The two `01-skyrim-modding-substrate.md` source reports gave opposite
recommendations, and this was flagged as bearing directly on ADR-0003. The
due-diligence prompt drafted here was fired and answered by
[report 07](../research/07-skyrimnet-substrate.md): direct SkyrimNet
coupling is rated **HIGH RISK** (closed C++ core, no LICENSE file, single
Ko-fi-funded maintainer, documented API-version drift across betas,
in-process crash-to-desktop failure mode), and a **Substrate Abstraction
Layer** (behind a generic provider interface) is rated **MEDIUM RISK** and
adopted, initially with SkyrimNet as primary provider.

**Amended by [report 10](../research/10-skyrimnet-health.md)**, a deeper
pass working from actual release history and integrator bug trails: the
API churn is concrete and damaging enough (v6→v9 in ~1 month, documented
IntelEngine/SeverActions breakage, no continuity statement even after an
exhaustive-as-possible targeted search) that the SAL's provider priority
inverts — **the standalone powerofthree's-Extender + SKSE_HTTP path is
now the reference implementation, SkyrimNet is an optional adapter pinned
to one beta/API version**, rated **LOW-MEDIUM RISK**, stronger than the
MEDIUM RISK rating with SkyrimNet as primary. See
[ADR-0003](0003-substrate-choice.md)'s amendment for the full evidence and
concrete promotion/drop thresholds. Action item tracked in
[`notes/ideas.md`](../../notes/ideas.md): ask SkyrimNet's maintainer
directly for a license and continuity statement.

Reports 07 and 09 also independently re-derived the save/reload sync
design from reports 05/06 while researching unrelated questions — a
fourth convergence, noted in ADR-0004/0005.

## Closed: save/reload timeline consistency (2026-08-20)

Reports [05](../research/05-save-reload-sync-protocol.md) and
[06](../research/06-save-reload-timeline-sync.md) answered the prompt that
was drafted here. Both independently converged on the same core design —
event-sourced service, save-embedded `SaveUUID`/generation identity via
SKSE co-save, fork-on-reload rather than rollback, tombstone-then-reap
branch GC — which is now captured in
[ADR-0004](0004-timeline-branching.md) and
[ADR-0005](0005-sync-handshake.md), with a corresponding branch-key change
to `chronicle/events.py`.

**Sub-disagreement resolved (2026-08-20) by report 09's repository
forensics.** Reports 05 and 06 characterized SkyrimNet's own reload
handling differently — 05: "effectively ignore/implicit"; 06: an
"explicit timeline cleanup protocol," sourced to a GitHub Discussion.
[Report 09](../research/09-save-sync-forensics.md) has the receipts:
SkyrimNet detects the divergence and **prompts the player**
(`ClearTimelineMessage`/`msgClearHistory`), confirmed via
SkyrimNet-GamePlugin issue #251, which also requests a public "erase and
forget from time X forward" API — still unshipped as of that issue. This
is neither pure silence (05) nor a fully automatic purge (06): it's
*ask-then-delete-on-confirm*. Combined with Mantella (ignore) and CHIM
(automatic destructive rollback), the ecosystem occupies three corners of
the design space — ignore / rollback / ask — and none of them ship the
fourth: **fork**, which is what ADR-0004 adopts. This doesn't change the
now-closed SkyrimNet due-diligence verdict (ADR-0003), but it does mean
report 09 supersedes 05/06 on this specific factual question.

**Implementation-risk notes carried forward** (uncertainties the source
reports flagged as unconfirmed, not settled facts):

- **CHIM's exact fork/prune trigger is reconstructed, not confirmed.** The
  specific numeric threshold (how many in-game days back counts as
  "old enough to fork") is inferred from CHIM's FAQ, Nexus changelog, and
  HerikaServer's timestamp field names — no primary Dwemer Dynamics source
  states the actual number. Don't copy a specific threshold value from
  either report as if it were verified; treat Chronicle's own threshold as
  a tunable to be set empirically.
- **The save-embedded-UUID pattern has no confirmed Skyrim precedent.**
  The strongest published prior art for "GUID-on-start + heartbeat, detect
  reload by comparing stored state against the save's clock" is from a
  different engine (the Neverwinter Nights "realms" module). Skyrim mods
  more commonly reconcile via timestamp comparison (CHIM's `gamets`) than
  via a stored GUID. Chronicle will be implementing and testing this
  co-save read/write path essentially from scratch — budget for that.
- **SKSE's `.skse`/`.ess` pairing is atomic by convention, not guaranteed.**
  Neither SKSE's headers nor either report claim transactional atomicity —
  `kPostLoadGame`'s success boolean exists precisely because a load can
  fail after `kPreLoadGame` fires. ADR-0005's idempotency/versioning rules
  exist to cover this gap, but a crash between co-save and `.ess` writes
  remains a residual risk worth a scenario test once the shim exists.

## Mostly-closed, one real gap: event-log growth/compaction for long play sessions (2026-08-27)

An external-AI conversation the owner had (Kimi) independently re-derived
a save/reload architecture — a global `state_version` counter, an SKSE
co-save mirror, "seek not rewrite" on reload, full-snapshot-every-N-
versions compaction — and asked whether it should be written down. Most
of it already is, in a more precise and more thoroughly-decided form:

- **"State_version counter" / "seek not rewrite" is ADR-0004's
  `(save_uuid, generation)` branch key + fork-on-reload, already
  implemented** (`chronicle/events.py`'s branch-keyed `EventLog`,
  `chronicle/fork.py`'s `fork_run()`). Loading an old save doesn't
  rewrite history — it opens a new `generation`, exactly the "the log
  contains every timeline branch that ever existed, you just move the
  pointer" idea, just keyed by two numbers instead of one and with a
  real GC/grace-period story for abandoned branches (ADR-0004's own
  git-gc analogy) that the Kimi conversation's version didn't have.
- **The SKSE co-save wire format** ("`{npc_id, form_id, state_version,
  social_blob_hash}`") is already specified, in more detail, as
  ADR-0005's co-save manifest schema table (`format_version`,
  `save_uuid`, `generation`, `parent_generation`, `head_seq`, `gamets`,
  `wall_ts`, `char_name_hash` — deliberately kept under ~100 bytes,
  since SKSE's per-call co-save writes are slow for large payloads).
- **"What if Python is unavailable at save/load"** is ADR-0005's
  DEGRADED mode: the shim never blocks, buffers outbound events in a
  bounded local queue (spilling to disk if full), and reconciles on
  reconnect — a stronger guarantee than the Kimi conversation's proposed
  "reconstruct from engine state + fixtures, log a warning" fallback,
  which would lose real belief provenance DEGRADED mode doesn't have to.
- **The RESOLVE decision table** (`chronicle/sync.py`, `chronicle
  sync-check`) already implements the six-way CONTINUE/FORK/ADOPT/
  NEW_TIMELINE/LEGACY_IMPORT/DEGRADED classification ADR-0005 specifies —
  this is not a design gap, it's shipped, tested code.

**The one part that's genuinely still open**: `chronicle/events.py`'s own
ADR (`0002-event-sourcing.md`) explicitly flags "log size/performance at
~1,000 NPCs over long play sessions needs attention eventually
(snapshotting or compaction), but is out of scope for the initial
skeleton." Nothing has closed that yet. Note the framing is different
from the Kimi conversation's concern, though: Chronicle's log is already
event-sourced (one small record per mutation), not periodic full-graph
dumps, so "50 quicksaves × 4.5MB" doesn't apply as stated — a quicksave
doesn't trigger any snapshot at all today, just whatever events already
happened. The real open question is narrower: does an actively-played
branch's append-only event log need periodic compaction (e.g. collapsing
fully-decayed claims into aggregate reputation scalars, as the
conversation itself suggested) once it's been running long enough, and
if so, on what trigger (event count? wall-clock? explicit checkpoint
saves only?). Deferred, not scheduled — revisit once a real long-session
run's log size is actually measured, rather than budgeted from a guess.

## Deferred: economic simulation

None of the four research prompts covered economic simulation (prices,
supply, the trade-ripple layer of the Jarl-assassination north-star
scenario in `docs/vision.md`) — it's slated as a later tier (v0.4),
deliberately out of scope while the belief tier is unproven. Noting it here
so it doesn't silently vanish from the plan.
