# Chronicle: Social Ray Tracing
### The fifteen systems described from the player's chair (2026-09-07)

Replaces the mechanism-first descriptions in `chronicle-systems-in-skyrim.md`. Same fifteen systems, inverted.

---

## The organizing principle

Path tracers don't simulate every photon in the room. They shoot a ray from the pixel the camera actually sees and follow it backward until it hits a light. Everything the camera can't reach is never computed, because nobody would have seen it.

Chronicle works the same way. The sim maintains beliefs, sentiments, strain, and phases across thousands of NPCs, but the only part that matters is the part a ray from the player's eye can reach. So every system below is written as a trace: **the moment the player notices**, then the bounces backward, then the founding event the path terminates at.

Four things follow from taking the metaphor seriously.

**Bounce depth is order-of-effect.** Direct light is the guard who watched you do it. First bounce is the guard who heard from the person who watched. Second and third bounces are where the good moments live — the price that went up, the door that closed, the stranger who already knows your name. As in rendering, the direct hit is the least interesting light in the scene.

**Unlit systems don't get built.** If a system's chain never reaches the player's eye at any bounce depth, it isn't wrong — it's unlit, and it shouldn't be built until something makes it visible. Two of the fifteen are flagged as unlit below, honestly rather than dressed up.

**Under-sampling reads as noise.** A path tracer with too few samples produces speckle. Chronicle under-sampled produces NPC behavior with no traceable cause, which the player calls "buggy" and uninstalls over. Every visible reaction must have a complete path home.

**The trace is both the debugger and the mechanic.** During development you point the engine at any NPC behavior and ask it to walk backward to the founding event; if the path doesn't terminate at something real, the behavior is noise and gets suppressed. In play, the same walk is the player asking "who told you that?" and following the answer. One code path, two uses — which is usually the sign an abstraction is correct.

Each system below gets: **what the player sees**, **the trace**, **the order it lands at**, and **how the player can walk it home**.

---

## 5. Gossip mutation and writeback
### *The system that makes consequence arrive somewhere else, later*

**What the player sees.** They come back to Riften after two months in the Reach. Maramal, who was warm before, is cold now — declines to bless their amulet, keeps the conversation short. In the same hour, three market vendors are noticeably friendlier than they were, and Grelka gives them a price she wouldn't have given anyone. Nobody explains any of it. Nothing in the journal changed.

**The trace.** Maramal's coldness resolves to a sentiment; the sentiment resolves to a belief — *the player killed Grelod Kind* — at secondhand reliability. Provenance says he heard it from Dinya Balu. Dinya heard it from a Honorhall donor. The donor heard it from Constance Michel, who was there. The path terminates at an event with a date, a location, and an eyewitness list: the orphanage, two months ago, the player. The friendly vendors trace back along a different branch of the same tree — same founding event, different listeners, opposite writeback, because most of Riften hated Grelod and Maramal's temperament treats a killing as a killing regardless of who died.

**The order.** Third. First order was the belief forming in four witnesses, invisible. Second was the belief traveling and mutating — by Whiterun it had become "an assassin is killing matrons in the Rift," which the player may hear separately and not recognize as their own act. Third order is the one that lands: a town that has quietly re-sorted itself around the player while they were away, expressed as prices, greetings, and one man who won't perform a ceremony.

**Walking it home.** "Why the cold shoulder?" gets Maramal naming what he heard. "Who told you?" gets Dinya. Two more questions gets Constance, who was standing there. The player can trace the whole path in five conversations, and at the end of it they know something they didn't: that Constance talked, that the orphans' gratitude spread it as approval, and that the version circulating in Whiterun has their crime attached to a person who doesn't exist.

**Why it's worth building despite being invisible on its own.** Gossip is not a feature; it's the delivery mechanism that lets every other system's consequences arrive at a distance in space and time from where they were earned. Delete it and Chronicle becomes local — act in Whiterun, Whiterun reacts, done. Keep it and the world extends past the room the player is standing in. It earns its place only because loud systems sit on top of it: crime knowledge that travels (§8) and dread that arrives before the player does (§10).

