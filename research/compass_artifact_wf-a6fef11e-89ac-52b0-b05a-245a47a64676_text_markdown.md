# Building a Skyrim SE/AE Social-Simulation Service: What to Build On, Fork, or Study

## TL;DR
- **Integrate with SkyrimNet's extension API for game-side event capture and state injection — don't rebuild that plumbing, and don't fork Mantella or CHIM for it.** SkyrimNet (MinLL) is the only actively maintained framework (a Beta 23 hotfix is the current build as of mid-2026) that already exposes a native Papyrus + C++ API — `RegisterEvent`, `RegisterShortLivedEvent`, `RegisterPackage`, `RegisterDecorator`, `DirectNarration`, plus lifecycle ModEvents — which is precisely the beliefs/rumors/grudges plumbing you need. But it is closed-source (no LICENSE file, DLL not published), so treat it as an integration target, not a fork base.
- **For the external-server transport pattern, study Mantella (Python backend, AGPL-3.0; Papyrus spell, MIT; Leidtier's SKSE_HTTP bridge) and CHIM/HerikaServer (PHP + PostgreSQL in a WSL2 VM, MIT).** Both prove the "external service + Papyrus HTTP bridge" architecture you're planning. MinAI — the previous leader for injecting cross-mod state into LLM prompts — is now **deprecated and no longer maintained**, with its own README redirecting users to SkyrimNet.
- **Your differentiator is the persistent, propagating social graph, and no existing mod occupies that space.** Reputation mods are quest-flag scoreboards, rumor mods are static dialogue injectors, and AI mods track per-NPC conversational memory but never a world-wide belief/rumor/grudge model. Build the simulation yourself in Python, seed it from xEdit-extracted faction+relationship records and UESP, hook events through SkyrimNet's API (with powerofthree's Papyrus Extender + SKSE_HTTP as a fallback path), and inject state back via runtime AI packages and prompt decorators.

---

## Key Findings

### 1. AI-NPC frameworks: SkyrimNet is the live one; Mantella and CHIM are transport exemplars; MinAI is dead

**SkyrimNet — `github.com/MinLL/SkyrimNet-GamePlugin`** *(build on / integrate — best-aligned)*
- **Architecture:** A single in-process SKSE DLL. Per its own Patreon beta announcement, "Unlike other AI projects that require complex external servers or WSL installations, SkyrimNet runs entirely as a single game DLL." It reads game state directly from memory, serves a React dashboard and API on `localhost:8080`, isolates heavy work onto worker threads, and uses seven specialized LLM roles (dialogue, memory, action selection, bio/diary generation, etc.).
- **Extension points (the important part for you):** A documented native Papyrus API (`SkyrimNetApi`) plus a public C++ DLL API. Confirmed functions from the API docs include:
  - `RegisterEvent(eventType, content, originatorActor, targetActor)` — persistent event for historical tracking.
  - `RegisterShortLivedEvent(eventId, eventType, description, data, ttlMs, sourceActor, targetActor)` — TTL-bounded real-time events that don't bloat context (their example: tracking the last spell an actor cast).
  - `RegisterAction`, `RegisterSubCategory`, `RegisterTag`, `RegisterDecorator` — expose LLM-selectable actions and prompt variables.
  - `RegisterPackage`/`UnregisterPackage`/`ScheduleDelayedPackageRemoval`/`ClearAllPackages`/`HasPackage` — **runtime AI-package injection** (directly relevant to overriding NPC behavior).
  - `DirectNarration(content, originatorActor, targetActor)` and `SendCustomPromptToLLM(...)` — force factual events into the world and issue custom prompts with callbacks.
  - Lifecycle ModEvents to subscribe to: `SkyrimNet_SpeechStarted`, `SkyrimNet_MemoryCreated`, `SkyrimNet_DiaryCreated`, and others; plus vector-embedded memory/world-knowledge CRUD, "mark actor busy," and an Inja template system with 100+ built-in decorators (factions, location, time, memory retrieval, combat, equipment).
