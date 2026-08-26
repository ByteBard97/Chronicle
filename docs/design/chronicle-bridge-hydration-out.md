# Design prep — ChronicleBridge, the "Out" direction (first slice)

**Status (2026-08-26):** the C++ half described in §3c is now written and
compiles cleanly against the real CommonLibSSE-NG headers on the Windows
build machine (`IdentityMap.{h,cpp}`'s new `ResolveChronicleNpcId`
reverse table, `OutboundClient.{h,cpp}`'s new `FetchHydrationPairs` +
hand-rolled hydration-pair parser, and the new
`HydrationPoller.{h,cpp}`, wired into `plugin.cpp` as a third
detached thread alongside the spatial-streamer and death-event loops).
**"Compiles cleanly" is the ONLY claim being made.** This is a WRITE to a
live game object (`RE::BGSRelationship::level`) — the first write path
in ChronicleBridge; every prior slice only ever read/observed. It has
**never been exercised against a live game or a real save** — no game
ran during this development pass. Scope is exactly the §3c ruling: only
sets `.level` on an EXISTING `BGSRelationship`; if `GetRelationship()`
returns null (no authored vanilla relationship for that pair — expected
to be the common case for Chronicle-relevant grudge pairs), the pair is
skipped, logged, never created. Do not treat this as tested or safe
until someone confirms it manually in an actual play session.

One gap remains, named explicitly rather than fixed here: the write does
call `TESForm::AddChange(BGSRelationship::ChangeFlags::kRelationshipData)`
to mark the record dirty for save serialization (the documented API for
that), but whether that alone is *sufficient* for a correct save/reload
round-trip of a `BGSRelationship` record is unverified.

**Update (2026-08-26): the "delivered before confirmed" gap is closed.**
The listener's `/whiterun/hydration` dedupe cache used to mark a pair
"delivered" the instant it handed it out — before the poller ever
confirmed the write actually succeeded (fad0d79's finding) — so every
pair the poller skipped (unresolvable NPC, no active game, or the common
no-existing-relationship case) was a silent, permanent drop from the
listener's perspective. This is now closed with an ack protocol:

- `HydrationPoller.cpp`'s `ApplyHydrationPair` now returns one of three
  `HydrationApplyOutcome` values (`OutboundClient.h`) instead of only
  logging: `kApplied` (the write succeeded), `kNoRelationship`
  (`GetRelationship()` returned null — PERMANENT, no authored vanilla
  relationship exists for that pair), or `kRetry` (either NPC failed to
  resolve, or no game was active at all — TEMPORARY, worth retrying).
- After processing a poll's whole batch on the main thread,
  `HydrationPollerThreadLoop` hands the collected outcomes back to its
  own (non-main) thread via a `std::promise`/`std::future` and POSTs
  them with the new `PostHydrationAck` (`OutboundClient.{h,cpp}`) to a
  new `POST /whiterun/hydration/ack` route — same host/port/sharedSecret
  as every other path, not a second config block. The ack POST, like
  every other network call in this plugin, never runs on the main
  thread.
- The listener (`adapters/skyrim/listener/listener.py`) no longer marks
  a pair "delivered" the instant `GET /whiterun/hydration` serves it.
  Each `(holder_id, target_id)` pair now moves through an explicit state
  machine — not-yet-offered / offered-awaiting-ack / permanently-skipped
  (at one specific rank) / applied (at one specific rank) — driven by the
  ack's `outcome`. An `applied` or `no_relationship` ack settles the pair
  at its current rank (a `no_relationship` skip is scoped to that exact
  rank only — if the rank later changes, e.g. the grudge decays back to
  0, the pair is offered again, since a different rank maps to a
  different in-game `RELATIONSHIP_LEVEL` the old skip said nothing
  about). A `retry` ack, or no ack ever arriving at all (the C++ side
  crashing/restarting mid-poll), simply forgets the pair — indistinguishable
  from what a listener restart already does to every pair, and eligible to
  be offered again next poll if its rank is still non-matching. See
  `listener.py`'s `_HydrationPairState` docstring for the full state
  machine, and `HydrationPoller.h`'s header comment for the C++-side
  mapping.

Given most Chronicle-relevant pairs have no authored vanilla relationship
at all, the expected steady state is still that most computed pushes are
permanently skipped (`kNoRelationship`) rather than applied — that has not
changed. What has changed is that the listener now *knows* this
definitively instead of guessing from silence, and genuinely-temporary
skips (`kRetry`) are no longer conflated with permanent ones.

Original status below, still true for everything not covered above:
design proposal for the C++ half; nothing here has been implemented or
tested — it needs the Windows build machine and a live game, per every
prior ChronicleBridge doc's discipline. Written because the design work
itself is headless and this is currently the single biggest gap between
what Chronicle simulates and what a player can see.

Sources: `adapters/skyrim/README.md`'s charter (names "Out" — AI-package
overrides on cell hydration, and prompt context for dialogue mods — but
nothing of it has ever been built; only "In" has two slices so far);
`docs/research/19-skyrim-quest-injection-machinery.md`'s three-tier risk
taxonomy (direct worldspace edits = high risk; tagged temporary spawns =
medium risk; **dialogue/reputation overlays = low risk, zero physical
world alteration** — and this report explicitly states Chronicle's own
hydration seam "should default to" this ordering); `docs/research/
19-21`'s shared finding that routing state changes through Skyrim's
Story Manager is the dominant failure mode in every surveyed
faction/quest mod (Story Manager Bottlenecks, dropped events under
Papyrus latency); `chronicle/social.py`'s `Reputation`/`Grudge` (the
state this slice exposes — already computed, already decayed at read
time, nothing new to build sim-side).

