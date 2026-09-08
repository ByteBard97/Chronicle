# Chronicle Systems in Skyrim: A Worked Design Tour (2026-09-06)

Companion to `master-feature-synthesis-2026-09-06.md`. That document says what to build and why; this one walks each of the fifteen systems through Skyrim itself — what Chronicle tracks, what fires it, and what the player actually sees, using the real people, places, and things of the game. Examples use vanilla NPCs and their real vanilla situations (existing feuds, secrets, and quest states) so the systems read as deepening the game that exists rather than pasting a sim on top of it. Each section ends with a note on how the system renders before the LLM integration lands, since the agreed build order puts the deterministic sim first.

A note on the examples: where a vanilla secret or feud already exists (Sybille Stentor's condition, the Grey-Mane/Battle-Born feud, Haelga's ledger, Romlyn Dreth's skimming), Chronicle adopts it as seed data rather than inventing a parallel version. The mod's credibility comes from noticing what Bethesda already authored and making it live.

---

## 1. Storylet Role-Casting on Radiant Story

**What it is.** Chronicle authors a library of quest and scene *shapes* — storylets with role slots and preconditions — and its belief engine casts real NPCs into those slots based on what has actually happened in the playthrough. The delivery mechanism is Bethesda's own Story Manager: Chronicle's C++ plugin raises a custom story event with the chosen actors and location attached, a Chronicle quest node catches it, and explicit alias fills (ForceRefTo on the quest's ReferenceAliases, not condition-matched search) install the cast. Vanilla radiant quests pick "a dungeon you haven't visited"; Chronicle picks "the specific person with the specific grievance."

**What Chronicle tracks.** The storylet library (each entry: role slots, preconditions expressed as belief-graph queries, a discovery-failsafe ladder, a completion contract); per-storylet cooldowns; a per-hold active-story cap.

**Worked examples.**
- *The Debt Called In.* Precondition: some NPC holds an unrepaid obligation belief toward the player worth more than a threshold, and that NPC's household has taken an economic-hardship event. Cast in a real save: the player saved Lucan Valerius's shop takings during a bandit scene weeks ago (obligation formed, never spent); a Chronicle war-levy event later strains Riverwood. The storylet fires: Lucan sends a courier letter asking the player to escort a supply run to Whiterun — and his letter cites the original event, because the storylet's text template has a slot that renders the founding memory. Sven or Faendal (whichever the belief graph says is on better terms with Lucan) is cast as the second escort.
- *The Accusation.* Precondition: a mutated rumor about the player (see §5) has reached an NPC with high boldness and a grudge channel already warm. Cast: the player brawled Mikael in the Bannered Mare a month ago; the rumor mutated in transit to Rorikstead into "beat a bard half to death." Ennis — bold, already sour on outsiders — confronts the player at the Frostfruit Inn, and his dialogue renders the *mutated* version, which the player can dispute, trace ("who told you that?" — the provenance chain is real data), or let stand.
- *The Empty Chair.* Precondition: a named NPC died and their institutional role (§15's lightweight version) is vacant. Cast: Nazeem died in a dragon attack on the Whiterun plains (vanilla dragons genuinely kill NPCs). Chronicle casts the succession scene: the Drunken Huntsman conversation where Ahlam — cause-labeled beliefs fully loaded — is written a widow's arc instead of despawning into nothing, and Chillfurrow Farm's operation passes visibly to a hired hand.

**Story Manager cautions (from the spike list).** Required aliases that fail to fill kill the quest silently, so every Chronicle quest ships with all aliases optional plus a stage-0 validation script that checks fills and reports failure back to the Python engine, which reschedules or falls back. Events are consumed once a quest starts from them, so Chronicle raises one event per intended story, never a broadcast event multiple nodes race for. Only persistent references and unique actors are findable outside the loaded area — Chronicle casts named NPCs by explicit reference, which sidesteps this, but generated NPCs (§3 remnants) must be created persistent.

**Pre-LLM rendering.** Storylet text is template-authored with memory-slot interpolation ("{founding_event_summary}"), exactly like vanilla radiant text with better fill data. Works fully voiced-unvoiced-mixed the way quest mods already do.

---

## 2. The Civil War and Dragon Crisis as Phased Struggles

**What it is.** The civil war stops being a frozen questline state and becomes a hold-by-hold phased conflict in the CK3 Struggle mold: named phases, entered when accumulated catalyst points cross a threshold, with a debounce timer so single events can't whipsaw the phase, and each phase changing what is legal, common, and possible in the affected holds. The dragon crisis gets the same treatment at lower intensity: an escalating regional phase track (Rumored → Sighted → Predatory → Under Siege) per hold, driven by actual dragon events.

**Phases (war), per hold.** *Uneasy Peace* → *Agitation* (recruiters in inns, seditious talk, guards doubled) → *Crackdown or Concession* (the Jarl's court chooses, biased by the Jarl's own beliefs) → *Open Hostility* (roadblocks, requisitions, skirmish spawns on roads) → *Aftermath* (occupation or relief, grief and rebuilding, §7 breaks and §12 memorials fire in volume). Catalyst events are weighted belief-graph facts: a Stormcloak recruiter's success in Ivarstead is +N agitation for the Rift; the player turning in Stormcloak couriers is +N crackdown-legitimacy for Imperial holds; a dragon razing a granary is catalyst for *whichever side the local rumor mill blames for the undefended granary* — which depends on §5's mutation and who spread the story.
**Worked example.** Vanilla's Battle for Whiterun becomes the *visible crest* of a slope the player has been walking for weeks: Agitation showed up as Heimskr preaching to bigger crowds and the Battle-Borns' shop refusing Grey-Mane custom entirely (§4 house-level state feeding the war track); Crackdown showed up as Commander Caius arresting a Talos worshipper — a scene Chronicle casts with a real named worshipper, generating real grievance beliefs in the watching crowd; by the time Balgruuf commits, the town the player fights through is one whose sides they watched form. After the battle, Aftermath is not a texture swap: Chronicle runs the funeral scene at the Hall of the Dead with the actual casualty list (vanilla tracks which named guards die), the widow arcs, the §12 memorial stone, and a month of altered schedules before Whiterun's phase decays back toward a wary peace.
**The balance trap, imported.** CK3's documented late-game problem — one phase becoming a stable attractor — maps here to Aftermath-forever or permanent Agitation. The fix is CK3's own: phase-specific decay pressure (Aftermath bleeds catalyst points toward peace automatically unless fresh hostile events refill them), tuned so a hold untouched for an in-game month visibly normalizes.
**Loyalty-cascade guard.** Phase transitions change *policy*, never directly rewrite individual NPC faction membership. Windhelm entering Crackdown does not make Brunwulf Free-Winter an enemy of Windhelm; it gives him grievance beliefs and lets §1 cast him into dissent storylets. The DF cascade is impossible by construction because group flags never propagate through individuals automatically.

**Pre-LLM rendering.** Phases render through spawn tables, guard barks (conditioned vanilla-style lines per phase), court scenes from templates, and economy knobs (invest/price changes merchants already support). No generated text required.

---

## 3. Power Vacuums and Broken Remnants

**What it is.** Cleared and broken things leave wreckage-people, and emptied territory gets claimed. When the player (or the war, or a dragon) removes a power — a bandit chief, a Forsworn camp, a Thalmor patrol route, a pirate crew — Chronicle rolls the consequence forward: remnants with memory, and a vacancy timer after which a neighboring power expands.

**Worked examples.**
- The player clears Valtheim Towers. Vanilla respawns the same anonymous bandits in ten days. Chronicle instead: two survivors fled (created persistent at the fight's end, §1-castable); the tower sits empty for a week (travelers on the Whiterun–Windhelm road visibly relax; Carlotta's produce prices ease a septim because the toll racket died — a one-line economy write with a citable cause); then either the survivors return with hired muscle and a grudge that names the fight, or — if the war phase is hot — a Stormcloak picket claims the towers, and the road's character changes entirely depending on the player's war alignment.
- Kematu's Alik'r are wiped in Swindler's Den. The vanilla world shrugs. Chronicle: Whiterun's Redguard rumor line notices ("whole warband, gone — Hammerfell will hear of this"), Saadia's belief state shifts from hunted to warily safe, and the den — a real cleared cell — becomes the vacancy: skooma cookers move in within two weeks unless a patrol storylet fires first, because a hidden cave near a trade road is *valuable*, and Chronicle's vacancy-claim table knows it.
- A dragon destroys the Kynesgrove mine crew (vanilla Sahloknir attack gone badly). The mine is the vacancy; Windhelm's court gets a §1 petition scene from Dravynea; whether the mine reopens with hired workers, gets squatted by bandits, or stays a tomb depends on whether the player, the Jarl's coffers (war-strained?), or nobody responds.

**Remnant rules.** Remnants are few, named, persistent, and capped (the Nemesis pacing lesson): at most a handful of live remnant threads per region, oldest resolved or retired first. A remnant's return is always telegraphed through §5 (rumor of someone asking about you in the Bannered Mare) before the ambush fires — the L4D pre-telegraphing rule as drama.

**Pre-LLM rendering.** Remnant dialogue is template-with-slots ("You killed {leader} at {place}. I carried him out."); vacancy changes render through spawns, prices, and barks.

---

## 4. Relationship Crystallization (Sentiments Model)

**What it is.** Belief clusters crystallize into a small vocabulary of named, directed, cause-labeled sentiment states — Friend, Sworn Friend, Rival, Enemy, plus self-directed Guilty and the asymmetric pair Grateful/Beholden — capped Sims-style at a few active sentiments per target, each carrying its founding memory. Sentiments are what proximity reacts to: the glare, the warmth, the leaving-the-room.

**Worked examples.**
- The player repeatedly backs Carlotta Valentia against Mikael's pestering (a real vanilla situation). Beliefs accumulate; Friend crystallizes with founding memory "stood up to the bard for me." From then on: Carlotta's market prices soften for the player only, her morning bark changes, and when the player walks the market she turns *toward* them — while Mikael, carrying Rival with founding memory "humiliated me in my own inn," goes cold, needles the player in barks, and (§5) is a preferential *source* node for negative rumors about them.
- Guilty, the offender-side state: the player, mid-Thieves-Guild questline, burgles Bersi Honey-Hand's shop and is never caught. Chronicle doesn't only track Bersi's suspicion — the *player-adjacent* version writes Guilty onto guild NPCs who know (Brynjolf jokes about it; that's his temperament), but writes it as visible weight onto a temperamentally decent cast member if one was involved. Where it really sings is NPC↔NPC: Torbjorn Shatter-Shield, whose vanilla dialogue already drips misdirected grief, picks up Guilty toward Nilsine after Chronicle events where his rage lands on her — and avoids her at home, which Nilsine's own dialogue can notice.
- House-level: the Grey-Mane/Battle-Born feud is the shipped seed. Chronicle promotes it to live Feuding state between the houses, so every member-to-member interaction inherits the tier: Olfrid won't fence Grey-Mane goods, Idolaf's recruiting pitch hardens, and the player's visible acts for one house move the *house* needle — culminating castable storylets (§1) at Faithful (a shared feast in Jorrvaskr's shadow) or deep Feud (a street brawl the guards break up, §8 witnesses fanning out).

**Proximity mechanics.** The C++ plugin runs a cheap same-cell check for sentiment pairs; on trigger, it plays the reaction tier: bark, idle/expression change, approach or exit. Caps: one proximity reaction per pair per game hour, so rooms don't churn.

**Pre-LLM rendering.** The named vocabulary *is* the pre-LLM rendering — a finite sentiment set maps to authored bark pools per voice type, exactly how vanilla handles disposition lines, just with real causes behind them.

---

## 5. Gossip Mutation with Transitive Writeback

**What it is.** The rumor engine's two rules that no shipped game combined: content mutates in transit within bounded classes (facts-of-record resist; interpretation, scale, and low-confidence identity drift), and *hearing a rumor moves the listener's own disposition toward its subject*, scaled by the rumor's reliability tier and the listener's temperament. Rumors travel on the real social graph with travel time — innkeepers and couriers are hubs, kin edges are fast (§14), hold borders and war phase (§2) shape the topology.

**Worked example, end to end.** The player kills Grelod the Kind (vanilla, pre-Dark-Brotherhood). Witness set: the orphans and Constance Michel. Constance's belief is Precise and eyewitness-tier. Runa Fair-Shield tells it *gratefully* — her temperament colors valence, not content. The rumor leaves Riften with a wagon driver (real travel-time edge to Ivarstead), mutating: "someone killed the old woman at Honorhall" → by Whiterun, "an assassin is killing matrons in the Rift" (scale-class mutation, identity degraded to Fuzzy). Writeback does the work: Riften listeners who *hated* Grelod (most of them — Chronicle seeds this from her vanilla reputation) shift mildly *positive* toward the unknown subject; Maramal shifts negative (temperament: killing is killing); Honorhall's donors get an economic beat. When the player is later identified in a retelling (a Fuzzy identity re-sharpened by someone who saw them leave the orphanage), the accumulated writeback *retroactively attaches* — Riften is suddenly, legibly, a town where half the people quietly approve of the player and the Temple of Mara doesn't, and the player can trace every strand by asking (§1.5's memory-viewer-as-dialogue).
**The player as node.** The player spreads rumors too — verbs: Gossip (share what you know, at your reliability tier), Confide (targeted, high-trust), Accuse (public, forces §6 reactions), and Plant (deliberate falsehood — Chronicle's mutation machinery run on purpose, with the false belief carrying the player as hidden provenance, discoverable if the chain is walked backward by someone motivated, which is how the player's lies can eventually find their way home).
**Bounds.** Deaths, marriages, battles — facts-of-record — never mutate into their negations; who/why/how-bad mutates freely below eyewitness tier. This is the fairness floor: the player can always trust the record layer, and so can the storyteller.

