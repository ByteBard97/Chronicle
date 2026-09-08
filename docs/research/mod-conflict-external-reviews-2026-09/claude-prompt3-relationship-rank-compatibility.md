# Relationship-Rank Conflicts: Chronicle vs. Popular Skyrim SE Relationship Mods

## TL;DR
- The vanilla relationship rank is a **single authoritative signed integer (−4 to +4) per ordered actor pair**, stored in one slot; any mod that calls `SetRelationshipRank` on the same NPC-to-player pair overwrites whatever Chronicle wrote, and vice versa — there is no "layering" or per-mod registry, so it is strictly last-writer-wins.
- Of the mods researched, **almost none write rank on generic/named townsfolk**: RDO overwhelmingly *reads* rank to gate dialogue (one-directional dependency, safe), and its only write is a manual player-triggered MCM tool; follower frameworks (NFF/AFT/EFF) and marriage-expansion mods only write rank when *you* recruit or marry a specific NPC (one-time writes). Genuine "flapping" race conditions are therefore rare and mostly limited to Chronicle vs. another *always-on background simulator*.
- The engine gives Chronicle a real detection hook: **`OnStoryRelationshipChange`** (via the Story Manager "Change Relationship Rank" event node) fires on essentially every rank write regardless of source — console, mod, or quest — so Chronicle can listen for external writes rather than polling.

## Key Findings

**1. Engine model — one value per pair, last-writer-wins.** The Creation Kit exposes relationship rank as a single field settable by `Actor.SetRelationshipRank(akOther, aiRank)` and readable by `GetRelationshipRank`, with values 4 Lover / 3 Ally / 2 Confidant / 1 Friend / 0 Acquaintance / −1 Rival / −2 Foe / −3 Enemy / −4 Archnemesis. There is no independent per-system storage; whoever writes last wins. Two caveats matter for Chronicle: (a) relationship data is **NOT stored for templated (leveled/generic) actors** and is wiped on session end — but all 19 of Chronicle's targets are *unique named* NPCs, so this does not affect them; (b) the value is directional (Actor→Player vs Player→Actor are separate slots).

**2. RDO is a reader, not a writer (mostly).** Relationship Dialogue Overhaul SE adds voiced lines gated by relationship/faction *conditions* — it reads rank, it does not systematically set it. Its only intentional write is a manual MCM tool ("make an NPC hate you, like you, or indifferent") and an MCM toggle to let rank-4 NPCs call the player a loved one. The infamous "Carlotta calls you 'love' at first sight" bug is a **condition (read) error**, not a rank write. Therefore RDO ↔ Chronicle is a **one-directional dependency (type b), safe** in the normal case: Chronicle sets rank, RDO reads it and picks appropriate dialogue. The only exception is if the player manually uses RDO's MCM on one of the 19 NPCs — a one-time write Chronicle would later stomp (type c).

**3. Follower/marriage mods are one-time writers.** NFF, AFT/iAFT, and EFF only touch rank when you actively recruit/marry a *specific* NPC (e.g., NFF forces rank to ≥1 when marrying). These are type-(c) one-time writes limited to whichever of the 19 you personally recruit or marry — not a background race.

**4. Chronicle's true race-condition risk is another background simulator**, not dialogue or follower mods. The dangerous partners are always-on systems that also write rank on townsfolk: NPC-to-NPC social simulators and runtime reputation/grudge systems.

**5. Detection hook exists.** `OnStoryRelationshipChange(akActor1, akActor2, aiOldRelationship, aiNewRelationship)` fires whenever rank changes, routed through the Story Manager's "Change Relationship Rank" event node — confirmed to fire from console, mod, or quest writes.

## Details

### How the vanilla relationship system actually works
The authoritative source is the Creation Kit wiki. `GetRelationshipRank - Actor` and `SetRelationshipRank - Actor` document a single signed value between −4 and +4 for a given pair of actors, with the named ranks listed above. The `Relationship` form in the CK (Object Window → Character → Relationships) defines an initial level between a Parent NPC and Child NPC; the wiki notes that "relationships override factions" for assistance/aggression in combat. The UESP "Disposition" page confirms the default rank is 0 (Acquaintance), that the range is −4 to +4, and that this hidden value (no longer an Oblivion-style visible disposition bar) governs theft thresholds, inheritance letters, and combat assistance.