## 0. What this is not (yet)

Not AI-package overrides (behavior changes — avoidance, schedule
rewrites), not dialogue generation, not Mantella/CHIM prompt-context
injection, not quest injection. Those are all real, named in the
charter, and all higher-risk or bigger-scoped than what follows. This
slice is the smallest thing that makes Chronicle's state *visible*
in-game at all, using mechanisms Skyrim already has natively — the same
"smallest real thing, name the rest honestly" discipline as the two
"In" slices.

## 1. The dependency this slice deliberately does not build

Everything downstream of this slice (dialogue conditions checking
reputation, guards remarking on a grudge, an NPC's price adjusting
toward a hated merchant) needs the full ADR-0005 sync-handshake's
epoch-fenced write discipline to be safe against writing hydration into
the wrong save/branch — `chronicle/sync.py`'s RESOLVE logic and
`chronicle fork` exist (headless, tested), but nothing wires them into
a live session yet (`docs/design/chronicle-sync-cli-integration.md`
§0's still-open item). This slice targets the same single-live-run
trust model the death-extraction slice already established (a human
names the live run; no multi-save branch awareness) — a **known,
already-precedented limitation**, not a new one.

## 2. Scope, precisely

- **What:** Skyrim's native `Actor.SetRelationshipRank(akOther, aiRank)`
  (Papyrus, callable directly from C++ via the Papyrus VM interface, or
  via a native equivalent if CommonLibSSE-NG exposes one — verify at
  implementation time) driven by Chronicle's own `Reputation`/`Grudge`
  state for a bounded set of (observer, subject) pairs. `SetRelationshipRank`
  is a native Skyrim mechanic (the same one vanilla marriage/family/
  faction relationships use, values roughly -4..4) that dialogue
  conditions, guard barks, and vendor behavior can already check via
  vanilla `GetRelationshipRank` conditions — no custom quest engine, no
  Story Manager, no new dialogue authoring required for this slice to be
  *observable* (existing vanilla conditioned dialogue already reacts to
  relationship rank changes in some cases; new Chronicle-aware dialogue
  is future work, out of scope here).
- **Where:** no worldspace restriction — like the death-extraction
  slice, a rank push is a discrete, low-frequency event (only when
  decayed reputation/grudge severity crosses a meaningful band), not a
  per-tick poll.
- **Direction:** Python → game only (the actual "Out" traffic; nothing
  in "In" changes). A new listener-side capability, not a new
  ChronicleBridge endpoint necessarily — needs a decision (§3) on
  whether the *game* polls the listener for pending hydration pushes, or
  the listener pushes to a socket ChronicleBridge holds open. Given
  ChronicleBridge's existing outbound-only pattern (it POSTs to the
  listener; nothing currently flows the other way), a poll
  (ChronicleBridge periodically GETs a small "pending hydration" queue)
  is the smaller change — no new inbound network surface on the game
  side, matching the existing trust model.
- **Value mapping:** Chronicle's `Reputation` is a continuous Beta-mean
  in `[0,1]`, `Grudge.severity` likewise. `SetRelationshipRank`'s scale is
  a small integer band. This slice needs a simple, named, documented
  bucketing function (e.g. severity `< 0.2` → rank 0/no change, `0.2-0.5`
  → rank -1, `> 0.5` and grudge not cooled → rank -2) — placeholder
  bands, not load-bearing precision, same convention as every other
  tunable constant in this codebase.

## 3. Open questions a real design-prep pass must still answer

- **Poll vs. push**, named above — needs a decision before any C++ work.
- **Which NPCs.** Only the named-cast identities `IdentityMap.cpp`
  actually resolves (growing from 1 to ~19 this session — see
  `docs/design/next-phases-2026-08.md`) can be targeted by
  `SetRelationshipRank` at all; a fallback-identity NPC has no resolvable
  in-game actor reference to call it on.
- **Idempotency/staleness.** A rank push must not repeatedly re-apply
  the same value every poll — needs a "last pushed rank" cache (in the
  listener, or read back from the game) so a poll cycle is a no-op when
  nothing changed, mirroring `EventLog.append()`'s dedupe discipline on
  the "In" side.
- **What happens on the FORK/ADOPT paths** `chronicle sync-check` can
  now compute but not act on (`docs/design/chronicle-sync-cli-
  integration.md`) — hydration pushes must stop, not misfire into the
  wrong branch's state, whenever the sync handshake isn't in a clean
  CONTINUE state. This slice should refuse to push anything until that
  wiring exists, rather than pushing blind.

