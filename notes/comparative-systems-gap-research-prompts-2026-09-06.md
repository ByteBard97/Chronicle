# Comparative-systems gap research prompts (2026-09-06)

Four self-contained prompts for external web-research agents (Gemini,
ChatGPT with browsing, Perplexity, Claude, Kimi, etc.) — paste each
individually. Written to fill specific gaps surfaced by two converging
processes: an exhaustive catalog of NPC-social mechanics across six
already-researched games (`docs/research/comparative-systems/
npc-social-mechanics-catalog-2026-09-06.md`), and five independent AI
agents (ChatGPT, Gemini, Kimi, Grok, Fable) who each brainstormed Skyrim
implementations against that catalog and, unprompted, flagged systems the
catalog was missing.

Ordered by priority. Prompt 1 is the most urgent — it isn't just a new
brainstorm candidate, it corrects a gap under an existing load-bearing
design claim.

---

## Prompt 1: Talk of the Town — RETIRED, do not run

**Superseded 2026-09-06: primary sources turned out to be directly
available** — a real GitHub repo (`github.com/james-owen-ryan/talktown`)
and four papers including James Ryan's own dissertation, found via a
direct web search rather than needing a research agent's secondhand
characterization. A fork was dispatched to clone the repo and read the
dissertation + the most relevant papers directly; see
`docs/research/comparative-systems/talk-of-the-town-primary-source-verification-2026-09-06.md`
once it lands. Do not run this prompt through an external agent — it
would only produce a worse, secondhand version of what direct primary-
source reading already covers.

**Why this was flagged urgent in the first place (kept for context):** Chronicle (an external
social-simulation mod for Skyrim SE/AE — NPCs form beliefs with
provenance, rumors mutate as they spread, grudges/obligations write back
into behavior) has a committed vision document (`docs/vision-v2.2.md`)
that states, as its central mitigation for the project's biggest bet:
"the epistemology is built on the most-validated data model in the
academic literature (Talk of the Town's belief facets, evidence chains,
predecessor lineage)." Despite that, **no dedicated primary-source
research on Talk of the Town exists anywhere in this project.** This
prompt exists to close that gap and verify the claim is actually accurate,
not to explore a new idea.

Investigate **Talk of the Town** (James Ryan, UC Santa Cruz — his
dissertation and the shipped playable installation "Bad News," which won
awards on the festival circuit around 2017). Specifically:

1. **The belief/knowledge representation.** How exactly is a character's
   knowledge of a fact structured? What does Ryan's own writing call a
   "belief facet"? Is there a literal, named "evidence chain" or
   "predecessor lineage" concept in his work, or is that Chronicle's own
   paraphrase of something described differently — quote the actual
   terminology from his dissertation/papers if it exists, and say plainly
   if Chronicle's phrasing doesn't map cleanly onto a real Talk of the Town
   concept.
2. **Rumor mutation and distortion in transit.** Does information actually
   change/degrade content as it passes person to person (not just become
   less certain or less detailed, but become *factually wrong* in a
   specific, traceable way)? This is the single most important question:
   Dwarf Fortress's own rumor system (already researched for this project)
   explicitly refuses to distort content in transit, and Talk of the Town
   is cited elsewhere as "the only system that implements rumor distortion
   with provenance" — verify this specific claim against Ryan's own
   published description of the algorithm.
3. **How beliefs are formed**: direct observation vs. hearsay, and whether
   witnessed vs. told knowledge is tracked as a meaningfully different kind
   of fact (confidence, certainty, source-attribution).
4. **Decay** — do beliefs/rumors fade or become less certain over time,
   and by what mechanism?
5. **What "Bad News" actually is as a shipped artifact** — is it a fully
   playable game demonstrating this system live, a tech demo, or primarily
   an academic paper with a small illustrative build? What can actually be
   inspected/played today, and is there any source code available (even
   partial) versus only papers/talks?
6. **License and reusability** — is any of Ryan's actual code
   open-sourced or otherwise available to study line-by-line, the way this
   project has previously verified other systems (IBSEN, HAMLET) by
   directly reading source rather than trusting secondary summaries?

Cite specific sources: Ryan's dissertation, published papers (AIIDE,
academic venues), his own talks/interviews, and the "Bad News" project
page if one exists. End with a plain verdict: **is Chronicle's stated
citation of Talk of the Town as its foundational data model accurate**,
and if the real system differs from what Chronicle's vision doc describes
in any material way, say exactly how.