Crucially for a simulator like Chronicle:
- **Single slot, last-writer-wins.** There is no API to register multiple independent relationship values; `SetRelationshipRank` overwrites. If Chronicle sets Nazeem to −2 (Foe) because of a simulated grudge and another mod sets him to +1 (Friend), the final stored value is simply whichever call executed last.
- **Directionality.** The rank is stored per ordered pair. Community console usage reflects this: players routinely run both `setrelationshiprank player X` (target→player) and `player.setrelationshiprank <target> X` to set both directions. A simulator that writes only one direction can produce asymmetric states another mod's conditions may read unexpectedly.
- **Templated-actor caveat.** The CK wiki (`SetRelationshipRank - Actor`) warns verbatim: "Relationship data is NOT stored for Templated Actors, and any scripts that would set relationship data on a Templated Actor will get wiped once your game session is over (which obviously has bad implications for Save/Load)." This is not academic — UESP's "Skyrim talk:Illia" page documents exactly this failure mode: using "'setrelationshiprank player 4'... templated actors do not save relationship data, which would explain why Illia suffers from recruitment problems after each play session." However, all 19 Chronicle targets (Ysolda, Idolaf Battle-Born, Saffir, Carlotta Valentia, Amren, Adrianne Avenicci, Lars Battle-Born, Braith, Fralia Gray-Mane, Nazeem, Lillith Maiden-Loom, Brenuin, Anoriath, Lucia, Heimskr, Sigurd, Olava the Feeble, Danica Pure-Spring, Olfina Gray-Mane) are unique persistent NPCs, so their ranks *do* persist — good for Chronicle, but it also means a conflicting write is permanent until overwritten.

### RDO — read, not write
RDO SE is fundamentally a dialogue mod. Its Nexus page (mods/1187) describes it as adding "over 5,000 lines of completely voiced dialogue for NPCs using the original voices. Friends, followers, spouses, rivals, and others have much more to say." These lines are gated by dialogue *conditions* that read `GetRelationshipRank` and faction membership. Mechanistically:

- **RDO reads whatever Chronicle writes.** If Chronicle drops Nazeem to Rival/Foe, RDO's negative/disapproving greetings become eligible; if Chronicle raises Ysolda to Friend/Confidant, friendlier lines play. This is the *intended* one-directional flow (type b) and is safe — no write-back to rank.
- **RDO's writes are limited and manual.** The RDO MCM lets the player "make a NPC hate you, like you, or indifferent," and there is an MCM option allowing rank-4 (lover) NPCs to refer to the player as a loved one. RDO's changelog notes: "Non-unique NPCs can now have their relationship rank towards the player adjusted in the MCM. The changes will not be saved for templated actors, but will be active for the duration of the game session where it was changed." These are deliberate, player-initiated, one-shot writes — not a background loop.
- **The Carlotta "love" bug is a read/condition error, not a write.** Users report: "This mod appears to cause an issue with Carlotta Valentina, where she calls you 'love' as if you're together." The root cause is mis-scoped dialogue conditions on Carlotta's hello/greeting topics — RDO's own readme documents reworking Carlotta's topics ("Carlotta has a hello topic that should only be used while offering her merchant services") and the "Update and MCM" patch changelog records a "Fixed wrong condition (xx93E824)" credited to a reporter. RDO is not setting her rank to Lover. **Implication for Chronicle:** this bug will not corrupt Chronicle's stored rank, but it *illustrates* that RDO conditions are the consumer of the rank value — so if Chronicle writes an unexpected rank (e.g., Lover on Carlotta as a "rumor" artifact), RDO will faithfully play lover dialogue: a *semantic* clash, not a data race.

**Verdict: RDO ↔ Chronicle = (b) one-directional dependency, safe.** The only conflict is the optional manual MCM write (type c), easily avoided by not using RDO's MCM on the 19 NPCs.

### Interesting NPCs (3DNPC)
3DNPC's relationship handling is confined to its *own* added NPCs (e.g., raising rank to enable marriage/follower status via `PotentialMarriageFaction`, sometimes set to 4 via console per its own support threads). It does not run a background system that writes rank on vanilla Whiterun townsfolk, and none of the 19 Chronicle targets are 3DNPC characters. **Verdict: no conflict** — disjoint NPC sets.

