# Academic Social-Simulation Engines Beyond The Sims: Synthesis (2026-09-06)

Three independent agents (Gemini, Claude, Kimi) ran gap-research Prompt 2 from
`notes/comparative-systems-gap-research-prompts-2026-09-06.md` — investigating
Comme il Faut (CiF), Prom Week, Ensemble, Versu, and City of Gangsters as
academic social-simulation engines two separate earlier research threads
(a brainstorm-agent pass and the Sims-research synthesis) independently
flagged as closer precedent than The Sims for Chronicle's actual goal:
genuine third-party social reasoning, not just dyadic tracking.

**Sources merged:**
`docs/research/comparative-systems/gap-research-raw-agent-reports-2026-09-06/academic-engines-gemini.md`,
`.../academic-engines-claude.md`, `.../academic-engines-kimi.md`. Claude's
report was the deepest of the first two (checks actual repo contents,
license files, commit/star counts). **Kimi's report is the most rigorous
of the three** — it independently re-derived most of Claude's findings from
its own evidence (repo metadata pulls, not just assertion), resolved two of
the three prior open disagreements with new empirical checks, and adds a
genuinely new artifact (MicroCoG, with a directly-parsed 40MB save file)
neither of the first two reports fully confirmed. Gemini's report bundles
this topic with Talk of the Town and Radiant AI in one combined document —
only its "Academic Social-Simulation Engines" section is used here.

## Verdict up front

**All five systems achieve genuine third-party/n-ary social reasoning —
the property that distinguishes them from The Sims** — but by different
mechanisms: CiF/Ensemble use weighted rule-bases summed into "volitions";
Versu uses a deontic modal logic (Exclusion Logic) with utility-based
action selection over social practices; City of Gangsters uses first-order
Horn-clause logic programming over a relationship graph. All three reports
agree on this core point.

**All three reports also agree on the sharper, more important negative
finding: none of the five tracks per-belief provenance the way Chronicle
does, and none of them mutate a fact's content as it propagates.** CiF's
own paper is explicit and is quoted directly by both Kimi and Claude: CiF
"does not simulate hidden information," and all events are immediately
known to all characters via its Social Facts Database (SFDB). City of
Gangsters' history elements record *what happened* and can explain a
relationship's current value, but these are objective public/relational
facts, not per-NPC subjective beliefs with a source/chain-of-custody the
way Talk of the Town's belief facets are (see the dedicated Talk of the
Town verification). Propagated facts in all five are faithful copies,
never distorted in transit. **Grudges/obligations writing back into
behavior is the cluster's strongest overlap with Chronicle** — City of
Gangsters' negative history elements gate action space and trigger
ambushes; Versu's deontic practices are the richest model of the five,
with one triggering fact able to shift several characters' obligations
simultaneously.

Kimi goes one step further than the other two and proposes a concrete
**hybrid architecture** combining the best-validated piece of each system
plus a new layer none of them have (see "Kimi's proposed architecture"
below) — this is a genuine value-add beyond an inventory of precedent.

## Per-system merged findings

### Comme il Faut (CiF)