---

## Prompt 2: Academic social-simulation engines beyond The Sims (Comme il Faut, Prom Week, Ensemble, Versu, City of Gangsters)

**Background:** two independent research threads for this project — a
brainstorm-agent pass and a separate Sims-specific research pass —
independently surfaced the same cluster of academic systems as closer
precedent than The Sims for Chronicle's actual goal (a world whose social
state evolves with genuine third-party reasoning, not just dyadic
tracking). None of these have a dedicated research file in this project
yet.

Investigate this cluster, treating each as related but distinct:

1. **Comme il Faut (CiF)** — McCoy, Treanor, Samuel, Mateas, Wardrip-Fruin
   (UC Santa Cruz). A "social physics" engine: reportedly ~5,000 weighted
   social-consideration rules and exchange-based social interactions, with
   a shared social-facts database supporting genuine third-party
   inference (e.g., an uninvolved character can reason "X is cheating on
   Y" from facts they weren't directly told). Investigate the actual rule
   representation, how an interaction is selected/scored, and how facts
   propagate/are queried by characters not directly involved.
2. **Prom Week** — the shipped game built on CiF. How playable/complete is
   it, what's the actual scope of its social simulation in the shipped
   product versus the underlying CiF research engine, and is source code
   available?
3. **Ensemble** — described as CiF's open-source successor engine.
   Confirm this is real (not a naming coincidence with an unrelated
   project), find its actual repository if one exists, check whether it's
   genuinely usable/maintained or effectively abandoned, and note its
   license.
4. **Versu** — Emily Short and Richard Evans's social-practice-based
   agent system (characters evaluate actions against social norms/roles,
   a "deontic" status model — permitted/obligated/forbidden — that can
   shift for multiple characters at once when a triggering fact arrives).
   How does this differ architecturally from CiF? Is any of it
   open-sourced, and is there a citable primary source beyond Evans's own
   talks (e.g., the IEEE Transactions on Computational Intelligence and AI
   in Games paper on Versu)?
5. **City of Gangsters** — Zubek, Horswill, Robison, Viglione (AIIDE
   2021), "Social Modeling via Logic Programming in City of Gangsters."
   A shipped commercial game using logic-programming-based social
   inference with second-order propagation across a reportedly large NPC
   population (~1,200). What's the actual inference mechanism, and how
   does it achieve that scale without the performance problems academic
   symbolic-planning systems are documented to hit elsewhere?

For each, report: architecture (as concretely as sources allow), license/
availability of any real code, shipped-vs-theoretical status, and how it
specifically differs from Chronicle's existing belief/rumor/grudge
design. End with a verdict: which of these five, if any, is worth a deep
line-by-line source study (the way this project has previously verified
IBSEN and HAMLET), and which are citable-but-not-inspectable (papers/talks
only, no real code to read)?

---

## Prompt 3: Bethesda's own Radiant AI / Radiant Story, as actually shipped

**Why this is the highest-value gap of the batch:** three independent
brainstorm-agent passes (out of five run against the mechanics catalog)
independently flagged this as the single most under-researched,
most-actionable gap — because it isn't a comparison target, it's the
actual substrate Chronicle has to read, cooperate with, or override
inside Skyrim itself. This project has previously researched Skyrim's
quest-injection machinery in the abstract (`docs/research/19` through
`21`), but not a dedicated, concrete pass on Radiant AI/Radiant Story's
real shipped mechanics across Bethesda's own titles.

Investigate:

1. **Radiant Story's actual node/condition system in Skyrim** — how
   quest aliases with "Find Matching Reference" / "Use Existing Reference"
   type conditions pick a live NPC or object at runtime (the underlying
   mechanism the community calls "radiant quest generation"). Cite Creation
   Kit documentation, Bethesda developer talks (Todd Howard, Bruce Nesmith,
   Emil Pagliarulo have all spoken on this at points), and any technical
   community writeups (the CK wiki, longtime modding community documentation).
2. **Whether this is genuinely the same pattern as "storylet role-casting"**
   (a King of Dragon Pass-lineage pattern this project's research already
   names as the single highest-value transferable idea from the academic
   AI-director literature) — cast a real NPC/location into a
   precondition-gated template — or only superficially similar. Be
   specific about where it's the same mechanism and where it diverges.
3. **Radiant AI's documented historical failure modes**, specifically
   Oblivion's infamous need-driven-behavior cascade failures (the "a
   beggar NPC was scripted to solve hunger, found no legal food, and
   killed another NPC to steal bread" family of stories) — verify what
   actually shipped/was patched versus what's exaggerated internet legend,
   citing developer post-mortems or primary interviews where possible.
4. **What's actually exposed to a mod like Chronicle**: via SKSE, Creation
   Kit's own scripting (Papyrus), or community-documented technique, what
   hooks exist to (a) observe Radiant Story firing a quest, (b) inject a
   Chronicle-sourced NPC/location into an existing radiant template rather
   than building a wholly separate quest system, or (c) at minimum avoid
   Chronicle's own generated content conflicting with Radiant Story's
   independent selections. Cite specific SKSE APIs or documented Papyrus
   functions if they exist.
5. **Fallout 4's version of the same system**, if meaningfully different
   from Skyrim's (Bethesda iterated on this across titles) — only if it's
   directly relevant to understanding what's changed/improved since
   Oblivion.

End with a verdict: how much of what a GM/storyteller-style director layer
would need (picking a real NPC, a real location, gating on real
precondition state) is Bethesda's own engine already doing natively, and
what's the smallest actual integration surface for Chronicle to hook into
it rather than building a parallel, competing system?

---

## Prompt 4: Remaining smaller gaps in already-covered games

Six smaller items, independently flagged as missing from existing
coverage of games this project has already researched in depth. Cover all
six; none need the depth of prompts 1-3, but each should get a real,
cited answer, not a one-line gloss.

1. **Crusader Kings III's Legends system** (Legends of the Dead
   expansion) — a "legend" as a narrative object with a named protagonist,
   typed quality/tier levels, and geographic province-by-province spread
   driven by spending resources on active promotion. How is spread
   actually modeled (is it more like a diffusion/adjacency simulation, a
   scripted radius, something else), what determines a legend's "quality"
   tier, and what mechanical effects (if any) does a spread legend confer
   beyond flavor?
