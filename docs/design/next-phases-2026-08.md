# Next phases (as of 2026-08-26)

**Status:** working plan, not an ADR or a ladder amendment — informal
coordination doc, revise freely as work lands.

**Course correction (advisor-caught):** everything in §0 below is real,
tested, headless plumbing — and every bit of it is invisible in Skyrim.
This doc had been sequencing off what the *ladder* had left unbuilt, not
off what closes the distance to the actual goal (`docs/vision-v2.2.md`):
a Skyrim world that visibly reacts to the player. Two concrete blockers
for that, now promoted to the top of this doc: the seam's **"out"**
direction (sim state → game, `adapters/skyrim/README.md`'s charter)
doesn't exist at all — only "in" (positions, deaths) has ever been built
— and the **named-cast gap** means almost none of the rules just landed
apply to any NPC the player can actually meet (verified: `IdentityMap.
cpp`'s `kNamedCast` has exactly one entry against 28 live-captured
Whiterun NPCs in `whiterun-positions.json`).

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

## 0b2. Standing capability discovered: the Windows build machine is reachable

SSH access to the owner's Windows machine (`geoff@192.168.0.211`) works
and has a fully set-up ChronicleBridge build toolchain (VS2022 Build
Tools, CMake+Ninja, vcpkg already bootstrapped) — confirmed by a real
clean build during this session. Connection details and the exact
working build recipe (the MSVC dev environment isn't loaded by default
over plain SSH — needs `vcvars64.bat` sourced via `cmd.exe` in the same
invocation as the build) are in `.claude/windows-build-machine.md`
(gitignored, local-only, per the owner's explicit request — re-read it
at the start of any future C++ work rather than rediscovering this).

**This retires every prior "needs the Windows build machine, not
attemptable from this session" caveat this document and its
predecessors have repeated about ChronicleBridge C++ work.** Compiling
and verifying C++ changes is now directly reachable from a headless
session. What's still NOT reachable: actually running Skyrim/MO2 and
observing live in-game behavior — that remains the owner's own
interactive desktop session (see root `HANDOFF-*.md` files,
`tools/launch-ngvo-skse.sh`). "Compiles cleanly" and "verified against
a live game" are two different claims; keep them distinct in every
future report on ChronicleBridge C++ work.

## 0f. Landed: hydration-out's C++ poller (`fad0d79`) — first WRITE path, unverified

All three ChronicleBridge slices (spatial streamer, death extraction,
hydration) are now built end to end. This one is different in kind from
everything before it: it's the first code in the whole project that
*writes* to a live game object (`RE::BGSRelationship::level`), not just
observes one. Compiled cleanly, independently re-verified with two full
clean rebuilds. **Never run against a live game or a real save — that
must stay true in every future summary of this work until someone
confirms it manually in an actual play session.** Real findings from
the build: `TESDataHandler::LookupForm<Actor>` resolves a placed
reference directly (simpler than guessed); `BGSRelationship::AddChange`
is needed to mark the write dirty for save serialization (documented
API, not confirmed sufficient); a real protocol gap exists where the
listener marks a pair "delivered" before the C++ side confirms the
write succeeded, so skipped pairs (the expected-common "no existing
relationship" case, or an NPC not currently resolvable) are silently
and permanently lost — named, not fixed. Ruled scope held: only updates
an existing relationship record, never creates one.

## 0e. Landed: hydration-out's Python-only slice (`e3e4b20`, `3044e14`)

`SocialStateStore.reputations()`, the pure `chronicle/hydration.py`
bucketing function (grudge severity → Skyrim relationship-rank scale,
decay-aware, reputation deliberately deferred), and `GET
/whiterun/hydration` on the listener — the one documented, narrowly-
scoped exception to "never import chronicle/ directly" (justified
because this route has no write path to protect). In-memory idempotency
cache, explicitly doesn't survive a listener restart (named gap, not
silent). 323 + 15 tests pass. **Still nothing on the C++ side** — no
poller exists yet to call this endpoint or actually invoke
`SetRelationshipRank` in-game; that's the natural next slice now that
both this and death-extraction have proven the "In"/"Out" split works
and the build machine is reachable.

## 0d. Landed: death-extraction's C++ half (`6ec2406`)

`DeathEventSink`, wired into `plugin.cpp` and `OutboundClient`, compiles
cleanly (independently re-verified with a full clean rebuild, not just
trusted from the report) against the real `commonlibsse-ng@3.6.0`
toolchain via the newly-discovered SSH build access. This is the second
ChronicleBridge slice fully specified end to end (Python listener half
already existed; the C++ half was the one thing left). `gamets` comes
from `RE::Calendar::GetHoursPassed()`, matching a wire-contract field
description that was already written before this code existed.
**Compiled, not live-tested** — no death event has ever actually been
observed or POSTed by this code; that needs the owner's own game
session.

## 0c. Landed: named-cast growth (`2f27cc8`)

`IdentityMap.cpp`'s `kNamedCast` grew from 1 entry (ysolda) to 19, using
the exact plugin/FormID pairs observed in a real Whiterun snapshot
(`whiterun-positions.json`), independently verified against that JSON
programmatically — zero transcription errors. Matching Python fixture
growth (`chronicle/fixtures/whiterun_schedule.py`/
`whiterun_relationships.py`): a schedule block per new NPC, and only 5
relationship edges for pairs with confident vanilla-lore backing
(Carlotta/Lucia, Amren/Saffir, both feuding households, Sigurd/Adrianne)
— deliberately schedule-only for the rest rather than inventing ties.
A regression test keeps the two hand-synced sides (C++ table, Python
fixture) from silently drifting apart. **Still unverified beyond direct
textual comparison** — the C++ side needs the Windows build machine and
a live game to confirm it actually compiles and resolves correctly.

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

## 3. Genuinely stops the loop (narrow — most things don't belong here)

- `git push` to the remote — always ask first, no exception.
- Actually testing anything against a live Skyrim process/real save —
  the SSH build machine (§0b2) closes the "can't compile C++" gap, but
  running the game is still the owner's own interactive session, not
  reachable from here.
- Spending a rule-budget slot on new scope (§2) deserves a heads-up in
  the commit message, not a stop — but committing to it silently, with
  no note, would be the wrong kind of quiet.

**Narrowed per repeated, explicit owner feedback (this session): researching**
**whether a mechanism is feasible, what the literature/prior art says, or**
**producing a design doc is NOT "opening new scope" and does not stop**
**anything** — only actually spending the rule-budget ceiling on
implementation does, and even that only needs a heads-up, not a pause.
When domain-expertise is missing (a modeling choice, an API's real
behavior, a literature question) the answer is Kimi/advisor/a research
agent followed by an executive decision, every time — not a question
back to the owner. Kimi being temporarily out of quota (2026-08-26) is
not a reason to fall back to asking; use a research agent instead.

Frozen documents (`docs/ui-spec.md`, `docs/scenario-ladder.md`,
`docs/ui-doctrines.md`) are not automatically stop-and-ask either — see
§1's rule-20 amendment for the standard: a reviewed design doc that
rules cleanly on its own questions may amend a frozen doc's stale
content, reported afterward rather than asked about first.