- **Licensing / maintenance:** **No LICENSE file in the public repo; the compiled `.esp`/`.pex` are generated at build and the native DLL is distributed only via Releases — the C++ core is closed-source.** Treat the public repo (Papyrus ~70%, HTML/JS/CSS) as reference and integration surface only. Actively maintained: a Beta 23 hotfix is the latest build ("Fixed a compatibility issue that was causing a CTD for players on version 1.6.640 of Skyrim"), following a steady beta cadence through 2026 (35 releases, 700+ commits).
- **Ecosystem already building on it:** SeverActions (38+ NPC actions, survival, arrest, relationship persistence via cosave), IntelEngine (an NPC-autonomy "Story Engine" DM that observes world state every few in-game hours and schedules NPC travel/meetings/deliveries). These are direct proof that third parties can build exactly the kind of world-state-driven system you want on top of SkyrimNet's action-YAML + event API.
- **Assessment: Integrate, don't fork.** Its `RegisterEvent`/`RegisterPackage`/decorator model is the shortest path to injecting your social state into prompts and behavior. Risk: closed DLL and an unstated license mean you cannot legally redistribute or modify its binary, and its API can change between betas.

**Mantella — `github.com/art-from-the-machine/Mantella` (+ `Mantella-Spell`)** *(study the transport)*
- **Architecture:** The cleanest example of the exact split you're building. A Python backend (`Mantella.exe`) runs an HTTP server; the Skyrim side is a Papyrus "spell" mod driven by a Quest that tracks the active conversation and receives updates as events. Communication moved from file read/write to HTTP in the v0.12 "Road to HTTP" rework (issue #230, PR by Leidtier), using Leidtier's SKSE_HTTP plugin so Papyrus can POST JSON and receive replies through a ModEvent. Conversation summaries are persisted per NPC as local text files; NPC bios come from a `skyrim_characters.csv`.
- **Licensing:** The Python backend is **AGPL-3.0**; the `Mantella-Spell` Papyrus mod is **MIT**. Bio content uses CC-BY-SA from the Elder Scrolls wiki. AGPL matters: if you fork the backend and expose it over a network, you must publish your source.
- **Maintenance:** Actively maintained; v0.14 is the current GitHub release (April 2026), following the v0.13 Nexus stable (Feb 2025). Forks worth knowing: **Pantella** (Pathos14489, more transparent launcher, 1,000+ NPC bios) and a Fallout 4 fork.
- **Assessment: Study, and optionally target as a second transport.** The Quest-tracks-conversation + HTTP-events pattern and the CSV bio pipeline are directly reusable ideas. Don't fork the AGPL backend unless you're prepared to open-source your service.

**CHIM / HerikaServer — `github.com/abeiro/HerikaServer` (Dwemer Dynamics)** *(study the event log + plugin model)*
- **Architecture:** A self-contained WSL2 Debian VM ("DwemerDistro") running Apache2 + PHP with a **PostgreSQL** database, bridging the SKSE plugin (AIAgent.esp) to AI providers (OpenRouter, ChatGPT, Deepgram, XTTS, MeloTTS, koboldcpp). Requires SKSE, powerofthree's Papyrus Extender, SkyUI, and PrismaUI.
- **Directly relevant features:** CHIM keeps an **"Events" log — a timestamped chronology of every in-game event** — and NPCs pull the most recent N events into their prompt context (this is essentially a primitive version of your event stream). It has "deep world awareness" of conversations and gameplay events, per-NPC long-term memory, dynamic biographies that update during play, an Oghma RAG system that injects lore, and a "send faction and location info" one-time sync to the server. There is a documented **plugin system**: modders bind a Papyrus script to the `CHIM_CommandReceived` ModEvent and register a manifest (`manifest.json` with `git_repo`, SQL `migrations/`), letting external mods add actions and DB tables without writing a server plugin.
- **Licensing / maintenance:** HerikaServer is **MIT** (file `MIT-LICENSE`). Character bios are CC-BY-SA from UESP. Actively maintained (4,000+ commits; issues into late 2025), but no tagged releases and a heavy install footprint (WSL2 VM).
- **Assessment: Study, don't build on.** The PHP/PSQL/WSL stack is exactly what you'd want to *avoid* imposing on users (SkyrimNet exists specifically because "users don't want to install Linux to play a Skyrim mod"). But CHIM's timestamped event log, faction/location sync, and DB-migration plugin model are strong design references for your own service.

