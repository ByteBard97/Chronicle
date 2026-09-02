# AI-NPC mod source study — Mantella, CHIM/HerikaServer, SkyrimNet (public surface), IntelEngine

**Date:** 2026-08-30
**Method:** direct source-code reads (not docs/READMEs) of four codebases, each cloned
read-only to `~/projects/chronicle-mod-research-clones/` (a sibling directory outside
this repo's git tree — nothing vendored, no license contamination):

- [`art-from-the-machine/Mantella`](https://github.com/art-from-the-machine/Mantella) (AGPL-3.0) + [`Mantella-Spell`](https://github.com/art-from-the-machine/Mantella-Spell)
- [`abeiro/HerikaServer`](https://github.com/abeiro/HerikaServer) (MIT core) — the server behind the mod "CHIM"
- [`MinLL/SkyrimNet-GamePlugin`](https://github.com/MinLL/SkyrimNet-GamePlugin) — **public-facing files only**; the core C++ DLL is closed-source (confirmed: `SkyrimNetApi.psc`'s ~870 functions are all `Global Native` — signatures only, zero implementation visible)
- [`galanx/IntelEngine-GamePlugin`](https://github.com/galanx/IntelEngine-GamePlugin) + [`IntelEngine-NativePlugin`](https://github.com/galanx/IntelEngine-NativePlugin) — a SkyrimNet submod

**Organic Factions was not cloned** — it has no public repository; it ships only as a
binary ESP on Nexus, un-clonable by this method.

Four independent read-only source passes (one per codebase, run in parallel), each
briefed with Chronicle's own architecture (ADR-0001/0002/0004/0005/0009/0011, the
2026-08-30 conversation-tier design notes) so findings are judged for relevance, not
reported in a vacuum. This report consolidates all four. Nothing was copy-pasted from
any of these codebases into Chronicle — all "borrow" items below mean *reimplement the
mechanism from understanding*, not reuse code (relevant for Mantella/AGPL-3.0
especially).

---

## Consolidated borrow list

1. **Streaming sentence-at-a-time TTS** (Mantella, `src/llm/sentence_queue.py` +
   `sentence_end_parser.py`/`sentence_accumulator.py`). A thread-safe queue with a
   sentence-boundary parser slices off complete sentences as the LLM streams tokens and
   hands each to TTS immediately — audio starts before the full reply finishes
   generating. This is the first *working implementation* found anywhere of what
   `docs/design/conversation-tier-design-notes-2026-08-30.md` §5 assumes ("TTS
   synthesizes per sentence-fragment as text arrives") without detailing how. Also has
   a `put_at_front()` priority-interrupt path — directly useful for "a committed line
   takes priority over queued ambient lines."

2. **Real prompt-cache breakpoint logic** (Mantella, `src/llm/claude_cache_connector.py`)
   — walks the message list backward to find the last user-turn boundary and stamps
   the cache-control marker there, rather than caching everything. A concrete instance
   of the same "stable prefix, growing suffix" principle as the design notes' §4
   prompt-segment ordering, just implemented against a hosted provider. Directly
   transferable to whatever prefix-caching code Chronicle writes for vLLM/SGLang.

3. **OpenAI-compatible-endpoint abstraction as the multi-provider strategy**
   (Mantella, `src/llm/client_base.py`) — unifies every backend behind the OpenAI
   client shape (base-URL swap) rather than a bespoke class per provider. This is
   independent validation that the conversation-tier notes' own requirement (any
   hosted gamemaster endpoint "must be a configurable OpenAI-compatible URL, never a
   hardcoded provider") is the field-standard, low-maintenance way to do it.

4. **`core_action`/`core_action_custom` split** (HerikaServer) — built-in vs.
   community-authored actions unioned via one view. A clean pattern for an extensible
   "what can this NPC do" registry, whenever Chronicle needs one.

5. **Package lifecycle as a tracked, reversible object** (SkyrimNet's public API:
   `RegisterPackage`/`UnregisterPackage` paired with `ScheduleDelayedPackageRemoval`,
   `ReinforcePackages` (re-apply if externally cleared), `ClearAllPackagesGlobally`
   (global escape hatch), and broadcast `SkyrimNet_OnPackageAdded/Removed` ModEvents).
   The actual injection mechanism is invisible (closed DLL) but the **API shape** —
   owner, priority, explicit removal path, observability — is directly applicable to
   Chronicle's open issue #4 (runtime package injection to replace the Mutagen
   NPC-record overrides for avoidance), regardless of which underlying mechanism gets
   chosen there.

6. **Structured event-schema registration with multiple render templates**
   (SkyrimNet's public API: `RegisterEventSchema` with typed fields and four format
   modes — `recent_events`/`raw`/`compact`/`verbose` — plus `interrupt`/TTL flags,
   companion `ValidateEventData`/`FormatEvent` calls). A clean, general answer to "one
   event, many rendering contexts" — exactly what Chronicle's dashboard and a future
   LLM-prompt renderer both need (the same claim rendered as a trace-viewer row vs. a
   prompt-injected fact vs. a rumor-propagation summary). `chronicle/claims.py` has no
   declared per-format-template concept today; worth adding, engine-side.

7. **Role-tagged model routing beyond voice/gamemaster** (SkyrimNet,
   `model-presets/recommended-models.yaml`) — named model "slots" (`default`, `combat`,
   `action_evaluation`, ...), each a ranked fallback list of `provider/model-id` with
   per-entry sampling overrides. Richer than the simple voice-vs-gamemaster split the
   conversation-tier notes currently assume; worth reconsidering if Chronicle ever
   wants, e.g., a cheap model for bulk claim-summarization distinct from the render call.

8. **Escalating stuck/departure recovery as native singletons** (IntelEngine,
   `SKSE/src/StuckDetector.h`/`DepartureDetector.h`) — position-polling with 3-level
   escalation (soft package re-evaluation → progressive teleport at
   2000→1000→500→250 units). Directly reusable for any future ChronicleBridge slice
   that makes an NPC travel/act autonomously — Chronicle has no analog today and would
   otherwise be debugging "NPC pathing silently failed" blind, the same class of
   problem the still-open `game action=load` investigation
   (`docs/design/simple-modlist-milestone.md`) suggests this project is prone to.

9. **Travel via ordinary AI packages/`PathTo` plus teleport-nudge fallback**
   (IntelEngine, `Source/Scripts/IntelEngine_Travel.psc`) — "leapfrog" teleport nudges
   around terrain obstacles as a last resort, `MAX_TASK_HOURS` force-completion so an
   NPC whose destination cell never loads doesn't hang forever. Cheap, concrete,
   worth reusing wholesale rather than reinventing if Chronicle ever ships an
   NPC-travel slice.

10. **SkyrimNet's own version-pin handshake, confirmed real** (IntelEngine,
    `SKSE/src/SkyrimNetAPI.h:139-151` — calls `PublicGetVersion()`, refuses/warns below
    a minimum). This is independent confirmation that report 10's recommended pattern
    (pin one API version, refuse to run on mismatch) is sound field practice, not just
    a theoretical suggestion — someone else already ships it for the same reason
    (SkyrimNet's own churn).

---

## Explicitly do NOT copy

- **Flat per-NPC `.txt` memory files, LLM-re-summarized on overflow** (Mantella,
  `src/remember/summaries.py`). Zero provenance, lossy and nondeterministic
  compaction. Confirms report 07's characterization directly from source. Chronicle's
  ADR-0007 inspectability requirement rules out LLM-driven log compaction categorically
  — the still-open event-log-compaction question in `open-questions.md` must stay
  deterministic, whatever it lands on.
- **Vector-embedding-only memory as a substitute for provenance** (HerikaServer) —
  `text-embedding-ada-002` (deprecated, still hardcoded) nearest-neighbor retrieval
  into a `memory_summary` table. No confidence, no decay, no origin chain; can't answer
  "why does this NPC believe this."
- **Region-flat, unpersonized rumors** (HerikaServer's `rumors` table — keyed to a
  `hold`, not an NPC, with a flat expiry and no propagation/mutation). This is the
  single clearest evidence found that Chronicle's per-NPC, mutating, provenance-tracked
  rumor design is solving a problem nothing else in this space has actually shipped —
  worth stating plainly in any pitch, not hedged as an assumption.
- **String-delimited function-call parsing with no schema enforcement**
  (HerikaServer's `funcret.php`: a bare `explode("@", ...)` split, default
  `argName = "target"`, no type-check or state-grounding before execution) — exactly
  the "trust LLM values inside valid-shaped output" failure mode reports 34/35 warned
  about abstractly. ADR-0011's design (menu-supplied grounding refs, engine validates
  before commit) is a direct, justified improvement over a real shipped alternative,
  not just theoretical caution.
- **870 lines in one un-versioned native-API class** (SkyrimNet's
  `SkyrimNetApi.psc`) — the exact surface shape report 10 already flagged as what broke
  repeatedly (v6→v9 churn). Keep ChronicleBridge's own slice APIs modular and
  independently-versionable, not one monolithic class. Also noted: ~15 near-identical
  copy-pasted hotkey function pairs — a sign of organic growth without a shared
  input-abstraction; don't replicate that structurally.
- **IntelEngine's gossip/memory data model** (`NPCIndex.cpp`'s
  `SetRecentGossipContext` — plain rendered text lines under headers like "## Rumors
  I've Heard," source/time only, no mutation function, no propagation graph). This
  sharpens, not just repeats, report 36's "LLM-written memories, not simulation state"
  characterization: it is literally prompt-context text, not a data structure.
  Adopting this model would reintroduce the exact problem Chronicle's claim/belief
  system exists to solve.

## Also confirmed real (neutral — neither borrow nor avoid, just now verified)

- **IntelEngine's political tick is real game-state, rate-limited** (`FactionPolitics.cpp`,
  driven by `RE::Calendar::GetCurrentGameTime()`, with `max_relation_change_per_tick`,
  `moraleDecayPerTick`, war-cooldowns). It does mutate actual faction/relationship
  ranks, not just narrative flavor — comparable in spirit to Chronicle's hydration
  slice, though simpler (linear decay/caps, no provenance).
- **IntelEngine-NativePlugin uses the same CommonLibSSE-NG + vcpkg stack as
  ChronicleBridge**, plus `sqlite3` for its `MemoryDB`/`PoliticalDB` tables — chosen
  specifically for query/join convenience over its gossip/political data. Worth a
  deliberate future decision on whether Chronicle ever wants local SQLite state on the
  C++ side vs. staying pure-Python-event-log; not an obvious win either way, just now
  a documented real precedent to weigh against.

## Confirmed invisible — do not overclaim insight here

- **SkyrimNet's actual package-injection mechanism** (does it touch `TESForm`, use
  `PutCreatedPackage`, or something else) — the public Papyrus stub gives zero
  implementation detail; entirely inside the closed DLL.
- **SkyrimNet's save/reload handling** — no `OnPlayerLoadGame`-equivalent hook exists
  anywhere in the public Papyrus surface (`skynet_MainController.psc` has only
  `OnInit()`). Must be entirely inside the closed DLL, if it exists at all — see next
  bullet.
- **HerikaServer has no save/reload sync mechanism of any kind** — grepped the entire
  PHP tree for `postLoadGame`/`save_uuid`/reload logic; nothing. State is keyed purely
  by an in-game timestamp (`gamets`) with no fork/branch concept. This means Chronicle's
  hardest unsolved problem (ADR-0005's co-save sync) has **no existing prior art to
  lean on anywhere in this ecosystem** — it's not that Chronicle overlooked an obvious
  solution; the rest of the field hasn't solved it either.
- **SkyrimNet's actual GameMaster decision algorithm** — config keys (cooldown,
  radius) are visible; the selection logic that picks which action to take is not.
- **The "NPCs sending physical letters" feature** attributed to a SkyrimNet submod in
  report 36's Reddit research — zero hits in either IntelEngine repo. Either it lives
  in a third, uncloned submod, or the secondhand Reddit characterization was wrong.
  Flag as unverified; do not carry forward as confirmed.

---

## Evidence quality

All findings above are grounded in direct reads of real files (paths/function/class
names cited throughout), not documentation or secondhand description — a step up in
rigor from reports 07/10/19-21/36's doc-and-community-report-based prior art. Four
independent read-only passes; no cross-checking between them was performed (each mod
was assigned to exactly one pass), so treat any single-codebase claim as one read, not
independently corroborated, the same evidentiary caveat this project's other research
already applies. SkyrimNet's closed core remains a hard evidence ceiling no amount of
further reading of the public repo will lift — anything about its actual runtime
behavior beyond the Papyrus-visible surface would need either a paid/traced live
instance or a statement from the maintainer, not more source reading.
