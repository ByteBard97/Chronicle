# Chronicle — Vision (v2.1)

**Status:** Revision after two independent repo-grounded reviews of v2 draft. Supersedes vision.md v1.
**Publication precondition:** this document cites a constitution (§5) and a finalized scenario ladder (§6). Those artifacts must land in the same commit as this vision — design-doctrines.md, ui-doctrines.md, and scenario-ladder.md (finalized from draft v0.2 plus review corrections) — so every reference here is true at merge time. Do not merge this file alone.
**Changed from v2:** timeline claim corrected; constitution references gated on co-commit; Bet 2's novelty claim scoped and sourced; tell-decision vs. derivation-trace placement disambiguated (trace = tier 1 infrastructure, tell-decision = tier 3 machinery); the inter-hold carrier mechanism added as a named prerequisite for the north star; v0.2 named in the road; "market confidence" clarified as a belief aggregate.

---

## 1. The dream

Skyrim's world is a stage set. Every NPC is a schedule and a barks table; nothing anyone does — the player included — changes what anyone else believes, wants, or remembers. Kill the Jarl and the world does not notice, because the world has no apparatus for noticing.

Chronicle is that apparatus: a social simulation that runs alongside Skyrim and gives its people an inner life with consequences. NPCs **witness** events and form **beliefs with provenance** — they know things because they saw them, or because someone told them, and the sim never forgets which. Beliefs travel as **rumors that mutate in transit**, warped by the teller's loyalties and the hearer's biases, every distortion recorded in a lineage. Beliefs and events accumulate into **grudges, obligations, and reputations that are observer-local** — you are the guild's hero and the widow's monster simultaneously, because those are different people who know different things. And accumulated state **writes back into behavior**: grief reroutes a mourner's days, a grudge empties the shared tavern table, a vacancy pulls a successor out of the web of relationships, and — eventually — an NPC crosses a threshold and *does something about it*.

The shorthand that emerged during design is honest about the ambition: **the Sims in Skyrim**. The Sims is autonomous characters, relationship state accumulated from interaction, autonomy that acts on that state, and — the part that makes it The Sims rather than an ant farm — a god-view where watching is the pleasure because everything is legible. Chronicle builds all four, with one upgrade The Sims never had: Sims have relationship *scores*; Chronicle's people have *epistemologies*. The Sims is a physics of feelings. Chronicle is a simulation of who knows what, how they came to know it, and how wrong they are.

## 2. The north-star test

One scenario is the acceptance test for the whole architecture. The player assassinates Jarl Balgruuf.

- **Succession**: the vacancy resolves through the court's actual relationship and faction state — not a scripted replacement. Different prior relationships produce a different Jarl.
- **Grief and grudge**: his household mourns on their calendars, not in a bark; his children hold grudges with the killing as their evidence; the mourners' rerouted days change who they meet and therefore what they hear.
- **The rumor**: news travels at the speed people move, along kin and trade and tavern edges — carried beyond the hold by the caravaneers and couriers whose routes stitch Skyrim together — and it *mutates*: a Stormcloak blacksmith retells it as an Imperial plot; three weeks later a Markarth merchant greets you with a thirdhand version that is confidently wrong, and the sim can show you every hop that made it so.
- **The ripple**: guard cohesion, market confidence (a belief aggregate over individual merchants — not a price model), and faction posture shift as aggregates over what individuals actually believe — never as a global flag.

When that scenario runs headless and every assertion passes with an intact evidence chain behind it, the architecture works. Everything in the build order exists to make that test passable one mechanism at a time.

## 3. The two bets

The research program — an intensive multi-agent effort producing 22+ cross-validated reports across shipped-game forensics, academic social simulation, hybrid LLM architectures, engine substrate, save-state synchronization, and UI prior art (filed under docs/research/, including the comparative-systems and dashboard-ui-prior-art collections) — established what exists and what doesn't. Chronicle makes exactly two novel bets, and it is honest that they are bets.

