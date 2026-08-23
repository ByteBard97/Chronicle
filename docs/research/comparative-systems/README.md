# Comparative systems research

Research on other games' social-simulation systems (Crusader Kings, and
others as they arrive), collected to inform Chronicle's own **reactivity**
design — how belief/grudge/rumor/obligation state should eventually
translate into observable NPC behavior. This is raw comparative material,
not yet-synthesized decisions: nothing here is an ADR, and none of it has
been checked against Chronicle's actual code the way `docs/research/`'s
main numbered series is expected to be before being merged into an ADR.

Distinct from the main `docs/research/00-index.md` series, which covers
Skyrim-modding-substrate and infrastructure research tied directly to
accepted ADRs. This folder is a working library for the "what should
reactivity look like" design question, feeding the scenario-ladder work
(see project conversation/notes) rather than a specific decision record.

## Crusader Kings (menu-driven, turn-based)

| File | Covers |
|------|--------|
| [ck-postmortems-and-design-lessons.md](ck-postmortems-and-design-lessons.md) | CK2→CK3 postmortems, designer commentary (Fåhraeus/Oltner), failure modes ("opinion-modifier soup," AI legibility), event-engine architecture (MTTH vs. on_action), storylet theory, a comparison table against King of Dragon Pass/Wildermyth/Total War/Mount & Blade, and a "what to copy/adapt/avoid" synthesis. |
| [ck-mechanics-inventory.md](ck-mechanics-inventory.md) | Detailed mechanics inventory: the opinion system's data model and decay/stacking rules, faction/threshold-to-action tables, council/scheme mechanics, the Secrets/Hooks economy, the Stress engine, the Memories system, and named relationship-crystallization states (Friend/Rival/Nemesis etc.) with their unlock/termination conditions. |
| [ck-opinion-decay-and-threshold-tables.md](ck-opinion-decay-and-threshold-tables.md) | Second independent pass on the same mechanics ground, emphasizing the CK2-vs-CK3 decay-model difference (flat-then-drop vs. gradual decay) and concrete numeric threshold/value tables (faction discontent gates, opinion modifier magnitudes, `ai_will_do`/`ai_chance` scoring). |
| [ck-fahraeus-primary-sources-and-legibility.md](ck-fahraeus-primary-sources-and-legibility.md) | Second independent pass on postmortems/design lessons, built from primary-source designer quotes (Fåhraeus's Gamasutra interview, his GDC 2014 talk) and documented player-facing legibility-failure case studies. Explicitly framed by its own author around Skyrim NPC reactivity. |
| [ck-failure-modes-and-reactivity-loop.md](ck-failure-modes-and-reactivity-loop.md) | Third independent pass on postmortems/design lessons, with two original diagrams (reactivity loop, failure-modes map — under `figures/ck-failure-modes-and-reactivity-loop/`), a structured failure-mode table, and citations reaching into Bret Devereaux's structural CK3 analysis and a Total War: Attila cross-genre comparison. |
| [ck-plaintext-numeric-values-inventory.md](ck-plaintext-numeric-values-inventory.md) | Fourth independent pass on the mechanics-inventory ground, distinguished by giving exact numeric values as plain markdown text with inline citations rather than embedded images — fills the gap flagged in `ck-mechanics-inventory.md`. Includes an explicit "evidence gaps and version caveats" section. |

Several CK files cover overlapping ground from independent research passes —
that's intentional (cross-checking, not redundant filing); read the
provenance header at the top of each for what's distinctive about it.

## Real-time spatial sims

| File | Covers |
|------|--------|
| [spatial-sim-shadows-of-doubt-nemesis-kenshi.md](spatial-sim-shadows-of-doubt-nemesis-kenshi.md) | Genre neighbors that simulate NPCs walking around a real-time 3D/voxel world (closer to Skyrim's own shape than CK's menu-driven model): Shadows of Doubt's witness/memory-decay pipeline and provenance-graph detective gameplay, Monolith's Nemesis System, and Kenshi's faction/legal/sight-based-crime systems. **Its Nemesis patent number is wrong — corrected by the next row.** |
| [spatial-sim-legal-boundaries-and-witness-propagation.md](spatial-sim-legal-boundaries-and-witness-propagation.md) | Second independent pass on the same three games. Corrects the above file's patent citation (the real Nemesis family is US 10,926,179 B2 + continuations, with a precise claim-by-claim breakdown of what's covered vs. free to use) and frames each game's witness/grudge-propagation unit distinctly: SoD's per-citizen precomputed batch simulation, Kenshi's faction-as-memory-unit (not per-NPC), and Nemesis's true per-NPC memory. |

## AI directors / drama management

| File | Covers |
|------|--------|
| [ai-directors-and-drama-management.md](ai-directors-and-drama-management.md) | Cross-game/academic survey of drama-management and AI-director architectures: Façade's beat manager, symbolic narrative planning (IPOCL, Experience Management), Left 4 Dead's pacing FSM, RimWorld's wealth-scaled Storytellers, Shadows of Doubt's provenance-anchored case generator, PaSSAGE's player-modeling content selection, and DeepMind Concordia's grounded-validation LLM Game Master. Converges independently on the same four-stage input/recognition/intervention/presentation pipeline as [19-skyrim-quest-injection-machinery.md](../19-skyrim-quest-injection-machinery.md), which covers the Skyrim-specific wiring for the same layer. Ahead-of-need — `docs/architecture.md` defers "prospective drama management." |
| [ai-directors-and-drama-management-v2.md](ai-directors-and-drama-management-v2.md) | Second independent pass: the declarative-optimization drama-management failure record (invest in intervention vocabulary before selection intelligence), plan-based mediation's formal license for retroactive reframing, Daggerfall's actual QBN/QRC template format, the storylet academic thread, and the AI Dungeon/Hidden Door consumer record as the sharpest cautionary evidence against unconstrained LLM generation. Companion to [20-skyrim-quest-injection-machinery-v2.md](../20-skyrim-quest-injection-machinery-v2.md). |
| [ai-directors-and-drama-management-v3.md](ai-directors-and-drama-management-v3.md) | Third independent pass: Sid Meier's perceived-vs-statistical-fairness lesson from Civilization's combat-odds backlash, storylet role-casting named as the highest-value transfer, and hard 2024–2026 LLM-drift benchmark numbers (NCP-Bench, TSL neuro-symbolic automata, Slice of Life, function-calling validity gates). Companion to [21-skyrim-quest-injection-machinery-v3.md](../21-skyrim-quest-injection-machinery-v3.md). |
| [ai-directors-and-drama-management-v4.md](ai-directors-and-drama-management-v4.md) | Fourth independent pass, no Skyrim-specific companion this time: Friends & Fables/ACE-1's atomic-memory-with-provenance redesign (the closest commercial analog yet to Chronicle's belief model), Todd Howard's own primary-source quote on Radiant Story's design intent, and two trust-failure modes new to this series — "promised policy not implemented" and "simulation illegibility" (Wildermyth's own discarded, too-deep overland-map feature). |

More reports along these lines are expected — add new files here with the
same filed-date/provenance header (see either file's top blockquote for
the template) rather than starting a separate location.
