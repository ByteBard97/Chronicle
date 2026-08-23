# Prior Art in Reactive-NPC and Social-Consequence Mods for Skyrim

**Research report — Prompt 1 (mod survey + community record)**
**Prepared:** August 2026 · **Scope:** Skyrim LE/SE/AE/VR, Oldrim through 2026 · Text-only report (no graphs or plots, per request)

---

## 0. Method, scope, and caveats

This report surveys (A) every mod lineage I could find that attempted simulation-driven NPC reactivity — reputation/consequence, NPC-life simulation, rumor/news propagation, and world-state consequence — and (B) the community record around them: wishlist threads, practitioner explanations of why the wished-for thing is hard, and reception evidence for the closest attempts.

Method notes and honesty caveats:

- Web search with `site:reddit.com` operators was used as instructed, supplemented by Nexus mod pages, Nexus forum archives, the AFK Mods archive, UESP, GitHub project documentation, and long-form technical writeups. Reddit thread bodies were retrievable through search indexing but Reddit pages themselves were not directly openable from this environment, so Reddit quotes come from indexed snippets; I quote only what the index returned and mark close paraphrase as such. Thread URLs are given so you can pull full context.
- Thread dates matter and are noted where known. Oldrim-era (2011–2015) claims about Papyrus limits predate mature SKSE64, po3's Papyrus Extender, JContainers, SPID, and Skyrim Platform; several 2013–2015 "impossible" claims are now merely "hard."
- The AI-dialogue frameworks (Mantella, CHIM, SkyrimNet) are not the subject, but they matter twice here: as the current state of the art in NPC memory, and as the reference point for the community's "they talk but nothing changes" complaint pattern. They are covered in A3 and B-c.
- Where a mod's existence is well-attested but a detail (e.g., authorship of a port) was not confirmed, I say so rather than guess.

---

## 1. Executive summary

**The headline finding: your core mechanic — NPC-to-NPC information propagation with provenance — has essentially never been shipped in the non-LLM modding era, and the community has been asking for it, in various phrasings, for over a decade.** The closest attempts are:

1. **Per-NPC memory of the player**, tried once seriously in the pre-SKSE64 era (kuertee's *NPC Reactions*, 2015) and once at AAA-adjacent scope (*Shadow of Skyrim*, 2022) — both bounded, player-centric, and neither propagates anything between NPCs.
2. **Global/telepathic reputation** (Skyrim Reputation, crime overhauls) — tracks player deeds but deliberately *assumes* what NPCs would know rather than modeling knowledge flow.
3. **Rumor broadcast, not propagation** (Skyrim Town Criers, 2025; vanilla's rumor-as-quest-trigger system) — one-to-many announcement keyed to quest stages, no mutation, no spread.
4. **LLM-era systems** (CHIM's Background Life, SkyrimNet's World Knowledge + the IntelEngine plugin's "gossip chains") — the first actual NPC-to-NPC information movement, but as generated text with no mechanical effect on schedules, disposition, or AI packages.

The walls everyone hit are well documented and cluster into five: (1) Papyrus VM throughput and the polling anti-pattern; (2) save bloat / orphaned script instances, and the resulting "never uninstall scripted mods" culture; (3) the engine only running AI processing on NPCs in loaded cells (with a known one-hour position-update bug on top), so off-screen simulation is impossible in-engine; (4) the voice constraint — every reactive line must exist as audio, forcing splicing, silent-voice hacks, or AI voice generation; and (5) the persistence/transience tradeoff — SKSE-side distribution (SPID) is free of save bloat precisely because it writes nothing to the save, which means it can't carry state either.

Your external-process architecture directly bypasses walls 1–3 for the *simulation* side, and the LLM mods have already proven the *injection* side at scale (SKSE plugin ↔ external process, state read from memory, results pushed back in). The walls that remain on the injection side are 4 (surfacing state as voiced dialogue) and a subtler one: any state you inject that must survive a save/reload either goes into the save (bloat risk returns) or must be re-injected each session (SPID's model).

---

# PART A — The mod survey

## A1. Reputation and consequence mods

### A1.1 Skyrim Reputation (dcyren, 2013 LE / 2019 SE) — the canonical dedicated reputation system

The most direct precedent for "track player deeds and change NPC treatment." Nexus SE ID 22374.[^9^]

- **What state is tracked:** A continuously accumulated morality score (quest completions, tracked crime statistics — assaults, murder bounties, petty crime bounties, bandit kills — race, build, Daedric vs. Aedric allegiance), multiplied by a "fame" score earned from quests, producing a good/bad reputation along three authored dimensions: Aedric-devotion vs. Daedric-worship, Lawfulness vs. Crime, Dependability vs. Power-hunger. About 3/4 of the game's quests are scored.[^9^]
- **Per-NPC or global:** **Global.** The author's own FAQ is unusually candid about the epistemics: the mod "makes assumptions about how a regular Skyrim Nord might respond to such a person or someone they knew had done similar things." There is no witness model and no information propagation; reputation is an inferred public gestalt.[^9^]
- **Witnessed-only or telepathic:** Telepathic-by-design, with a crime-statistics lag (stats only accumulate after install; up to one in-game day to recalculate).[^9^]
- **How it surfaces:** Voiced NPC comments spliced from existing sound files (which is why non-English translations are unsupported — the composites have no matching localized audio), thane recognition, faction ally/hostility changes toggleable in an MCM.[^9^]
- **Limits and postmortem evidence:** The maintenance history is itself evidence. *Skyrim Reputation Improved* (2021, Nexus 52416) exists to fix: assault counts "randomly increasing," quest-related NPCs wrongly included, thanes not recognized outside city bounds, Cidhna Mine prisoners turning hostile — and it *adds* deeper tracking the original couldn't do, explicitly "Requires Papyrus Extender" for black-soul-trap and cannibalism tracking, and JContainers for preset persistence.[^11^] In other words: the 2019 original hit the ceiling of plain Papyrus + base SKSE event coverage, and the community patch needed po3's Papyrus Extender (2020s SKSE maturity) to go further.
- **Reception (preview of Part B):** "Worth it for immersion, but it's not a fundamental change to the game. In the early game it makes a big difference…"[^156^] — the recurring verdict is that it is a flavorful but shallow global overlay.

### A1.2 The crime-overhaul lineage (witness mechanics, not reputation)

- **Crime Overhaul** (SE, Nexus 19647, 2018): rebalances bounties, arrest dialogue, punishment severity. Compatibility notes show the standard posture: load below USSEP, patch against Contraband Confiscation, and its own "recommended mods" list is the witness-sanity stack — NARC (stops animals reporting crimes), Crime Bounty Decay (bounties decay while you're outside the hold).[^80^] A 2015 Nexus forums WIP thread for a "Skyrim Crime Overhaul" shows the design ambitions of the era (hire mercenaries to "teach someone a lesson," conspiracy-to-commit-murder fallout) and the author openly learning skills to build them — a typical abandoned-WIP trajectory.[^78^]
- **The witness problem they patch:** Vanilla's crime system is itself the community's favorite example of fake consequence. Bounties are tracked per-hold (nine holds plus the Companions, Orc strongholds, and Raven Rock separately), animals can be witnesses, and killing all witnesses erases the bounty.[^148^] The Hired Thugs event is the canonical "nothing happened" mechanic: even an unseen theft or murder can spawn thugs, and the note they carry naming the person who hired them "will have no effect on your future relations with that NPC — you won't even be able to confront them about it. In other words, the game will treat the event as though nothing had ever happened."[^148^]
- **Realistic AI Detection (RAID)** (OlivierDoorenbos): adjacent but instructive — a *script-free*, 45-GMST recalibration of the detection formula (view cones, light, search durations, reduced NPC "wall-hacking"). Notably for your architecture survey: it demonstrates how much perceived NPC intelligence can be bought with zero scripts, zero persistence, and zero save impact, purely by retuning engine constants — and its documentation is a goldmine on how the detection formula actually works (including that only imagespace "Sunlight Scale" and weather "Ambient/Sunlight" feed detection lighting, so ENB darkness is invisible to NPCs).[^123^]

### A1.3 Master of Disguise (fireundubh) — faction-level reactive state, and its documented failure mode

Turns equipped faction armor into faction membership: discovery rolls combine Sneak/Illusion skill, behavior, race, and disguise coverage into an identity score rolled against 0–99; race/faction bias tables (e.g., Altmer bonus with Thalmor, penalty with Stormcloaks); witness handling ("If the NPC is dispatched without any witnesses nearby, the player's disguise will be restored"); and a full faction-relations overhaul where opposing factions react to your disguise.[^5^]

The instructive part for you is the *community postmortem* on its epistemics. A Nexus forums troubleshooting thread contains this practitioner critique (paraphrase/quote from the indexed text): the "steal a sweetroll and every guard in the country instantly knows" mechanic is clumsy; boots-and-robes worn for two seconds "marking you forever as part of the Necromancer faction… is a terrible mechanic. It should not kick-in until you have interacted with NPCs… And it should never have a permanently global effect."[^10^] That is precisely your provenance thesis stated as a bug report, in 2019.

### A1.4 Shadow of Skyrim — Nemesis and Alternative Death System (Syclonix, 2022) — the closest shipped thing to per-NPC relationship memory

Nexus SE ID 65136, SKSE + SkyUI required, SE/AE/VR only.[^3^]

- **What state is tracked:** Up to 5 Nemesis slots and 5 combined debuff/reward-buff slots — deliberately *bounded* state. An enemy who defeats you gets a unique generated name, title, stat boosts, a situational buff, and can take and *use* your gear; you get a situational debuff and a revenge quest; state persists across sessions because death is converted to respawn instead of reload (avoiding both save-reload state loss and the save-reload bug).[^3^]
- **Per-NPC or global:** Per-NPC, player-centric only. The author is explicit about what the system deliberately does *not* do — and the list reads like a patent-avoidance map of Shadow of Mordor's social layer: "No Interactions between Nemeses… No Changes to a Second Nemesis Based on Player Interactions with a First Nemesis… No Factions/Faction Manager… No Hierarchies… No Social Vendettas."[^3^]
- **Mechanism:** SKSE event-driven (defeat events), quest-aliased tracking, MCM configuration. Distribution posture: "Do not uninstall this mod (or any scripted mods) mid-playthrough," must sit at the end of load order, do not merge, do not change FormIDs — the standard scripted-mod persistence constraints.[^3^]
- **Why it stopped where it did:** The author (Syclonix/SoloManGames) "has moved on to create his own game," per a 2025 Nexus forums thread requesting an "Encounter Overhaul" continuation — whose wishlist is exactly your feature set: nemeses who *recognize and taunt you* on re-encounter, react to how the first fight went, and present fate choices (kill/spare/report).[^2^] Reception was strongly positive (IGN coverage; FudgeMuppet calling it one of "the Skyrim mods we've desired for a long time"; the forum thread calls it "the best alternate death mod. It actually brings enemies to life").[^12^][^7^][^2^]

### A1.5 Recognition-surface mods (where reputation becomes audible)

These don't track much state themselves, but they are the shipped art of *surfacing* state through dialogue conditions — directly relevant to your injection layer.

- **Guard Dialogue Overhaul (Eckss; SE port Nexus 22075):** guards' attitude ramps with your quest-earned standing; "optimised conditions and item detection"; fixes the "guards keep following me" bug; and — technically notable — publishes its global values through the injected "SPIKE" compatibility system "so other mods can reference them freely."[^18^] GDO is the proof that a dialogue-conditions-plus-globals architecture can carry a convincing reputation *surface* with essentially no runtime cost.
- **Relationship Dialogue Overhaul (cloudedtruth):** 5,000+ spliced lines across 50+ voice types keyed to relationship rank (friends, rivals, spouses, followers); rivals get escalating insults and eventually refuse dialogue; service refusal when disliked.[^17^] The author's own performance statement is a practitioner data point: RDO "is NOT script heavy… There's nothing that's actively checking around the player or constantly polling for updates all the time" — the condition-evaluation model (engine evaluates conditions when dialogue triggers) is the cheap path; active scanning is the expensive one.[^17^]
- **Immersive Speechcraft SE (SirSalami; original by another author):** adds follow/barter/command/gift/beg/trick/fight/train/weather options to all generic-voiced NPCs via "1000+ voice files renamed and reused," Speech-skill-gated, with per-NPC cooldowns.[^83^] Notably, uniquely-voiced NPCs are excluded — the voice-type wall again.
- **"Don't You Know Who I Am?"** (LE-era fame dialogue mod): known to me only via Skyrim Reputation's documented incompatibility ("Speech options not affecting Skyrim Reputation and vice versa")[^9^] and a 2015 r/skyrimmods request for similar mods[^25^] — evidence of the persistent "NPCs should acknowledge my fame" demand.
- **Wintersun — Faiths of Skyrim (Enai Siaion):** the favor-system lineage: per-deity favor 0–100% raised by tenet-following, decaying on taboo violation, granting scaled abilities. Author's claims: "Lightweight scripts, no save bloat," removable mid-playthrough.[^71^] Mechanically it is a *private* two-party ledger (player↔deity), not social state — but it is the most polished shipped example of accumulating, decaying, behavior-conditioned standing, and its implementation trick is documented: favor scaling is implemented via the unused VoicePoints/VoiceRate actor values (and conflicts with any other mod using them).[^71^]

### A1.6 NPC Reactions (kuertee, LE 2015) — the Oldrim deep attempt and its era's walls

The most under-cited precedent. Nexus LE ID 65243.[^107^]

- **What it did:** NPCs react to your worn faction gear (Stormcloak/Imperial/Thalmor/Thieves Guild/Dark Brotherhood), clothing class, and location; guards who see you in DB/TG gear or sneaking *follow you*; homeowners watch you indoors; corpses in cities get attended. Crucially: **"NPCs will remember you for 24 hours (or a month if you're wearing Dark Brotherhood gear)"** — configurable per-reaction memory timers (24h / 720h defaults, up to a year), a genuine per-NPC memory of observed player state.[^107^]
- **Mechanism and limits:** On-the-fly scripted evaluation of nearby NPCs (with a visible failure mode — a silent "…" response means "the mod is currently evaluating their appropriate reaction"), FISS/INI/console configuration. The page's troubleshooting section is Oldrim Papyrus-wall evidence in the wild: instructions to check Papyrus logs for "Suspended stack count is over our warning threshold, dumping stacks," with the author's linked Bethesda-forums guide on cleaning the resulting damage.[^107^]
- **Why it stopped:** No SE port ever appeared (the author had a broad LE catalog and left the scene); the design was CPU-bound on the Papyrus VM doing proximity evaluation — precisely the workload the VM is worst at.

---

## A2. NPC-life simulation mods

### A2.1 The Immersive Citizens / AI Overhaul lineage

- **Immersive Citizens — AI Overhaul (Shurah, 2015 LE → SE):** rebuilds NPC root AI: survival instinct (flee/hostility-avoidance), weather-aware sheltering, sleep/eat/visit behaviors, combat-style overrides, plus manual navmesh fixes. The author's own FAQ documents both mechanism and walls: conflicts are overwhelmingly *navmesh and load-order* conflicts (city overhauls breaking NPC movement, NPCs clustering or getting stuck), and the FAQ casually documents the **cloak-spell technique and its failure mode** — mods adding a hidden cloak spell on the player to "add new abilities to nearby NPCs through a scripted magic effect," which makes NPCs think you're attacking them.[^122^] The FAQ also asserts NPCs can't get permanently stuck indoors under IC and blames Run For Your Lives for a stuck-NPC bug — contested-community lore, but useful as author-stated design rationale.[^122^]
- **AI Overhaul SSE (SpiderAkiraC):** the community's current default. The recurring Reddit verdict across multiple comparison threads: IC "adds more interesting changes, but also adds objects, which cause compatibility issues. AI overhaul has a simpler…"; "AIOH is more updated and newer and more compatible, Immersive Citizens has extremely specific scripted behavior"; and the compatibility story that decided it — "AI overhaul has a Synthesis patcher so it's way more compatible."[^15^][^20^][^31^]
- **What they simulate vs. stage:** Both *re-drive* the existing package/condition system — they are better-authored inputs to the same engine scheduler, not a simulation layer. Nothing about what an NPC *knows* changes; only where it goes and what it flees from.

### A2.2 Arthmoor's event-driven pair: Run For Your Lives / When Vampires Attack

Citizens flee indoors during dragon/vampire attacks; guards/Companions/Vigilants/followers fight. Mechanism is documented and elegant: spawned dragons detected **via animation events**, hand-placed dragons via combat-state changes, vampire attacks via their spawn events; NPCs picked "first come, first serve by the game engine" **up to a limit of 150** — a hard cap on per-event processing that is itself an engineering-evidence data point.[^36^] The 2021 v3.0 merged When Vampires Attack into one package.[^38^] Long-running community confirmation that the pair (and IC) coexist, with the usual compatibility folklore.[^33^][^35^]

### A2.3 The hard engine wall under all of them: AI processing only happens in loaded cells

The single most important practitioner fact for your architecture, stated by a mod that exists to patch it: **NPC AI Process Position Fix - NG** (Maxsu/doodlum): "Skyrim's engine has a limitation where it could only update an NPC's AI process position for one hour at most if that NPC is loaded in current loaded cells… when you are waiting or sleeping in an inn all night, the NPCs won't go home… the loaded NPCs in the fast travel destination will not update their daily life schedule positions." The SKSE fix detects wait/sleep/fast-travel and force-updates positions — with documented failure modes (visible fade-in, teleports, failure "when you have too many NPCs loaded in a cell or the game is under high-load"), and explicit non-support for NPCs in scenes, in combat, or driven by quest-alias packages.[^115^] The OpenMW community states the general version bluntly: "AI on NPCs isn't processed unless they are loaded, nor are scripts ran."[^121^] **Implication: no in-engine mod can simulate off-screen NPC life; the engine does not run those actors. Your external process doesn't just bypass a performance constraint — it bypasses an absence-of-execution constraint.**

### A2.4 Travel, schedules, marriage, and social-logic dressing

- **Travellers of Skyrim (SE Nexus 1973):** 50 new NPCs randomly traveling between 18 inns and profession locations, eating/chatting/sitting on arrival; killable, respawning.[^126^] Staged autonomy: packages choose destinations randomly; nothing is remembered or communicated. The Nexus forums thread on "How can you make NPCs Travel throughout Skyrim" documents the underlying technique (patrol markers, LinkRef chains, preferred road pathing) and its emergent quirks.[^128^] NPCs Travel (skyquest) plus a community MCM covers similar ground.[^125^]
- **Marriage Mod — To Have and To Hold:** divorce, remarriage on spouse death, polygamy to 11 spouses, spouse relocation to faction homes — quest-script state, not simulation.[^127^]
- **Realistic Conversations / Social NPCs / Chatty NPCs and Followers:** the social-*texture* layer. Realistic Conversations is **completely script-free** — GMST/social-logic edits so NPCs talk to each other more, greet the player less robotically, with cooldown memory of who they've talked to (engine scene cooldowns).[^118^] Social NPCs raises NPC-NPC scene frequency.[^116^] Chatty NPCs adds ~1,500 spliced vanilla lines for NPC-NPC greetings, health inquiries, and follower interactions, with 3–6 hour cooldowns and proximity gating ("only trigger if both NPCs are fairly close to the player") — note the gating: ambient social life only exists near the player, by design, because that is when the engine runs scenes.[^113^]
- **Interesting NPCs (3DNPC, Kris Takahashi):** 250+ voiced NPCs with *interconnected* static references (NPCs talk about each other, location-based follower commentary) — the hand-authored ceiling of "NPCs know each other": rich but frozen at authorship time.[^144^]

---

## A3. Rumor and news propagation attempts (your core mechanic)

**Short version: there is no shipped non-LLM mod that spreads information between NPCs. Everything below is either broadcast, hand-authored, or LLM-era. This gap is corroborated by the community record in Part B — a 2024 r/skyrimmods thread asking "Are there any npc gossip mod?" received exactly one substantive answer ("Denizens of Morthal is the only one I know of").**[^24^]

1. **Vanilla's own "rumor" system** is quest triggers wearing a trench coat: innkeeper/guard rumor lines that start quests. The Choice is Yours (kryptopyr) exists precisely to *stop* "random greetings, comments, and rumors from triggering quests" — i.e., rumors are a delivery mechanism for quest starts, carry no information, and go nowhere.[^57^]
2. **Skyrim Town Criers (2025, Nexus 156867):** the closest thing to a news system ever shipped — and it's brand new. Criers in Whiterun, Windhelm, Solitude, Riften announce hold-spun news (the same event propagandized differently per Jarl's alignment), 3,600+ ElevenLabs-generated vanilla-voice lines, message pools that change with quest progress and player decisions, per-city unique pools.[^13^] This is **one-to-many broadcast keyed to quest state**: no NPC hears another NPC, nothing mutates in transit, no individual knows anything another doesn't at the individual level. But it demonstrates two things you'll care about: AI-voiced vanilla-timbre lines are now an accepted production technique (2025), and per-hold *framing* of the same fact is already a shipped, praised concept.[^13^][^14^]
3. **Denizens of Morthal / Denizens of Skyrim (2022–):** "a small slice of a bigger mod which aims to get the NPCs of Skyrim talking to each other," adding named NPCs with schedules and personal dialogue (Erandur/Valdimar personal dialogue updates).[^52^][^55^][^49^] Ambition stated; shipped form is authored scenes, not propagation.
4. **More to Say:** includes literal "gossip with Valga and Narri at Dead Man's Drink" nodes — spliced-voice dialogue, hand-placed.[^117^]
5. **LLM-era (the first actual movement of information between NPCs):**
   - **Mantella (2023–):** NPC conversation memory, event awareness, and **Radiant Dialogue** — two NPCs having generated conversations with each other.[^85^] The community review thread singled radiant dialogue out as the highlight: "This makes the world feel lived and breathed in a way I've seen no other mod accomplish."[^124^]
   - **CHIM (Dwemer Dynamics, 2024–):** the most mechanically explicit: a **Background Life** system where tracked NPCs generate inner thoughts on a 5-day cadence, send the player letters, travel between major locations based on goals — "Finally they are able to travel to any major location in Skyrim based on their current goals and thoughts" — and **"a rumor will be generated that NPCs in that location will be aware of for a temporary period of time."** Plus "complex relationship tracking between other people, groups, objects and even ideologies," long-term memory stores, diaries, and witness-scoped awareness ("Each AI NPC will only be aware of events which they have witnessed").[^90^]
   - **SkyrimNet (MinLL, 2025–):** single-SKSE-DLL architecture (no external server — the DLL itself hosts the pipeline, reading game state "straight from memory"), per-NPC vector memory with importance and decay, and **World Knowledge**: facts scoped by conditions ("only NPCs in Whiterun, only members of a specific faction, or only once a particular quest has reached a particular stage"), injected always or semantically.[^153^] Its community plugin **IntelEngine** is, as far as I can find, the first shipped implementation of *propagating* information: "gossip chains that propagate between NPCs," NPCs traveling on foot across cells and holds to scheduled meetings, off-screen faction-war developments feeding quest generation.[^153^] And **SeverActions** adds per-companion rapport/trust/loyalty/mood ledgers plus a crime-and-arrest action pack.[^153^]
6. **Anima (2024):** LLM NPC-to-NPC dialogue with awareness of in-game events — smaller, rougher, same direction.[^114^]

**Verdict for A3:** Every pre-LLM attempt is broadcast or authored; the LLM systems move information between NPCs but the payload stays *textual* — it colors what NPCs say; it does not re-drive disposition ranks, AI packages, or schedules (SkyrimNet's own "Current Limitations": "vanilla quest dialogue trees still go through Skyrim's normal system").[^153^] The mechanical-feedback loop you propose — beliefs with provenance → mutated rumors → schedule/behavior change — is unbuilt.

---

## A4. Consequence and world-state mods

- **Civil War Aftermath SE (korodic, 2016):** burn enemy camps, kill the (de-essentialed) commanders, courier-delivered reward. Persistence model is the tell: "Will the camps respawn? No, it's a one-time deal." World-state change as irreversible, one-shot, reference-disabling — the standard, cheapest persistence.[^48^]
- **After the Civil War — Siege Damage Repairs (tarlazo, 2018):** cities repaired on game-hour timers (globals exposed: 492h default; donations shorten it), completion triggered "when you enter an interior cell after the required period has expired" — state changes deliberately deferred to a safe moment to avoid visible world-swapping.[^46^] A small masterclass in *when* to apply persistent world edits.
- **Destroy the Thieves Guild (LE original → SE ports; and the 2024 Fewer Prompts patch):** removes essential flags, adds a wipe-out quest and minor recovery quests.[^45^][^64^] The Fewer Prompts patch is technically instructive: the original "adds a dialogue topic to every actor in the Riften town faction," which the patch trims to guards/Mjoll/Bersi by adding conditions to two dialogue branches — `PlayerRef.DoesNotExist = 1` as a kill-switch condition.[^41^] Shows the cost of blunt topic injection.
- **Helgen Reborn:** rebuilds Helgen via a full questline, including the choice of Helgen's allegiance (independent/Imperial/Stormcloak) — persistence via quest stages plus swapped/rebuilt location content.[^62^]
- **The Second Great War / Open Civil War SSE (simtam) / Killable Generals:** the war-continuation cluster; referenced as recommended/compat partners by the above.[^48^][^46^]
- **Alternate Start — Live Another Life (Arthmoor)** — included not as a consequence mod but for the most-quoted persistence warning in the scene, which your users will quote at you: "Any mod that is more than pure mesh or texture replacements has the possibility to leave behind permanent changes to your save that you may not want. This is not something modders can correct for. It is how the game was designed by Bethesda."[^67^]

**A4 pattern:** persistence is achieved through quest stages, globals, enabled/disabled references, and one-way doors (de-essentializing, burning camps). Nobody persists *relational* state (who knows what about whom) — only *world configuration*. Relational state is exactly the thing with no native storage slot.

---

## A5. Techniques that worked, walls everyone hit, and author testimony

### Techniques that worked

1. **Condition-gated dialogue over computed state** (GDO, RDO, Skyrim Reputation): engine evaluates dialogue conditions at trigger time; zero polling; unlimited apparent depth via spliced vanilla audio. The reputation *surface* is a solved problem.[^18^][^17^][^9^]
2. **Event-driven detection over polling** (RFYL's animation events, Shadow of Skyrim's defeat events, Mantella's SKSE hooks): subscribe, don't scan.[^36^][^3^]
3. **Bounded state with hard slot caps** (Shadow of Skyrim's 5+5, RFYL's 150-NPC cap): persistence cost stays constant; authors say so openly.[^3^][^36^]
4. **Script-free GMST/condition-only change** (RAID, Realistic Conversations): zero save footprint, uninstall-safe, surprisingly large perceived-intelligence gains.[^123^][^118^]
5. **Transient SKSE distribution** (SPID): powerofthree's own forum answers confirm the tradeoff explicitly — "SPID distribution is transient — when you close the game all changes from SPID are gone and the next game session will create a new distribution… There is no way to make it persistent since it's the way SPID is design to operate."[^105^] Free of bloat *because* it stores nothing.[^106^]
6. **External process ↔ in-game bridge** (Mantella's external server; CHIM's WSL2 "AI brain" + in-game AIAgent; SkyrimNet's single DLL reading game state from memory with guarded patterns and worker threads; Skyrim Platform's TypeScript runtime with a Papyrus bridge): the injection architecture you're planning is now well-trodden, with documented stability patterns (reference-counted entity wrappers, validity checks, lock ordering, "a stuck network call… can never freeze… the game process").[^85^][^90^][^153^][^70^]

### The walls (confirmed, with the specific claim for each)

1. **Papyrus VM throughput.** Community: "Papyrus is super slow and doesn't warn you if you mess up."[^72^] Practitioner, blunter: Papyrus "was designed so non programmers could do menial tasks… slow, limited… You will need to resort to all kind of hacks and aggressive and convoluted optimization methods."[^81^] The 2014 "Script Bloat?" thread records the era's folk remedy of INI budget tweaks (`[Papyrus]` section) — i.e., the VM's per-frame budget is a user-tunable symptom, not a solution.[^77^]
2. **Save bloat / orphaned scripts.** The community's own definitions: bloat is when "one save is 7MB and the next is 40MB and the next is 70MB"[^135^]; caused by "objects or script references [that] get spawned by the game" and never released[^132^]; and, importantly, "Mods that cause save bloat are quite rare actually… its entirely on a script by script basis"[^137^] — heavy-but-famous mods (Frostfall, Campfire, RnD) get repeatedly *cleared* of the charge.[^136^] Corollary culture: "Do not uninstall this mod (or any scripted mods) mid-playthrough" (Shadow of Skyrim)[^3^]; Arthmoor's permanent-changes warning.[^67^]
3. **No off-screen execution.** AI and scripts don't run for unloaded actors (OpenMW docs; NPC AI Process Position Fix), with the extra one-hour position-update bug for loaded actors.[^121^][^115^] Any "daily-schedule encounter" spreading rumors *in-engine* can only happen for NPCs near the player.
4. **The voice wall.** Every reactive line needs audio in that NPC's voice: hence RDO's 50+ voice-type splicing[^17^], Chatty NPCs' 1,500 spliced lines[^113^], Skyrim Reputation's English-only composites[^9^], Immersive Speechcraft's 1,000+ renamed vanilla files excluding unique voices[^83^], and the 2023–2025 pivot to xVASynth/ElevenLabs generation (Town Criers' 3,600 lines).[^13^] Dialogue-record conflicts are also a top mod-interop failure ("It's nearly impossible to have that many mods without… conflicts" in dialogue records; the "can't click on dialogue" bug is "almost universal" with mods adding uniquely-voiced NPCs).[^73^][^79^]
5. **Persistence/transience zero-sum.** Native per-NPC relational storage doesn't exist; your options are the save (bloat + uninstall fragility), external stores bridged by SKSE (JContainers/PapyrusUtil — with community-documented load-order/FormID invalidation caveats[^74^]), or SPID-style re-derivation each session (no memory).[^105^]
6. **Navmesh and AI-package contention** as the practical ceiling for behavior change (Immersive Citizens' entire support burden; r/skyrimmods wiki on bad-navmesh micro-stutter).[^122^][^120^]

### Authors who explicitly wanted deeper social simulation

- **dcyren (Skyrim Reputation):** the FAQ documents the deliberate substitution of *assumption* for *simulation* — NPCs react to what the system guesses they'd know, because tracking actual knowledge flow wasn't built.[^9^]
- **Syclonix (Shadow of Skyrim):** shipped per-enemy memory, then itemized the entire social layer (nemesis interactions, hierarchies, social vendettas) as out of scope — and the 2025 community continuation thread is literally a request for recognition-and-grudge dialogue on top of his skeleton.[^3^][^2^]
- **The 2015 Crime Overhaul WIP author:** designing consequence webs ("conspiracy to commit murder" tracing back to the player) while publicly learning the skills to build them; never shipped.[^78^]
- **The Master of Disguise critique (2019):** the demand for witnessed, revocable, non-global knowledge stated as user criticism.[^10^]

---

# PART B — The community record

## (a) Wishlist threads — the perennials

The demand recurs in stable phrasings, at multi-year intervals, across r/skyrimmods and r/skyrim:

| Year | Thread | The ask (most-upvoted formulation, quoted/paraphrased from index) |
|---|---|---|
| 2015 | r/skyrimmods, "Are there any mods like 'Do you know who I am'…" | NPCs should "acknowledge stuff you've done"[^25^] |
| 2016 | r/skyrimmods, "Is there a mod where NPC's memorize favors you did for them?" | Per-NPC favor memory; top answer cites only the vanilla friend/favor system ("It's how the Ebony blade detects who's your friend") — i.e., the wish was answered with a 2011 mechanic[^22^] |
| 2018 | r/skyrim, "A Mod that makes NPCs remember how I saved the world?" | Post-main-quest recognition; answers point to GDO and Don't You Know Who I Am — recognition *surfaces*, not memory[^34^] |
| 2018 | r/skyrimmods, "Mod to stop all characters from magically knowing I just [committed a crime]" | Witness-only crime knowledge; the perennial anti-telepathy complaint[^141^] |
| 2020 | r/skyrimmods, "Making npcs feel more 'alive'" | "Less cardboard cutout… more dynamic" — the general form[^159^] |
| 2023 | r/skyrimmods, "Crime overhaul mod?" | "Stops the Guards being all-seeing and actually have to witness the crime… If I kill someone in the Wilds, I don't want a bounty magically placed on me. The entire crime system in Skyrim has never been fit for purpose."[^53^] |
| 2024 | r/skyrimmods, "Are there any npc gossip mod?" | Literal gossip; one answer exists ("Denizens of Morthal")[^24^] |
| 2024–25 | r/ElderScrolls, "My biggest wish for ES6: the return of a proper faction and reputation system" | "Gimme choices that lock off access to certain groups, quests…" — the wish has outlived the game and been transferred to TES6[^140^] |
| 2025 | Nexus forums, "Shadow of Skyrim — Encounter Overhaul" | Nemeses who recognize, taunt, fear you; fate choices — the grudge-memory wish on top of the best existing skeleton[^2^] |

**Nemesis-specific demand:** When Syclonix announced Shadow of Skyrim (May–June 2022 dev post), it landed on pre-existing demand — FudgeMuppet introduced it as "one of those Skyrim mods we've desired for a long time," IGN covered it at release, and the announcement thread is the community's most concentrated statement of "I wish Skyrim had Shadow of Mordor's nemesis system."[^1^][^7^][^12^]

**Gossip/rumor as a mod idea:** thin but persistent — the 2024 gossip thread is the canonical instance, and the striking thing is how *few* answers exist for a question asked for years.[^24^] The "Dark Missives" mod-idea thread (DB contracts generated from player deeds like brawls) shows the adjacent "world reacts to your deeds via generated content" formulation.[^84^]

## (b) Practitioner explanations — which wall is claimed, precisely

Collected engineering claims, with provenance, for checking against your architecture:

1. **"Papyrus is super slow and doesn't warn you if you mess up, which leads to longer bug searches and worse quality mods."** — r/skyrimmods thread promoting Skyrim Platform (2021).[^72^] *Claim: VM throughput + tooling, not expressiveness.*
2. **"Papyrus… was designed so non programmers could do menial tasks… You will need to resort to all kind of hacks and aggressive and convoluted optimization methods just to have your mod still looking like a slow clunky mess in game."** — modder writeup advocating Skyrim Platform's TypeScript.[^81^] *Claim: language/VM ceiling for complex logic.*
3. **Save bloat is reference/script-instance accumulation, mod-specific not category-wide:** "Mods that cause save bloat are quite rare actually… entirely on a script by script basis"[^137^]; "The cause is that objects or script references get spawned by the game in…" (SkyBirds thread)[^132^]; healthy saves grow linearly and slowly, bloat is stepwise (7MB → 40MB → 70MB).[^135^] *Claim: unbounded per-save reference growth; the remedy culture is ReSaver/script-cleaners and never-uninstall.*
4. **Scripts and AI do not execute off-screen:** "AI on NPCs isn't processed unless they are loaded, nor are scripts ran."[^121^] Plus the loaded-cell one-hour position-update limit and its SKSE patch.[^115^] *Claim: in-engine simulation of off-screen social life is not slow — it is absent.*
5. **SPID can't persist:** "SPID distribution is transient… There is no way to make it persistent since it's the way SPID is design to operate."[^105^] *Claim: the bloat-free path forfeits memory by construction.*
6. **Condition-checked dialogue is the cheap reactive surface; active scanning is the expensive one:** RDO author's "nothing… constantly polling" statement[^17^]; kuertee's on-the-fly evaluation producing visible latency ("…" placeholder responses) and Oldrim stack dumps.[^107^]
7. **Package schedules are real but shallow in Skyrim:** the definitive technical audit (paavohtl's "What was Radiant AI, anyway?") finds Skyrim's package system *more* modular than Oblivion's but with shallower schedules — only a couple dozen weekday-dependent packages (half for one Dark Brotherhood quest), widespread "fake food" (`CreateFakeFood`) eating, and conditions (weather/quest-stage/globals/distance) doing the conditional lifting; Starfield regressed further (~6% of packages scheduled).[^152^] The companion essay explains the design-philosophy retreat from emergence to "modular random encounters."[^143^] *Claim: the scheduler exists and is condition-rich; Bethesda itself stopped feeding it.*
8. **Uninstall is destructive by engine design:** Arthmoor's warning.[^67^]
9. **Voice is the content bottleneck** — see A5 wall #4 (splicing economics, translation breakage, unique voice types excluded by design).[^9^][^83^][^13^]
10. **Skyrim Platform's own bridge caveat:** "Skyrim Platform supports listening for Papyrus Events triggered on objects in the game, but it is very slow and not recommended" (2021) — even the modern alternative keeps Papyrus as event source and moves logic out.[^70^] *This is the strongest existing endorsement of your split: in-game layer as thin event/surface shim, heavy logic external.*

## (c) Reception evidence — the promise/thread gap

- **Skyrim Reputation:** "Worth it for immersion, but it's not a fundamental change to the game. In the early game it makes a big difference…" (r/skyrimmods, 2025-ish)[^156^]; second thread: "a good mod overall… but it also ranks based on quests you've [completed]"[^157^]; Xbox thread asking "Is it balanced? Did you enjoy the mechanic?" with mixed replies.[^160^] **Pattern: praised as flavor; felt as global and shallow; the quest-statistic basis is noticed and disliked.**
- **Shadow of Skyrim:** praised for making enemies memorable ("actually brings enemies to life")[^2^]; coverage framed it as fulfilling a long-held wish[^7^][^12^]; the continuation thread shows the praise curdling into want of *recognition and dialogue depth* — nemeses who remember *you*, not just exist.[^2^]
- **Immersive Citizens:** beloved concept, but its support history is navmesh conflicts, NPC clustering, stuck behaviors, and load-order discipline[^122^]; the community's practical verdict is the AI Overhaul switch ("more compatible… Synthesis patcher").[^15^][^31^]
- **Mantella / AI-dialogue mods:** the reception split is stark. Discord-feedback wall: "dream game," "brought to life."[^85^] Independent critique: "Skyrim becomes the interface for a role-playing conversation with an AI program… it is very laggy… the aspirational idea is better than the end product."[^134^] User experience threads: ~10-second response latency called "pretty immersion breaking"; cost and install complexity as barriers; the radiant NPC-NPC dialogue singled out as the best feature.[^131^][^124^]
- **The "they talk but nothing changes" pattern (your product thesis):** it shows up in three documented forms. (1) *Question form:* the "What Are The Capabilities Of Mantella?" thread — "can you get AI NPCs to actually do stuff?… Do NPCs know who they are… what are some limitations you've found particularly bothersome?"[^96^] (2) *Critique form:* Stewart's essay — conversation without world consequence.[^134^] (3) *Vendor-roadmap form:* SkyrimNet admits vanilla dialogue trees bypass its system entirely ("Integrating the two is on the roadmap")[^153^], and the ecosystem's newest plugins (IntelEngine's gossip chains/off-screen developments, SeverActions' trust/crime ledgers, CHIM's relationship tracking and Background Life) are all explicitly building the consequence/action layer on top of chat — i.e., the developers themselves have validated "talk isn't enough" as the direction.[^153^][^90^] I'd characterize the complaint as *recurring and structurally central to 2024–2026 discussion*, though the literal phrasing varies; I did not find a single mega-thread with that exact title.
- **Master of Disguise:** technically admired; its epistemics criticized as "clumsy… terrible mechanic… never have a permanently global effect."[^10^]
- **Vanilla itself:** the Hired Thugs "nothing had ever happened" mechanic (UESP) is the community's canonical example of fake consequence, and the witness/animal-witness quirks (guards "may still become aware" of unwitnessed crimes; horses reporting crimes) are documented bugs/meme fuel.[^148^]

---

## Synthesis — what this means for your architecture

1. **The gap is real and specifically shaped.** Shipped art covers: global reputation (A1.1), witnessed-behavior reaction (A1.3, A1.6), bounded per-enemy memory (A1.4), broadcast news (A3.2), and authored interconnection (A2.4). Nobody has shipped **beliefs-with-provenance that spread, mutate, and feed back into schedules**. The community's most-upvoted asks map one-to-one onto it (witness-only knowledge, NPC memory of deeds, gossip, nemesis recognition).
2. **The walls that killed in-engine attempts are mostly not yours.** Papyrus throughput, no-off-screen-execution, and per-save storage are in-engine walls; practitioner consensus (including Skyrim Platform's own docs) already endorses "thin in-game shim, heavy logic external."[^70^] Mantella/CHIM/SkyrimNet have productionized your bridge pattern, including the hard-won stability discipline.[^153^]
3. **Your remaining walls are surfacing and persistence, not simulation.** (a) Beliefs must surface through dialogue conditions/globals/relationship ranks/packages — the GDO/RDO condition architecture is proven and cheap, but voice remains the content bottleneck (budget for AI-voice generation or silent-voice tooling). (b) State that must survive reloads must either enter the save (bounded, SPID-slot-style caps à la Shadow of Skyrim's 5+5) or be re-injected per session (SPID's transient model) — the community's save-bloat antibodies are strong and the "never uninstall" culture will be quoted at your mod.
4. **Design expectations set by reception:** players punish *telepathy* (global, instant, unearned knowledge) more than they punish shallow simulation; they reward *recognition* disproportionately (GDO respect ramps, nemesis names); and the most-loved features of the AI mods are NPC-NPC interactions (radiant dialogue, gossip chains) — the exact layer you're mechanizing.[^124^][^153^]
5. **Date-sensitive caveat honored:** Oldrim claims (stack dumps, script-cleaner folklore) describe a pre-SKSE64-maturity world; but the structural claims that still bind in 2026 are engine-execution scope (loaded cells), voice/audio binding, and save-format persistence — none of which SKSE maturity has removed.

---

## Sources

[^1^]: https://www.reddit.com/r/skyrimmods/comments/up4xjr/upcoming_release_shadow_of_skyrim_nemesis_and/
[^2^]: https://forums.nexusmods.com/topic/13511228-shadow-of-skyrim-encounter-overhaul/
[^3^]: https://www.nexusmods.com/skyrimspecialedition/mods/65136
[^5^]: https://fireundubh.github.io/skyrim/master_of_disguise_sse
[^7^]: https://www.youtube.com/watch?v=L5tZcXJHczI
[^9^]: https://www.nexusmods.com/skyrimspecialedition/mods/22374
[^10^]: https://forums.nexusmods.com/topic/7794508-master-of-disguise-se-problem/
[^11^]: https://www.nexusmods.com/skyrimspecialedition/mods/52416
[^12^]: https://www.ign.com/articles/someone-added-shadow-of-mordors-nemesis-system-to-skyrim
[^13^]: https://www.nexusmods.com/skyrimspecialedition/mods/156867
[^14^]: https://www.reddit.com/r/skyrimmods/comments/1mqegvr/mod_release_skyrim_town_criers/
[^15^]: https://www.reddit.com/r/skyrimmods/comments/17mn9qk/ai_overhaul_vs_immersive_citizens_ai/
[^17^]: https://www.nexusmods.com/skyrimspecialedition/mods/1187
[^18^]: https://www.nexusmods.com/skyrimspecialedition/mods/22075
[^20^]: https://www.reddit.com/r/skyrimmods/comments/10coalr/immersive_citizens_vs_ai_overhaul/
[^22^]: https://www.reddit.com/r/skyrimmods/comments/4ajg1k/is_there_a_mod_where_npcs_memorize_favors_you_did/
[^24^]: https://www.reddit.com/r/skyrimmods/comments/197tabu/are_there_any_npc_gossip_mod/
[^25^]: https://www.reddit.com/r/skyrimmods/comments/31jv7o/are_there_any_mods_like_similar_to_do_you_know/
[^31^]: https://www.reddit.com/r/skyrimmods/comments/1dtkxyk/immersive_citizens_or_ai_overhaul/
[^33^]: https://www.reddit.com/r/skyrimmods/comments/eqhwyr/run_for_your_lives_and_immersive_citizens/
[^34^]: https://www.reddit.com/r/skyrim/comments/7p14tv/a_mod_that_makes_npcs_remember_how_i_saved_the/
[^35^]: https://www.reddit.com/r/skyrimmods/comments/2gwr3e/should_i_use_run_for_your_lives_and_when_vampires/
[^36^]: https://www.nexusmods.com/skyrimspecialedition/mods/2272
[^38^]: https://www.afkmods.com/index.php?/files/file/372-run-for-your-lives/
[^41^]: https://www.nexusmods.com/skyrimspecialedition/mods/125360
[^45^]: https://gaming.stackexchange.com/questions/38662/is-there-a-way-to-bring-down-the-thieves-guild-in-riften
[^46^]: https://www.nexusmods.com/skyrimspecialedition/mods/20668
[^48^]: https://www.nexusmods.com/skyrimspecialedition/mods/3484
[^49^]: https://www.nexusmods.com/skyrimspecialedition/mods/178752
[^52^]: https://www.nexusmods.com/skyrim/videos/14669
[^53^]: https://www.reddit.com/r/skyrimmods/comments/14ivebm/crime_overhaul_mod/
[^55^]: https://www.reddit.com/r/skyrimmods/comments/j3fpc8/denizens_of_morthal_erandur_and_valdimar_show_off/
[^57^]: https://www.nexusmods.com/skyrimspecialedition/mods/3850
[^62^]: https://tes-mods.fandom.com/wiki/Helgen_Reborn
[^64^]: https://creations.bethesda.net/en/skyrim/details/9255/Destroy_the_Thieves_Guild___Special_Edition
[^67^]: https://www.afkmods.com/index.php?/files/file/270-alternate-start-live-another-life/
[^70^]: https://github.com/mrowrpurr/SkyrimPlatformPapyrusBridge
[^71^]: https://www.nexusmods.com/skyrimspecialedition/mods/22506
[^72^]: https://www.reddit.com/r/skyrimmods/comments/ppecbx/are_you_a_mod_author_do_you_like_coding_more_then/
[^73^]: https://www.reddit.com/r/skyrimmods/comments/149jhth/dialogue_options_dont_appear/
[^74^]: https://forums.nexusmods.com/topic/4949935-best-tool-for-creating-data-structures-in-skyrim-papyrus-jcontainers-or-alternative/page/2/
[^77^]: https://www.reddit.com/r/skyrimmods/comments/265iii/script_bloat/
[^78^]: https://forums.nexusmods.com/topic/3124930-skyrim-crime-overhaul-mod/
[^79^]: https://www.reddit.com/r/skyrimmods/comments/vgqmed/why_so_many_mods_have_the_cant_click_on_dialogue/
[^80^]: https://www.nexusmods.com/skyrimspecialedition/mods/19647
[^81^]: https://geek-of-all-trades.neocities.org/programming/skyrim/no-more-papyrus
[^83^]: https://www.nexusmods.com/skyrimspecialedition/mods/21296
[^84^]: https://www.reddit.com/r/skyrimmods/comments/ehplzw/dark_missives_mod_idea/
[^85^]: https://www.nexusmods.com/skyrimspecialedition/mods/98631
[^90^]: https://www.nexusmods.com/skyrimspecialedition/mods/126330
[^96^]: https://www.reddit.com/r/skyrimmods/comments/1g5k8u6/what_are_the_capabilities_of_mantella/
[^105^]: https://www.nexusmods.com/skyrimspecialedition/mods/36869?tab=posts
[^106^]: https://www.nexusmods.com/skyrimspecialedition/mods/36869
[^107^]: https://www.nexusmods.com/skyrim/mods/65243
[^113^]: https://www.nexusmods.com/skyrimspecialedition/mods/133266
[^114^]: https://www.nexusmods.com/skyrimspecialedition/mods/123799
[^115^]: https://www.nexusmods.com/skyrimspecialedition/mods/69326
[^116^]: https://www.nexusmods.com/skyrimspecialedition/mods/96446
[^117^]: https://www.nexusmods.com/skyrimspecialedition/mods/22622
[^118^]: https://www.nexusmods.com/skyrimspecialedition/mods/1717
[^120^]: https://www.reddit.com/r/skyrimmods/wiki/navmesh/
[^121^]: https://modding-openmw.gitlab.io/go-home/
[^122^]: http://ai4egames.com/skyrim/ic/
[^123^]: https://www.nexusmods.com/skyrimspecialedition/mods/2345
[^124^]: https://www.reddit.com/r/skyrimmods/comments/1fo5ana/review_of_ai_mods/
[^125^]: https://www.nexusmods.com/skyrimspecialedition/mods/73541
[^126^]: https://www.nexusmods.com/skyrimspecialedition/mods/1973
[^127^]: https://www.nexusmods.com/skyrimspecialedition/mods/8589
[^128^]: https://forums.nexusmods.com/topic/1738511-how-can-you-make-npcs-travel-throughout-skyrim/
[^131^]: https://www.reddit.com/r/skyrimmods/comments/1dweh2y/mantella_mod_experience_is_it_worth_it/
[^132^]: https://www.reddit.com/r/skyrimmods/comments/4mcvxz/skybirds_new_testing_being_done/
[^134^]: https://davidvstewart.substack.com/p/rethinking-ai-in-video-games
[^135^]: https://www.reddit.com/r/skyrimmods/comments/271vxg/the_dreaded_save_bloat_did_a_new_game_fix_my/
[^136^]: https://www.reddit.com/r/skyrimmods/comments/9e7h0x/about_end_game_save_bloating_what_are_some_script/
[^137^]: https://www.reddit.com/r/skyrimmods/comments/4frohk/i_cant_grasp_save_bloat/
[^140^]: https://www.reddit.com/r/ElderScrolls/comments/1ilp53w/my_biggest_wish_for_es6_the_return_of_a_proper/
[^141^]: https://www.reddit.com/r/skyrimmods/comments/8dmczj/mod_to_stop_all_characters_from_magically_knowing/
[^143^]: https://medium.com/@gatherer286/lost-features-a-critical-essay-on-tes-iv-oblivions-radiant-ai-a0150144ddef
[^144^]: https://www.nexusmods.com/skyrimspecialedition/mods/29194
[^148^]: https://en.uesp.net/wiki/Skyrim:Crime
[^152^]: https://blog.paavo.me/radiant-ai/
[^153^]: https://github.com/MinLL/SkyrimNet-GamePlugin
[^156^]: https://www.reddit.com/r/skyrimmods/comments/1qut4dv/skyrim_reputation/
[^157^]: https://www.reddit.com/r/skyrimmods/comments/1vhcpl1/reputation/
[^159^]: https://www.reddit.com/r/skyrimmods/comments/i7t2dd/making_npcs_feel_more_alive/
[^160^]: https://www.reddit.com/r/SkyrimModsXbox/comments/16gir43/skyrim_reputation_opinions/
