# Social Simulation Literature for Game-Scale Belief Systems

**Scope:** a social simulation layer for roughly 1,000 named NPCs, supporting beliefs with provenance and strength, rumor propagation with mutation, grudges, obligations, and reputation.  
**Date:** 2026-08-21  
**Recommended stack:** Talk of the Town-style subjective beliefs and evidence chains; Gossamer-style gossip phases; City of Gangsters-style sparse relationship histories; simplified epidemic rumor states; observer-local trust/reputation; and cheap cognitive-memory approximations rather than a full cognitive architecture.

## 1. Executive recommendation

Build the social layer around **immutable world events plus mutable subjective beliefs**. The simulator records what objectively happened once, then gives every NPC its own belief instances pointing at claim variants. Each belief carries confidence, verbatim and gist strength, evidence type, source chain, timestamps, and mutation history. Rumors do not update globally every tick; they activate only when NPCs meet, remember something salient, decide whether to share it, and mutate it during retrieval or retelling.

The main scale rule is: **never maintain or update a complete 1,000-by-1,000 social matrix**. A complete directed graph over 1,000 NPCs has 999,000 ordered pairs. Use sparse acquaintance, witness, family, workplace, faction, and reputation edges instead. Socialog's reported decline from roughly 15–25 ms per tick at 50 characters to about 600 ms per tick at 450 characters illustrates why per-tick all-pair evaluation becomes expensive as casts grow.[^1] City of Gangsters is the closest shipped scale precedent: it represented approximately 1,200 interactive NPCs with a sparse directed relationship graph and logic-programmed social inference rather than a complete relationship matrix.[^2]

The recommended model can be implemented in Python with SQLite or DuckDB for canonical events, claim variants, evidence, obligations, and relationship history; NumPy arrays or typed Python records for active memory caches; and deterministic seeded mutation functions for repeatable playtests. The result should be inspectable: every rumor, grudge, obligation, or reputation score should answer “who believes this, from what evidence, through whom, since when, and why has it changed?”

### Adoption guide

| Category | Use |
|---|---|
| **Adopt directly** | Canonical-truth/subjective-belief split; evidence predecessor chains; encounter-driven rumor spread; Gossamer's witness/reflection/propagation/decay loop; sparse relationship histories; bounded short-term and long-term memory; observer-local reputation. |
| **Adopt in simplified form** | DK/MT/SIHR rumor states; bounded-confidence updates for continuous attitudes; Friedkin–Johnsen private dispositions; Beta or subjective-logic reputation evidence; BOID-style obligations as records rather than full deliberation; ACT-R-inspired activation; verbatim/gist memory separation. |
| **Study, but do not copy wholesale** | Comme il Faut, Prom Week, Ensemble, Versu/Praxish, Lyra, Kismet, Anthology, Felt, Winnow, Centrifuge, Drolta, Generative Agents. These offer strong mechanisms and warnings, but copying an entire architecture is usually less useful than extracting its data model. |
| **Avoid at game scale** | Full pairwise social recomputation; one global reputation score; heavyweight BDI/normative deliberation for every NPC; unconstrained LLM feedback into canonical social state; and unbounded memory retention. |

---

## 2. UCSC Expressive Intelligence Studio lineage and character knowledge

### 2.1 James Ryan, *Curating Simulated Storyworlds* (2018)

**Citation:** James Ryan, *Curating Simulated Storyworlds*, PhD dissertation, University of California, Santa Cruz, 2018.[^3]

**Mechanism:** Ryan's dissertation argues that simulation alone does not yield stories: rich simulations generate enormous amounts of raw event history, most of which is boring or narratively unusable. His answer is **curationist emergent narrative**—simulate broadly, then use authored or learned sifting methods to select events, belief changes, conflicts, and character arcs worth presenting. Talk of the Town supplies the simulated world, while story-sifting tools treat the history as queryable narrative material. This separation matters because narrative presentation can evolve without contaminating the underlying simulation.

**Implementability in Python at game scale:** Highly applicable as an architectural principle, not as a complete runtime. Store raw events and belief transitions in relational tables, then run cheap batch sifters every few seconds or on chapter/quest boundaries. At 1,000 NPCs, avoid querying every event against every authored pattern continuously; index by event type, location, participant, relationship, and time bucket. The dissertation's key lesson—separate simulation, curation, and presentation—should be adopted directly.

### 2.2 Ryan, Summerville, Mateas, and Wardrip-Fruin, “Toward Characters Who Observe, Tell, Misremember, and Lie” (2015)

**Citation:** James Ryan, Adam Summerville, Michael Mateas, and Noah Wardrip-Fruin, “Toward Characters Who Observe, Tell, Misremember, and Lie,” AIIDE 2015.[^4]

**Mechanism:** This is the foundational paper for subjective knowledge in a simulated storyworld. Characters can observe events, receive testimony, form beliefs, misremember details, and intentionally lie. Beliefs are therefore not copies of global truth: they are claim variants with provenance and strength. Evidence can come from direct observation or another character's statement, and later versions of a belief can link back to predecessors. Mutation is modeled through operations such as omission, transfer, exaggeration, confabulation, and category-consistent substitution.

**Implementability in Python at game scale:** Adopt directly. Represent each fact as a typed claim with named slots, then store per-holder `BeliefInstance` records and linked `Evidence` records. Mutation can be a small library of deterministic, seeded slot transforms: drop a slot, replace an entity with a category sibling, strengthen a number, change source attribution, or merge similar episodes. This is much cheaper than probabilistic logical inference and produces inspectable explanations.

### 2.3 Ryan and Mateas, “Simulating Character Knowledge Phenomena in Talk of the Town” (2017)

**Citation:** James Ryan and Michael Mateas, “Simulating Character Knowledge Phenomena in Talk of the Town,” in *Game AI Pro 3*, chapter 37, 2017.[^5]

**Mechanism:** The chapter turns the AIIDE model into implementation guidance. Talk of the Town maintains belief facets, evidence objects, predecessor chains, source affinity, evidence type, source confidence, age, salience, and transition schemas. The same underlying event can become several incompatible beliefs as it is observed, recalled, told, and retold. Crucially, the design distinguishes the world simulator's canonical account from what each person thinks happened, allowing interrogation, gossip, deception, and dramatic irony.

**Implementability in Python at game scale:** This should be the primary implementation reference. The chapter's structures map cleanly to relational rows and dataclasses. At 1,000 NPCs, keep only active belief caches in memory and persist cold belief chains to SQLite. Evidence strength can be computed lazily from type, source affinity, source reliability, and age; do not recompute the entire belief graph when one piece of evidence changes.

### 2.4 Ryan, Mateas, and Wardrip-Fruin, “Open Design Challenges for Interactive Emergent Narrative” (2015)

**Citation:** James Owen Ryan, Michael Mateas, and Noah Wardrip-Fruin, “Open Design Challenges for Interactive Emergent Narrative,” ICIDS 2015.[^6]

**Mechanism:** The paper identifies four design challenges that matter beyond the simulator itself: modular content, compositional representation, story recognition, and story support. Its core warning is that improving simulation richness does not automatically improve the player's experience; the system must also expose causes, recognize interesting event sequences, and support them without destroying emergence.

**Implementability in Python at game scale:** Adopt the practice immediately. Build a belief inspector that can show a claim, every variant, its evidence chain, and all holders sorted by confidence or relationship. Add deterministic replay seeds and exportable event timelines. These tools are cheaper than additional simulation sophistication and will save more development time.

### 2.5 Max Kreminski, “Toward Better Gossip Simulation in Emergent Narrative Systems” (Gossamer, 2023)

**Citation:** Max Kreminski, “Toward Better Gossip Simulation in Emergent Narrative Systems,” IEEE Conference on Games, 2023.[^7]

**Mechanism:** Gossamer is the strongest direct post-Talk-of-the-Town model for this project. It divides gossip into four phases: **witnessing**, **reflection**, **propagation**, and **decay**. Each character has an individual memory database; witnesses record event interpretations, reflection derives salient gossip, propagation transmits selected claims during social encounters, and decay weakens or forgets old material. Familiarity and salience can be estimated from entity-reference counts, and DataScript-style queries make memory content authorable and inspectable.

**Implementability in Python at game scale:** Adopt directly, replacing DataScript with SQLite, DuckDB, or a small Python query layer. Run witness and reflection processing only for NPCs involved in or near events; run propagation only during encounters; run decay as a periodic batch. Gossamer's phase boundaries are the right way to prevent rumor logic from becoming a monolithic global update.

### 2.6 Johnson-Bey, Nelson, and Mateas, “Exploring the Design Space of Social Physics Engines in Games” (2022)

**Citation:** Shi Johnson-Bey, Mark J. Nelson, and Michael Mateas, “Exploring the Design Space of Social Physics Engines in Games,” ICIDS 2022.[^8]

**Mechanism:** This paper organizes social simulation engines around three recurring concerns: characters and relationships, social dynamics, and interaction between the player/NPCs and the social system. It shows that “social physics” is not one mechanism but a design space: systems can simulate attraction, norms, practices, obligations, information, or group identity, and they can expose those systems through very different player-facing actions.

**Implementability in Python at game scale:** Use it as a requirements checklist. Before adding a mechanism, identify whether it changes relationships, beliefs, norms, affordances, or narrative selection. The paper does not give a drop-in runtime, but it prevents a common architecture failure: mixing reputation, obligation, attraction, and knowledge into one opaque affinity score.

### 2.7 Shi Johnson-Bey, *Designing Reusable Tools for Social Simulation-Driven Emergent Storytelling* (2025)

**Citation:** Shi Johnson-Bey, *Designing Reusable Tools for Social Simulation-Driven Emergent Storytelling*, PhD dissertation, UC Santa Cruz, 2025.[^9]

**Mechanism:** Johnson-Bey's dissertation collects work on reusable social simulation and story-sifting infrastructure, including Neighborly, Minerva, Drolta, composable sifting patterns, and anomaly detection as a tool for finding unusual simulation traces. Its central contribution is tool reuse: social simulation should expose structured data that can be queried, visualized, and reused across projects rather than hard-coded into one game's narrative logic.

**Implementability in Python at game scale:** Highly relevant. Drolta is especially promising because it uses Python and SQLite rather than requiring a custom in-memory logic engine. Adopt the dissertation's modularity: social facts first, query layer second, narrative patterns third. Treat autoencoder anomaly detection as a development aid for surfacing strange runs, not as a replacement for authored story patterns.

