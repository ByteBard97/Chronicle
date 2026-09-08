# Talk of the Town: Primary-Source Verification (2026-09-06)

Chronicle's vision document (`docs/vision-v2.2.md` §3, Bet 1) states, as its
central mitigation for the project's biggest bet: "the epistemology is
built on the most-validated data model in the academic literature (Talk of
the Town's belief facets, evidence chains, predecessor lineage)." No
dedicated primary-source research on Talk of the Town existed anywhere in
this project before this file. This verifies the claim directly against
James Ryan's actual source code and papers — cloned/downloaded and read
directly, not summarized by a research agent — matching this project's
established practice on HAMLET and IBSEN (both verified by reading real
source, which caught a real error in HAMLET's case).

**Sources read directly, all confirmed real:**
- Repository: `github.com/james-owen-ryan/talktown` (cloned, MIT-licensed)
- Ryan & Mateas, "Simulating Character Knowledge Phenomena in *Talk of the
  Town*" (2017 book chapter draft, 18pp) — read in full
- Ryan, "Curating Simulated Storyworlds" (PhD dissertation, UC Santa Cruz,
  2018, 815pp) — table of contents and chapter structure confirmed; Chapter
  9 ("Talk of the Town," pp. 371-460) and Chapter 10 ("Case Study: *Bad
  News*," pp. 461-539) are the directly relevant chapters
- Ryan, Mateas & Wardrip-Fruin, "Toward Characters Who Observe, Tell,
  Misremember, and Lie" (2015/2016) and "A Simple Method for Evolving Large
  Character Social Networks" (2016) — downloaded, available for further
  reading if needed but not required to answer the questions below (the
  2017 chapter supersedes/condenses their content on the knowledge system
  specifically)

## 1. Belief/knowledge representation

**"Belief facet" is a real, literal term** — confirmed exactly as
Chronicle's vision doc uses it. Per the 2017 paper §3.4: a character's
composite knowledge is structured as an *ontology* of **mental models**,
one per person/place they know about. Each mental model is a list of
**belief facets**, one per attribute (hair color, workplace, marital
status, etc.). Each individual belief facet carries these fields (quoted
directly from the paper):

- **Value** — the belief content itself (e.g., the string `brown`)
- **Mental Model** — if the value resolves to another entity, a pointer to
  that entity's own mental model (this is how "character believes person X
  works at business Y" links to a separate belief-object about Y)
- **Predecessor** — "the belief facet that the owner previously held, if
  any... a given chain of predecessors represents a perfect history of an
  NPC's beliefs about some attribute" — **this is the literal source of
  Chronicle's "predecessor lineage" phrase**, and it means exactly what it
  sounds like: one character's own belief history over time, superseded
  facet by superseded facet.
- **Parents** — "if this knowledge originated in information from other
  characters, this will point to the belief facets of those characters
  that spawned this current facet... allows the system to trace the
  history and trajectory of any piece of information" — **this is the
  actual cross-character provenance/lineage mechanism**, distinct from
  Predecessor (which is same-owner, over-time; Parents is
  cross-character, at-transmission).
- **Evidence** — "a list of the pieces of evidence by which the owner of
  this facet formed and continues to substantiate it," each evidence piece
  itself carrying Source, Location, Time, and Strength metadata
- **Strength** — sum of the strength of all supporting evidence
- **Accuracy** — whether the belief matches current ground truth

**Verdict on this part of the citation: accurate, and precise.** "Belief
facets" and "predecessor" are both Ryan's own exact terms. "Evidence
chains" in the vision doc is a reasonable paraphrase of two separate real
fields (Parents + Evidence) rather than one single named field — worth
knowing if anyone designs against this literally, since Chronicle's own
implementation will need to decide whether to keep these as two fields
(as Ryan does) or fold them into one, but it is not a misrepresentation.

## 2. Rumor mutation/distortion in transit

**Confirmed, and the mechanism is richer than a simple "each retelling
adds noise" model.** The paper's evidence typology (§3.5, "eleven types
across five categories" per its own count — this verification directly
confirmed nine of the eleven; see caveat below) includes, under **How
knowledge originates**:

- **Reflection** — inherent self-knowledge (no computation)
- **Observation** — direct perception, gated by salience
- **Transference** — "if one entity reminds a character of another entity
  (determined by feature overlap between his or her respective mental
  models of them), he or she may unconsciously copy beliefs about one to
  the mental model of the other" — a real, distinct **misattribution**
  mechanism (confusing two similar people/places), a form of content
  becoming wrong that has no DF equivalent
- **Confabulation** — "a character *unintentionally* concocts new
  knowledge about some entity... probabilistically, according to the
  distribution of that feature type in the town" (e.g., a confabulated
  hair-color belief has the same odds of being `black` as the town's real
  hair-color distribution) — invented false knowledge, not decay
- **Lie** — "an NPC *intentionally* conveys information to another
  character that she herself does not believe... no existing knowledge is
  propagated by the lie" — the system tracks internally that it's a lie
  (for later analysis/visualization) but the recipient treats it exactly
  like a truthful statement; the paper also documents a specific **false
  flag** tactic (lying about who told you the lie) as a deliberately
  supported player strategy in the *Talk of the Town* game design
- **Implant** — efficiency shortcut, plausible starting knowledge seeded
  directly into minds at the end of world-generation

Under **How knowledge reinforces itself**: **Declaration** — retelling a
belief slightly strengthens the teller's own conviction in it (cited to a
real psych source, Wilson et al. 1985 on retelling-and-recall), meaning "an
NPC who frequently tells the same lie might come to actually believe it."

