# Design prep — ChronicleBridge, the "Out" direction (first slice)

**Status:** design proposal for the C++ half; nothing here has been
implemented or tested — it needs the Windows build machine and a live
game, per every prior ChronicleBridge doc's discipline. Written because
the design work itself is headless and this is currently the single
biggest gap between what Chronicle simulates and what a player can see.

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