### 2.8 Neighborly

**Citation:** Shi Johnson-Bey et al., Neighborly project and associated social simulation tooling.[^10]

**Mechanism:** Neighborly is a reusable, community-scale social simulation framework in the UCSC lineage. It models characters, relationships, locations, occupations, life events, and town-level history in a way intended to support emergent stories. Compared with Talk of the Town, it is more directly concerned with reusable tooling and simulation components that can be carried across projects.

**Implementability in Python at game scale:** Study its data model and component boundaries, but do not assume the full framework is needed. For a new game, copy the pattern of typed social facts, relationship histories, and event-driven updates into the game's own ECS or persistence layer. The lesson is reuse through stable schemas, not necessarily importing every system.

### 2.9 Felt: a simple story sifter

**Citation:** Max Kreminski, Melanie Dickinson, and Noah Wardrip-Fruin, “Felt: A Simple Story Sifter,” ICIDS 2019.[^11]

**Mechanism:** Felt treats story discovery as pattern matching over simulation state and history. Authors write declarative patterns that find interesting combinations of characters, beliefs, relationships, and events. Instead of forcing the simulator to produce only narratively good behavior, the system overgenerates and then sifts.

**Implementability in Python at game scale:** Adopt as a batch query model. SQL views, pandas queries, or a small rule engine can implement most Felt-like patterns over indexed event and belief tables. Continuous matching over all history would be expensive, so trigger sifting after important events or during quest-generation passes.

### 2.10 Winnow: incremental story sifting

**Citation:** Max Kreminski, Melanie Dickinson, and Michael Mateas, “Winnow: A Domain-Specific Language for Incremental Story Sifting,” AIIDE 2021.[^12]

**Mechanism:** Winnow improves on one-shot sifting by maintaining partial matches as simulation data arrives. A story pattern can therefore be recognized progressively without rescanning the complete history. Partial-match pools, invalidation, and expiration make it possible to notice emerging stories while a simulation continues.

**Implementability in Python at game scale:** Study closely and implement selectively. For 1,000 NPCs, incremental matching is valuable for high-value patterns such as “A wronged B, A is spreading a rumor about B, and B has an unpaid obligation to A.” Use it only for a small authored pattern set; generic incremental rule matching over every social fact would recreate the performance problems of a full production system.

### 2.11 Centrifuge

**Citation:** Max Kreminski, Shi Johnson-Bey, and collaborators, Centrifuge visual story-sifting work.[^13]

**Mechanism:** Centrifuge gives authors a visual interface for constructing and testing story-sifting patterns against Talk of the Town-like simulation data. Its importance is authorability: social simulation produces many possible narratives, and non-programmer authors need ways to inspect matches, refine patterns, and understand false positives.

**Implementability in Python at game scale:** Do not copy the interface wholesale, but copy the workflow. A simple internal web page or notebook that runs named SQL/Drolta queries and shows matching timelines will provide most of the benefit. This is a development tool, not runtime overhead.

### 2.12 Drolta

**Citation:** Shi Johnson-Bey, Drolta project and dissertation material.[^14]

**Mechanism:** Drolta is a Python/SQLite story-sifting language with Datalog-inspired semantics. It makes simulation state and event history queryable without requiring a specialized in-memory database. Because it sits on ordinary relational storage, it is particularly compatible with an append-only event log and materialized per-character belief views.

**Implementability in Python at game scale:** Strong candidate for adoption in simplified form. Even if the actual Drolta language is not used, its architecture—Python orchestration, SQLite persistence, declarative narrative patterns—is directly practical. It is more appropriate for quest hooks and narrative selection than for per-tick social cognition.

### 2.13 Composable story-sifting patterns (2025)

**Citation:** “Emergent Narratives with Composable Story Sifting Patterns,” ACM 2025.[^15]

**Mechanism:** This work makes story patterns composable and incremental. High-level events can be detected from lower-level events, partial matches can persist, and matches can expire or become invalid when simulation state changes. The result is a cleaner path from raw social simulation to quests, rumors, and narrative beats.

**Implementability in Python at game scale:** Adopt the composition principle. Define low-level pattern queries such as `harm_event`, `witnessed_by`, `has_grudge`, and `owes_favor`, then compose them into named narrative patterns. Keep pattern evaluation event-triggered and budgeted.

### 2.14 Awash: prospective story sifting

**Citation:** Awash paper on prospective story-sifting intervention.[^16]

**Mechanism:** Awash combines story sifting with indirect intervention. Instead of merely noticing completed stories, the system identifies partially matched patterns and can nudge the world toward satisfying them through drama-manager-like stage directions. This turns sifting into a prospective narrative-control mechanism.

**Implementability in Python at game scale:** Useful for quest generation, but dangerous if hidden from designers. At game scale, use it sparingly: when a high-value pattern is close, add an optional opportunity, invitation, witness, or reminder rather than forcing NPC behavior. Keep interventions authored and explainable.

### 2.15 TED: fast declarative character simulation

**Citation:** Ian Horswill and Samuel Hill, “Fast, Declarative, Character Simulation Using Bottom-Up Logic Programming,” AIIDE 2024.[^17]

**Mechanism:** TED uses bottom-up logic programming to make declarative character simulation fast enough for game use. The reported comparisons describe it as dramatically faster than Prolog-style evaluation, compact relative to C#, and only modestly slower than hand-written C# in the tested workloads. The relevant mechanism is not logic for its own sake, but efficient rule evaluation over social state.

**Implementability in Python at game scale:** Study for rule-evaluation strategy, not necessarily as a dependency. A Python implementation should use SQL joins, indexed relational tables, and targeted rule queues rather than naive recursive logic programming. TED supports the broader conclusion that declarative social rules can be practical if evaluation is data-indexed and incremental.

### 2.16 Socialog and the cost of pairwise social physics

**Citation:** Socialog performance analysis in the UCSC social simulation lineage.[^18]

**Mechanism:** Socialog demonstrates the characteristic scaling trap of social physics: pairwise social rules are easy to express but expensive when evaluated across every pair of characters. The reported timing growth—from tens of milliseconds at 50 characters to hundreds of milliseconds at 450—shows that social rule evaluation can become the bottleneck before rendering or pathfinding does.

**Implementability in Python at game scale:** Treat this as a warning. Do not compute attraction, opinion, obligation eligibility, and rumor affordances for all ordered pairs. Use candidate generation from location, faction, kinship, workplace, existing relationships, and recent encounters. Maintain per-NPC shortlists and update only edges touched by events.

### 2.17 Kismet

**Citation:** Kismet papers from the UCSC expressive-AI lineage.[^19]

**Mechanism:** Kismet explores socially driven character interaction and authored conversational/social affordances. It belongs to the same general design family as social physics engines: behavior becomes legible when characters act from explicit social state, roles, motives, and constraints rather than purely local dialogue scripts.

**Implementability in Python at game scale:** Study for interaction design and author-facing representations. The specific system should not be treated as a scalable belief engine. Extract the idea that dialogue choices should read and write typed social facts, with every consequence visible to the social layer.

### 2.18 Anthology

**Citation:** Anthology character-simulation work, AIIDE 2022.[^20]

**Mechanism:** Anthology combines motive-based decision-making, relationship knowledge, action preconditions/effects, inspection interfaces, and documentation. It is important because it treats author understanding and debugging as first-class features of a character-simulation architecture.

**Implementability in Python at game scale:** Adopt the inspectability and motive records. At 1,000 NPCs, full motive deliberation for everyone is unnecessary; run detailed decision-making only for NPCs in active scenes and use scheduled background routines for the rest. Anthology is a good design reference, not a wholesale runtime blueprint.

---

## 3. Social-physics anchor systems and LLM-era comparisons

### 3.1 Comme il Faut

**Citation:** “Comme il Faut: A System for Authoring Playable Social Models,” AIIDE 2011.[^21]

**Mechanism:** Comme il Faut represents social situations as rules over characters, relationships, social context, and desired dramatic effects. It allows authors to specify how social state changes the meaning and consequences of actions. Rather than scripting every scene, it evaluates a shared social model to determine what characters can plausibly do and how others should react.

**Implementability in Python at game scale:** Study but do not copy wholesale. Its most valuable lesson is that social actions need typed preconditions and social effects. At 1,000 NPCs, do not run broad rule matching for every NPC; instantiate candidate actions only for current conversation participants and NPCs directly affected by an event.

### 3.2 Prom Week

**Citation:** Josh McCoy et al., “Prom Week: Social Physics as Gameplay,” FDG 2011, and “Prom Week,” FDG 2012.[^22]

**Mechanism:** Prom Week operationalizes Comme il Faut as a playable game. Characters have relationships and social facts; player-selected social actions succeed or fail according to the social model and then change that model. Its success demonstrates that authored social rules can support play, but its production history also shows how expensive it is to author enough rules and content for dramatic variety.

**Implementability in Python at game scale:** Use its player-facing pattern: social moves should be explicit actions with visible prerequisites and consequences. For a systemic world, generate a smaller set of general moves—confide, accuse, apologize, ask favor, collect debt, blackmail—rather than thousands of bespoke social interactions.

### 3.3 Ensemble

**Citation:** “Ensemble: A Social Physics Engine for Games,” FDG 2015.[^23]

**Mechanism:** Ensemble distilled lessons from Comme il Faut and Prom Week into a publicly described social physics engine. It models social state, character desires, history, and rules that determine which social actions are possible and how they change relationships. The engine makes social state portable across game projects rather than embedding it in one script.

**Implementability in Python at game scale:** Study its separation of social facts, rules, and action selection. A Python version should use typed tables and indexed candidate queries, not global symbolic search. Ensemble is architecturally instructive but should be reduced to a small domain-specific rule set for a 1,000-NPC game.

### 3.4 Versu

**Citation:** Emily Short and collaborators, “How Versu Works,” official Versu documentation.[^24]

**Mechanism:** Versu models social interaction through concurrent social practices. Characters can occupy roles in multiple practices at once, and role-specific evaluations determine what behavior is appropriate, offensive, compliant, or disruptive. The system records why an action was selected, making social reasoning inspectable. It is especially relevant for obligations, face, propriety, and context-dependent behavior.