- **Architecture (agreed by all three):** UC Santa Cruz (McCoy, Treanor, Samuel, Mateas, Wardrip-Fruin et al.), a rule-based "social physics" engine. ~5,000 weighted **influence rules** (Claude and Kimi both describe these as Horn-clause-style, deliberately conjunctive for deterministic evaluation, grouped into reusable **microtheories**) summed into a character's **volition** to take a social action. A **Social Facts Database (SFDB)** logs every played exchange as queryable public history. **Trigger rules** run independently of specific exchanges and can derive new state for uninvolved characters — all three reports cite the same canonical example: "X is cheating on Y if X and Y are dating and there is a character Z also dating X."
- **Availability — resolved, Claude and Kimi corroborate each other independently, contradicting Gemini:** Gemini's report doesn't address CiF's own source directly (treats it as "open-source, but completely superseded by Ensemble," recommending "read Ensemble's code" instead). **Both Claude and Kimi independently confirm the actual ActionScript source is publicly present** inside `ExpressiveIntelligence/PromWeek`'s repository (Claude: `trunk/` folder, ~93% ActionScript by GitHub language detection; Kimi: names the exact files — `SocialFactsDB.as`, `Predicate.as`, `Rule.as`, `InfluenceRule.as`, `SocialGame.as`, `Microtheory.as`, `Trigger.as` — and separately did an XML content audit finding 9,470 `Predicate`, 5,938 `Rule`, 4,214 `InfluenceRule` elements in the master content library). Both agree there is **no project-wide license file** (Kimi: "no obvious license file... only obvious license file belonged to bundled third-party FirePHPCore code"). **This disagreement is now resolved 2-vs-1 with independent corroborating evidence, not just vote count**: Gemini's "discard, inaccessible" framing is wrong; the source is real, readable, and specifically catalogued by two independent audits. Kimi's practical caveat, distinct from Claude's: the *code* is readable today, but the Flash/AIR *runtime* itself is obsolete, so treat this as "inspect the architecture," not "run the game."

### Prom Week

- **Shipped status (agreed by all three):** the complete, shipped consumer game built on CiF — not a stripped-down subset. Released free on Facebook/Kongregate (Feb. 2012), 2012 IGF Technical Excellence finalist, 2012 IndieCade finalist. Kimi adds hard empirical detail beyond Claude's summary: an 18-character cast (named individually from a direct XML audit), 51 relationship declarations, 141 trait declarations, 392 propositions, 491 network edges, 13,003 total play traces logged between release and May 2012 (5,425 used in evaluation), with 263 fully-distinct playthroughs analyzed for one character's story alone — the strongest evidence yet that this is a genuinely deep, replayable shipped domain, not a toy demo.
- **Inspectability — resolved, 2-of-3 corroborate directly:** Gemini rated this **Low/Discard** ("severe inspection challenges," citing Flash's deprecation). **Both Claude and Kimi found the same repo's ActionScript source directly readable** and reached the same verdict independently: legitimate to study/cite, not legally clean to reuse (no license, code visible since a 2019 GitHub push, long after the 2012 game). Kimi's specific addition: even licensing aside, the Flash/AIR stack is genuinely obsolete for *running* the game today (the official play page still hosts the SWF, but normal modern-browser Flash execution isn't a practical path) — so "inspect the architecture" and "play the game" are two different, both-limited claims, worth keeping separate.

### Ensemble

- **Architecture (agreed by all three):** CiF's ground-up successor (Samuel, Reed, Maddaloni, Mateas, Wardrip-Fruin, "The Ensemble Engine: Next-Generation Social Physics," FDG 2015). Same core loop as CiF but a **data-driven schema** (categories declared by properties like `isBoolean`, `directionType`, `duration` rather than hardcoded), splitting **volition rules** (adjust desire) from **trigger rules** (directly change state), plus — a detail only Kimi and the underlying paper emphasize — **arbitrary role binding** (a rule can involve more than two roles at once, e.g. "enemy of my enemy is my friend" needs three) and **hierarchical, multi-participant actions** (an action can decompose into subactions, e.g. "reveal a friend's secret to a third party"). Repository: `github.com/ensemble-engine/ensemble`, **BSD-4-clause** license (all three reports agree this is the most permissively-licensed system in the cluster, though Kimi notes the UC-specific advertising/acknowledgement clause is unusual and worth reviewing before commercial reuse).
- **Maintenance status — now resolved 2-of-3 with independent new evidence, not just vote count.** Gemini calls Ensemble "actively maintained" and ranks it #1 of five for deep study, asserted without a cited source. Claude found a specific contradicting primary source: a 2024 FDG postmortem ("Paradise," Kreminski et al.) stating Ensemble "has changed hands several times and is no longer maintained." **Kimi independently pulled its own repository metadata rather than relying on either prior claim or citation**: created July 2016, **last push November 2022**, 63 stars, 10 forks, 85 open issues, no archived flag — concluding "public and inspectable but stale, not actively maintained." Kimi's empirical finding doesn't cite Claude's 2024-postmortem source at all, making it a genuinely independent confirmation rather than an echo — **two independently-sourced findings (a direct commit-history check and a cited postmortem) now agree Ensemble is stale/unmaintained against Gemini's unsourced "actively maintained" claim.** Treat Ensemble as **stale but still the best-licensed, best-documented codebase in the CiF family** — Kimi's own final verdict explicitly separates "worth studying" from "actively maintained," which is the more useful framing than either prior report's binary.