**Mechanism, compressed.** Beliefs carry mutability classes; facts-of-record hold while scale, motive, and low-confidence identity drift in transit. Receiving a belief about a third party moves the listener's disposition toward that party, scaled by reliability tier and temperament. Travel runs on the social graph with real transit time.

---

## 14. Kin-priority routing
### *The system that makes families act like families*

**What the player sees.** They humiliate Idolaf Battle-Born in the Whiterun market at midday. That evening, Olfrid's prices at the family's business have hardened, Bergritte's greeting is gone, and Alfhild won't serve them at the Bannered Mare's Battle-Born table. Not next week. That evening. The household moved as one unit, faster than the town did.

**The trace.** One bounce, and a short one. Idolaf → household edge → every Battle-Born, at high reliability because kin don't garble each other. The path terminates at the market, four hours earlier.

**The order.** Second, and the second order is the whole point: the first-order effect is Idolaf's own reaction, which the player already expected. The interesting effect is the *speed and reliability* differential — the family knows accurately and immediately while the town gets a mutated version three days later. The player learns the shape of the social graph by watching how fast news outruns them.

**Walking it home.** Trivially — Olfrid will say his brother told him. The trace's value here isn't investigation, it's calibration: the player learns which relationships are fast pipes, and starts making decisions about *where* to do things.

**Honest flag.** This system produces almost nothing on its own. It's a weight change on §5 that makes other systems land correctly. Under the ray-tracing rule it survives only because it changes the *timing* of visible effects, and timing is visible. It's a week of work; it should be treated as part of §5 rather than as its own feature.

---

## 4. Crystallization
### *The system that makes the room react to you*

**What the player sees.** They walk into Whiterun market. Carlotta looks up and turns toward them, mid-sentence with a customer. Two stalls down, Mikael sees them, stops playing, and leaves. Nobody has said anything. The player has been read by the room in four seconds.

**The trace.** Carlotta's turn resolves to a Friend sentiment with a founding memory attached — *stood up to the bard for me* — which resolves to three separate occasions the player backed her against Mikael's pestering. Mikael's exit resolves to Rival, founding memory *humiliated me in my own inn*, same events from the other side. The path terminates at a specific evening in the Bannered Mare.

**The order.** First, and this is the one system on the list where first-order is correct. Crystallization is Chronicle's direct light — it's what makes the sim perceptible minute-to-minute, and everything else is indirect illumination on top of it. Build it early even though it depends on §5 and §14, because without it the player has no evidence that any of this exists.

**Walking it home.** The sentiment's founding memory is queryable in dialogue. "Have I done something for you?" — Carlotta names the night. This is the smallest possible version of the trace mechanic and the right place to prototype it.

**Why the named vocabulary matters.** A scalar disposition can't be talked about. Friend, Rival, Grateful, Beholden, Guilty — a small named set with causes attached is what lets NPCs *say* what they feel and why, which is what lets the player trace anything at all. The vocabulary is the API between the sim and every conversation in the game.

**Mechanism, compressed.** Belief clusters project onto a capped set of named directed states, each carrying its founding memory. A same-cell proximity check fires reaction tiers — bark, expression, approach, exit — rate-limited to once per pair per hour.

---

## 10. Dread
### *The system that makes reputation arrive before you do*

**What the player sees.** They walk into Belethor's shop for the first time in weeks. The sleaze is gone. He's careful, quiet, and gives them a price they didn't ask for. Across town, Uthgerd looks them dead in the eye and says something admiring about the road to Rorikstead. Two people, same information, opposite reactions.

**The trace.** Belethor's caution resolves to Intimidated, which resolves to a belief — *the player executed a bandit chief in front of the man's captured prisoners* — at reliable-rumor tier, arriving via a caravan guard who was one of those prisoners. The path terminates at the player choosing to do it in front of witnesses rather than out of sight. Uthgerd holds the *same belief at the same tier* and her boldness dial converts it to respect instead of fear.

**The order.** Second. First order was the prisoners forming eyewitness beliefs, which the player watched happen and probably didn't think about. Second order is a shopkeeper in a different city adjusting his behavior toward them without a word being exchanged about why.