**Implementability in Python at game scale:** Adopt the concept of active social practices, but keep only a few concurrently active per scene. Model practices as state machines or rule sets—courtship, negotiation, investigation, feast, trial—with role slots and role obligations. Full Versu-style generality is likely unnecessary; scene-local practice evaluation is cheap and authorable.

### 3.5 Praxish and RePraxis

**Citation:** Max Kreminski, Praxish repository and paper; Shi Johnson-Bey, RePraxis repository.[^25][^26]

**Mechanism:** Praxish is a partial reconstruction of Versu's Praxis logic language, including an exclusion-logic database, social practices, planning, arithmetic, subqueries, impossible-action detection, and database diffs. RePraxis ports related ideas to a .NET in-memory logical database. Together they show how Versu's social-practice model can be recreated as executable infrastructure rather than treated as a black box.

**Implementability in Python at game scale:** Study Praxish closely for practice and exclusion semantics, but use SQL and explicit Python rule functions where possible. A game team will benefit more from readable schemas and debuggers than from recreating a general logic language. `DB.diff`-style change tracking is worth adopting for debugging and UI explanations.

### 3.6 Lyra

**Citation:** Sasha Azad and Chris Martens, “Lyra: Simulating Believable Opinionated Virtual Characters,” AIIDE 2019.[^27]

**Mechanism:** Lyra separates private attitude, expressed opinion, uncertainty, bias, public-compliance threshold, private-acceptance threshold, opinion clustering, and affinity groups. A character may privately disagree with what they are willing to say publicly, and social influence can change expression before it changes conviction. This is directly relevant to rumor, reputation, faction pressure, and polite lying.

**Implementability in Python at game scale:** Adopt in simplified form for continuous attitudes and ideological positions. Store `private_opinion`, `public_opinion`, `uncertainty`, and `compliance_threshold` per NPC-topic pair. Do not use it for concrete event beliefs such as “Mara stole the ring”; those belong in the claim/provenance model.

### 3.7 Generative Agents

**Citation:** Park et al., “Generative Agents: Interactive Simulacra of Human Behavior,” UIST 2023.[^28]

**Mechanism:** Generative Agents stores observations in a memory stream and retrieves memories using recency, importance, and relevance. Recency uses exponential decay; importance is an LLM-rated score; relevance is embedding similarity. Important accumulated memories trigger reflection, which creates higher-level beliefs that can guide plans. The system demonstrates how memory retrieval can produce believable daily behavior and conversations.

**Implementability in Python at game scale:** Study, but do not copy as the source of truth. Per-NPC LLM importance scoring and embedding retrieval are too expensive and too opaque as the canonical basis for 1,000 persistent characters. Adapt the formula cheaply: recency from timestamps, importance from event tags and relationship intensity, relevance from keyword/entity overlap. If an LLM is used, let it summarize already-grounded retrieved records.

### 3.8 Slice of Life

**Citation:** Slice of Life work on symbolic social state with LLM surface realization.[^29]

**Mechanism:** Slice of Life uses symbolic social state to ground generated character dialogue. The symbolic system remains the authority over relationships and facts, while the language model turns selected state into natural language. This reduces hallucination relative to allowing the model to invent social facts, although it does not eliminate generation errors.

**Implementability in Python at game scale:** Adopt the boundary. A practical pipeline is: social simulation selects grounded facts → prompt renderer converts them to dialogue context → LLM generates wording → postprocessor checks that no forbidden new facts were introduced → symbolic state changes only through explicit action outcomes. Never write generated prose directly back into canonical memory.

### 3.9 Paradise

**Citation:** “Paradise: A Social Simulation Game with Large Language Models,” ACM 2024.[^30]

**Mechanism:** Paradise extended Ensemble-style social physics with GPT-3 and documented a “worst-of-both-worlds” failure mode. The symbolic model and the LLM could disagree: generated dialogue produced social implications that the symbolic engine had not authorized, while tightly constraining the model made dialogue repetitive. The work is valuable precisely because it reports the integration failure clearly.

**Implementability in Python at game scale:** Treat it as a required postmortem. Use LLMs only as surface realizers, optional summarizers, or offline content generators. Social truth should change only when the simulation applies a typed action effect. If generated dialogue is allowed to affect state, route it through a strict extractor and reject unsupported claims.

### 3.10 Bad News

**Citation:** *Bad News* project and publications.[^31]

**Mechanism:** Bad News combines a simulated town, character knowledge, and live performance. A performer interacts with a player using information tracked by the underlying simulation. It demonstrates the dramatic power of persistent character knowledge and social history, but also the difficulty of maintaining a rich authored world and a playable interaction loop.

**Implementability in Python at game scale:** Study for experience design. The most transferable feature is not its full architecture but its use of concrete knowledge—who knows what, who is related to whom, what happened recently—to create socially specific interactions. At 1,000 NPCs, maintain this concreteness in data, not in LLM prompts.

---

## 4. Rumor propagation, opinion dynamics, and cultural transmission

### 4.1 Daley–Kendall rumor model

**Citation:** D. J. Daley and D. G. Kendall, “Stochastic Rumours,” 1965.[^32]

**Mechanism:** The Daley–Kendall model divides a population into ignorants, spreaders, and stiflers. Ignorants become spreaders when they hear a rumor; spreaders transmit during contacts; spreaders become stiflers when they meet another spreader or stifler and conclude the rumor is already known or no longer worth telling. It is the classic epidemic-style rumor model.

**Implementability in Python at game scale:** Adopt as a per-claim state machine, not as a global differential-equation simulation. For each NPC and active claim variant, store `unaware`, `active`, `stifled`, or `forgotten`, plus exposure count and timestamps. Update only during encounters. This is cheap at 1,000 NPCs and gives designers understandable transmission knobs.

### 4.2 Maki–Thompson directed-contact variant

**Citation:** D. P. Maki and M. Thompson, *Mathematical Models and Applications*, 1973; later directed-contact and random-awareness extensions.[^33]

**Mechanism:** Maki–Thompson modifies Daley–Kendall so that spreaders stop spreading when they contact someone who has already heard the rumor, emphasizing directed pairwise contacts and the social cost of redundant transmission. Later variants add awareness, heterogeneous contact structure, and repeated exposure.

**Implementability in Python at game scale:** Useful for tuning redundancy. During an encounter, if the listener already knows the claim, increment the teller's redundancy count and lower willingness to retell. This produces natural “everyone already knows that” behavior without global rumor bookkeeping.

### 4.3 Repeated-exposure and k-awareness variants

**Citation:** repeated-exposure and k-awareness rumor-model literature.[^34]

**Mechanism:** These models require several exposures before adoption or transmission, representing skepticism, salience thresholds, and social reinforcement. An NPC may hear a claim once and ignore it, then accept it after hearing it from multiple independent sources or from a highly trusted source.

**Implementability in Python at game scale:** Adopt directly. Store exposure count, distinct-source count, and highest-source trust. Acceptance can require either one strong source or several weak independent sources. This creates robust emergent behavior: rumors spread through taverns differently than through isolated households.

### 4.4 SIHR: susceptible–infected–hibernator–removed

**Citation:** Zhao et al., SIHR rumor-spreading model, 2012, and heterogeneous-network extensions.[^35]

**Mechanism:** SIHR adds a hibernator state between active spreading and final removal. A hibernator has stopped spreading for now but can be reactivated later. This captures forgetting followed by remembering, or a rumor becoming dormant until a new event makes it relevant again.

**Implementability in Python at game scale:** Strongly recommended. The extra state is cheap and narratively valuable. Move active rumor knowledge to hibernation after time without rehearsal; reactivate it when a related event, location, person, or accusation becomes salient. This supports old scandals resurfacing without keeping every rumor active forever.

### 4.5 SEIOR and refutation/incubation variants

**Citation:** SEIOR rumor-spreading model with exposed, hesitant, infected, and removed states.[^36]

**Mechanism:** SEIOR-style models separate exposure, hesitation/incubation, active spreading, and recovery/removal. Variants add refutation, counter-rumor exposure, forgetting, remembering, and resistance. These models better represent people who hear a rumor but wait, verify it, or spread a denial instead.

**Implementability in Python at game scale:** Adopt the state distinctions but simplify the math. Useful states are `unaware`, `heard`, `checking`, `believing`, `spreading`, `refuting`, `dormant`, and `forgotten`. Transitions can be rule-based and seeded rather than numerically integrated. At game scale, interpretability matters more than epidemiological fidelity.

### 4.6 Deffuant–Weisbuch bounded confidence

**Citation:** Deffuant, Neau, Amblard, and Weisbuch, “Mixing Beliefs among Interacting Agents,” 2000.[^37]

**Mechanism:** Agents hold continuous opinions. When two agents' opinions are within a confidence bound, each moves partially toward the other; otherwise they ignore or reject each other. The mechanism produces convergence, clustering, and polarization depending on the confidence threshold.

**Implementability in Python at game scale:** Use only for continuous attitudes—trust in a faction, perceived guilt, moral approval—not for event facts. Update opinions during encounters with `x += mu * (y - x)` when the opinion distance is below the NPC's tolerance. Store tolerance per NPC and topic. This is O(k) over actual encounters, not O(N²).

### 4.7 Hegselmann–Krause bounded confidence

**Citation:** Hegselmann and Krause, “Opinion Dynamics and Bounded Confidence Models,” 2002.[^38]

**Mechanism:** Each agent averages the opinions of all agents whose opinions fall within its confidence interval. Repeated local averaging produces opinion clusters. It is less conversational than Deffuant–Weisbuch but useful for factions, public sentiment, or institutional consensus.

**Implementability in Python at game scale:** Use in batch form for group sentiment, not every NPC-NPC pair. For a topic, group NPCs by faction or community and update active members against their local neighbors. At 1,000 NPCs, this can be a periodic vectorized pass over sparse adjacency lists.

### 4.8 Friedkin–Johnsen persistent private beliefs

**Citation:** Friedkin and Johnsen, social influence network theory.[^39]

**Mechanism:** Friedkin–Johnsen models social influence while preserving a person's initial private belief. An agent's expressed or updated opinion is a weighted combination of prior disposition and social pressure. The persistent private term prevents everyone from collapsing into the same consensus.

**Implementability in Python at game scale:** Adopt in simplified form. Store `private_bias` and `current_opinion`; update current opinion toward trusted neighbors while private_bias pulls it back. This is useful for stubborn NPCs and stable factional disagreement, and it is cheap to compute on encounter edges.

