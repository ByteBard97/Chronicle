---
date: 2026-08-20
sources: [compass_artifact_wf-a36b4778-4794-5cb9-bff1-d08533c3a4eb_text_markdown.md]
topic: "Social simulation literature for game-scale belief systems"
status: filed
---

# Social Simulation Literature for Game-Scale Belief Systems

## Findings

- [BUILD-ON] Ryan et al.'s Talk of the Town facet model (Value, nested mental model, Predecessor, Evidence list, Strength, Accuracy flag) is a near-direct template for Chronicle's Belief/Facet dataclass — it is already Python and matches the "beliefs with provenance and strength" requirement exactly.
- [BUILD-ON] Rumor propagation should be split into two cheap, independent per-tick passes: Daley–Kendall SIR-style spreading (who currently knows/repeats a rumor, O(active edges)) and a Bartlett/Griffiths serial-reproduction mutation graph (how content drifts on each retelling, O(features) per hop). This directly maps to Chronicle's "rumor propagation with mutation" requirement.
- [BUILD-ON] ACT-R base-level activation (`B_i = ln(Σ t_k^{-d})`, approximated as running activation + last-access timestamp) is a closed-form, O(1)-per-memory decay/misremembering formula suitable for 1000 NPCs; pair with the Generative Agents recency×importance×relevance retrieval score (drop the LLM-based importance/relevance, use heuristics/tag overlap instead).
- [DESIGN-INPUT] Opinion/reputation drift (as opposed to factual belief content) should be modeled separately via bounded-confidence dynamics (Deffuant–Weisbuch pairwise or Hegselmann–Krause synchronous) — a few floats per interacting pair, cheap enough for scale, and it produces polarization/consensus/fragmentation clustering that a single "belief strength" scalar cannot.
- [DESIGN-INPUT] Obligations/grudges should be implemented as explicit records (deadline + sanction, NorMAS-style) or decaying scalar modifiers (RimWorld thought/moodlet pattern) rather than full deontic logic — the theorem-prover-grade norm systems (Versu exclusion logic, Comme il Faut) are tractable but not "drop-in": they trade expressiveness for authoring burden.
- [RISK] The single most load-bearing shipped-game finding: City of Gangsters (~1200 NPCs, matching Chronicle's scale) converged on "more than twenty rules is too many" — legibility, reversibility, and a small hand-authored rule set matter more than model sophistication at this scale.
- [RISK] Performance ceilings (5000 NPCs at 60fps, 2000 NPCs at 7.55ms/tick) are proven only in C# (TED/Simulog), not Python; the original Python Talk of the Town (~400 NPCs) "required many minutes to simulate a city." Chronicle's Python implementation should expect to vectorize (NumPy) the propagation/opinion hot paths and profile early rather than assume Python parity.
- [RISK] CK3's patch history (AI interaction spam throttled from ~300 to ~30 interactions per character per century) is a direct warning about needing a per-tick interaction budget/cap at NPC scale, independent of model correctness.
- [DEFER] Story sifting (Felt/Drolta Datalog-over-EAV pattern, Kreminski et al.) — valuable for surfacing interesting rumors/grudges to the player once the simulation is producing more content than a player can attend to, but not required for a v1 belief/rumor/obligation engine.
- [DEFER] OCC/EMA appraisal architectures (FAtiMA) as a principled generator of grudges/gratitude from goal-appraisal — a richer alternative to hand-authored grudge triggers, worth revisiting post-v1.

## Details

### Belief-with-provenance model

**James Ryan, Adam Summerville, Michael Mateas, Noah Wardrip-Fruin — "Toward Characters Who Observe, Tell, Misremember, and Lie" (EXAG @ AIIDE 2015 / AIIDE vol. 11, pp. 56–62).** Each character holds an ontology of mental models (one per person/place), each built from belief facets — one per attribute (name, hair color, occupation, whereabouts, etc.). Each facet carries a Value, a link to a nested mental model, a Predecessor (the prior belief, giving history), an Evidence list, a Strength (sum of supporting evidence strengths), and an Accuracy flag. A nine-type evidence typology spans origination (reflection, observation, transference, confabulation, lie), propagation (statement, eavesdropping), deterioration (mutation), and termination (forgetting); mutation probability depends on a character's memory attribute, facet type, and belief strength, via a hand-authored belief mutation graph. Belief revision is strength-based: a contradicting belief is adopted only once accumulated evidence strength exceeds the incumbent. Implementability: excellent — already Python, and the data structures map one-to-one onto Chronicle's stated requirement (beliefs with provenance and strength).

**Shi Johnson-Bey, Mark J. Nelson, Michael Mateas — "Neighborly: A Sandbox for Simulation-Based Emergent Narrative" (IEEE CoG 2022, pp. 425–432).** An open-source (MIT, Python 3.8–3.12) rational reconstruction of Talk of the Town. Entities built from YAML archetypes; a priority queue of Systems updates each timestep; a global directed relationship network models friendship/romance as scalar affinities (-50 to 50, adapted from TotT's "charge"/"spark") carrying searchable modifier tags (Friend, Enemy, Coworker, Love Interest); life events are production rules with preconditions/post-effects. Implementability: high — this is a literal Python library built for community-scale social sim, and its ECS + rules-engine + relationship-network architecture is the closest existing scaffold to Chronicle's problem. Sibling projects by the same author (Minerva, Drolta, TDRS, Anansi) extend the same ideas but are less directly reusable (SQLite/Unity/C#).

**Ryan's dissertation, "Curating Simulated Storyworlds" (UC Santa Cruz, 2018).** Frames the curationist/story-sifting problem: a simulation emits far more events than a player can attend to, so a sifting layer must surface the narratively interesting subsequences. Relevant to Chronicle because 1000 NPCs will generate more grudges/rumors/obligations than can be surfaced without a sifter (see Details §6, deferred).

### Rumor mutation & propagation

**Daley–Kendall (1964/65) rumor model, Maki–Thompson variant.** SIR-analogue with Ignorants/Spreaders/Stiflers; unlike disease SIR, "recovery" is interaction-driven (a spreader stifles on meeting someone who already knows) and there is no epidemic threshold — any β/α > 0 spreads macroscopically. Implementability: trivial, O(active spreader edges) per tick — directly usable for "who currently knows/repeats rumor X" across 1000 nodes.

**Bartlett (1932) serial reproduction, formalized as a Bayesian Markov chain by Xu & Griffiths (2010), Kalish/Griffiths/Lewandowsky.** Each retelling reconstructs (not copies) information, biased toward the transmitter's prior/schema, with distortion compounding and a documented negativity/schema-consistency bias. Implementability: this is the principled justification for Ryan's hand-authored mutation graph — represent rumor content as a small feature vector and resample features toward a schema/prior with a per-feature mutation probability on each hop, O(features) per transmission.

**Cognitive cascades (Rabb, Cowen, de Ruiter, Scheutz — PLOS One 2022).** Explicitly couples an internal belief model to network contagion, unlike most epidemic models. Heavier per-tick cost; worth knowing as a fallback if pure SIR proves too mechanical, but not needed for v1.

### Opinion/reputation drift

**Deffuant–Weisbuch (2000) / Hegselmann–Krause (2002) bounded-confidence models.** Each agent holds a continuous opinion in [0,1]; in DW, a random interacting pair moves toward each other by a compromise factor μ only if their opinion gap is under a confidence bound c (`x_i += μ(x_j − x_i)`); HK is the synchronous multi-neighbor variant. Outcomes (consensus/polarization/fragmentation) depend on c, with cluster count ≈ ⌊1/2c⌋. Implementability: extremely cheap (one subtraction, one comparison, two updates per pair). Models attitudes/opinions, not factual belief content — the source report explicitly recommends pairing this with the Ryan facet model rather than substituting for it, since aggregate opinion models give believable statistical spread but no narratively meaningful individual reasons.

### Norms, obligation, reciprocity

**Richard Evans & Emily Short — Versu (IEEE TCIAIG 2014); Evans, "Using Exclusion Logic to Model Social Practices" (2011).** A social practice is a recurring social situation implemented as a reactive joint plan providing affordances/suggestions to autonomous agents (never controlling them directly); agents choose via utility-based reactive action selection. Norms/obligations are represented in exclusion logic, a modal logic without negation/disjunction chosen specifically for its efficient decision procedure. Implementability: medium — the original stack is lost, but a 2023 open-source reconstruction (Praxish, AIIDE 2023) exists; the social-practice-as-affordance pattern is implementable and is the cleanest published obligation/norm model for characters.

**Comme il Faut / Prom Week (McCoy et al.) and Ensemble Engine (Samuel et al., FDG 2015).** Social state is a database of relationships/networks/status/history; characters compute volitions from a large body of social considerations (Prom Week shipped on the order of thousands of rules) ranking desired social exchanges; a responder accepts/rejects, and trigger rules cascade further changes. Ensemble is the open-source (JS), domain-agnostic reimplementation. Implementability: high for the pattern itself, but the source report flags authorial burden as the real cost — reciprocity/obligation emerge from rules rather than being first-class primitives.

**Normative multi-agent systems (NorMAS) literature (Boella, van der Torre, Dignum).** Norms as explicit deontic statements (addressee, activation/expiration, rewards/sanctions) enforced by a violation-detecting monitor. Implementability: the obligation-with-deadline-and-sanction pattern is trivially implementable and is what a game actually wants; full deontic-logic verification is unnecessary overhead. This is the recommended v1 pattern for Chronicle's obligation system.

**FAtiMA / OCC / EMA appraisal architectures (Dias, Mascarenhas & Paiva; Gratch & Marsella).** Events appraised against goals produce OCC emotions that modulate behavior; FAtiMA Toolkit is open-source, rule-based. Implementability: medium, more machinery than strictly needed for grudges/reputation alone, but OCC's praiseworthiness/desirability appraisal of others' actions is a clean, principled way to generate grudges and gratitude as first-class decaying relationship modifiers — a good v2 bridge between face/reciprocity and Chronicle's grudge system. Deferred for v1.

### Memory decay & misremembering

**ACT-R base-level activation (Anderson & Schooler).** `B_i = ln(Σ_k t_k^{-d})` over times-since-access t_k, decay parameter d (typically 0.3–0.5); reproduces the empirical power law of forgetting, and repeated access re-strengthens the trace. Implementability: excellent, closed-form, a few operations per memory; at 1000-NPC scale, approximate with a running activation + last-access timestamp rather than full access history (the report notes this approximation is non-monotonic in d and should be parameter-tested).

**Stanford Generative Agents retrieval score (Park et al., UIST 2023).** `score = α_recency·recency + α_importance·importance + α_relevance·relevance` (α=1 each in the original); recency is exponential decay (γ≈0.995/hour), importance an LLM-or-heuristic 1–10 rating, relevance an embedding cosine similarity; periodic reflections synthesize higher-level beliefs written back into the memory stream. Implementability: high if the LLM is dropped in favor of heuristic importance and tag-overlap relevance — this is the de-facto modern memory-retrieval design and composes with ACT-R decay. Documented failure mode: reflection can hallucinate patterns; keep retrieved top-k small (3–5).

**Source confusion / misattribution.** No single canonical algorithm exists; the report recommends operationalizing it by making provenance a mutable, decaying field — reuse Ryan's evidence typology (each belief carries a Source) and corrupt/swap the Source field on retrieval failure, combined with Bartlett-style mutation on content.

### Shipped-game postmortems

**Robison, Viglione, Zubek & Horswill — "AI Design Lessons for Social Modeling at Scale" (AIIDE 2021); Zubek, Horswill, Robison & Viglione — "Social Modeling via Logic Programming in City of Gangsters" (AIIDE 2021, doi:10.1609/aiide.v17i1.18912).** City of Gangsters ships a network of ~1200 NPCs — almost exactly Chronicle's target scale — with NPC opinions of the player modulating outcomes. Four lessons: legibility is paramount (actions and consequences must be visible/comprehensible at scale, or ambiguity kills the experience); actions should be reversible; modeled social norms must be a succinct set; and surface them obsessively ("more than twenty rules strikes us as too many"). Built with top-down logic programming, found well-suited to inference over a 1000+ character relationship network. The source report calls this the single most relevant citation to Chronicle's project, given the near-identical NPC count.

**Ian Horswill & Samuel Hill — TED/Simulog (AIIDE 2024; EXAG @ AIIDE 2024).** Bottom-up (Datalog-style) logic programming achieving 5000 characters at 60fps (13.87ms average inner-frame) and 2000 characters at 7.55ms/tick on an Apple M3 Pro — but in C#, not Python; without native compilation and per-predicate parallelism the ceiling drops to 2000 NPCs. Original Python Talk of the Town (~400 NPCs) "required many minutes to simulate a city." Implementability: not directly (C#), but serves as both a feasibility proof and a performance warning — Chronicle's Python hot paths (propagation, opinion updates) should be vectorized (NumPy) rather than assumed to scale naively.

**Ian Horswill — "Postmortem: MKULTRA" (AIIDE 2018).** Documents the practical difficulty of debugging emergent character reasoning and the gap between an expressive knowledge representation and a legible player experience — a caution for any rich belief/provenance system.

**Dwarf Fortress (Tarn Adams, AIIDE 2016/2019/2021).** Models rumors, grudges, relationships, secret identities with on-the-fly identity replacement in rumors/witness reports; relationships tracked at name/visual/reputation granularity. Adams notes the social layer got less depth than the physical simulation, and per the wiki NPCs in some cases "don't actually remember the event" — they re-derive reactions when retold, a pragmatic shortcut Chronicle could copy to avoid storing full event histories per NPC.

**RimWorld.** A thought/moodlet system: social memories are opinion modifiers with fixed decay durations (e.g., "you killed my mother" ≈ −80 opinion, some effectively permanent), driving insults/fights/romance thresholds. A clean, cheap, shippable model of grudges as decaying scalar modifiers — the pragmatic opposite of Ryan's rich facets, and a plausible fallback if Chronicle's full belief model proves too expensive per-NPC.

**Crusader Kings 3.** Schemes, hooks (weak/strong, expiring ~a decade), secrets, scalar opinion with stacked/expiring modifiers. Documented failure modes: AI acting against stated personality, and (patch 1.4.0) AI interaction spam throttled from ~300 to ~30 interactions per character per century — a direct, citable warning about needing a per-tick interaction budget at NPC scale.

**Talk of the Town / Bad News.** The simulation was rich but the interactive gameplay layer was never fully realized (Bad News used a live human performer instead); a caution that a deep social model is necessary but not sufficient without a presentation/sifting layer.

## Caveats (carried from source)

- Scale claims (5000 NPCs at 60fps, 2000 NPCs at 7.55ms/tick) are C#-only (TED/Simulog); treat as feasibility proof, not a Python performance promise.
- Bounded-confidence and SIR models describe aggregate dynamics only — use alongside, not instead of, the Ryan facet model for per-belief provenance.
- Norm/obligation systems are the least drop-in of the five areas surveyed; every implemented system trades expressiveness for authoring burden or logical restriction.
- Some sources are secondary/informal (wikis, patch notes, dev interviews for RimWorld/CK3/Dwarf Fortress) — reliable for design behavior, not peer-reviewed; the DF and City of Gangsters AIIDE papers are the citable primary sources.
- The Generative Agents reflection mechanism can hallucinate patterns and is LLM-dependent as published; the non-LLM heuristic adaptation recommended here is a simplification, not the validated original.