## 3b. Split, per the "In" slices' own precedent: a Python-only first cut

Both existing ChronicleBridge slices split cleanly into a headless
Python half (buildable and tested now) and a C++ half (needs the
Windows machine + a live game). This slice splits the same way — ruling
on §3's "poll vs. push" question now rather than leaving it open:
**poll.** Matches the reasoning already in §3: no new inbound network
surface on the game side, and ChronicleBridge's existing pattern is
already outbound-only (it POSTs; nothing currently flows the other
way).

**Python-only scope, buildable today:**

- `SocialStateStore` has `grudges()` (enumerates all grudges) but no
  equivalent for reputations — only single-key `reputation(observer_id,
  subject_id, context)` lookup. Add `reputations() -> tuple[Reputation,
  ...]`, mirroring `grudges()`'s exact shape, in `chronicle/social.py`.
- A pure bucketing function, `chronicle/hydration.py` (new module,
  headless, no adapter dependency — same "chronicle/ never imports
  adapter-specific concerns" boundary `chronicle/sync.py` follows):
  `relationship_rank_for(reputation: Reputation | None, grudge: Grudge | None, *, at_gamets: float) -> int`,
  implementing §2's placeholder bands (decayed grudge severity `<0.2` →
  0, `0.2-0.5` → -1, `>0.5` and not cooled → -2; reputation's Beta-mean
  folded in only if you find a clean way to combine the two signals —
  otherwise grudge alone for this first cut, reputation deferred, and
  say so explicitly rather than inventing a combination formula).
- A pending-hydration endpoint on the listener
  (`adapters/skyrim/listener/listener.py`), `GET /whiterun/hydration`,
  gated behind the same `--live-run` requirement `/whiterun/events`
  already uses (never default-enabled against a fixture/demo run):
  computes the current bucketed rank for every named-cast NPC pair with
  a grudge, diffs against a "last pushed" cache (in-memory is fine for
  a first cut — the idempotency requirement from §3, "must not
  repeatedly re-apply the same value every poll" — persisting the cache
  across listener restarts is a real gap to name, not solve, here), and
  returns only the pairs whose bucket actually changed. This is the
  shape a not-yet-built C++ poller would call; nothing calls it yet.
- Tests: `reputations()`'s enumeration; `relationship_rank_for()`'s
  bucket boundaries and decay-awareness (a grudge that's cooled by
  `at_gamets` returns 0 even if its stored severity was once high); the
  endpoint's diff/dedupe behavior (a second poll with no state change
  returns nothing; a real change surfaces once, and only once, until it
  changes again).

**Still explicitly not built:** the C++ poller itself, `SetRelationshipRank`
calls, anything on the game side. This Python half has no effect on a
live game until that exists — it's the same "prove the smallest real
thing headless, name what's deferred" discipline as every other slice.

## 3c. A real finding that narrows the C++ poller's first cut

Checked against the actual CommonLibSSE-NG headers (via this session's
SSH build access) before writing any code, since §2 assumed
`SetRelationshipRank` was a simple runtime setter — it isn't.
`Actor.SetRelationshipRank`'s underlying engine state is
`RE::BGSRelationship`, a persistent `TESForm`-derived record living in
`TESNPC::relationships` (a `BSTArray<BGSRelationship*>*`), found via the
real, reverse-engineered `BGSRelationship::GetRelationship(TESNPC*
a_npc1, TESNPC* a_npc2)`. Setting a rank on a pair that already has an
authored relationship is a simple field write (`relationship->level =
...`); **creating a new relationship record for a pair that has none is
form-registration territory this project doesn't yet understand well
enough to do safely** — unclear whether it needs explicit registration
into `TESNPC::relationships`, save-serialization bookkeeping, or other
steps a naive `new BGSRelationship` wouldn't get right, and getting this
wrong risks actual save-file integrity, a materially different risk
class than everything built so far (pure observation/telemetry).

**Ruling: the first C++ poller cut only sets `.level` on an EXISTING
`BGSRelationship`.** A named-cast pair with a computed rank change but
no existing relationship record is skipped (logged, not attempted) —
this is the honest "smallest real slice" cut, not a workaround. Most
Chronicle-relevant pairs (grudge holders/targets) won't have an
authored vanilla relationship anyway, so this scopes down coverage
significantly for the first cut; expanding to relationship *creation*
is real, separate future work needing its own research pass (how the
game's own runtime `SetRelationshipRank` console command actually
creates one, if it does) before any code.

## 4. Non-goals for this slice

- AI-package overrides (behavior/schedule changes) — a real, separate,
  higher-risk future slice.
- Dialogue generation or Mantella/CHIM prompt-context injection — the
  vision doc's own ordering puts LLM layers strictly last.
- Quest injection / GM-director content (`docs/research/19-21`'s main
  subject) — a much larger, separately-scoped future capstone
  (`docs/vision-v2.2.md` §6 names it explicitly as "not on the version
  road" for exactly this reason).
- Any change to `chronicle/social.py` — `Reputation`/`Grudge` already
  compute everything this slice needs; this is a pure read-and-export
  problem.