### 4.9 Axelrod cultural dissemination

**Citation:** Robert Axelrod, “The Dissemination of Culture,” 1997.[^40]

**Mechanism:** Agents have cultural feature vectors. Similar agents are more likely to interact, and interaction copies one feature from neighbor to neighbor. The model produces local convergence and persistent cultural boundaries because dissimilar agents stop interacting before they become similar.

**Implementability in Python at game scale:** Use at faction/community level rather than individual gossip level. A small vector of cultural traits—dialect, taboo, religion, fashion, guild practice—can drift through sparse social edges. Mutation can randomly alter a feature. Do not use it for concrete claims or grudges.

### 4.10 Mesoudi's cultural-evolution agent-based modeling framework

**Citation:** Alex Mesoudi, cultural-evolution agent-based modeling tutorial and associated models.[^41]

**Mechanism:** Mesoudi's framework operationalizes vertical, horizontal, and oblique transmission; unbiased and biased mutation; content bias; indirect bias; conformist bias; blending inheritance; migration; and social-network transmission. It gives implementable recipes for how cultural traits change as they are copied between individuals and generations.

**Implementability in Python at game scale:** Highly useful for long-running worlds. Use biased mutation for rumor content, conformist bias for faction norms, and blending inheritance for reputation or attitude drift. Keep trait vectors small and update on social encounters or scheduled background ticks.

### 4.11 Gossamer as the integration point

Gossamer belongs in both the UCSC and rumor-model sections because it is the best bridge between cognitive character knowledge and network-style propagation. Daley–Kendall gives a compact state machine for willingness to transmit; Gossamer supplies the semantic content, memory, mutation, and salience machinery. The practical synthesis is: use epidemic states to decide **whether** a rumor moves, and Gossamer/Talk-of-the-Town mechanisms to decide **what variant moves and how it changes**.[^7][^32]

---

## 5. Social norms, obligations, face, reciprocity, trust, and reputation

### 5.1 BOID architecture

**Citation:** Broersen, Dastani, Hulstijn, and van der Torre, “The BOID Architecture: Conflicts between Beliefs, Obligations, Intentions and Desires,” 2001.[^42]

**Mechanism:** BOID extends BDI by treating obligations as a separate mental/social component. Beliefs, obligations, intentions, and desires can conflict, and different agent types resolve those conflicts differently: realistic, selfish, simple-minded, and social agents prioritize the components in different ways. The central contribution is not just adding obligations, but making norm compliance a matter of conflict resolution.

**Implementability in Python at game scale:** Adopt obligations as typed symbolic records, not as a full BOID reasoner. A useful NPC policy can compare `desire_score`, `obligation_score`, `risk`, and `relationship_cost` for a small candidate action set. Reserve deeper deliberation for focal NPCs; background NPCs can follow cached routines and violation responses.

### 5.2 Normative multi-agent systems review

**Citation:** Savarimuthu and Cranefield, “Norm Creation, Spreading and Emergence: A Survey of Simulation Models of Norms in Multi-Agent Systems,” 2011.[^43]

**Mechanism:** The review covers architectures and simulation models for norm creation, recognition, adoption, compliance, enforcement, and spread. It places BOID, BIO, normative KGP agents, OP-RND, internalization models, and EMIL in a common landscape. Its main value is taxonomic: norms can be explicit or implicit, imposed or emergent, and enforced through sanctions, reputation, or internal motivation.

**Implementability in Python at game scale:** Use the taxonomy to limit scope. A game should choose a small set of explicit norms—repay debts, keep promises, do not steal, testify truthfully, defend kin—and represent them as data with applicability conditions and sanctions. Do not attempt open-ended norm emergence unless that is the game's central system.

### 5.3 EMIL-A and EMIL-S

**Citation:** EMIL project reports and papers on norm recognition, adoption, and simulation.[^44]

**Mechanism:** EMIL models the full social life cycle of norms: recognizing a norm, adopting it, forming normative beliefs, goals, and intentions, invoking norms in interaction, defending them, punishing violators, and spreading them. EMIL-A is the agent architecture; EMIL-S is the simulation environment. It is one of the most complete implemented treatments of norm dynamics.

**Implementability in Python at game scale:** Study but simplify aggressively. The useful runtime subset is: norm salience, violation detection, witness propagation, sanction selection, and norm invocation as a dialogue/accusation action. Full norm-recognition and norm-spreading cognition is likely too expensive and too hard to author for a 1,000-NPC game unless norm emergence is the core feature.

### 5.4 Norm-aware BDI and N-2APL

**Citation:** norm-aware BDI and N-2APL literature discussed in normative-agent surveys.[^43]

**Mechanism:** Norm-aware BDI systems add obligations, permissions, prohibitions, deadlines, and sanctions to practical reasoning. N-2APL-style systems let norms generate obligations and influence plans. The mechanism is precise: a norm can create a duty before a deadline, detect violation afterward, and trigger repair or punishment.

**Implementability in Python at game scale:** Adopt the data schema, not the theorem prover. An `Obligation` should include issuer, debtor, beneficiary, action, condition, deadline, witnesses, status, excuse, sanction, and evidence. A scheduler can check due obligations for active or quest-relevant NPCs; the full set can be batch-checked daily.

### 5.5 Nowak–Sigmund image scoring and indirect reciprocity

**Citation:** Martin A. Nowak and Karl Sigmund, “Evolution of Indirect Reciprocity by Image Scoring,” *Nature*, 1998.[^45]

**Mechanism:** Individuals observe others helping or refusing to help and assign image scores. Future agents condition cooperation on the recipient's score, allowing cooperation to spread through indirect reciprocity: “I help you because you helped others.” Later work distinguishes scoring rules and shows how reputation assessment norms affect stability.

**Implementability in Python at game scale:** Adopt in simplified observer-local form. Do not maintain one global image score; maintain per-observer or per-community reputation evidence. Helping, refusing, cheating, punishing, and fulfilling obligations should add signed evidence counts. Context matters: refusing to help an enemy should not necessarily lower someone's reputation among their allies.

### 5.6 Computational Brown–Levinson politeness

**Citation:** Miller, Wu, and Funk, computational models of Brown–Levinson politeness and face threat.[^46]

**Mechanism:** Brown–Levinson theory separates positive face (the desire to be approved of) from negative face (the desire not to be imposed upon). Face-threatening acts can be estimated from power, social distance, imposition, and character. The computational model compares expected face threat to observed redress, yielding an imbalance that can be interpreted as politeness or offense.

**Implementability in Python at game scale:** Adopt in simplified form for dialogue action evaluation. An accusation, request, refusal, or command can carry a face-threat score based on social distance, status difference, favor size, and public/private setting. Politeness modifiers reduce threat; humiliation increases it. Feed the result into grudge formation, obligation acceptance, and reputation change.

### 5.7 Subjective logic

**Citation:** Audun Jøsang, subjective logic and trust modeling literature.[^47]

**Mechanism:** Subjective logic represents an opinion as belief, disbelief, uncertainty, and a base rate. Trust can be discounted when passed through an intermediary, and multiple opinions can be fused. Projected probability turns an uncertain opinion into a practical decision value. This is directly suited to testimony: a character's confidence in a source changes how much of that source's claim should be accepted.

**Implementability in Python at game scale:** Strong candidate for adoption. Store `(b, d, u, a)` per NPC-claim or NPC-source-topic tuple. Discount testimony by source trust, fuse independent evidence, and use projected probability for decisions. It is more expressive than a scalar confidence score but still cheap enough for thousands of active beliefs.

### 5.8 Beta reputation system

**Citation:** Jøsang and Ismail, “The Beta Reputation System,” 2002.[^48]

**Mechanism:** The Beta system represents reputation from counts of positive and negative outcomes using a Beta distribution. Expected reputation is derived from the counts, and uncertainty decreases as evidence accumulates. It is simple, probabilistically meaningful, and naturally supports recency weighting by decaying old evidence.

**Implementability in Python at game scale:** Adopt directly for reputation evidence. Use observer-local, context-specific `(alpha, beta)` counts rather than a universal score. For example, an NPC may be trustworthy about debts but unreliable about combat rumors. Add forgetting by multiplying old counts by a decay factor or using sliding time windows.

### 5.9 ReGreT

**Citation:** Sabater and Sierra, ReGreT reputation model.[^49]

**Mechanism:** ReGreT combines direct reputation, witness reputation, neighborhood reputation, and system reputation. Direct experience is usually most reliable; witness reports depend on witness trust; neighborhood and system reputation provide generalized evidence when direct interaction is sparse. The model is sociologically richer than a single global score.

**Implementability in Python at game scale:** Use its layered evidence design. Keep separate tables for direct interactions, witnessed claims, community summaries, and institutional badges. At runtime, combine only the layers relevant to the observer and context. Do not eagerly propagate every direct event to every community.

### 5.10 FIRE

**Citation:** Huynh, Jennings, and Shadbolt, FIRE trust and reputation model.[^50]

**Mechanism:** FIRE combines interaction trust, role-based trust, witness reputation, and certified reputation. It also includes reliability and confidence measures based on evidence counts and rating deviation. The model is especially relevant where institutions can certify roles or credentials, and where witnesses provide evidence with varying reliability.

**Implementability in Python at game scale:** Adopt selectively. Certified reputation maps well to guild ranks, noble titles, licenses, and public offices. Witness reputation maps to rumor evidence. Interaction trust maps to direct relationship history. Keep these separate so a forged certificate, trusted friend, and personal experience remain distinguishable.

### 5.11 Recommended obligation and grudge records

The literature supports a practical split between **obligations**, **grudges**, and **reputation**:

```text
Obligation(
  id, issuer, debtor, beneficiary,
  action, condition, deadline,
  status, witnesses, sanctions, excuse,
  created_at, fulfilled_at, violated_at
)

Grudge(
  holder, target, source_event_id,
  severity, grievance_type,
  emotional_strength, evidentiary_strength,
  last_rehearsed, forgiveness_threshold
)

Reputation(
  observer, subject, context,
  beta_alpha, beta_beta,
  direct_count, witness_count, certified_count,
  uncertainty, last_updated
)
```