**Walking it home.** "You seem nervous." Belethor names what he heard and who from. That answer identifies a specific caravan guard, who is a real NPC the player can find — and who has a lot more to say about that afternoon.

**Why the contrast is the content.** A global fear score would make Belethor and Uthgerd behave identically, which teaches the player nothing. Per-observer dread means *who still meets your eye* is a readout of who the people around you actually are. Fear becomes a sorting mechanic rather than a stat.

**The built-in price.** Terrified NPCs comply and then report. Sibbi Black-Briar gives up everything under pressure and tells Maven at the first opportunity. That's what stops the fear build from being strictly dominant.

---

## 6. The production-rule layer
### *The system that makes the same event mean different things to different people*

**What the player sees.** They draw a weapon in the Bannered Mare, once, without thinking. Four things happen at once. The guard by the door moves to intercept and his line is about the war, not the weapon. A farmhand in the corner is out the door before anyone else has moved. Uthgerd laughs and asks if they plan to use it. Hulda goes wary and says nothing. Four reactions, one event, all of them legible as *these specific people*.

**The trace.** Each reaction resolves to a rule that fired, and each rule cites the state that selected it: the guard's cites the hold's war phase at Crackdown; the farmhand's cites a Terrified sentiment toward the player from §10; Uthgerd's cites her boldness dial plus a Friendly sentiment founded on a fistfight the player lost. The paths terminate in four different places — a war the player has been fighting, a bandit camp, a brawl in this same room months ago.

**The order.** First-order visible, but it's the *substrate* — the layer through which every other system's effects get expressed as behavior. Under the ray-tracing frame it's not a light source at all; it's the shading model. Nothing about it is visible on its own, and everything visible passes through it.

**Walking it home.** Not directly traceable by the player, and it doesn't need to be — the reactions it selects are traceable via the systems that supplied their inputs.

**Why it exists.** Every AI-director failure in the research corpus is a language model deciding outcomes. Every success is a deterministic core deciding and language rendering. This table is where that doctrine becomes a file you can read, diff, and mod. Pre-LLM it selects a bark pool; post-LLM it selects what the model is allowed to say. The decision never moves.

---

## 13. The conversation ladder
### *The system that makes people take warming up*

**What the player sees.** They need Falk Firebeard's help with something urgent, walk into the Blue Palace, and find that the request they want to make isn't available to them. What's available is court smalltalk. Three exchanges later — and the topics that worked were about the Wolfskull business he's actually worried about this week — the option they came for appears.

**The trace.** The unavailable option resolves to a rung gate: the request class requires Openness, the conversation opened at Greeting. The topics that climbed the rungs resolve to Falk's live belief state — the game surfaced the things he currently cares about, which are different in a save where Wolfskull is resolved.

**The order.** First order, and mostly *felt* rather than seen. This is the second system I'd flag as weakly lit: a player who never notices the gate just experiences conversations as slightly longer. Its real justification is defensive — it's the structural fix for the instant-intimacy failure that dominates LLM roleplay, and it needs to exist before the language layer lands, not after.

**Walking it home.** Not applicable; there's no causal chain to trace, only a state to notice.

**Where it becomes visible.** The hostile ladder — Needle → Insult → Challenge — is the lit half, because the player can climb it *on purpose* to manufacture a public brawl in front of chosen witnesses. That's a real verb, and it's the reason to keep the system.

---

## 9. Leverage
### *The system that lets the player act on the social world instead of receiving it*

**What the player sees.** They know Sybille Stentor is a vampire. Nothing in the game has told them what to do about it. There's a dialogue option to say so out loud in the Blue Palace, and a different one to let her know they know.

**The trace.** Forward, for once — this is the one system where the player is the light source. Expose sends the belief into the rumor graph at the player's own reliability tier, and *that tier decides what happens*: a Thane with standing detonates the court, while an unknown drifter watches the accusation mutate into "the Dragonborn's gone mad" and lands the writeback on themselves. Hold creates a hook — spendable, once, on the second-most-connected person in Solitude. Release converts it to an obligation that outlives the secret.

**The order.** First order by design, because this is the player's move. The interesting effects are downstream: exposing Bolli's name from Haelga's ledger doesn't just embarrass him, it detonates a marriage, which vacates a role at the fishery, which changes who the player deals with at the docks two weeks later.

