# Open questions

Tensions surfaced by research that contradict an existing decision record or
another report. Resolving one means proposing an ADR update and getting
explicit sign-off before marking it resolved here.

**Status (2026-08-20): research phase complete.** Every item below is
resolved or closed except the deferred economy tier, which is deliberately
out of scope, not unresolved. See `docs/research/00-index.md`.

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

## Closed: SkyrimNet — build-on or study-only? (2026-08-20)

The two `01-skyrim-modding-substrate.md` source reports gave opposite
recommendations, and this was flagged as bearing directly on ADR-0003. The
due-diligence prompt drafted here was fired and answered by
[report 07](../research/07-skyrimnet-substrate.md): direct SkyrimNet
coupling is rated **HIGH RISK** (closed C++ core, no LICENSE file, single
Ko-fi-funded maintainer, documented API-version drift across betas,
in-process crash-to-desktop failure mode), and a **Substrate Abstraction
Layer** (SkyrimNet as primary provider, powerofthree's Extender +
open-source SKSE_HTTP as secondary, both behind a generic provider
interface) is rated **MEDIUM RISK** and adopted. See
[ADR-0003](0003-substrate-choice.md), now `accepted`.

Report 07 also independently re-derived the save/reload sync design from
reports 05/06 while researching this unrelated question — a third
convergence, noted in ADR-0004/0005.

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

## Deferred: economic simulation

None of the four research prompts covered economic simulation (prices,
supply, the trade-ripple layer of the Jarl-assassination north-star
scenario in `docs/vision.md`) — it's slated as a later tier (v0.4),
deliberately out of scope while the belief tier is unproven. Noting it here
so it doesn't silently vanish from the plan.