An obligation is a socially recognized constraint with a possible violation. A grudge is a holder-specific memory and emotional response to a harmful event. Reputation is an observer-local expectation built from evidence. Keeping them separate prevents a common design bug in which one relationship score silently drives contradictory behaviors.

---

## 6. Memory, forgetting, misremembering, and source confusion

### 6.1 ACT-R declarative memory

**Citation:** Anderson et al., ACT-R integrated theory and declarative-memory tutorials.[^51]

**Mechanism:** ACT-R computes declarative activation from base-level learning and spreading activation. Base-level learning depends on the times at which a memory has been used; repeated rehearsal strengthens it, while long gaps produce power-law forgetting. Retrieval probability and retrieval latency both depend on activation, making recall graded rather than binary.

**Implementability in Python at game scale:** Adopt a simplified activation score. For each belief or memory, combine recency, rehearsal count, emotional intensity, relationship relevance, and current context. Use the score to decide recall and to rank candidate gossip. Exact ACT-R timing equations are optional; the important properties are decay, rehearsal, context sensitivity, and probabilistic retrieval.

### 6.2 Source monitoring

**Citation:** Johnson, Hashtroudi, and Lindsay, “Source Monitoring,” *Psychological Bulletin*, 1993.[^52]

**Mechanism:** People infer where a memory came from using its perceptual detail, semantic content, cognitive operations, emotion, and contextual cues. Source errors occur when these cues are weak or when a person must guess. The model explains confusion between something seen, imagined, inferred, self-generated, or heard from another person.

**Implementability in Python at game scale:** Adopt as provenance metadata. Every evidence record should store evidence type, source, directness, time, place, and source confidence. During low-strength recall, allow source mutation: a first-hand observation can become “someone told me,” testimony can be attributed to a similar NPC, or an inference can become a remembered observation.

### 6.3 Fuzzy-trace theory

**Citation:** Reyna, Corbin, Weldon, and Brainerd, fuzzy-trace theory review, 2016.[^53]

**Mechanism:** Fuzzy-trace theory separates verbatim traces from gist traces. Verbatim traces preserve surface details and support recollection rejection; gist traces preserve meaning and can support plausible false memories and phantom recollection. The two traces can decay at different rates, so a person can remember the gist while corrupting the details.

**Implementability in Python at game scale:** This is the best psychological basis for rumor mutation. Store separate `verbatim_strength` and `gist_strength`. When verbatim is high, quote exact slots; when gist is high but verbatim is low, mutate details while preserving moral meaning. This directly supports omission, exaggeration, category substitution, and false specificity.

### 6.4 Recollection rejection

**Citation:** Brainerd, Reyna, and related work on recollection rejection.[^54]

**Mechanism:** A strong verbatim memory can reject a plausible but false gist statement. For example, an NPC who clearly remembers that the bridge was closed can reject the rumor that someone crossed it at noon, even if that rumor fits the gist of the suspect's movements.

**Implementability in Python at game scale:** Adopt as a contradiction test. Before fusing or accepting a rumor, compare it to high-verbatim beliefs held by the listener. A strong contradictory memory should lower acceptance, trigger skepticism, or generate a correction. This produces believable interrogations and rumor refutation.

### 6.5 Kope, Rose, and Katchabaw: autobiographical memory for believable agents

**Citation:** Kope, Rose, and Katchabaw, “Modeling Autobiographical Memory for Believable Agents,” AIIDE 2013.[^55]

**Mechanism:** This implemented model uses immediate, short-term, and long-term memory pools. Memory nodes are linked by keywords, emotional valence, weights, timestamps, spreading activation, decay, context, and recency. The Minecraft implementation used dozens of NPC villagers and demonstrated that cognitively inspired memory can be made cheap enough for an interactive system.

**Implementability in Python at game scale:** Strong implementation reference. Use bounded pools rather than unlimited history: immediate scene memory, a small short-term queue, and summarized long-term memories. Link memories by entities, locations, event types, and emotional tags. Move low-activation memories out of the active cache and retain only summaries or evidence rows on disk.

### 6.6 Affective episodic memory

**Citation:** affective episodic-memory model with affective strengthening and repetition.[^56]

**Mechanism:** Emotional intensity and repetition increase memory strength, while activation decays over time. Affect can therefore make betrayal, humiliation, rescue, and danger more durable than routine events. Repetition acts as rehearsal and can preserve both accurate and false memories.

**Implementability in Python at game scale:** Adopt the principle. Add `emotional_intensity` and `rehearsal_count` to memory records. A humiliating public accusation should decay more slowly than a neutral purchase, and repeated retelling should strengthen a rumor even when it mutates.

### 6.7 Episodic timing and episode blending

**Citation:** Brom and Burkert episodic-timing work referenced by agent-memory literature.[^57]

**Mechanism:** People place episodes within socially understood time patterns and may blend similar episodes as precise timing is forgotten. Two market fights can become one; an event can migrate from “last winter” to “a few months ago”; repeated routines can be remembered as a generic episode.

**Implementability in Python at game scale:** Useful as a mutation rule. When time strength decays, quantize exact timestamps into fuzzy buckets and allow same-location/same-participant episodes to merge. Preserve canonical truth in the event log; only the NPC's memory should blur.

### 6.8 Dwarf Fortress memory and personality change

**Citation:** Bay 12 Games development log on memory; Dwarf Fortress documentation on thoughts, preferences, and personality facets.[^58][^59]

**Mechanism:** Dwarf Fortress uses bounded short-term and long-term memory. Short-term memories can be transferred to a limited number of long-term slots, grouped by category, softened over time, and reflected upon. Repeated emotional experience can produce durable personality or value changes. This turns memory into long-run character development rather than a simple event list.

**Implementability in Python at game scale:** Adopt the bounded-memory pattern. Give each NPC a small active pool and a capped long-term pool per category. When a category overflows, summarize old events into traits, grudges, fears, or values. This is cheaper than retaining every memory and creates legible character arcs.

### 6.9 Generative Agents memory retrieval

Generative Agents is also a memory model: recency, importance, and relevance select memories; reflection converts clusters of important memories into higher-level beliefs.[^28] For this project, the same scoring idea can be implemented deterministically. Use timestamp recency, authored importance, emotional intensity, entity overlap, and current-location overlap. Reserve embeddings or LLM importance scoring for rare high-level summarization, if at all.

### 6.10 Recommended belief-memory record

```text
Claim(
  id, kind, slots,
  canonical_event_id, truth_status
)

BeliefInstance(
  holder_id, claim_id, variant_id,
  confidence, uncertainty,
  verbatim_strength, gist_strength,
  source_summary,
  first_learned, last_rehearsed
)

Evidence(
  id, belief_id,
  evidence_type, source_id, predecessor_id,
  location_id, timestamp, strength
)

RumorState(
  npc_id, claim_variant_id,
  stage, last_heard, last_told,
  exposure_count, distinct_source_count
)
```

Canonical claims never mutate. A mutation creates a new claim variant plus evidence pointing to its predecessor. This preserves auditability while letting NPCs genuinely disagree.

---

## 7. Shipped games, prototypes, and postmortems

### 7.1 City of Gangsters: technical architecture

**Citation:** Robert Zubek, Ian Horswill, Emily Robison, and Matthew Viglione, “Social Modeling via Logic Programming in City of Gangsters,” AIIDE 2021.[^2]

**Mechanism:** City of Gangsters models about 1,200 interactive NPCs using a sparse directed social graph. Relationship state is derived from history elements that record value changes, actors, targets, expiration, explanations, and context. Logic rules propagate social consequences across relationships. The model distinguishes temporary from permanent history, giving a practical version of episodic versus semantic social memory.

**Implementability in Python at game scale:** This is the closest scale precedent and should be treated as a primary engineering source. Store relationship history as rows, derive current valence on demand, and keep explanation strings or structured cause references. Do not create rows for every possible pair; create edges only after acquaintance, shared group membership, witnessed interaction, or institutional relevance.

### 7.2 City of Gangsters: design lessons

**Citation:** Emily Robison, Matthew Viglione, Robert Zubek, and Ian Horswill, “AI Design Lessons for Social Modeling at Scale,” AIIDE 2021.[^60]

**Mechanism:** The design paper reports four lessons: social behavior must be legible, actions should be reversible enough to avoid social death spirals, norms should be succinct and genre-appropriate, and individuals should sometimes be fungible so the player can accomplish equivalent social actions through different people. These are practical fixes for simulations that are internally consistent but frustrating to play.

**Implementability in Python at game scale:** Adopt all four. Every relationship score should expose contributing events. Grudges and violated obligations should have repair paths. Norms should be few and themed. Candidate-generation code should support “any friendly fence,” “any corrupt official,” or “any witness from the market,” not just one indispensable NPC.

### 7.3 RimWorld

**Citation:** official RimWorld description; RimWorld social-mechanics documentation; Tynan Sylvester's design talks and interviews.[^61][^62][^63]

**Mechanism:** RimWorld combines directed opinions, relationship facts, social thoughts, event memories, mood effects, and social consequences. One colonist can dislike another because of insults, rejected advances, shared history, or harmful events. Opinions affect lovers, marriage, cheating, fights, and social behavior. The system is not a rich belief-provenance model, but it is highly effective at turning social events into player-legible drama.

**Implementability in Python at game scale:** Adopt its layered simplicity. A directed opinion can be derived from recent social thoughts, durable relationship facts, traits, and shared events. Keep explanations attached to each modifier. Do not expect RimWorld's model to handle deception or rumor provenance without adding the Talk of the Town belief layer.

### 7.4 Dwarf Fortress

**Citation:** Bay 12 Games memory development log and Dwarf Fortress social documentation.[^58][^59]

**Mechanism:** Dwarf Fortress links events, thoughts, emotions, memories, personality facets, values, and long-term reflection. A traumatic event can become a memory, lose emotional intensity, be grouped with related memories, and eventually alter personality or values. Its key achievement is persistence with bounded storage: not every event remains equally detailed forever.

**Implementability in Python at game scale:** Adopt bounded memory and summarization. At 1,000 NPCs, this is more scalable than retaining every event verbatim. Let repeated similar experiences become a trait shift or durable grievance, then archive the detailed events. This produces character change without unbounded memory growth.

### 7.5 Crusader Kings III: schemes, secrets, hooks, favors, and stress

**Citation:** official CK3 developer diary on schemes, secrets, and hooks; official Steam news copy; developer-diary index and accessible mechanics summaries.[^64][^65][^66][^67]