**Walking it home.** Backward from those downstream effects, the path terminates at the player's own choice — which is the most satisfying possible termination, and the reason this system carries more weight than its position suggests.

**The honest limit.** This is the only system on the list where the player reaches in and squeezes. Everything else happens *to* them. A world that only ever reacts starts to feel like weather, and one social verb is thin cover for that. The partial answer is that Chronicle doesn't need many new social verbs — it needs the ordinary Skyrim verbs (going somewhere, killing something, carrying something, giving something away) to be read richly by the social layer. Helping Arcadia restock is a fetch quest; what makes it a social act is that the graph notices who benefited and who saw it.

**Seeded, not invented.** Sybille's condition, Haelga's ledger, Romlyn's skimming, Maven's grip on half of Riften — all authored by Bethesda and surfaced almost nowhere. Chronicle's credibility here comes from noticing what already exists.

---

## 11. The pacing director
### *The system that makes the world's timing feel authored*

**What the player sees.** They've spent three quiet days enchanting in Whiterun. Hulda mentions, in passing, that someone was asking after them by name. Two days later, on the Rorikstead road, that person is waiting. The player saw it coming and it still lands, because they chose not to follow up.

**The trace.** The telegraph resolves to a director decision: Whiterun's clock sat in Quiet long enough to open a budget, and the director spent it on a warning rather than an event. The ambush resolves to a §3 remnant thread — a survivor of a fight the player had six weeks ago, who has been alive in the sim the whole time. The path terminates at a bandit camp the player cleared and forgot.

**The order.** Second, and it's the order that separates authored-feeling from random. First order is that events fire; second order is that they fire *when the player has room for them* and are announced before they arrive.

**Walking it home.** The ambusher names the fight he survived. One bounce, and it's the payoff for the whole thread.

**The suppression case matters as much.** After the Battle for Whiterun, the director *withholds* the queued rival-brawl and the skooma-den claim, because Aftermath states get grief and rebuilding, not noise. The player never sees this happen, and its absence is exactly why the funeral isn't interrupted by a jilted lover and a conspiracy.

**The belief-citation rule.** Every off-screen event must cite a motivating belief or it's rejected. The scheduler proposes "Jenassa leaves for Markarth," finds no reason, and drops it. This is the automated version of the ray-tracing discipline: no bounce the camera can't justify.

---

## 8. Non-telepathic crime
### *The system that makes getting away with it a real question*

**What the player sees.** They pick Madesi's strongbox at night with one person in sight. No bounty appears. Nothing happens for two days. Then market barks start landing wrong — "some of us saw what you did" — with still no bounty, no guard interest, no journal entry. Four days after that, a guard stops them.

**The trace.** The barks resolve to a belief held by Grelka, eyewitness tier, and to a second copy she traded to Marise for gossip value. The bounty, when it finally exists, resolves to a report: a named person told a named official on a specific day. The path terminates at the player's own decision about *when* to do it and who was closing their stall.

**The order.** First through third, laddered, and the ladder is the gameplay: knowledge exists before it spreads, spreads before it's reported, is reported before it's actionable. Each gap is a window the player can act in — pay Grelka, spend a hook on her, leave the hold, or get to the guard first with their own version.

**Walking it home.** "Who reported me?" has an answer, and the answer is a person standing in the market.

**Jurisdiction as character.** The same theft in Markarth reaches the guard faster under a Silver-Blood-tightened watch. In Windhelm, a Dunmer witness reports to Ambarys before any guard. Under a war phase shift, an old Solitude bounty arrives in Riften with the occupation — legal knowledge reorganizing with the front line.

**Named risk.** Suppressing vanilla's instant psychic bounty is real engine surgery. Staged fallback: leave guard-witnessed crimes on vanilla behavior, route only unwitnessed crimes through Chronicle — which is the interesting half regardless.

---

## 1. Storylet casting
### *The system that makes quests be about the player's actual history*

**What the player sees.** A courier hands them a letter from Lucan Valerius. It asks for help with a supply run, and it references — specifically, correctly — the night the player stopped a bandit taking his shop's takings. That was seven weeks ago, unmarked, and the player had assumed it was scenery.