Under **How knowledge deteriorates**: **Mutation** — "as an
operationalization of memory fallibility, knowledge may mutate over time,"
governed by a hand-authored **belief mutation graph** giving explicit
probabilities for a facet's value flipping to specific other values (the
paper's own example: a `black`-hair belief has a 0.75 chance of drifting to
`brown`, 0.15 to `red`, 0.07 to `gray`, 0.03 to `white`). **Important
nuance**: mutation is a *per-owner*, over-time memory-fallibility event —
it happens to a belief a character already holds, independent of the act
of telling it to someone else — not a per-hop "retelling introduces a
random change" event the way a literal game-of-telephone works. Since
propagation (§3.7) just copies a facet's *current* value from teller to
listener, the net effect across the social network is the same
end-to-end — information really does drift into being factually wrong as
it ages and spreads — but the mechanism is "your own memory of the fact
degrades over time" plus "you can misattribute similar entities to each
other" plus "someone lies to you," rather than "the message itself gets
garbled at each hop."

Under **How knowledge terminates**: **Forgetting** — belief facets can be
dropped entirely, gated by the character's memory attribute and the
facet's salience.

**Verdict on this part of the citation: strongly confirmed, arguably an
understatement.** Chronicle's own research (already verified for this
project) found Dwarf Fortress's rumor system *explicitly refuses* to
distort content in transit — the only sanctioned falsehood in DF is
identity misattribution for secret-identity holders. Talk of the Town's
Mutation + Transference + Confabulation + Lie give it four independent,
general-purpose mechanisms for content becoming actively wrong, all with
full source/location/time/strength provenance attached and both a
same-owner history (Predecessor) and cross-character lineage (Parents)
preserved throughout. The claim that it is "the only system that
implements rumor distortion with provenance" holds up well against the
primary source.