### Marriage-expansion mods
- **Marry Me Serana / Marriable Serana**: add a single custom-flagged NPC (Serana) to the marriage faction; they do not touch the 19 Whiterun townsfolk. **No conflict.**
- **Multiple Marriages SSE (Dudestia)** and **ORomance Plus**: these set rank/marriage state on whichever NPC *you* marry. ORomance implements its own parallel relationship-point system rather than continuously rewriting vanilla rank. If you marry one of the 19 (e.g., Ysolda, Carlotta, Olfina), the mod performs a **one-time write** (typically rank ≥1 or 4) that Chronicle's grudge simulation could later stomp — **type (c)**. This is the most realistic marriage-mod interaction: e.g., you marry Ysolda (rank 4 Lover), then Chronicle's rumor engine later recomputes her rank downward, silently "divorcing" the relationship at the data level or triggering odd dialogue.

### Follower-trust / loyalty frameworks
- **Nether's Follower Framework (NFF)**: writes rank only on recruitment/marriage of a specific NPC — "When forcing the ability to marry an NPC and their game relationship rank with the player is less than 1, it is set to 1." Its **Regard/Affinity systems are explicitly separate** from vanilla rank: the NFF guide states "Regard has no affect or influence from your vanilla game relationship to them," and adds that "the relationship system for followers is often inflated, making them instantly allies or lovers" — i.e., NFF deliberately does *not* continuously rewrite vanilla rank, using its own parallel scale instead. **Verdict: type (c) one-time write**, only if you recruit/marry one of the 19.
- **AFT / iAFT** and **EFF**: same pattern — rank writes occur at recruit/convert time for the specific follower, not in a background loop. RDO ships compatibility patches for EFF, AFT, iAFT, UFO, and FLP, confirming these coexist at the dialogue level.

**Verdict for all follower frameworks: (c) one-time writes** scoped to NPCs you actively recruit; no flapping unless Chronicle re-writes the same NPC afterward.

