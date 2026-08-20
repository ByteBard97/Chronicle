# Source papers

The eight research reports (`docs/research/01-09`) already distilled these
to implementable specificity — you don't need to re-read a paper to
implement the mechanism it describes. This directory exists for the
handful that are worth having locally because schema and rule-authoring
work will return to them repeatedly, not read them once. Everything else
in the reports' reference lists is fine to leave as a citation.

Only committed PDFs that are clearly open-access (AAAI/AIIDE proceedings,
or hosted directly by the author on their own site). Two sources below
are link-only — see "Not downloaded" — because scripted access was
blocked; fetch manually in a browser if wanted.

## Downloaded

| File | Citation | Why we care |
|---|---|---|
| `ryan-et-al-2015-observe-tell-misremember-lie.pdf` | James Ryan, Adam Summerville, Michael Mateas, Noah Wardrip-Fruin, "Toward Characters Who Observe, Tell, Misremember, and Lie," AIIDE 2015 | The nine-type evidence typology and mutation operations (omission, transfer, exaggeration, confabulation, category-consistent substitution) — direct source for `chronicle`'s belief-mutation rules. Report 02/08's most load-bearing single citation. |
| `zubek-et-al-2021-city-of-gangsters-social-modeling.pdf` | Robert Zubek, Ian Horswill, Emily Robison, Matthew Viglione, "Social Modeling via Logic Programming in City of Gangsters," AIIDE 2021 | Closest shipped scale precedent (~1,200 NPCs, sparse directed graph, no complete matrix) — the primary engineering source for ADR-0006's sparse-graph rule. |
| `robison-et-al-2021-ai-design-lessons.pdf` | Emily Robison, Matthew Viglione, Robert Zubek, Ian Horswill, "AI Design Lessons for Social Modeling at Scale," AIIDE 2021 | Companion design-lessons paper: legibility, reversible actions, few/thematic norms, fungible individuals. The "more than twenty rules is too many" ceiling — the single best design constraint any report surfaced, per report 08. |
| `kreminski-2023-gossamer.pdf` | Max Kreminski, "Toward Better Gossip Simulation in Emergent Narrative Systems," IEEE Conference on Games 2023 | The witness/reflection/propagation/decay gossip loop — first item in report 08's "build first" list, and load-bearing for the build order in `docs/architecture.md`. Citation checked (legitimate peer-reviewed venue) when this report was filed. |

## Not downloaded — link only

| Citation | Link | Why link-only |
|---|---|---|
| James Ryan and Michael Mateas, "Simulating Character Knowledge Phenomena in Talk of the Town," *Game AI Pro 3*, ch. 37, CRC Press, 2017 | http://www.gameaipro.com/ (chapter listing) ; publisher page: https://www.taylorfrancis.com/chapters/edit/10.4324/9781315151700-37 | The belief-facet data model `chronicle`'s schema is copying almost verbatim (ADR-0006). gameaipro.com returns a 403 to scripted requests (bot-protected, not necessarily paywalled) — fetch manually in a browser if you want the PDF locally. |
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