**The trace.** The letter resolves to a storylet whose preconditions matched: an unrepaid obligation above threshold, plus an economic-hardship event in the holder's household. The hardship resolves to a war levy from §2. The obligation resolves to the bandit incident, with its date and witness list. Two independent paths, terminating in two different things the player did or lived through.

**The order.** Second. First order is that a quest appears — vanilla does that. Second order is that the quest is *about* the player's history, cast from real data, and would have been a different quest with a different person in it in a different save.

**Walking it home.** The letter does the tracing for them, which is the point: the storylet's text template interpolates the founding memory.

**Engine cautions, handled by design.** Aliases ship optional with a stage-0 validation script reporting fill failures back to the Python engine, because required aliases that fail to fill kill a quest silently. One story event per intended story, because events are consumed. Cast named persistent NPCs, because only persistent references and unique actors resolve outside the loaded area.

---

## 3. Vacuums and remnants
### *The system that makes the player's violence leave a hole in the map*

**What the player sees.** They clear Valtheim Towers. Three days later Carlotta's produce is a septim cheaper and she mentions the road's been easier. A week after that, travelers on the Whiterun–Windhelm road are visibly relaxed. Two weeks later, either the towers are held by a Stormcloak picket and the road is a different kind of dangerous, or a survivor with a grudge and hired help is waiting on it.

**The trace.** The price drop resolves to a toll racket ending — one line of economy write with a citable cause. The picket resolves to §2's war phase deciding who claims a vacancy near a trade road. The ambusher resolves to a persistent survivor created at the end of the original fight, who has been in the sim ever since. All paths terminate at the player clearing the tower.

**The order.** Second and third — a produce price and a road's character are third-order effects of an afternoon of combat, and they're the most convincing evidence Chronicle can offer that the world noticed.

**Walking it home.** Carlotta explains the price if asked. The survivor names the fight without being asked.

**Caps.** Few, named, persistent, and capped per region — the Nemesis pacing lesson. Returns always telegraph through §5 before the ambush fires.

---

## 7. Strain and breaks
### *The system that makes hardship accumulate and then show*

**What the player sees.** Arcadia's shop is closed. It has never been closed. Potion supply in Whiterun visibly gaps, prices at the alternative move, and Danica asks the player to gather restocking reagents. Two days later Arcadia is back and steadier than she was before it happened.

**The trace.** The closure resolves to a break requiring both acute and chronic strain elevated. Acute resolves to the dragon at the western farms three days ago. Chronic resolves to five weeks of Whiterun sitting in Agitation under §2. Neither alone would have done it — the dragon a month earlier would have been one bad day, weathered. The path terminates at a war the player may have started.

**The order.** Second, and the second-order effect is the interesting one: the player experiences a *supply shortage in a city* as the visible face of one person's accumulated stress. The intervention is third order — the fetch quest exists because the break happened because the war ground on.

**Walking it home.** Danica names the cause. Arcadia, after catharsis, names it herself in different words.

**Guards.** Two concurrent breaks per settlement maximum, catharsis mandatory, chronic decline past a threshold requires director sign-off. The tantrum-spiral triple lock.

**Open spike.** The AI-package override mechanism for schedule swaps needs verification.

---

## 2. Phased struggles
### *The system that makes the civil war something the player lives in rather than triggers*

**What the player sees.** Over five weeks in Whiterun, without a single quest marker: Heimskr's crowd gets bigger. The Battle-Born shop stops serving Grey-Manes entirely. Guard barks harden. A Talos worshipper — a named person the player has spoken to — is arrested in the street. By the time Balgruuf commits, the player has watched the town choose sides in real time, and knows which people are on which side because they saw it happen.

**The trace.** Each of those resolves to a hold phase transition, and each transition resolves to accumulated catalyst points from real events: recruiter successes, arrests, a razed granary and — critically — *who the local rumor mill blamed for the undefended granary*, which resolves back through §5 to who spread the story. The path terminates in dozens of small events, most of which the player witnessed and none of which announced themselves as war content.

**The order.** Third and beyond. This is Chronicle's deepest bounce: a shop's customer policy is three steps removed from a recruiter's conversation in an inn a month ago.