### Where a genuine race condition (type a) can occur
A true "flapping" race requires a *second always-on background writer* on the same townsfolk. Candidates surfaced in research:
- **Social NPCs** (a Master's-thesis mod implementing the "Comme il Faut" social model from *Game AI Pro 2*) — NPCs autonomously pursue romance/insult each other via quests. It is scoped to two locations near Whiterun (Honningbrew Meadery and a custom "Comme il Faut House") and primarily governs NPC-to-NPC interactions, so overlap with the 19 player-facing ranks is limited — but it is conceptually the same class of always-on writer.
- **Skyrim Reputation** and similar reputation systems — these mostly gate reactions via factions/globals rather than per-NPC `SetRelationshipRank`, so direct rank contention is limited.
- **NPCs Have Relationships** — sets NPC-to-NPC dispositions *statically via CK records at load*, not at runtime, so it cannot flap against Chronicle; it's a plugin-level record edit resolved once by load order.
- **Follower Dismissal – Immersive Relationship System** — implements a runtime "grudge mode" that writes rank (rank limits 0.0–4.0, grudge mode allows going negative, reconciliation quests set rank back to 1.0). If pointed at any shared NPC this is the closest analog to Chronicle and **would genuinely race (type a)** — two grudge engines fighting over one value.

**The only genuine type-(a) risk for Chronicle is another runtime rank-writing simulator** (another grudge/social/reputation engine) targeting the same named NPCs. Two such systems on a polling/`UpdateGameTime` loop will overwrite each other every cycle, producing oscillation visible as NPCs whose greetings/aggression flip repeatedly.

### The detection hook Chronicle should use
Chronicle can detect external writes rather than polling. The Story Manager exposes a **"Change Relationship Rank"** event node ("Event triggered whenever an Actor changes his Relationship Rank with another actor," carrying Actor1, Actor2, Old Relationship, New Relationship). The corresponding Papyrus quest event, per the CK wiki Quest Script page, is:

```
Event OnStoryRelationshipChange(ObjectReference akActor1, ObjectReference akActor2, Int aiOldRelationship, Int aiNewRelationship)
```

documented as "Sent when this quest is started by a relationship change story manager event." The mod *Relationship Change Notifications* (Nexus mod 34670) proves this works in practice: it has "only one small script activated when the OnStoryRelationshipChange event fires. Doesn't matter if it's triggered by a console command, some kind of mod or a completed quest."

**Caveat Chronicle's author must handle:** the event is routed through the Story Manager's SM Event Node decision tree. The CK wiki (Category:Story Manager) is explicit that "A quest that has a selected event type must be added to the SM Event Node for that event and can only be started through the Story Manager. You cannot start it directly, even with the StartQuest console command." Chronicle's listening quest must therefore be added to the vanilla node with **"Shares Event" checked**, or it risks (a) being suppressed by another mod's quest that starts first, or (b) suppressing other mods' relationship-change quests. Because the event carries old *and* new rank plus both actors, Chronicle can precisely detect "someone other than me just changed Nazeem's rank from −2 to +1" and decide whether to reassert its simulated value or defer.

## Recommendations

**Stage 1 — Establish the authority model (do first).** Because the engine is last-writer-wins with no arbitration, the cleanest design is: Chronicle owns the *simulated* rank in its own script variables, writes to the vanilla field only when its simulated value actually changes, and registers an `OnStoryRelationshipChange` listener (with "Shares Event" checked) so it *knows* when an external write occurred.

**Stage 2 — Classify each coexisting mod and code exceptions:**
- Treat **RDO** as a pure consumer — do nothing; it will read Chronicle's ranks and pick dialogue. Document that players should not use RDO's MCM rank tool on the 19 NPCs (the only type-c clash).
- Treat **follower/marriage mods (NFF, AFT/iAFT, EFF, Multiple Marriages, ORomance)** as one-time writers — add an exception so Chronicle does **not** re-simulate the rank of any of the 19 while they are the player's active follower or spouse (check `PlayerFollowerFaction` / marriage faction / `IsPlayerTeammate` before writing). This prevents Chronicle from silently "divorcing" a married Ysolda or demoting a recruited Amren.
- Treat **another runtime grudge/social/reputation simulator** (Social NPCs, Follower Dismissal's grudge mode, any future one) as the only genuine race — declare incompatible or gate behind a user toggle.

**Stage 3 — Implement anti-flapping guards:**
- Debounce writes: only call `SetRelationshipRank` when the target value differs from the current `GetRelationshipRank`, to avoid needless event churn.
- On an `OnStoryRelationshipChange` where the new value ≠ Chronicle's intended value and the change was not self-originated, either (i) yield for a cooldown period, or (ii) reassert after a delay — but never in a tight loop. A cooldown plus an "external change detected" journal entry is safer than immediate reassertion (immediate reassertion is precisely what produces flapping if the other mod does the same).
- Decide explicitly whether Chronicle writes one direction (NPC→player) or both, and document it.

**Benchmarks that change the recommendation:**
- If testing shows an installed mod continuously rewrites any of the 19 ranks (observable as repeated `OnStoryRelationshipChange` events you didn't cause within seconds), escalate that mod from "coexist" to "incompatible/toggle."
- If a follower/marriage mod is present, the marriage-faction/teammate exception (Stage 2) is mandatory, not optional.
- If Chronicle ever expands to generic/templated townsfolk (guards, generic citizens) rather than the 19 unique NPCs, revisit the whole design — those ranks won't persist across sessions (per the CK templated-actor warning) and the model breaks.

## Caveats
- **No mod literally named "Chronicle" that simulates Whiterun grudges/rumors and writes rank on these 19 NPCs could be found on Nexus or the open web as of September 2026.** The only Nexus "Chronicle" is an unrelated ENB weather preset. This report therefore analyzes Chronicle *as described in the task* — an always-on grudge/rumor simulator writing vanilla rank on 19 named Whiterun NPCs — and maps it against documented behavior of the other mods; the Chronicle-specific conclusions are architectural inferences from the engine model, not observations of a shipping mod.
- The precise internal engine mechanism by which `SetRelationshipRank` triggers the Story Manager event is not documented on a single authoritative page; the "fires from console/mod/quest" conclusion rests on the CK wiki event definitions plus the empirical description in *Relationship Change Notifications*. Treat it as well-supported but verify in your own load order.
- The Carlotta "love" bug root cause (mis-scoped dialogue conditions) is assembled from RDO's own readme fixes plus user bug reports rather than a single definitive dev statement of the exact offending condition record.
- Mod behaviors change across versions; RDO, NFF, AFT, and the marriage mods are actively updated, and MCM options/write behavior may differ by version. Verify against the specific versions in your load order.
- This analysis assumes SE/AE Papyrus and Story Manager behavior; LE differs only trivially on these points, though some cited pages conflate the two.