**Mechanism:** CK3 operationalizes secrets as discoverable information, schemes as long-running hostile or personal projects, agents as participants who improve schemes, hooks as leverage derived from secrets or favors, and favors as obligations. Weak and strong hooks force or strongly pressure compliance. Stress and personality traits constrain how far characters can act against their nature.

**Implementability in Python at game scale:** Highly relevant to obligations and information warfare. Represent secrets as claim/evidence bundles with exposure risk; hooks as enforceable obligation records; schemes as multistep tasks with agent contributions; and favors as explicit debt records. CK3 is less useful for fine-grained rumor mutation but excellent for turning private information into social leverage.

### 7.6 “1000 NPCs at 60 FPS” lineage

**Citation:** Robert Zubek's publication list and related game-AI work on thousand-NPC social simulation.[^68]

**Mechanism:** This work addresses the practical question of running a large social cast at interactive rates. The recurring strategy is to avoid universal pairwise computation, use sparse relationship structures, cache derived values, update only touched edges, and move expensive reasoning to event handlers or background batches.

**Implementability in Python at game scale:** Use it as a performance mandate. Python can handle the proposed 1,000-NPC layer if the per-tick work is proportional to active encounters and recently changed edges, not total NPC pairs. Heavy queries should run at scene transitions, daily ticks, or quest-generation time.

### 7.7 Prom Week as a production warning

Prom Week is both a success and a warning.[^22] It proves that explicit social physics can drive player-facing drama, but it also demonstrates the authoring burden of producing enough social rules, reactions, and narrative variation. For a 1,000-NPC systemic game, the answer is not to author more unique interactions; it is to author a compact set of general social moves whose effects vary with beliefs, obligations, roles, and relationship histories.

### 7.8 Paradise as an LLM-integration warning

Paradise's clearest lesson is that symbolic social physics and LLM dialogue generation can undermine each other when both are allowed to define social reality.[^30] If the language model invents a betrayal that the social model never recorded, later simulation cannot reason over it consistently. If the social model overconstrains every utterance, the model becomes a brittle template engine. The robust design is asymmetric: symbolic state drives generation, while generated language cannot alter state except through explicit, validated action outcomes.

### 7.9 Generative Agents as a scaling warning

Generative Agents demonstrates impressive social believability, but its memory, reflection, and dialogue pipeline depends on repeated LLM calls.[^28] That is acceptable for a research prototype with a small cast and short simulated period; it is not a safe default for a persistent 1,000-NPC game. The lesson is to copy the retrieval policy, not the implementation cost.

### 7.10 Common failure pattern across shipped and prototype systems

Across these systems, failures are rarely caused by a missing mathematical model. They come from poor legibility, unbounded state, irreversible social collapse, too many authored rules, all-pairs recomputation, or unclear ownership of truth. The safest engineering pattern is a small symbolic core with strong explanations and optional narrative/LLM layers that cannot silently rewrite the core.

---

## 8. Recommended architecture for 1,000 NPCs in Python

### 8.1 Data ownership

Use five ownership layers:

1. **Canonical event log:** append-only records of what objectively happened.
2. **Claim and variant store:** typed claims and mutated variants derived from events.
3. **Subjective belief store:** per-NPC belief instances with evidence and memory strengths.
4. **Social state store:** sparse relationships, grudges, obligations, trust, and reputation.
5. **Narrative/query layer:** story sifters, quest hooks, explanation views, and UI.

Only the first layer is objective. Everything else is observer-relative. An NPC's memory may become wrong, but the game must retain enough canonical history to debug why it became wrong.

### 8.2 Update model

Use encounter- and event-driven updates:

- **On world event:** create canonical event and candidate claims.
- **On witness:** create subjective belief with direct evidence.
- **On reflection:** compute salience, emotional effect, gist summary, and willingness to share.
- **On encounter:** select rumors based on activation, relationship, topic relevance, privacy, and motive.
- **On transmission:** create listener belief, mutate low-verbatim claims, append evidence chain, and update rumor state.
- **On contradiction:** compare against strong verbatim beliefs; trigger rejection, correction, or uncertainty.
- **On decay batch:** lower verbatim/gist strength, hibernate old rumors, summarize old memories, and age temporary relationship modifiers.
- **On obligation check:** detect due, fulfilled, excused, or violated obligations for active or scheduled NPCs.
- **On reputation update:** add observer-local evidence; do not broadcast a universal score.

### 8.3 Mutation policy

Mutation should be deterministic under a seed and driven by memory state:

| Condition | Allowed mutation |
|---|---|
| High verbatim strength | Exact slots, quote-like retelling, contradiction rejection |
| Medium verbatim strength | Minor omissions, uncertainty markers, time fuzzing |
| High gist, low verbatim | Category substitution, exaggeration, actor transfer, inferred motive |
| Weak source memory | Source confusion, “I heard,” wrong intermediary |
| Repeated rehearsal | Stronger confidence even when details drift |
| Emotional intensity | Better gist retention, stronger blame, more durable grudge |
| Contradictory direct evidence | Rejection, correction, or reduced confidence |

Never mutate canonical truth. Create a new variant and link it to its predecessor.

### 8.4 Rumor state machine

Use a compact per-NPC/per-variant state machine:

```text
unaware -> heard -> checking -> believing -> spreading
                         \-> refuting
heard -> dormant
believing/spreading/refuting -> dormant -> reactivated
any state -> forgotten
```

Transition rules can incorporate Daley–Kendall redundancy, Maki–Thompson repeated-contact effects, SIHR hibernation, and SEIOR hesitation/refutation. This keeps network-science insights while retaining narrative semantics.

### 8.5 Trust and reputation scoring

A practical formula is:

```text
source_trust(observer, source, topic)
claim_opinion = discount(source_trust, testimony_opinion)
fused_belief = fuse(existing_belief, new_discounted_evidence)
reputation(observer, subject, context) = Beta(alpha, beta) with recency decay
```

Use subjective logic when uncertainty matters; use Beta counts when designers want simple evidence accumulation. Keep both observer-local and context-specific. A character can be a reliable witness about tavern gossip, unreliable about finance, and certified as a guild official simultaneously.

### 8.6 Obligations and hooks

An obligation becomes active when its condition is satisfied. A deadline creates a scheduled check. Fulfillment, violation, excuse, forgiveness, and sanction are explicit transitions. Hooks can be represented as high-priority obligations backed by secret evidence:

- **Favor hook:** beneficiary can invoke a recorded favor.
- **Secret hook:** holder can threaten exposure of a secret claim.
- **Debt hook:** creditor can demand repayment or service.
- **Duty hook:** institution can invoke role authority.

The social layer should know who can invoke which hook, whether the target acknowledges it, and what witnesses would think of refusal.

### 8.7 Storage and performance budget

A practical Python architecture can use:

- SQLite or DuckDB for durable canonical events, evidence, obligations, and cold beliefs.
- In-memory dictionaries keyed by NPC for active relationships and recent memories.
- Sparse adjacency lists for social edges.
- NumPy or batch SQL for decay and reputation updates.
- Deterministic RNG streams per NPC or event family.
- Materialized views for common queries such as “active grudges,” “known secrets,” and “obligations due.”

A reasonable budget is:

| Workload | Budget strategy |
|---|---|
| Active scene with 10–30 NPCs | Full belief, gossip, obligation, and face evaluation |
| Nearby NPCs | Relationship and rumor eligibility only |
| Offscreen NPCs | Daily or scheduled batch updates |
| Global reputation | No global computation; update affected observer-local rows |
| Story sifting | Event-triggered and incremental over a small authored pattern set |

### 8.8 Inspectability requirements

Every generated social outcome should support a drill-down explanation:

```text
Mara refused Petyr because:
- Petyr owes Mara a favor from 12 April.
- Mara believes Petyr spread the warehouse rumor.
- The belief came from Leni, whose reliability Mara rates low.
- Two independent witnesses strengthened the gist but not the details.
- Refusing publicly would impose high face threat on Petyr.
- Mara has a grudge with emotional strength 0.71 and evidentiary strength 0.44.
```

This explanation requirement should shape the schema from the beginning. If the simulator cannot answer why, it will be difficult to debug or author.

---

## 9. Prioritized reading and build order

### Build first

1. **Canonical events, claims, variants, belief instances, and evidence chains** — Ryan et al. 2015 and Ryan/Mateas 2017.[^4][^5]
2. **Gossip phases** — Gossamer's witness/reflection/propagation/decay loop.[^7]
3. **Sparse relationship histories** — City of Gangsters.[^2]
4. **Bounded memory and mutation** — fuzzy-trace theory, source monitoring, and simplified ACT-R.[^51][^52][^53]
5. **Obligations and grudges as typed records** — BOID, norm-aware systems, CK3 hooks, and City of Gangsters history.[^42][^60][^64]
6. **Observer-local reputation** — Beta reputation, subjective logic, ReGreT, and FIRE.[^47][^48][^49][^50]

### Add next

1. DK/MT/SIHR rumor-state transitions.
2. Deffuant–Weisbuch and Friedkin–Johnsen updates for continuous attitudes.
3. Face-threat scoring for accusations, requests, refusals, and public humiliation.
4. Batch story sifters over SQL or Drolta-like queries.
5. Dwarf Fortress-style long-term memory summarization.

### Defer

1. Full norm emergence.
2. General-purpose logic programming.
3. Autoencoder anomaly detection.
4. Prospective drama management.
5. LLM reflection or dialogue integration.

LLM integration should come last and should only render or summarize grounded symbolic state.

---

## 10. Source classification table

