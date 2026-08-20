# Source papers

The eight-plus research reports (`docs/research/01-10`) already distilled
these to implementable specificity — you don't need to re-read a paper to
implement the mechanism it describes. This directory exists for the
handful worth having locally because schema and rule-authoring work will
return to them repeatedly, not read them once.

Format: plain Markdown, converted from the original PDFs (`pdftotext
-layout` extraction, cleaned up by hand/agent for column-interleaving
artifacts and hyphenation breaks — full-text transcriptions, not
summaries). Markdown instead of PDF for git-friendliness (diffable,
greppable, no binary bloat) and consistency with the rest of `docs/`.
Each file's frontmatter names the original PDF and full citation. The
source PDFs themselves were open-access (AAAI/AIIDE proceedings, or
hosted directly by the author) and are not retained in the repo after
conversion — if you need the original typeset PDF, the links below still
work.

## Converted

| File | Citation | Why we care |
|---|---|---|
| [`ryan-et-al-2015-observe-tell-misremember-lie.md`](ryan-et-al-2015-observe-tell-misremember-lie.md) | James Ryan, Adam Summerville, Michael Mateas, Noah Wardrip-Fruin, "Toward Characters Who Observe, Tell, Misremember, and Lie," AIIDE 2015. [PDF](https://ojs.aaai.org/index.php/AIIDE/article/download/12825/12672) | The nine-type evidence typology and mutation operations (omission, transfer, exaggeration, confabulation, category-consistent substitution) — direct source for `chronicle`'s belief-mutation rules. Report 02/08's most load-bearing single citation. |
| [`zubek-et-al-2021-city-of-gangsters-social-modeling.md`](zubek-et-al-2021-city-of-gangsters-social-modeling.md) | Robert Zubek, Ian Horswill, Ethan Robison, Matthew Viglione, "Social Modeling via Logic Programming in City of Gangsters," AIIDE 2021. [PDF](https://robert.zubek.net/publications/social-modeling-via-logic-programming-in-city-of-gangsters.pdf) | Closest shipped scale precedent (~1,200 NPCs, sparse directed graph, no complete matrix) — the primary engineering source for ADR-0006's sparse-graph rule. (Note: the paper credits "Ethan Robison," not "Emily Robison" as reports 02/08 cited — the paper is the more trustworthy source.) |
| [`robison-et-al-2021-ai-design-lessons.md`](robison-et-al-2021-ai-design-lessons.md) | Emily Robison, Matthew Viglione, Robert Zubek, Ian Horswill, "AI Design Lessons for Social Modeling at Scale," AIIDE 2021. [PDF](https://robert.zubek.net/publications/ai-design-lessons-for-social-modeling-at-scale.pdf) | Companion design-lessons paper: legibility, reversible actions, few/thematic norms, fungible individuals. The "more than twenty rules is too many" ceiling — the single best design constraint any report surfaced, per report 08. |
| [`kreminski-2023-gossamer.md`](kreminski-2023-gossamer.md) | Max Kreminski, "Toward Better Gossip Simulation in Emergent Narrative Systems," IEEE Conference on Games 2023. [PDF](https://mkremins.github.io/publications/Gossamer_CoG2023.pdf) | The witness/reflection/propagation/decay gossip loop — first item in report 08's "build first" list, and load-bearing for the build order in `docs/architecture.md`. Citation checked (legitimate peer-reviewed venue) when this report was filed. |

## Not converted — link only

| Citation | Link | Why link-only |
|---|---|---|
| James Ryan and Michael Mateas, "Simulating Character Knowledge Phenomena in Talk of the Town," *Game AI Pro 3*, ch. 37, CRC Press, 2017 | http://www.gameaipro.com/ (chapter listing) ; publisher page: https://www.taylorfrancis.com/chapters/edit/10.4324/9781315151700-37 | The belief-facet data model `chronicle`'s schema is copying almost verbatim (ADR-0006). gameaipro.com returns a 403 to scripted requests (bot-protected, not necessarily paywalled) — fetch manually in a browser if you want it converted too. |
| James Ryan, *Curating Simulated Storyworlds*, PhD dissertation, UC Santa Cruz, 2018 | https://escholarship.org/uc/item/1340j5h2 | eScholarship's CDN returns a WAF challenge to scripted requests. Long (dissertation-length); the story-sifting chapters matter once the narrative/query layer (ADR-0006 layer 5) gets built, not before — fetch then if still wanted. |

## Repos worth cloning separately, not vendoring here

Neighborly, Minerva, and Drolta (Shi Johnson-Bey) are MIT-licensed Python
you may lift code or patterns from directly, which makes them more useful
as a live clone than a static paper:

- `github.com/ShiJbey/Neighborly`
- Minerva and Drolta — see links in `docs/research/08-social-sim-literature-v2.md` §2.7/§2.12

Not cloned into this repo now — do it if/when the narrative/query layer
(ADR-0006 layer 5) is actually being built and a specific pattern is
needed, rather than speculatively.