### Versu

- **Architecture (agreed by all three):** Richard Evans and Emily Short (with a Linden Lab-backed team). Two core ideas: **social practices** (role-agnostic, concurrent, parameterized, persistent joint models of recurring situations — a greeting, dinner, courtship, accusation — that offer non-controlling **affordances** rather than directly controlling agents) and **Exclusion Logic** (Evans, DEON 2010) as the underlying world-representation formalism, where a literal `A!B` operator marks "B is the unique way A is the case" and automatically retracts stale data when a practice changes state. All three reports agree this is the strongest precedent in the cluster for Chronicle's grudges/obligations: a single incoming fact can reconfigure several characters' obligations simultaneously via a deontic (permitted/obligated/forbidden) status model. **Kimi adds a distinct, important nuance the other two don't emphasize**: Versu's runtime behavior is not just static deontic labels — norm violations remain *available* (especially to the player), and a violation can spawn a responsive subpractice (disapproval, forgiveness, anger, eviction) rather than simply flipping a flag. Kimi also documents Versu's **speculative action-consequence scoring** (an agent tentatively executes an action's postconditions, evaluates the resulting state against its own desires, then rolls back before committing to the *actual* best action) as a distinct, separately-citable design pattern — explicitly contrasted in the primary source against The Sims' simplified expected-effect model, which can diverge from actual conditional effects.
- **Availability (agreed core fact across all three):** the original engine is proprietary and effectively lost — developed at Little Text People, later at Linden Lab, which (per Emily Short's own 2014 blog post, cited independently by both Claude and Kimi) refused to sell her the codebase and IP after cancelling the project. Versu itself is "citable, not inspectable" across all three reports, unanimously.
- **Reconstruction naming — now resolved, 2-of-3 corroborate the same project, Gemini's citation likely wrong or obscure:** Gemini names **"Wyclef"** (a Santa Clara University senior thesis) as the relevant open reconstruction. **Both Claude and Kimi independently cite the same project instead: `mkremins/praxish`** (JavaScript, MIT-licensed via a `LICENSE.txt`/`LICENSE.md` file, authored by Dameris/Hernandez Roman/Kreminski, published as "Praxish," AIIDE 2023). Kimi did its own repository audit and confirmed: initial 2023 creation, **development continuing into 2026**, MIT license, and specific file contents (`db.js` for the exclusion-logic tree database — including a source comment flagging a possible subtle bug in the always-overwrite exclusion behavior, evidence Kimi actually read the code rather than asserting from the README; `praxish.js`; `planner.js`; and `swaygent.js`, a hybrid decision module combining Praxish's practices with Ensemble-like influence/volition rules). **Claude additionally cites a second project, `ShiJbey/RePraxis`** (C#, MIT, v1.4.0 Nov 2024, a Unity package) — Kimi's report does not mention RePraxis at all, neither confirming nor denying it as a separate project. Net effect: Praxish (`mkremins/praxish`) is now confirmed by two independent audits as real, actively developed, and MIT-licensed — treat this as the primary Versu-reconstruction citation going forward. Gemini's "Wyclef" remains uncorroborated by either other report and should be treated as unverified/likely a lesser-known or miscited project unless checked directly. Whether RePraxis is a genuinely separate, additional reconstruction (Claude's claim) is still open — worth a two-minute check of `github.com/ShiJbey/RePraxis` directly if it matters to a future design decision, but does not affect the primary recommendation (study Praxish first).

### City of Gangsters

- **Architecture (agreed by all three):** Robert Zubek, Ian Horswill, Ethan Robison, Matthew Viglione. Shipped commercially (SomaSim, Q3 2021, still listed on Steam/Epic per Kimi's direct check). A labeled directed graph of characters with relationship edges carrying a type, scalar valence, and a **history** of individual deltas — each history element can itself name an actor/target/explanation, letting a nominally dyadic edge encode n-ary provenance-like context (Kimi's cited example: "Alice dislikes Bob because Bob harmed Alice's brother Chris"). Both Claude and Kimi cite the same two papers (Zubek/Horswill/Robison/Viglione's AIIDE 2021 technical paper, and a companion design-rationale paper by Robison/Viglione/Zubek/Horswill, "AI Design Lessons for Social Modeling at Scale") and agree the propagation logic is **BotL** (Ian Horswill's game-oriented logic-programming language), deliberately capped at **second-order** propagation (A→B→C, no further) for legibility and performance, achieving real-time performance via static memory allocation and no garbage-collection after instantiation.
- **New from Kimi, not in either prior report — a materially important correction of the population-size claim:** Kimi directly parsed a bundled ~40MB real game save file (via the MicroCoG demo, see below) and found **46,397 total serialized entities, 13,241 person entities (11,196 apparently living), and 350,200 relationship edges** — dwarfing the oft-cited "~1,200 active NPCs" figure. Kimi's resolution: **the two numbers aren't a contradiction** — the paper's "~1,200" refers specifically to *active, interactively-relevant* NPCs, while the save also serializes a much larger background genealogy/acquaintance graph (dominated by extended-family edge types: 139,622 cousin edges, 54,500 nibling edges, 39,358 sibling edges). This is a real, evidence-based nuance neither Gemini nor Claude's reports surfaced — worth using "~1,200 *active*, tens of thousands *total*" as the more accurate framing in any future Chronicle design document, not just "~1,200 NPCs."
- **Also new from Kimi: the social-history layer is comparatively sparse relative to the static graph** — only 1,906 social-history items across 19 distinct action types in the parsed save (top types: vandalism 374, violence 339, burglary 325, gang trespass 270). Kimi's explicit design lesson for Chronicle: "do not create a rumor object for every NPC about every event; create claims only when perception or communication rules say they matter" — a concrete architectural recommendation the other two reports don't make this specifically.
- **Availability — resolved and materially upgraded by Kimi.** Both Gemini and Claude found the game's own source closed. Claude found `github.com/ianhorswill/BotL` (full C# source, no license file, ~123 commits) and flagged a related demo, `github.com/ianhorswill/MicroCoG`, whose license "could not be independently confirmed." **Kimi resolves this open item directly**: MicroCoG is **confirmed MIT-licensed**, and — going well beyond a license check — Kimi actually loaded and parsed MicroCoG's bundled real 40MB save file and read its `SocialInference.cs` source, quoting the exact predicate-based reaction-rule shape (`ReactionToAction`, scored via summed `ReactionBuff` values keyed by relationship class/type) as "the clearest implementation template for Chronicle propagation" in the whole cluster. This upgrades MicroCoG from "flagged as unconfirmed" (Claude's state) to "confirmed MIT, directly inspectable, best practical implementation-level proxy in the entire five-system study" (Kimi's verdict) — a genuine resolution, not just a repeated claim.

## Kimi's proposed architecture (new, not in Gemini's or Claude's reports)

Kimi goes beyond inventorying the five systems and proposes a concrete
hybrid Chronicle architecture, worth recording even though evaluating it is
a design decision, not a research finding:

> An Ensemble-like schema and scoring layer (author-defined social
> categories, arbitrary-role volition/trigger rules) + a Versu-like
> practice layer (concurrent, role-agnostic social situations offering
> affordances rather than controlling agents, with speculative
> actual-consequence scoring) + a City-of-Gangsters/MicroCoG-like sparse
> relationship graph (second-order-capped propagation, event-triggered not
> continuous, explanation-bearing history elements) + **a new first-class
> epistemic claim graph** (the piece none of the five systems have) that
> separately tracks: an objective event log → per-agent private beliefs
> with source/confidence/provenance → communicated claims that can mutate
> in transit (with named mutation types: exaggeration, misattribution,
> detail loss, motive inference, faction framing, self-serving distortion)
> → evaluations/grudges/obligations as first-class objects with causes and
> settlement conditions → practice-mediated behavior → new objective
> events.

Kimi also proposes a concrete four-tier scaling strategy (Hot/Warm/Cold/
Archive simulation buckets keyed by proximity to the player and claim
salience) directly modeled on City of Gangsters' own sparse-graph
discipline, and a specific debugging-tooling wishlist (claim lineage
visualization, "why does NPC X believe this," rumor-diff comparison between
two NPCs, deterministic replay) modeled on Versu's own inspector tooling.
This is design-stage material, not a research verdict — flagged here for
whoever picks up the actual Chronicle epistemic-layer design, not adopted
as a conclusion of this synthesis.

## Inspectability verdict (all three reports' findings merged; Kimi's independent corroboration used to break remaining ties)

**Worth a deep line-by-line source study (real code exists to read):**
1. **MicroCoG** (new top entry, per Kimi's resolution) — MIT-licensed, C#, ships with a real 40MB save file, the clearest concrete implementation template for belief/relationship propagation in the whole cluster.
2. **City of Gangsters / BotL** — full C# engine, source-available, no license (read, don't copy). The unique proven-at-scale precedent (tens of thousands of total NPCs in a real save, ~1,200 of them active).
3. **Ensemble** — BSD-4-clause (the one cleanly-reusable license in the cluster), confirmed stale/unmaintained by two independent checks (a cited 2024 postmortem and Kimi's own repo-metadata pull) but still the best-documented CiF-family codebase for line-by-line study.
4. **CiF / Prom Week** — ActionScript source present in-repo, no license (read, don't copy), confirmed by two independent audits — Gemini's "discard, Flash is dead" framing is resolved as incorrect for *inspection* purposes (still correct that the Flash *runtime* itself is impractical to actually run).
5. **Praxish** (`mkremins/praxish`) — MIT-licensed, actively developed into 2026 per Kimi's direct check, confirmed by two independent reports as the primary Versu-reconstruction to study for a "one fact shifts many NPCs' obligations" mechanic.

**Citable-but-not-inspectable:** **Versu** itself — proprietary, cancelled, no source ever released, playable today only "on aging iPads." Cite the IEEE TCIAIG 2014 paper and Evans's DEON 2010 paper directly; study the ideas through Praxish instead.

## What neither engine offers Chronicle (all three reports agree)

Per-belief provenance and in-transit rumor mutation — Chronicle's two
actual headline mechanics — have **no analog in any of these five
systems**. Treat this whole cluster as precedent for the *third-party
inference substrate* (how an uninvolved NPC reasons about facts, how
grudges/obligations gate action space, how to scale symbolic inference to
a large NPC population) — not for the provenance/rumor-mutation layer,
which remains uniquely Talk of the Town's contribution (see the dedicated
verification file).

## Remaining open items for a future direct check

- Whether `ShiJbey/RePraxis` is a genuinely separate, additional Versu
  reconstruction (Claude's claim, uncorroborated by Kimi or Gemini) or a
  variant/rename of the same project as `mkremins/praxish` — low priority,
  since Praxish alone is now sufficiently confirmed as the primary study
  target regardless of the answer.
- `db.js`'s flagged possible bug in Praxish's exclusion-operator
  implementation (Kimi found the source's own comment questioning whether
  "always overwrite" on `!` is correct) — worth reading directly before
  treating Praxish's exclusion semantics as a faithful Versu reconstruction
  rather than at face value.