**MinAI — `github.com/MinLL/MinAI`** *(study only — deprecated)*
- **What it was:** A "comprehensive enhancement to CHIM" and "bridge between LLMs and various Skyrim Mods" — the leader in injecting *cross-mod* state into prompts. Its Modders' Guide exposed exactly the primitives you care about: five mod-events to push arbitrary key/value state to the server (e.g., a `hunger` key updated to "Min is Very hungry"), plus faction-based action gating (`minai_NoActionsFaction`, etc.). Release 2.0 added guards being aware of the player's bounties across holds and exposed actor relationship rank in prompts — early versions of your beliefs/reputation ideas.
- **Status:** **Deprecated.** Its README states: "This project is no longer maintained. Please use SkyrimNet instead as an alternative to CHIM/MinAI." Last release 2.1.3 (April 2025). No LICENSE file (all-rights-reserved).
- **Assessment: Study the ModdersGuide for its key/value state-injection and faction-gating design, then use SkyrimNet's live API instead.**

---

### 2. SKSE event hooking and existing event-forwarding bridges

**What you can hook natively (Papyrus, via Actor/ObjectReference/Cell scripts):**
- **Deaths:** `OnDeath` / `OnDying`, `OnEnterBleedout`.
- **Combat/violence:** `OnCombatStateChanged`, `OnHit`.
- **Crimes:** Story Manager quest-start events including **crime gold**, **discover dead body**, assault, plus theft/pickpocket via faction and crime-gold checks; assault is also trackable via the "Player assaulted this NPC" faction.
- **Cell attach/load:** `OnCellAttach` (reference's parent cell attached), `OnCellDetach`, `OnCellLoad` (fires every time the cell loads, possibly multiple times per session), `OnLocationChange`. `Cell.IsAttached()` tells you if a cell is in the loaded area.
- **Dialogue/quests:** quest-stage fragments, Story Manager dialogue events; SkyrimNet additionally exposes quest journal prompts.
- **Item transfers:** `OnItemAdded` / `OnItemRemoved`, `OnContainerChanged`; PAPER adds batch variants.
- **Packages/schedule:** `OnPackageStart` / `OnPackageChange` (know when an NPC changes behavior); plus `OnSit`/`OnGetUp`, `OnEquip`/`OnUnequip`, `OnActivate`.

**Extender plugins that add more events:**
- **powerofthree's Papyrus Extender** (`github.com/powerof3/PapyrusExtenderSSE`; Nexus 22854): the current build advertises "over 442 new Papyrus functions, and 82 events" — including filtered hit events (`RegisterForHitEventEx`/`OnHitEx`), magic-effect/active-effect events, weather-change, and payload animation events. Open-source (source on GitHub), and a near-universal dependency (CHIM requires it). **Use this as your primary event-expansion layer.**
- **Kris's Papyrus Extender** (Nexus 115164) and **PAPER** (`github.com/DennisSoemers/PAPER`): additional functions/events, notably `OnBatchItemsAdded`/`OnBatchItemsRemoved` and impact events.

**Bridges to external processes (the transport question):**
- **Leidtier's SKSE_HTTP plugin** (`github.com/Leidtier/SKSE_HTTP`): the mechanism Mantella uses. It lets Papyrus build strongly-typed dictionaries, serialize them to JSON, send HTTP requests, and receive replies via the `SKSE_HTTP_OnHttpReplyReceived` / `SKSE_HTTP_OnHttpErrorReceived` ModEvents. This is the single most important existing component for a "Papyrus → your Python server" path if you don't go through SkyrimNet. *(License unconfirmed — verify the LICENSE file at the repo directly before redistributing; it is a native C++ SKSE DLL.)*
- **Skyrim Platform** (part of skymp, `github.com/skyrim-multiplayer/skymp`; **GPL-3.0**): a full JavaScript/TypeScript runtime inside the Skyrim process, with a rich `on(event)`/`once(event)` system (equip, etc.), engine-function **hooks** (`sendAnimationEvent`, `sendPapyrusEvent`), and the ability to call SKSE functions natively. Heavier dependency for users, GPL forces source disclosure of forks, but by far the most flexible way to observe and intercept events if you want to write your bridge in TS rather than C++.
- **Custom SKSE plugin:** the `SkyrimScripting/SKSE_Template_WebSockets` template (CommonLibSSE-NG, supports SE/AE/GOG/VR) shows how to communicate out of Skyrim over WebSockets — a clean starting point if you decide to write your own thin C++ event-forwarder rather than depend on SKSE_HTTP.

**Assessment:** If you integrate with SkyrimNet, you get event capture and injection through its API and rarely touch SKSE directly. If you go standalone, the proven stack is **powerofthree's Papyrus Extender (events) + SKSE_HTTP or a WebSockets SKSE plugin (transport)**, or **Skyrim Platform** if you prefer TS and function-level hooks.

---

### 3. Runtime AI-package override and cell hydration

- **Static overhauls (study for schedule data, don't build on):** **Immersive Citizens – AI Overhaul** (Nexus 173) and **AI Overhaul SSE** (Nexus 21654) rewrite NPC schedules and behavior, but through **ESP records applied at load, not at runtime**. They are mutually incompatible, highly load-order-sensitive, and Immersive Citizens is effectively frozen and hostile to third-party patching (author locked comments; community reports of save corruption). They demonstrate Skyrim's package-priority model — vanilla quest AI and mods like Wet & Cold / Holidays apply packages at higher priority than these overhauls, which is the exact conflict surface you'll face if you push runtime packages.
- **Runtime package injection (the clean path):** SkyrimNet's `RegisterPackage`/`UnregisterPackage`/`ScheduleDelayedPackageRemoval` is the best available runtime API; IntelEngine already uses SkyrimNet packages to make NPCs physically travel and act. If standalone, you apply/remove packages via Papyrus (with powerofthree helpers) keyed off your social state.
- **The cell-hydration problem you must handle:** NPCs only exist as fully-simulated actors when their parent cell is attached; outside that they are inert. Track attach/detach with `OnCellAttach`/`OnCellDetach` (or SkyrimNet's nearby-actor awareness / auto-activate distances) to know when to *hydrate* an NPC (apply grudge-driven packages, inject beliefs into context) and *dehydrate* (persist state to your DB, stop pushing per-frame data). Also account for a known engine limitation, solved by **NPC AI Process Position Fix – NG** (Nexus 69326): Skyrim only updates an unloaded NPC's schedule position for at most one hour, so after the player waits/sleeps/fast-travels, off-screen NPCs won't be where their schedule says. If your simulation reasons about NPC locations while cells are detached, you must model this yourself or depend on that fix.

---

### 4. Reputation / rumor / dynamic-consequence mods — what they built and why they stalled

- **Skyrim Reputation** (dcyren; Nexus SE 22374, also 95269): assigns good/evil morality points across categories, amplified by a "fame" rating into an overall reputation and titles; guards and NPCs react and greet accordingly, toggleable in MCM. **Why it's limited:** it's a global quest-flag/morality scoreboard, not a per-NPC or propagating model — reputation is a single number, not knowledge that spreads. It conflicts with mods that alter quest outcomes. A community fix exists ("Skyrim Reputation – Fixed and Patched," Nexus 42538) plus Enai-mod patches, indicating the original stalled and needed community upkeep.
- **Rumors of Skyrim / Rumors of Skyrim Voiced** (Nexus SE 177826) and **Rumors like in Oblivion** (Nexus 21002): inject 50–59 new townsfolk dialogue lines where NPCs comment on murders/thefts/pickpocketing in their own and sometimes other cities, with an optional "crime framework" that gates lines by crime counts. **Why they stall:** these are **static dialogue pools triggered by crime-gold thresholds**, not a rumor-propagation system — no NPC actually *learns*, *believes*, or *forwards* anything; the "framework" is a counter.
- **NPCs React To Necromancy (And More)** (Nexus 70428): cooldown-gated reaction lines to summoned/undead creatures — again reactions, not persistent state.
- **NPC Reactions / NPCs React to Custom Races** (Nexus): react to worn faction armor, race, location — condition-driven dialogue, no memory.
- **The gap and the lesson:** Every prior attempt used **static dialogue or a single global flag** because vanilla Skyrim gives you cheap ways to *react* but no substrate for *state that changes and spreads*. That is exactly the void an external Python service fills — and confirms your core thesis. Study these for their crime-detection triggers (crime gold, dead-body discovery) as event inputs, but expect to build the belief/rumor propagation model from scratch.

---

### 5. Data sources for NPC roster, factions, and relationships

- **UESP (CC-BY-SA):** `Skyrim:People` lists all named NPCs; `Skyrim:Factions` (and A–Z sub-pages) documents the game's **1,475 faction pages** with member lists and interrelationships; `UESPWiki:CSList` is a raw record browser for NPC_/faction/relationship records across Morrowind/Oblivion/Skyrim. Authoritative for human-readable roster and lore, and the source both CHIM and Mantella already cite for bios.
- **Creation Kit / xEdit (authoritative machine-readable):** Faction records (rank, combat-reaction) and **Relationship (RELA) records** encode NPC-to-NPC dispositions (parent/sibling/friend/enemy, etc.). These drive vanilla behaviors like hired thugs and "you killed my friend" letters. This is the ground truth to seed your grudge/relationship graph. Note there is no built-in Papyrus function to list all NPCs related to a given actor — you must extract RELA records offline (via xEdit scripts) and build the reverse index yourself.
- **Ready-made extraction tools/datasets:**
  - **Info NPC Extractor xEdit Script** (Nexus SE 159144): Pascal/xEdit scripts that export detailed NPC_ and ACHR records (name, factions, AI data, race) to CSV/INI, explicitly built for Mantella/CHIM/SPID pipelines. **Best starting point for extracting your own load-order-accurate dataset.**
  - **"NPCs Have Relationships"** (Nexus SE 140482): a relationship-setting mod whose author reports, verbatim, "586 relationships across 397 NPCs, according to xEdit. I don't really believe that. I'm probably reading it wrong." — a useful sanity-check on how sparse vanilla RELA data actually is (you will need to synthesize many relationships).
  - **Kaggle "People of Skyrim"** (`kaggle.com/datasets/muhajipra/people-of-skyrim`): a scraped dataset — "acquired by using Beautiful Soup 4 to scrape the data from infobox of each character listed in en.uesp.net/wiki/Skyrim:People ... the total number of named characters are 1009." Scraper source at `github.com/muhajipra/scrapeskyrimwiki`. Convenient for prototyping, but verify against your actual load order.
  - **The Imperial Library** hosts cleaned game-data exports for TES titles.

---

## Recommendations

**Stage 1 — Prototype against SkyrimNet (2–4 weeks).**
Build your Python social-simulation service as a standalone process with a clean internal event bus. Write a thin SkyrimNet integration that (a) subscribes to SkyrimNet lifecycle ModEvents and registers your own events via `RegisterEvent`/`RegisterShortLivedEvent`, and (b) injects social state into prompts via `RegisterDecorator` (e.g., a `{{grudge_context(npc.UUID)}}` decorator) and behavior via `RegisterPackage`. This gets you end-to-end fastest because SkyrimNet already solves event capture, memory, and prompt assembly.
- *Benchmark to proceed:* you can make an NPC's dialogue reflect a grudge you injected from your DB, and drive a package change from social state.
- *Threshold to change course:* if SkyrimNet's closed DLL/unstated license blocks your distribution model, or its API proves too unstable across betas, fall back to Stage 2.

**Stage 2 — Build a transport-independent bridge (parallel track / fallback).**
Abstract your transport so the same service can talk to Skyrim through **either** SkyrimNet **or** a standalone bridge: **powerofthree's Papyrus Extender** (events) + **Leidtier's SKSE_HTTP** or a small **CommonLibSSE-NG WebSockets plugin** (transport). Consider **Skyrim Platform** (GPL-3.0) if you'd rather write the in-game side in TypeScript with function-level hooks. This insulates you from any single framework's fate.
- *Threshold:* adopt the standalone bridge as primary if you need to ship without a SkyrimNet dependency or want a permissive license end-to-end.

**Stage 3 — Own the social graph and seed it.**
Extract faction + RELA + NPC data with the **Info NPC Extractor xEdit script** against your target load order; cross-reference UESP/Kaggle for names and lore. Store beliefs/rumors/grudges/relationships in SQLite or Postgres. Model rumor **propagation** explicitly (who knows what, confidence, source, decay) — this is your novel contribution; nothing in the ecosystem does it. Handle **cell hydration** by persisting NPC state on `OnCellDetach` and re-applying packages/context on `OnCellAttach`, and account for the schedule-update engine limitation (bundle or recommend NPC AI Process Position Fix – NG).

**Stage 4 — Consume, don't fork.**
Fork nothing. Study CHIM's timestamped **event log** and DB-migration **plugin manifest** model, Mantella's **Quest-tracks-conversation + HTTP-events** pattern and CSV bio pipeline, and MinAI's **key/value state-injection and faction-gating** design — then implement your own. If you ever want to distribute NPC bios, reuse UESP/wiki text under CC-BY-SA with attribution, exactly as CHIM and Mantella do.

---

## Caveats
- **SkyrimNet is closed-source with no declared license.** You can integrate against its public API, but you cannot legally redistribute or modify its DLL, and it can change the API between betas. Confirm licensing terms with the author before building a commercial or widely-distributed product on it.
- **License traps:** Mantella's Python backend is **AGPL-3.0** (network-copyleft — forking and serving it obligates source disclosure); Skyrim Platform is **GPL-3.0**. HerikaServer and Mantella-Spell are MIT. **Leidtier's SKSE_HTTP license is unconfirmed** — verify its LICENSE file before depending on/redistributing it. MinAI and SkyrimNet have no LICENSE file (all-rights-reserved by default).
- **An engine update is coming.** SKSE's site notes Bethesda announced an incoming Skyrim update (posted Aug 14, 2026) — historically these break every native SKSE plugin (SkyrimNet, SKSE_HTTP, Papyrus Extender, Skyrim Platform) until updated. Design your service so the Python/DB side keeps running and only the thin in-game bridge needs a rebuild.
- **Cell hydration and off-screen simulation are the hard parts.** Skyrim does not simulate detached-cell NPCs and only updates their schedule position for up to one hour after wait/sleep/fast-travel. Any belief/location reasoning your service does about off-screen NPCs must be modeled entirely on your side; the game will not reconcile it for you.
- **Vanilla relationship data is sparse** (~hundreds of RELA records across ~1,000+ named NPCs). Expect to synthesize most of your relationship/faction-affinity graph rather than harvest it, and validate any extracted dataset against the user's actual load order, since modded NPCs won't appear in UESP/Kaggle scrapes.
- **Source-quality note:** exact function/event counts and version/date figures were taken from the mods' own repos, Nexus pages, and official docs; where a repo lacks a LICENSE file, "all-rights-reserved" is inferred from the absence of a license rather than an explicit statement, and the SKSE_HTTP license remains an open item to verify directly.