**Pre-LLM rendering.** Mutation classes are structured transforms on belief records; rendering is template families per tier ("they say...", "I heard from {source}...", "everyone knows..."). The LLM later makes retellings idiomatic; the mutations themselves never depended on it.

---

## 6. The Production-Rule Reaction Layer

**What it is.** The deterministic middle layer: a ranked, most-specific-wins rule table that takes (incoming event or player line, target NPC's beliefs, sentiments, temperament dials, current strain, war phase) and outputs a *reaction class* — before any text exists. The LLM, when it arrives, voices the chosen class; until then, bark pools do. Shipped as external JSON, moddable, with a neutral fallback so coverage is total.

**Worked examples.**
- Event: player draws a weapon in the Bannered Mare. Rules, most-specific first: IF actor is guard AND war phase ≥ Crackdown → `challenge_escalate`. IF witness holds Terrified toward player (§10) → `flee_and_report`. IF witness is Uthgerd the Unbroken (temperament: bold, brawler; sentiment toward player: Friendly-after-the-fistfight) → `amused_challenge` ("Planning to use that, or just showing off?"). ELSE → `alarm_wary`. Same event, four different Whiterun reactions, every one explainable from data.
- Player line class: *ask a large favor* (borrow 500 septims). IF target holds Beholden toward player AND STC rung ≥ Openness (§13) → `grant_with_reference_to_debt`. IF target is Belethor (temperament: mercenary; sentiment: none) → `counter_offer` — his vanilla "everything's for sale" persona as a rule, not a script. IF target holds Rival → `refuse_mock`, and the refusal is itself a §5-spreadable event ("hah — came begging to *me*").
- Event: dragon kills livestock at Chillfurrow Farm. Rule for owner (Nazeem, temperament: vain, brittle): `blame_authorities` — he berates the guards, generating grievance beliefs *in the guards*. Rule for Severio Pelagia next door (steadier dials): `stoic_repair` plus a §7 strain tick. The same catastrophe individuates.

**Why it must exist.** Every AI-director failure catalogued in the research is an LLM deciding outcomes; every success is a deterministic core deciding and language rendering. This table is where Chronicle's "sim decides, LLM renders" doctrine becomes a file you can read, diff, and mod.

**Pre-LLM rendering.** Reaction classes map to voice-type bark pools and dialogue branches. The JSON is the same file the LLM era uses; only the renderer swaps.

---

## 7. Strain and Breaks (Unified Stress System)

**What it is.** The single subsystem behind CK stress, RimWorld mood bands, and DF's dual axes: per-NPC acute strain (event-driven, fast decay) and chronic strain (slow accumulation under sustained hardship), with visible breaks requiring both elevated, break flavor chosen weighted-random-within-band by temperament, catharsis after, and needs-driven recovery the player can assist.

**Worked examples.**
- A dragon hits the Western Watchtower and the fight spills toward town (vanilla Mirmulnir, gone worse). Acute strain spikes across Whiterun; nothing breaks — one bad day, weathered, per the dual-axis rule. But if the war phase keeps Whiterun in Agitation for weeks *and then* the dragon comes, chronic is already high: Arcadia (temperament: anxious healer) breaks as `overwork_collapse` — her shop shutters two days, potion supply visibly gaps, and Danica sends a §1 storylet asking the player to gather her restocking reagents (the intervention verb: resolvable hardship). Catharsis afterward: Arcadia's dialogue steadies, resilience buff for a season.
- Windhelm under Aftermath (Imperial-occupation path): Ambarys Rendar's chronic strain — his whole vanilla characterization is chronic grievance — crosses into `bitter_withdrawal`: the Cornerclub stops serving non-Dunmer, a visible, political break that feeds §2 catalyst points. The player can intervene (a §1 storylet vouching for a Nord regular) or let it calcify into a coping tag.
- The positive flavor, DF's strange mood: after the player clears Kynesgrove's dragon, Balimund-class inspiration fires on whichever smith the belief graph puts closest to the event — say Hert at the mill was cast as a survivor — no; keep it to actual smiths: Windhelm's Hermir Strong-Heart, whose vanilla dialogue idolizes Oengul, enters a forge-obsession break and produces a named blade commemorating the Kynesgrove dead (§12 object), which enters the world as both an item and a rumor.

**Guards.** Settlement-level break caps (no more than two concurrent visible breaks per town), catharsis mandatory, chronic decline past a threshold requires storyteller sign-off (§11) — the tantrum-spiral triple lock.

**Pre-LLM rendering.** Breaks are schedule/package swaps plus bark-pool changes — the most engine-native system on the list; the SKSE package-override verification is the one open spike.

---

## 8. Non-Telepathic Crime

**What it is.** Crime knowledge becomes belief like everything else: a crime creates witness beliefs in actual observers (portal-gated radius, walls block, archways don't), those beliefs travel the §5 graph at rumor speed, bounties exist per legal namespace only after a report reaches someone with authority to issue one, and *recognition* of the player is itself a belief-gated process with a visible double-take.

**Worked examples.**
- The player picks Madesi's strongbox in the Riften market at night. Witnesses: whoever the portal-scan actually finds — say Grelka, closing her stall. No guards saw it. Vanilla: instant 25-gold psychic bounty. Chronicle: Grelka (temperament: sour, minds-her-own-business dials middling) holds an eyewitness belief; the §6 table decides she mutters rather than reports (reporting is a choice, scored). Two days later she trades it to Marise for gossip-value; Marise's writeback sours her toward the player; nobody has yet told a guard. The player, walking the market, gets barks that *know* — "some of us saw what you did" — before any bounty exists. When it finally reaches the Riften guard (or doesn't, if the player spends §9 leverage on Grelka first), the bounty is issued by an actual official, dated, and the player can learn who reported by walking the chain.
- Jurisdictional character: the same theft in Markarth reaches the guard faster (Silver-Blood-tightened watch, §2 phase-dependent) and arrest means Cidhna Mine — vanilla's own flavor, now systemic. In Windhelm, Suvaris Atheron witnessing a crime against a Dunmer reports it to *Ambarys* first, not the guard — the delegated-namespace mechanic wearing the Grey Quarter's real politics.
- War topology: an Imperial-hold bounty travels by courier along Imperial-controlled roads. The player wanted in Solitude walks into Stormcloak Riften *clean* — until the war phase shifts, couriers re-route, and last month's crimes arrive with the occupation. Legal knowledge reorganizing with the front line is the civil-war ask in its sharpest playable form.

**The hard part, named honestly.** Suppressing the vanilla instant-bounty broadcast is real engine surgery (the standing research flag). The staged fallback if interception proves unsafe: leave vanilla bounty behavior for guard-witnessed crimes, and route only *unwitnessed-by-guards* crimes through Chronicle — which is coincidentally the interesting half.

**Pre-LLM rendering.** Entirely bark/dialogue/bounty mechanics; no generated text anywhere in the core loop.

---

## 9. Secrets, Hooks, and the Leverage Economy

**What it is.** Restricted-audience beliefs — secrets — become a playable economy. Chronicle seeds secrets from what Bethesda already authored, generates a few per hold from its own templates, and lets NPCs create more through §5's machinery (an affair is just a belief with a two-person witness set). Discovering one offers the fork: Expose (broadcast it into the rumor graph and take the visible social consequences) or Hold (gain a hook — spendable leverage, one per NPC, strong secrets reusable on cooldown). A third verb, Release ("your secret is safe"), converts the hook into a deep obligation.

**Worked examples, all vanilla-seeded.**
- *Sybille Stentor.* The Blue Palace's court wizard is a vampire — authored into the game, surfaced almost nowhere. As a Chronicle secret: discoverable through a night-schedule anomaly the sighting system (§8's machinery pointed at NPCs) can actually catch. Expose: Solitude convulses — Elisif's court takes a §2 legitimacy hit mid-war, Falk Firebeard's strain spikes, and the *player's reliability tier* determines whether the town believes it or laughs (an accusation without evidence mutates into "the Dragonborn's gone mad," writeback landing on *the player*). Hold: a strong, reusable hook on the second-most-connected person in the capital — court gossip on demand, a blind eye from the palace, a forced audience.
- *Haelga's ledger.* The Dibellan lover-tokens quest already in the game becomes the template case for many-small-secrets: each mark in the ledger is a separate secret about a separate Riften man (Bolli's marriage, Hofgrir's pride). Chronicle lets the player spend them retail — a hook on Bolli is fishery discounts and dock gossip; exposing Bolli instead detonates his marriage into a §1 storylet chain (Nivenor's revenge shopping spree is already vanilla flavor; Chronicle gives it a cause).
- *Romlyn Dreth* skims Black-Briar mead — vanilla. The interesting edge: this secret's *danger class* is Maven. Exposing it to the town is minor; selling it to Maven is a hook-transfer to the most dangerous holder in the Rift, paid in her coin and her attention. Chronicle models secrets as having interested parties, not just subjects — the buyer side of the leverage economy.
- NPC-held hooks close the loop: Maven holds hooks on half of Riften (vanilla text says as much); Chronicle makes them data. When the player crosses her, her retaliation storylet spends a real hook — Bolli's boats stop carrying the player's bounty-clearing paperwork, because she owns Bolli, and the player can discover *why* by walking the graph.

**Guards.** One hook per NPC held by the player; hooks are never global reputation (they are point-to-point by construction); Release is always available so a mercy build plays the whole economy without a single exposure.

**Pre-LLM rendering.** Hook-spend and expose verbs are dialogue options with template outcomes; the ledger of held secrets renders as a journal section.

---

## 10. Dread: Fear as a Second Axis

**What it is.** Per-observer intimidation, orthogonal to liking: an NPC's fear of the player is a function of what that NPC *believes* the player has done (witnessed > reliable rumor > tavern talk) against their own boldness dial. Crossing thresholds produces Intimidated (compliance, no plotting, nervous barks) and Terrified (flee, comply with anything, report to authorities at the first safe moment). No global fear score exists — Whiterun can dread the player while Solitude has never heard of them, and *that contrast is the feature*.

**Worked examples.**
- The player executes a bandit chief in front of the captured caravan crew rather than out of sight. Witness beliefs are eyewitness-tier violence; the crew disperses to three holds, and for weeks the player meets strangers who flinch — with traceable reasons. Belethor (boldness: low, greed: high) tips into Intimidated the moment the Whiterun rumor lands: prices drop unasked, and his §6 rule under Intimidated forbids the mocking counter-offer class entirely. His shop goes quiet when the player enters; the vanilla sleaze evaporates, replaced by careful courtesy — the *same person under fear*, legible without one line of exposition.
- Contrast case: Uthgerd, boldness maxed, hears the same rumor and her reaction class is `respect_challenge` — fear-immune NPCs turn the dread system into a *sorting* mechanic; who still looks you in the eye tells the player who they're dealing with.
- The Terrified edge and its cost: Sibbi Black-Briar (in jail, reachable, cowardly under the swagger) tips Terrified after the player leans on him with a §9 hook plus a violent reputation. He gives up everything — and then reports the intimidation to Maven at the first opportunity, because Terrified NPCs *comply then tell*, which is the built-in price tag that keeps fear builds from being strictly optimal.
- Dragons cast a system-shadow: a hold at Under Siege (§2 dragon track) applies an ambient dread modifier *toward the sky*, and an NPC who has personally watched the player Shout a dragon out of the air holds awe — mechanically dread with positive valence — which gates unique reaction classes (guards' vanilla "you can shout down a dragon?" lines become earned, per-witness, instead of global).

**Pre-LLM rendering.** Fear tiers map to bark pools, flee/avoid packages, and price/compliance modifiers — all engine-native.

---

## 11. The Pacing Director

**What it is.** A per-hold and global throttle in the L4D shape — Quiet → Building → Crisis → Aftermath → Recovery — that governs how much Chronicle content fires where, with three iron rules: every intrusion is telegraphed before it lands, every off-screen event must cite the belief state that motivated it, and the director steers toward a *distribution* of experiences (so a stealth-thief save and a war-hero save get different mixes) rather than one optimal drama curve.

**Worked examples.**
- The player has spent three quiet in-game days enchanting in Whiterun. The Whiterun clock is deep in Quiet; the director's budget opens. It does not spawn an ambush — it schedules a *telegraph*: Hulda mentions someone was asking after the player (the §3 remnant thread, aging nicely). The player who follows up meets the threat on their own initiative; the player who ignores it gets the ambush two days later on the road — pre-announced, therefore fair.
- Crisis suppression: the Battle for Whiterun just ended (Aftermath). The director *withholds* the pending Rival-brawl storylet and the skooma-den vacancy event — not deleted, queued — because Aftermath states get grief and rebuilding content, not noise. This is the rule that stops Chronicle from being the mod where a dragon, a conspiracy, and a jilted lover all arrive during the funeral.
- Belief citation as the absurdity filter: the off-screen scheduler proposes "Jenassa leaves Whiterun for Markarth." The director requires a motivating belief; finding none, it rejects the event. It finds instead that Saffir and Amren's household carries an unresolved sword-grievance thread (vanilla quest state) plus war strain — and approves "Amren takes guard work," which arrives to the player as Saffir's changed market dialogue. Nothing moves without a reason that could be quoted.
- Distribution steering: the director tracks per-family story counts (conflict, kindness, mystery, politics, commerce). A save drowning in conflict beats gets its next budget biased toward the kindness/commerce families — the Targeted-Trajectory rule as a quota table, which is also the knob an MCM slider exposes as "world temperament."

**Pre-LLM rendering.** The director is pure Python scheduling; its outputs are which storylets fire when — no text of its own.

---

## 12. Physical and Cultural Provenance Objects

**What it is.** The sim made touchable, within the no-geometry rule (placed objects, written text, performed songs — never edited meshes): memorial stones with the real casualty list, commissioned plaques, named weapons whose descriptions accumulate history, letters and journals as evidence, and bard songs about real events that are simultaneously performances and rumor-objects.

**Worked examples.**
- After the Battle for Whiterun, a memorial stone appears by the Gildergreen bearing the names of the guards who actually died in that save's battle. Fralia Grey-Mane's schedule gains a weekly visit if a Grey-Mane is on it; reading the stone grants the player the casualty beliefs at monument-tier reliability. DF's reactive-vs-descriptive distinction is preserved: NPCs who lost someone named there have their §7 strain touched by proximity to it — the stone *does something* to the people it names.
- Hermir Strong-Heart's §7 inspiration blade — "Kyne's Answer, forged in the month the dragon fell at Kynesgrove" — is a real enchantable weapon whose description names the event and whose existence is a rumor. If the player carries it, recognition scenes key off it; if they sell it, it travels (DF artifact propagation, bounded: Chronicle tracks its holder), and its provenance record appends each notable change of hands.
- The Bards College closes the loop: a Chronicle event above a fame threshold generates a song commission storylet — the verses assembled from the event's belief record (template verse forms pre-LLM, composed properly post-LLM), performed on the college's real stages and inn circuit. The song is a broadcast-tier rumor with a *melody*: hearing "The Burning of the Bee and Barb" in Solitude seeds Riften beliefs in listeners who've never been east — including mutations, because the bard heard it thirdhand, and Chronicle knows exactly how garbled the version he learned was.
- Evidence objects, the quiet workhorse: the §9 conspiracy against the player leaves a paper trail *because the plot storylet's discovery-failsafe ladder requires it* — a note in a plotter's pocket, a ledger discrepancy at the warehouse — placed in real containers, readable, each one a belief-grant with provenance. Investigation gameplay is just the evidence system read in reverse.

**Spike honesty.** Persistent placed objects and dynamic book/item text via SKSE need the flagged verification pass; bard-performance injection is the least-trodden path of the four and stays out of the first milestone.

**Pre-LLM rendering.** Template verse/inscription forms with slot fill — stiff but serviceable; the LLM upgrade is pure polish on an already-working delivery channel.

---

## 13. The Conversation Ladder (STC)

**What it is.** A per-conversation escalation state — Greeting → Rapport → Openness → Confidence — that gates the big verbs regardless of standing. Even a Sworn Friend can't be cold-opened with "lend me a thousand septims and tell me your secrets"; the conversation has to warm. Rungs climb through small talk, shared topics (the belief graph supplies what this NPC actually cares about today), gifts in context, and recent shared events; hostile ladders exist too (Needle → Insult → Challenge) and gate how fast a brawl can be provoked.

**Worked examples.**
- The player needs Falk Firebeard's help mid-crisis. At Greeting, the §6 table only exposes court-formal classes. One rung of rapport — and the topics that climb it are drawn from Falk's live beliefs (the Wolfskull rumor he's worried about, at this save's actual state) — unlocks Openness, where the real request classes live. The ladder is why Chronicle conversations feel like *working* a person rather than operating a vending machine, and it's fully deterministic.
- Standing changes the ladder's *slope*, not its existence: Sworn Friend Jenassa starts at Rapport and climbs to Confidence in one warm exchange; Rival Mikael starts below Greeting, and the only ladder he offers the player is the hostile one — which is itself content, because deliberately climbing it to Challenge in front of the Bannered Mare crowd is how a player *manufactures* the §8-witnessed brawl that finally settles things.
- The LLM guardrail role, stated for the record: when the conversation tier lands, the current rung is injected into context and the render is constrained to rung-appropriate register — the structural fix for instant-intimacy, the most-cited LLM-roleplay failure in the research corpus.

**Pre-LLM rendering.** Rungs gate which dialogue branches are visible — vanilla dialogue-condition machinery, nothing more exotic.

---

## 14. Kin-Priority Belief Routing

**What it is.** Household and kin edges are privileged rumor channels: fast, high-reliability, and mandatory for events involving kin. The Sims' hard ceiling — a spouse with zero systemic awareness of their partner's public fight — inverted into a rule small enough to build in a week.

**Worked examples.**
- The player humiliates Idolaf Battle-Born in a §13 hostile-ladder exchange at the market. By dinner, the *entire Battle-Born household* holds the belief at kin-tier reliability — Olfrid's shop prices for the player harden that evening, not next week, and Bergritte's bark goes cold. The feud (§4 house state) moves as a bloc because the routing made the house a genuine information unit.
- Aventus Aretino's situation runs the poignant direction: kin routing is why Windhelm's adults *know* about the boy performing the Black Sacrament (vanilla: they discuss it in the street) — and Chronicle extends it: when the player resolves that thread, whichever way, the Aretino-adjacent households (Idesa Sadri, who vanilla-canonically watches over him) get the outcome first and react before the general rumor wave lands.
- The dark edge that makes it a mechanic rather than flavor: kin routing is *interceptable*. The §2.3 rule that a report needs a living, reachable reporter applies — a player silencing the one witness before they reach their family is making a real, horrible, systemically-coherent choice, and the family's later behavior ("she never came home") runs on the absence.

**Pre-LLM rendering.** Pure Python routing weights; visible entirely through reaction timing.

---

## 15. Group Practices and Third-Party Inference (Research-Gated)

**What it is.** The deontic layer — held at design-candidate status until the BotL and Praxish/RePraxis reads land, per the master doc. The pitch in Skyrim terms: institutions (a Jarl's court, the Companions, the Thieves Guild, a temple) carry obligated/permitted/forbidden status sets that flip for all bound members at once when a triggering fact of sufficient reliability arrives.

**Worked examples, written as the test cases the research read should be evaluated against.**
- A reliable murder accusation against the player reaches Dragonsreach. Today's Chronicle answer: N individual belief updates, arriving raggedly. The Practices answer: the *court* transitions the player's status to Suspect — Irileth's, Proventus's, and the guards' available reaction classes all shift in the same instant, because the institution knows, and "the room turns on you" happens as one legible event. Balgruuf's personal beliefs remain separate — he can privately doubt the charge while his court's practice binds his guards — which is precisely the institutional-vs-personal distinction the design must keep or the layer isn't worth having.
- The Companions after the player's Circle ascension: practice flip grants Whiterun-wide permitted-status changes (Jorrvaskr's doors, Eorlund's forge access, brawl-backup obligations from Farkas and Vilkas) as one operation instead of a dozen hand-tracked pairwise states — the bookkeeping argument for the layer.
- Third-party inference, the CiF/City-of-Gangsters half: Marise sees Bolli leaving Haelga's at dawn *twice* and infers the affair no one told her — an uninvolved z concluding "x cheats on y" from premises. That inference then enters the rumor graph as her belief, provenance "I saw enough." Whether Chronicle wants NPCs who deduce (powerful, but every inference rule is a new way to be wrong at scale) is exactly what the City of Gangsters source read should answer — Zubek shipped it over ~1,200 NPCs, so the costs are knowable rather than speculative.

**Pre-LLM rendering.** Status flips render through the same §6 reaction classes; inference, if adopted, is invisible machinery.

---

## Coda: One Week in Whiterun (the systems in a single braid)

Day 1: the player, freshly Thane, brawls Mikael over Carlotta (§13 hostile ladder, §8 witnesses). Rival crystallizes (§4); the rumor leaves town garbling itself (§5). Day 2: Battle-Born standing dips for the player after Idolaf's needling goes badly (§14 routes it house-wide by dusk); Belethor, hearing the bandit-execution story from a caravan guard, quietly stops haggling (§10). Day 3: the war clock ticks Whiterun into Agitation (§2) — Heimskr's crowd grows, guard barks harden (§6 phase rules); the director (§11), reading rising tension, shelves the pending vacancy event and schedules a telegraph instead: Hulda mentions a stranger asking the player's name (§3 remnant). Day 4: the dragon hits the western farms; Nazeem berates the guards, Severio repairs (§6); Arcadia, chronic strain already war-loaded, breaks (§7) — and Danica's restock storylet casts the player (§1). Day 5: the player helps, Grateful crystallizes, and Constance-tier witnesses seed a kindness rumor that *counter-writes* the execution story's dread in listeners who hold both (§5 writeback doing moral bookkeeping no scalar could). Day 6: the memorial mason arrives for the farm dead (§12); Fralia's schedule bends toward the stone. Day 7: the remnant makes his move on the Rorikstead road — telegraphed, expected, personal, and when he names the fight he survived, the player remembers it too, because it actually happened. Every line of that week is a database row with a date, a witness list, and a reason — which is the whole pitch.