2. **Crusader Kings III's Struggle/Phase system** — a regional conflict
   modeled as discrete named phases (e.g., something like Opportunity →
   Hostility → Tension → Compromise), each phase gating different
   available player/AI actions. Get the actual phase names/transition
   triggers right, not an approximation — this project is specifically
   considering it as a template for modeling Skyrim's civil war as a
   multi-phase conflict rather than a binary questline.
3. **The Nemesis System's intel/interrogation system** (Shadow of
   War) — "worms" (interrogatable low-rank orcs) and intel items that
   reveal a target captain/warchief's strengths, weaknesses, and location
   before engagement. How is intel actually acquired and spent, and is
   there a mechanical cost/risk to interrogation?
4. **RimWorld's Ideology DLC** — ideoligions: precepts, rituals,
   conversion mechanics, and per-pawn certainty scores, as a collective
   belief layer distinct from (and interacting with) individual mood.
   Also cover RimWorld's **art-description/"Tales" system**: how a
   generated artwork's description references real recorded colony
   events, and how that differs mechanically from Dwarf Fortress's own
   engraving/provenance-object pattern (already researched for this
   project).
5. **Dwarf Fortress's Villains update (v0.47)** — world-gen-layer intrigue
   networks: agents, embezzlement, corruption plots, and fortress-mode
   interrogation. Also cover the documented "loyalty-cascade" emergent
   failure mode (ordering the execution of a citizen can make the
   executioners themselves traitors to their own civilization, cascading
   further) as a specific cautionary case study for any faction-membership
   or forced-compliance mechanic.
6. **Watch Dogs: Legion's "play as anyone" system** — every pedestrian
   carries a procedurally generated schedule, job, and relationship web,
   plus an assembled recruitment-grievance chain (e.g., a specific
   relative was wronged by a specific faction, making that pedestrian
   recruitable through that exact grievance). How is the grievance chain
   actually generated/gated, and does it draw on any pre-simulated social
   graph or is it assembled fresh per-pedestrian at recruitment time?

For each of the six, report: the concrete mechanic, a citation (developer
material, wiki with primary sourcing, or a credible technical writeup),
and — briefly, one sentence each — whether it looks like a natural
extension of something already in `docs/research/comparative-systems/npc-social-mechanics-catalog-2026-09-06.md`
or a genuinely distinct new mechanic.