| Source | Mechanism | Classification | Game-scale assessment |
|---|---|---|---|
| Ryan et al. 2015 | Subjective beliefs, provenance, misremembering, lying | **Adopt directly** | Excellent; cheap symbolic records and seeded mutations |
| Ryan & Mateas 2017 | Talk of the Town belief facets and evidence chains | **Adopt directly** | Primary implementation model |
| Ryan 2018 dissertation | Curationist emergent narrative | **Adopt directly** | Separate simulation from story selection |
| Gossamer 2023 | Witness/reflection/propagation/decay | **Adopt directly** | Best gossip architecture for this project |
| City of Gangsters | Sparse relationships, history, explanations | **Adopt directly** | Closest shipped scale precedent |
| RimWorld | Directed opinions and social thoughts | **Adopt in simplified form** | Legible and cheap; lacks provenance |
| Dwarf Fortress | Bounded memories and personality change | **Adopt directly** | Excellent long-term persistence model |
| CK3 | Secrets, hooks, schemes, favors | **Adopt in simplified form** | Strong obligation/leverage model |
| DK/MT/SIHR/SEIOR | Rumor states and transitions | **Adopt in simplified form** | Use encounter-driven state machine, not global ODE |
| Deffuant–Weisbuch / HK | Bounded-confidence opinion updates | **Adopt in simplified form** | Continuous attitudes only |
| Friedkin–Johnsen | Persistent private beliefs | **Adopt in simplified form** | Good for stubbornness and stable factions |
| Axelrod / Mesoudi | Cultural transmission and mutation | **Study / simplify** | Best for faction culture, not event facts |
| Subjective logic | Trust, uncertainty, discounting, fusion | **Adopt directly** | Cheap and expressive enough |
| Beta reputation | Evidence-count reputation | **Adopt directly** | Very cheap; make it observer-local |
| ReGreT / FIRE | Layered reputation evidence | **Adopt in simplified form** | Separate direct, witness, role, certified evidence |
| BOID | Obligations in conflict resolution | **Simplify heavily** | Keep obligation records and policies, not full BDI |
| EMIL | Norm recognition and enforcement | **Study** | Too much for whole-cast runtime |
| Computational politeness | Face threat and redress | **Adopt in simplified form** | Useful for dialogue and offense |
| ACT-R | Activation, rehearsal, decay | **Simplify** | Use scoring properties, not full cognitive architecture |
| Source monitoring | Provenance confusion | **Adopt directly** | Directly supports misremembering |
| Fuzzy-trace theory | Verbatim/gist separation | **Adopt directly** | Best mutation model for rumors |
| Kope et al. 2013 | Agent autobiographical memory | **Adopt in simplified form** | Practical bounded-memory reference |
| Comme il Faut / Prom Week | Authored social physics | **Study** | Strong interaction model; high authoring burden |
| Ensemble | Reusable social physics | **Study** | Extract architecture, avoid broad rule search |
| Versu / Praxish | Practices, roles, exclusion logic | **Study** | Excellent for scene-level roles |
| Lyra | Private/public opinion separation | **Adopt in simplified form** | Useful for attitudes, not event claims |
| Felt / Winnow / Drolta | Story sifting | **Study / simplify** | Use batch or small incremental pattern sets |
| Generative Agents | Memory retrieval, reflection, planning | **Study** | Copy retrieval formula, not LLM dependence |
| Paradise | Symbolic/LLM integration postmortem | **Study as warning** | Keep LLM out of canonical state |
| Socialog | Social-physics scaling | **Study as warning** | Avoid all-pairs recomputation |

---

## 11. Final design verdict

The literature points to a hybrid system rather than a single imported architecture. Use **Talk of the Town** for truth/belief/provenance, **Gossamer** for gossip life cycle, **City of Gangsters** for sparse social state and explanations, **Dwarf Fortress** for bounded long-term memory, **CK3** for secrets/hooks/obligations, **Beta/subjective-logic reputation** for trust, and **fuzzy-trace/source-monitoring models** for misremembering. Use epidemic rumor models as scheduling and transition rules, and bounded-confidence models only where the state is genuinely continuous.

The decisive implementation constraint is not Python itself; it is algorithmic shape. A Python social layer can support 1,000 named NPCs if it is sparse, event-driven, lazily evaluated, and aggressively bounded. It will fail if it stores complete pairwise state, recomputes social physics globally each tick, retains all memories forever, or lets generated prose overwrite canonical facts.

---

## References

[^1]: Samuel Hill and Ian Horswill, “An Executable Ontology for Social Simulation,” including the Socialog performance discussion for 50 and 450 characters. https://ceur-ws.org/Vol-3626/paper9.pdf

[^2]: Robert Zubek, Ian Horswill, Emily Robison, and Matthew Viglione, “Social Modeling via Logic Programming in City of Gangsters,” AIIDE 2021. https://doi.org/10.1609/aiide.v17i1.18912 ; PDF: http://robert.zubek.net/publications/social-modeling-via-logic-programming-in-city-of-gangsters.pdf

[^3]: James Ryan, *Curating Simulated Storyworlds*, PhD dissertation, University of California, Santa Cruz, 2018. https://escholarship.org/uc/item/1340j5h2

[^4]: James Ryan, Adam Summerville, Michael Mateas, and Noah Wardrip-Fruin, “Toward Characters Who Observe, Tell, Misremember, and Lie,” *Proceedings of AIIDE*, 2015. https://ojs.aaai.org/index.php/AIIDE/article/view/12825

[^5]: James Ryan and Michael Mateas, “Simulating Character Knowledge Phenomena in Talk of the Town,” *Game AI Pro 3*, chapter 37, CRC Press, 2017. Chapter listing: http://www.gameaipro.com/ ; publisher page: https://www.taylorfrancis.com/chapters/edit/10.4324/9781315151700-37/simulating-character-knowledge-phenomena-talk-town-james-ryan-michael-mateas

[^6]: James Owen Ryan, Michael Mateas, and Noah Wardrip-Fruin, “Open Design Challenges for Interactive Emergent Narrative,” ICIDS 2015, pp. 14–26. https://doi.org/10.1007/978-3-319-27036-4_2

[^7]: Max Kreminski, “Toward Better Gossip Simulation in Emergent Narrative Systems,” IEEE Conference on Games, 2023. https://mkremins.github.io/publications/Gossamer_CoG2023.pdf

[^8]: Shi Johnson-Bey, Mark J. Nelson, and Michael Mateas, “Exploring the Design Space of Social Physics Engines in Games,” ICIDS 2022. https://escholarship.org/uc/item/5811p2s0

[^9]: Shi Johnson-Bey, *Designing Reusable Tools for Social Simulation-Driven Emergent Storytelling*, PhD dissertation, University of California, Santa Cruz, 2025. https://escholarship.org/uc/item/4mr6c29j

[^10]: Shi Johnson-Bey, Mark J. Nelson, and Michael Mateas, “Neighborly: A Sandbox for Simulation-Based Emergent Narrative,” IEEE Conference on Games, 2022. https://doi.org/10.1109/CoG51982.2022.9893631

[^11]: Max Kreminski, Melanie Dickinson, and Noah Wardrip-Fruin, “Felt: A Simple Story Sifter,” ICIDS 2019. https://mkremins.github.io/publications/Felt_SimpleStorySifter.pdf

[^12]: Max Kreminski, Melanie Dickinson, and Michael Mateas, “Winnow: A Domain-Specific Language for Incremental Story Sifting,” AIIDE 2021. https://doi.org/10.1609/aiide.v17i1.18903

[^13]: Shi Johnson-Bey and Michael Mateas, “Centrifuge: A Visual Tool for Authoring Sifting Patterns for Simulated Storyworlds.” https://eis.ucsc.edu/papers/Johnson-Bey_Centrifuge_PLIE2021.pdf ; repository: https://github.com/ShiJbey/centrifuge

[^14]: Shi Johnson-Bey, Drolta and Minerva discussion in *Designing Reusable Tools for Social Simulation-Driven Emergent Storytelling*. https://escholarship.org/content/qt4mr6c29j/qt4mr6c29j.pdf ; project page: http://shijbey.github.io/projects.html

[^15]: “Emergent Narratives with Composable Story Sifting Patterns,” ACM, 2025. https://doi.org/10.1145/3723498.3723809

[^16]: Ben Clothier and David E. Millard, “Prospective Story Sifting Intervention for Emergent Narrative” / Awash paper. https://eprints.soton.ac.uk/482864/1/Awash.pdf

[^17]: Ian Horswill and Samuel Hill, “Fast, Declarative, Character Simulation Using Bottom-Up Logic Programming,” AIIDE 2024. https://ojs.aaai.org/index.php/AIIDE/article/view/31866

[^18]: Samuel Hill and Ian Horswill, “An Executable Ontology for Social Simulation,” Socialog/Voix de la Ville performance section. https://ceur-ws.org/Vol-3626/paper9.pdf

[^19]: Adam Summerville and Ben Samuel, “Kismet: A Small Social Simulation Language,” 2020. https://ceur-ws.org/Vol-2827/CAC-Paper_7.pdf ; mirror: https://mkremins.github.io/casual-creators-workshop/papers/ICCC20_paper_190.pdf

[^20]: Sasha Azad, Jennifer Wellnitz, Luis Garcia, and Chris Martens, “Anthology: A Social Simulation Framework,” AIIDE 2022. https://doi.org/10.1609/aiide.v18i1.21967

[^21]: Josh McCoy, Mike Treanor, Ben Samuel, Noah Wardrip-Fruin, and Michael Mateas, “Comme il Faut: A System for Authoring Playable Social Models,” AIIDE 2011. https://doi.org/10.1609/aiide.v7i1.12454

[^22]: Josh McCoy, Mike Treanor, Ben Samuel, Michael Mateas, and Noah Wardrip-Fruin, “Prom Week: Social Physics as Gameplay,” FDG 2011. https://doi.org/10.1145/2159365.2159425 ; Josh McCoy, Mike Treanor, Ben Samuel, Aaron A. Reed, Noah Wardrip-Fruin, and Michael Mateas, “Prom Week,” FDG 2012. https://doi.org/10.1145/2282338.2282384 ; official publication list: https://promweek.soe.ucsc.edu/about/academic-publications/

[^23]: Ben Samuel et al., “The Ensemble Engine: Next-Generation Social Physics,” FDG 2015. http://www.fdg2015.org/papers/fdg2015_paper_07.pdf

[^24]: Emily Short and collaborators, “How Versu Works.” https://versu.com/about/how-versu-works/

[^25]: Max Kreminski, Praxish repository and AIIDE paper. https://github.com/mkremins/praxish ; https://doi.org/10.1609/aiide.v19i1.27537

[^26]: Shi Johnson-Bey, RePraxis repository. https://github.com/ShiJbey/RePraxis

[^27]: Sasha Azad and Chris Martens, “Lyra: Simulating Believable Opinionated Virtual Characters,” AIIDE 2019. https://ojs.aaai.org/index.php/AIIDE/article/view/5232 ; PDF: https://ojs.aaai.org/index.php/AIIDE/article/download/5232/5088/8330