**Bet 1 — subjective belief with provenance can drive NPC behavior in a walk-around world.** Every precedent surveyed gives up one half. Crusader Kings has consequence-rich social state but no subjectivity — opinion is summed attitude with perfect information, no provenance, no mutation. Shadows of Doubt has per-observer knowledge with decay, but its citizens don't *act* on it beyond testimony. Kenshi collapses the witness to the faction. The Nemesis system does true per-NPC memory for a bounded roster — and routes it into a patented rank loop Chronicle deliberately avoids. None of the surveyed systems ships believes-because-she-was-told, wrong-because-it-mutated, *acts-because-she-believes* in a spatial world. The mitigation for the bet: the epistemology is built on the most-validated data model in the academic literature (Talk of the Town's belief facets, evidence chains, predecessor lineage), and every tier of it is regression-tested headless before any richer layer sits on it.

**Bet 2 — showing the player how a story changed as it traveled.** The comparative research's flattest finding: this has **no shipped game precedent** in any system surveyed. CK3 has secrets (binary known/unknown); nothing in the games literature renders a belief's mutation history. The nearest analogues are cross-domain: phylogenetics tooling (Nextstrain/Auspice, which annotates mutations directly on lineage branches) and one academic prototype (the "bargaining chips" study, where knowledge-as-inspectable-objects playtested well precisely after hidden social knowledge had failed). This is simultaneously Chronicle's signature mechanic and its least-derisked feature — a scoped claim from a specific research pass, not an independently verified absolute. The mitigation: the variant tree is built first as a *debugging instrument* — it must exist for the developers regardless — so the player-facing bet rides on infrastructure that pays for itself even if the presentation bet fails.

Everything else in Chronicle is deliberately unoriginal: adopted from shipped systems with the failure history read first. That's the doctrine corpus (§5).

## 4. The observation thesis

The dashboard is not tooling for the mod. It is the other half of the product.

Three facts, established independently, converge here. First, the Sims' 25-year lesson: the core pleasure of a social simulation is *legible observation* — the plumbob, the moodlet, the relationship panel; watching is playing. Second, the market's one-sentence complaint about every social system in every game, quoted from the mod that exists to fix RimWorld's: it "gives you a list of names and a number beside each one. It never tells you *why*." Chronicle's provenance layer is the first architecture where *why* is always answerable, all the way down. Third, the UI research confirmed a genuine four-way gap: ABM platforms have inspection without time travel; the Smallville lineage has persistence without interaction; games have legibility without debugging depth; replay systems have the timeline grammar without agent semantics. No surveyed tool combines them. Chronicle's dashboard — god-view map, global tick scrubber where every view renders as-of-T, provenance drill-down, variant lineage tree, run comparison — is that unbuilt instrument.

The consequence for priorities: observability is first-class from the first commit — the event-sourced store, deep-linkable ticks, and the **derivation trace** (specified in the ladder as tier-1 infrastructure: an append-only record of every roll with its value, every rule that fired, and every rule that declined with its reason) — because the same artifact serves three audiences on one timeline. Now: the developer debugging tier assertions. Next: the player who alt-tabs to watch the news of the Jarl's death crawl across the map toward Riften. Eventually: the second-screen mode — Skyrim on the TV, the living town on the monitor — which costs nothing extra because it was the debugger all along. And when the LLM conversation tier arrives, the dashboard inherits the best debugging affordance no debugger has: pause the world and *interview* an NPC against their actual memory.

## 5. The constitution

Design authority lives in three documents committed alongside this vision: **design-doctrines.md** (doctrines distilled from shipped-game failure history), **ui-doctrines.md** (the convergent interaction patterns, pattern assignments for the four hard views, and a prohibition list), and the ADRs. Three doctrines are load-bearing enough to inline:

- **Expected randomness.** Every NPC behavior is probabilistic in firing, deterministic in explanation — surprising in outcome, retroactively explainable in cause, with the reason attached at the moment of action. (Fåhraeus's principle; enforced mechanically by the derivation trace rather than aspirationally by design intent.)
- **Every derived state answers "why."** Who believes this, from what evidence, through whom, since when — the inspectability requirement shapes the schema, not the UI. If the simulator cannot answer why, it cannot be debugged, authored, or enjoyed.
- **One honest mechanic, one named fake.** Every shipped spatial social sim pairs a load-bearing simplification with an honestly-simulated felt mechanic. Chronicle's pair, stated so nobody discovers it as a scandal: it **fakes continuous NPC movement** (discrete schedule blocks, sampled encounters — the same abstraction Skyrim itself uses offscreen) and **honestly simulates belief provenance and mutation** (the thing nobody in the surveyed field has shipped). The fake carries one obligation the honest mechanic must meet: information can only travel where bodies go, so the world's **mobile carriers** — caravaneers, couriers, traveling merchants, NPCs whose schedule blocks span holds — are first-class citizens of the fixture data, because they are the bridges every cross-hold story crosses.

## 6. The shape of the road

**Build order** is the scenario ladder (scenario-ladder.md, finalized from the reviewed v0.2 draft): each tier adds exactly one mechanism, forces exactly the tooling its assertions need, and stays in the regression suite forever. In outline: beliefs and their claims-layer mechanics; one-hop transmission plus the derivation trace; multi-hop propagation with mutation and variant conflict; social accumulation, decay, and the tell-decision gate; state writing back into schedules — the first visible reactivity; roles and vacancy; and the Jarl as a composition test with no new machinery. One amendment carried from vision review into the ladder: **mobile carriers** (inter-hold schedule blocks and the bridge-node fixtures they imply) are a named prerequisite exercised before the composition test, because the north star's Markarth and Riften beats structurally depend on them.

**Version road:** v0.1 is the headless ladder through its early tiers with the dashboard's core views. **v0.2 is the Skyrim seam** — event extraction in, hydration overrides out, save-timeline sync — begun only after the headless suite is green. v0.3 is NPC-initiated social actions with CK-style thresholds, hysteresis, and crystallized named relationships. v0.4 is the economy tier. The LLM layers come strictly last and strictly as renderers — a small local model as semantic mutation engine for ~30 gossip-hub NPCs, a conversation model performing sim state as dialogue with structured output writing evidence back, procedural voice (design-once-then-clone) giving every NPC a permanent unique voice. The LLM is the actor, never the author: facts come from the sim, always.

**The substrate strategy**: pure-Python engine-agnostic core; the Skyrim seam isolated behind a provider abstraction (open-source reference path first, SkyrimNet as a pinned optional adapter); save/reload handled by fork-never-delete timeline branching anchored in the co-save. Skyrim is the first renderer, not the identity — the sim would work over RimWorld or a 2D world, and proving it headless first is what keeps that true.

**Non-goals, stated to stay honest:**
- No economy simulation before v0.4; no LLM anywhere before the symbolic tiers are green; no voice before dialogue exists.
- No in-engine code before the headless scenario suite passes (the seam is the grungiest work and the sim must not wait on it).
- No nemesis-style chains where a player↔NPC-A interaction automatically rewrites NPC-B's parameters+rank+dialogue (patent doctrine; observer-local propagation and vacancy-triggered succession are the compliant — and better — design anyway).
- No global reputation, ever. No belief without an evidence chain, ever. No behavior threshold without hysteresis and an attached reason, ever.
- Not a chatbot mod. The existing AI-NPC mods put a mouth on a static world — "wide as the ocean, deep as a puddle." Chronicle is the missing world; mouths come last.

## 7. What success looks like

Near: the composition-test scenario passes headless, and a stranger can open the dashboard, scrub to the assassination, watch the stain of the news spread, click a wrong belief in Markarth, and walk the chain back to the dagger — without anyone explaining the tool to them.

Far: a player three weeks into a modded playthrough hears an innkeeper repeat a mangled version of something they actually did, realizes the mangling has a history, alt-tabs to the map, and finds the exact blacksmith who bent the story. The world remembered, imperfectly, the way worlds do. That moment — *the lie has a biography, and you can read it* — is the product.