**Walking it home.** Partially. The player can ask why the arrest happened and get a chain; the full phase state is better surfaced as court dialogue than as a traceable path.

**Two imported guards.** Phase-specific decay pressure, so no phase becomes a permanent attractor — a hold untouched for a month visibly normalizes. And phases change policy only, never individual faction membership: Windhelm entering Crackdown gives Brunwulf grievance beliefs and makes him castable into dissent storylets, but never flips his allegiance. The loyalty cascade is impossible by construction.

---

## 12. Provenance objects
### *The system that makes the sim touchable*

**What the player sees.** A memorial stone by the Gildergreen that wasn't there before, bearing names — the actual guards who died in this save's battle. Fralia Grey-Mane visits it weekly, because one of the names is hers to visit. Later, in a Solitude inn, a bard performs a song about a fire in Riften the player has never heard of, and the version he sings is wrong in specific ways.

**The trace.** The stone's names resolve to a casualty list from a real battle. Fralia's new schedule resolves to a kin edge to one of those names. The bard's song resolves to a rumor object with a provenance chain, and its wrongness resolves to the specific mutations it accumulated on the way to him — which means the player, hearing it, is receiving a garbled belief and can trace the garbling.

**The order.** Second. The object is first-order — it exists, the player reads it. The second-order effect is that the object *acts on people*: proximity to the stone touches the strain of those it names. The Dwarf Fortress distinction, preserved — reactive, not merely descriptive.

**Walking it home.** The stone grants the casualty beliefs at monument reliability. The bard can be asked where he learned it.

**Spike honesty.** Persistent placed objects and dynamic item text via SKSE need verification. Bard-performance injection is the least-trodden of the four and stays out of milestone one.

---

## 15. Group practices and third-party inference
### *The system that makes a room turn on you at once*

**What the player sees.** They walk into Dragonsreach and the room has changed. Not one person at a time — Irileth, Proventus, and every guard on the floor are all treating them as a suspect in the same instant. Balgruuf, privately, is not sure he believes it, and says so.

**The trace.** The simultaneity resolves to an institutional status flip: the court's practice moved the player to Suspect, binding every member at once, while Balgruuf's *personal* beliefs remain separate from what his court's practice obliges his guards to do. The path terminates at a reliable accusation arriving at the court.

**The order.** First, and the value is entirely in the simultaneity — the same information arriving raggedly across N individuals is a different and much worse experience than a room turning as one.

**The risky half.** Third-party inference: Marise sees Bolli leaving Haelga's at dawn twice and concludes an affair nobody told her, which then enters the rumor graph with provenance "I saw enough." Powerful, and every inference rule is a new way to be wrong at scale. Zubek shipped this over roughly 1,200 NPCs in City of Gangsters, so the costs are knowable rather than speculative — read BotL and Praxish/RePraxis before deciding.

**Status.** Research-gated. Not a build item yet.

---

## What the frame changed

Running the trace on all fifteen produced three findings that the mechanism-first version hid.

**Two systems are weakly lit.** Kin-routing (§14) produces no visible effect of its own; it changes the *timing* of other systems' effects, which is real but means it should be treated as part of §5 rather than as a feature. The conversation ladder (§13) is felt rather than seen, and its lit half is the hostile track, which is a player verb rather than a gate.

**The deepest bounces are the best content.** Every example that made the world feel alive rather than mechanical landed at second or third order: a produce price, a closed shop, a shop's customer policy, a cold shoulder from a priest two months later. First-order effects are what other mods already do.

**Gossip is plumbing, and that's the argument for it.** It generates nothing visible by itself. It is the only reason consequences can arrive somewhere other than where they were earned, at a time the player didn't choose — which is the entire difference between a reactive world and a set of local scripts.

**The one structural worry, unresolved.** Fourteen of fifteen systems act on the player. One lets the player act on them. The frame makes this obvious in a way the old document didn't: almost every trace terminates at something the player did *physically* — killed, cleared, carried, gave — and the social layer's job is to read those ordinary acts richly. That may be the correct answer rather than a gap, but it's worth deciding on purpose instead of by default.