[^28]: Joon Sung Park et al., “Generative Agents: Interactive Simulacra of Human Behavior,” UIST 2023. https://doi.org/10.1145/3586183.3606763 ; arXiv HTML: https://ar5iv.labs.arxiv.org/html/2304.03442

[^29]: Mike Treanor, Ben Samuel, and Mark J. Nelson, “Slice of Life: A Social Physics Game with Interactive Conversations using Symbolically Grounded LLM-Based Generative Dialogue,” FDG 2025. https://doi.org/10.1145/3723498.3723806 ; PDF: https://mtreanor.com/publications/fdg2025-sliceOfLife.pdf

[^30]: Jack Kelly, Michael Mateas, and Noah Wardrip-Fruin, “Paradise: An Experiment Extending the Ensemble Social Physics Engine with Language Models,” FDG 2024. https://doi.org/10.1145/3649921.3659841

[^31]: Ben Samuel, James Ryan, Adam Summerville, Michael Mateas, and Noah Wardrip-Fruin, “Bad News: An Experiment in Computationally Assisted Performance,” ICIDS 2016. https://doi.org/10.1007/978-3-319-48279-8_10

[^32]: D. J. Daley and D. G. Kendall, “Stochastic Rumours,” *IMA Journal of Applied Mathematics* 1(1), 42–55, 1965. https://doi.org/10.1093/imamat/1.1.42

[^33]: D. P. Maki and M. Thompson, *Mathematical Models and Applications*, Prentice-Hall, 1973; for a modern restatement and random-awareness extension, see “The Maki–Thompson Model with Random Awareness.” https://arxiv.org/html/2508.07099v1

[^34]: Alejandra Rada, Cristian F. Coletti, Elcio Lebensztayn, and Pablo M. Rodríguez, “The Role of Multiple Repetitions on the Size of a Rumor,” 2021. https://arxiv.org/html/2006.07992v2

[^35]: Laijun Zhao et al., “SIHR Rumor Spreading Model in Social Networks,” *Physica A* 391, 2444–2453, 2012. https://doi.org/10.1016/j.physa.2011.12.008 ; heterogeneous-network extension: https://onlinelibrary.wiley.com/doi/10.1155/2019/4268393

[^36]: Jianhong Chen, Hongcai Ma, and Shan Yang, “SEIOR Rumor Propagation Model Considering Hesitating Mechanism and Different Rumor-Refuting Ways in Complex Networks,” *Mathematics* 11(2), 283, 2023. https://doi.org/10.3390/math11020283

[^37]: Guillaume Deffuant, David Neau, Frédéric Amblard, and Gérard Weisbuch, “Mixing Beliefs among Interacting Agents,” *Advances in Complex Systems* 3, 87–98, 2000. https://doi.org/10.1142/S0219525900000078

[^38]: Rainer Hegselmann and Ulrich Krause, “Opinion Dynamics and Bounded Confidence: Models, Analysis and Simulation,” *Journal of Artificial Societies and Social Simulation* 5(3), 2002. https://www.jasss.org/5/3/2.html

[^39]: Noah E. Friedkin and Eugene C. Johnsen, “Social Influence and Opinions,” *Journal of Mathematical Sociology* 15, 193–205, 1990. https://doi.org/10.1080/0022250X.1990.9990069

[^40]: Robert Axelrod, “The Dissemination of Culture: A Model with Local Convergence and Global Polarization,” *Journal of Conflict Resolution* 41(2), 203–226, 1997. https://doi.org/10.1177/0022002797041002001

[^41]: Alex Mesoudi, cultural-evolution agent-based modeling tutorial and repository. https://doi.org/10.5281/zenodo.5155821 ; https://github.com/amesoudi/cultural_evolution_ABM_tutorial

[^42]: Jan Broersen, Mehdi Dastani, Joris Hulstijn, Zisheng Huang, and Leendert van der Torre, “The BOID Architecture: Conflicts between Beliefs, Obligations, Intentions and Desires,” *Proceedings of the Fifth International Conference on Autonomous Agents*, 2001. https://doi.org/10.1145/375735.375766

[^43]: Bastin Tony Roy Savarimuthu and Stephen Cranefield, “Norm Creation, Spreading and Emergence: A Survey of Simulation Models of Norms in Multi-Agent Systems,” *Multiagent and Grid Systems* 7(1), 21–54, 2011. https://doi.org/10.3233/MGS-2011-0167

[^44]: EMIL project, especially *EMIL-T Deliverable 5.1*, chapter 9, “Making the Theory Explicit: The EMIL-A Architecture,” and “Enhancing Agents with Normative Capabilities.” http://cfpm.org/EMIL-D5.1.pdf ; https://www.scs-europe.net/conf/ecms2010/2010%20accepted%20papers/abs_ECMS2010_0055.pdf

[^45]: Martin A. Nowak and Karl Sigmund, “Evolution of Indirect Reciprocity by Image Scoring,” *Nature* 393, 573–577, 1998. https://doi.org/10.1038/31225 ; PubMed: https://pubmed.ncbi.nlm.nih.gov/9634232/

[^46]: Christopher A. Miller, Peggy Wu, and Harry Funk, computational Brown–Levinson politeness model. https://cdn.aaai.org/ICCCD/2007/ICCCD07-010.pdf ; related IEEE Intelligent Systems manuscript: https://www.sift.net/sites/default/files/publications/MWF-IEEEIS-vsubmit2.pdf

[^47]: Audun Jøsang, subjective logic; for a recent social-network treatment, see “A Subjective Logic Based Approach to Modeling Trust and Reputation in Social Networks.” https://arxiv.org/html/2404.14789v1

[^48]: Audun Jøsang and Roslan Ismail, “The Beta Reputation System,” BLED 2002. https://aisel.aisnet.org/cgi/viewcontent.cgi?article=1086&context=bled2002

[^49]: Jordi Sabater and Carles Sierra, “Social ReGreT, a Reputation Model Based on Social Relations.” https://www.iiia.csic.es/~jsabater/Publications/2002-CCIA.pdf

[^50]: Trung Dong Huynh, Nicholas R. Jennings, and Nigel R. Shadbolt, “FIRE: An Integrated Trust and Reputation Model for Open Multi-Agent Systems.” https://eprints.soton.ac.uk/259557/1/aamas-trust04.pdf

[^51]: John R. Anderson et al., “An Integrated Theory of the Mind,” including ACT-R declarative-memory activation. http://act-r.psy.cmu.edu/wordpress/wp-content/themes/ACT-R/workshops/2004/IntegratedTheory.pdf ; ACT-R subsymbolic tutorial: https://people.ucsc.edu/~abrsvn/ACT-R_subsymbolic_3.pdf

[^52]: Marcia K. Johnson, Shahin Hashtroudi, and D. Stephen Lindsay, “Source Monitoring,” *Psychological Bulletin* 114(1), 3–28, 1993. https://doi.org/10.1037/0033-2909.114.1.3 ; PubMed: https://pubmed.ncbi.nlm.nih.gov/8346328/

[^53]: Valerie F. Reyna, Jonathan C. Corbin, Rebecca B. Weldon, and Charles J. Brainerd, “How Fuzzy-Trace Theory Predicts True and False Memories for Words, Sentences, and Narratives,” 2016. https://doi.org/10.1016/j.jarmac.2015.12.003 ; open access: https://pmc.ncbi.nlm.nih.gov/articles/PMC4815269/

[^54]: Charles J. Brainerd, Valerie F. Reyna, and related work on recollection rejection. https://link.springer.com/content/pdf/10.3758/bf03193375.pdf

[^55]: David Kope, Penn Rose, and Michael Katchabaw, “Modeling Autobiographical Memory for Believable Agents,” AIIDE 2013. https://doi.org/10.1609/aiide.v9i1.12686 ; PDF: https://ojs.aaai.org/index.php/AIIDE/article/download/12686/12534

[^56]: “An Affective Episodic Memory Model for Virtual Agents,” including affective strengthening, repetition, activation, and decay. https://pmc.ncbi.nlm.nih.gov/articles/PMC8550857/

[^57]: Episodic-timing and episode-blending work discussed in the agent-memory literature, especially Kope, Rose, and Katchabaw's review of autobiographical-memory models. https://ojs.aaai.org/index.php/AIIDE/article/download/12686/12534

[^58]: Bay 12 Games, *Dwarf Fortress* 2018 development log, memory-system entries. http://www.bay12games.com/dwarves/dev_2018.html

[^59]: Dwarf Fortress documentation on thoughts, preferences, and personality facets. https://dwarffortresswiki.org/index.php/Thoughts_and_preferences ; http://www.dwarffortresswiki.org/index.php/Personality_facet

[^60]: Emily Robison, Matthew Viglione, Robert Zubek, and Ian Horswill, “AI Design Lessons for Social Modeling at Scale,” AIIDE 2021. https://ojs.aaai.org/index.php/AIIDE/article/view/18911

[^61]: Ludeon Studios, official *RimWorld* description. https://rimworldgame.com/

[^62]: *RimWorld* social-mechanics documentation. https://rimworldwiki.com/wiki/Social

[^63]: Tynan Sylvester, *RimWorld* design talk and postmortem coverage. https://www.gamedeveloper.com/design/video-how-i-rimworld-i-found-success-through-ridiculous-contrarian-design

[^64]: Paradox Interactive, “CK3 Dev Diary #5: Schemes, Secrets, and Hooks.” https://forum.paradoxplaza.com/forum/threads/ck3-dev-diary-5-schemes-secrets-and-hooks.1289167/

[^65]: Paradox Interactive, official *Crusader Kings III* Steam news mirror for schemes, secrets, and hooks. https://store.steampowered.com/news/app/1158310/view/1716364455374240580

[^66]: *Crusader Kings III* developer-diary index. https://ck3.paradoxwikis.com/Developer_diaries

[^67]: Accessible secondary mechanics summaries for CK3 schemes, secrets, and hooks. https://www.gamereactor.eu/crusader-kings-iii-is-introducing-schemes-secrets-and-hooks/ ; https://www.gamewatcher.com/crusader-kings-3-schemes-secrets-hooks-intrigue

[^68]: Robert Zubek publication list, including “1000 NPCs at 60 FPS” and City of Gangsters social-modeling work. https://robert.zubek.net/publications/index.html