**Honest completeness caveat**: the paper states its evidence typology has
"eleven types across five categories," but the pages read directly show
four named categories (originates/reinforces/deteriorates/terminates)
totaling nine explicitly-detailed types (Reflection, Observation,
Transference, Confabulation, Lie, Implant, Declaration, Mutation,
Forgetting). Section 3.6's own text also references **Statement** and
**Eavesdropping** as evidence-metadata categories in passing, which are
very likely two of the missing types (statement being the "ordinary true
retelling" complement to Lie) — this verification did not track down the
fifth category or pin down the exact missing two with full certainty.
Worth a five-minute follow-up read of the paper's full §3.5 if anyone
needs the complete eleven-type/five-category enumeration for a design
document; the core mechanics above are unaffected either way.

## 3. Observation vs. hearsay

Confirmed as meaningfully distinct: each evidence piece carries a
**Source** field (which character delivered it, for statements/lies/
eavesdropping — blank for direct Observation), and evidence **Strength**
is type-dependent ("a statement is weaker than an observation") and, for
statement/lie/eavesdropping evidence specifically, additionally scaled by
"the affinity its owner has for its source and the strength of that
source's own belief at the time of propagation" — i.e., a belief acquired
secondhand from someone you like and who was themselves confident is
stronger evidence than one from someone you distrust or who was
uncertain. This is a real, working confidence/certainty/source-attribution
model, not a flat true/false or witnessed/told binary.

## 4. Decay

Confirmed via two independent mechanisms: **evidence Strength decays over
time** on a per-evidence-type basis (built into the base strength model),
and **Forgetting** is a distinct, explicit termination mechanism (§3.5,
gated by the owning character's memory attribute and the facet's
salience — "the probability of memory deterioration decreases as these
saliences grow larger," per §3.6).

## 5. What *Bad News* actually is

**Confirmed via the dissertation's own Chapter 10 ("Case Study: *Bad
News*," pp. 461-539) and its List of Figures**: *Bad News* is a real,
**repeatedly-performed live installation/theatrical experience** — figure
captions describe performances at the San Francisco Museum of Modern Art,
a Slamdance DIG showcase in Los Angeles (Dec. 2016), and a CAVE-like
physical-space variant called *Cattive Notizie* (2017). Per the 2017
paper: "we have actually already used this framework in a completed
mixed-reality experience called *Bad News*... over the course of
performing this piece dozens of times." Critically, one figure shows *"a
web chat between the Bad News wizard (me, i.e. Ryan) and actor (Ben
Samuel)"* — **Bad News is a Wizard-of-Oz-style experience**: the Talk of
the Town simulation generates the storyworld and its knowledge/belief
content offline, but a live human actor performs an NPC in real time,
fed lines by a human "wizard" operator, in front of a live audience/
participant. It is not an autonomously AI-narrated video game.

**The standalone, playable *Talk of the Town* 2D video game, by contrast,
appears to have never shipped as a finished consumer product.** The 2017
paper says outright: "the simulation is fully implemented; the gameplay
layer is currently being developed," and the dissertation's own List of
Figures caption for its screenshots calls it "the videogame prototype
*Talk of the Town* (2015)" — prototype, not release. So: the underlying
belief/knowledge simulation is real, rigorously implemented, and
validated through dozens of actual live performances (via *Bad News*), but
if anyone goes looking for a shippable, playable *Talk of the Town* game
to study end-to-end, it does not exist in that form.

## 6. License and reusability — the important caveat

**The GitHub repo is real, substantial, and MIT-licensed** (confirmed
`LICENSE` file, "Copyright (c) 2016 James Ryan"). It is not an empty
placeholder like HAMLET's repo. It contains a genuinely large simulation
(`person.py` alone is 107KB) covering town generation, character routines,
births/deaths/marriages/divorces, businesses, occupations, and a social
**salience** system (how much one character's presence weighs on
another's attention/memory).

**But the actual belief/mental-model/knowledge-phenomena system described
above — the entire subject of this verification — is not in the public
repository.** Direct evidence, found by reading the code rather than
trusting the README or license alone:

- `config/misc_character_config.py`'s own comment, verbatim: *"Memory
  parameters; memory is important in the full Talk of the Town framework,
  since it affects the likelihood of misremembering knowledge — **that's
  been taken out here**, but I can imagine memory still being useful in
  some way, so I'm keeping that here."*
- `person.py:1340` references `self.mind.mental_models` — but `mind.py`'s
  actual `Mind` class never defines or initializes a `mental_models`
  attribute anywhere in the file; it only implements a memory-*capability*
  scalar (a heritable floating-point trait), not the belief/mental-model
  system itself. This is a dangling reference confirming the real module
  was stripped out before the repo was made public.
- No `Belief`, `BeliefFacet`, `MentalModel`, or `PersonMentalModel` class
  exists anywhere in the repository (`grep`-confirmed).
- No gossip/propagation code exists either (`grep` for "gossip,"
  "hearsay," "misremember," "observe," "lie" as a verb all come up empty
  except the one config-comment above).

**This directly parallels the HAMLET lesson this project already
learned**: an MIT license and a substantial-looking repo do not mean the
specific subsystem you actually want is present in the code. What's public
here is the town/person/relationship/social-network substrate (matching
the scope of the "simple method for evolving large character social
networks" paper) — genuinely useful on its own terms — but not the
knowledge/belief/mutation engine that is the entire reason this project
cited Talk of the Town in the first place. **Anyone wanting to study the
real belief-mutation algorithm has to work from the papers (fully
sufficient — the 2017 chapter documents the mechanism in complete,
implementable detail, down to the exact pseudocode in Listings 1-2) rather
than from working source.**

## Final verdict

**Chronicle's citation is accurate and well-founded.** "Belief facets" and
"predecessor" are Ryan's own literal terms, used correctly. "Evidence
chains" is a fair paraphrase of the real Parents + Evidence fields. The
claim that Talk of the Town is the strongest available academic precedent
for belief distortion-with-provenance holds up directly against the
primary source, and if anything the real mechanism (four independent
distortion pathways — Mutation, Transference, Confabulation, Lie — each
fully evidenced with source/location/time/strength metadata, plus a
dual-lineage model of Predecessor-over-time and Parents-across-characters)
is richer than the vision doc's short summary suggests.

**The one correction to make going forward**: don't expect to find a
working reference implementation of the belief system in the public repo.
The design is fully specified in the papers (particularly the 2017 chapter
in this file's source list, which includes runnable pseudocode) but the
actual code implementing it was deliberately excluded from what Ryan
published on GitHub. Any Chronicle design work that wants to "check
against the real implementation" needs to work from the papers, not from
cloning and reading `talktown`'s source.
