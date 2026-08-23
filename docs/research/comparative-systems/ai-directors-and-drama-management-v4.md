---
date: 2026-08-23
sources:
  - "GM Agent Field Survey.md"
topic: "AI drama managers / director architectures — fourth independent pass"
status: filed
---

# AI Directors and Drama Management, v4

Fourth independent pass on the same ground as
[ai-directors-and-drama-management.md](ai-directors-and-drama-management.md),
[-v2](ai-directors-and-drama-management-v2.md), and
[-v3](ai-directors-and-drama-management-v3.md). No Skyrim-specific
companion arrived with this report (unlike the 19/20/21 pairing), so this
file stands alone. Despite being the fourth pass over the same field,
this report introduces one entirely new commercial system not covered by
any prior pass — **Friends & Fables / ACE-1** — whose redesign converges
independently on Chronicle's belief-provenance model, plus a primary
Todd Howard quote on Radiant Story's original design intent and two
trust-failure modes absent from every prior filing's taxonomy.

## What's genuinely new here (not in passes 1–3)

- **[BUILD-ON — the single most valuable new item] Friends & Fables'
  public, versioned redesign (Franz v1 → ACE-1) is the closest commercial
  analog yet found to Chronicle's belief-with-provenance model, arrived
  at independently through production pain.** Franz v1 ("the first AI
  chat bot to manage game state") generated a response, then updated
  state *from* the response — and failed exactly as predicted: memory
  drift in long campaigns, a creature narrated "both dead and alive" with
  no clean recovery, custom instructions that could flavor text but
  "cannot impose mechanics, dice rolls, XP... or directly change game
  state." The fix, ACE-1 ("Agentic Campaign Engine"), explicitly
  **separates the AI Game Master (the face) from the campaign engine (the
  truth)**, reworking memory from hierarchical summarization (which
  "compressed away" important details) into **atomic memory units**
  ("Neela offered 50 gold for the safe transport of her cat") ranked by
  type, recency, and relevance, plus structured relationship scores and a
  **"View Context" feature** letting players inspect exactly what the GM
  could see. Their own diagnosis is the single most quotable line in this
  entire four-report series: **"When an LLM lacks a source of truth, it's
  more prone to making things up."** Two transferable lessons, stated
  verbatim by the source: memory representation is a *correctness*
  feature (atomic, provenance-carrying facts beat compressed summaries
  whenever downstream decisions depend on them — precisely Chronicle's
  belief-facet model), and context transparency is a *trust* feature (a
  context inspector converts "the GM is cheating" suspicions into
  debuggable inclusion bugs). **If Chronicle ever exposes GM-generated
  content to players, an equivalent to "View Context" — showing exactly
  which belief/rumor/grudge a quest cites — is the concrete, shipped-
  precedent way to earn that trust.**
- **[BUILD-ON] Todd Howard's own 2011 description of Radiant Story's
  design intent is now on file, and it's a precise primary-source
  statement of the exact "generation is template selection + alias
  binding" ceiling already established in reports 19–21.** Quoted
  directly: "Traditionally in an assassination quest, we would pick
  someone of interest... Now there is a template for an assassination
  mission and the game can conditionalize all the roles — where it
  happens, under what conditions... who wants someone assassinated, and
  who they want assassinated." The promised input signal was real game
  history (where you've been, who you've killed, your skills, your
  friends and enemies) plus contingency mechanics (a murdered shopkeeper's
  sister inheriting his quest role) and dungeon targets biased toward
  unexplored places. **What actually shipped was the conservative core of
  that promise** — worth citing this quote specifically if an ADR ever
  needs to state precisely what Bethesda's own team intended vs. what the
  engine ultimately allowed.
- **[RISK — new trust-failure mode] "Promised policy not implemented" is
  a distinct failure mode from every prior filing's taxonomy.** Left 4
  Dead's Director has a stated design policy of punishing players who
  rush ahead of the group — but community post-mortems document that this
  policy "massively fails" in practice; the mechanism doesn't actually
  implement the contract Valve's own documentation implies. **This is
  different from an invisible decisive variable (RimWorld) or visible
  outcome substitution (Mimesis)**: it's a director whose *stated,
  legible* rules don't match its *actual* behavior — a documentation/
  implementation gap, not a design flaw. Any future Chronicle GM that
  publishes self-limits (per the third pass's "published self-limits"
  recommendation) must verify those limits are actually enforced, not
  merely asserted — an aspirational fairness doc is worse than no
  fairness doc if it's wrong.
- **[RISK — new trust-failure mode] "Simulation illegibility" — deep
  systems players can't read produce noise, not stories — is Wildermyth's
  own documented lesson from a discarded feature, not previously filed.**
  The Wildermyth team built and *threw away* a more simulationist overland
  map (populations that grew and shrank, dynamic threats) because "all
  those systems made it difficult for players to understand where to go
  and what to do." Their own account: "simulation depth that players
  cannot read is wasted depth." **This is a direct, concrete caution for
  Chronicle specifically** — the project's own architecture bets heavily
  on a rich, sparse social-simulation graph; this is documented evidence
  from a shipped, well-received game that depth invested where the
  presentation layer can't surface it is depth wasted, and the fix
  (concentrate depth where it's presentation-legible; discard or hide the
  rest) is as important a design constraint as the "provenance for free"
  thesis Chronicle already commits to.
- **[BUILD-ON] RimWorld's raid-point formula is now on file with exact
  numbers, sharper than the general characterization in prior passes.**
  `(Wealth Points + Pawn Points) × Difficulty × Starting Factor ×
  Adaptation Factor`, where Storyteller Wealth is linearly interpolated
  (0 points at ≤14k wealth, 4,200 points at 1M), pawns contribute 15–140
  points each scaled by wealth, and minimum raid-point thresholds gate
  raid *types* (mechanoids at 300, sieges at 500, sappers at 700) — a
  legibility feature disguised as balance, since the threat ladder is
  stable enough to be learned. The community wealth-management exploit
  list is now concrete: parking items in off-map caravans (they don't
  count toward wealth), letting weapons deteriorate to 10% of value at no
  functional loss, deliberately capping "progress" wealth. **The general
  lesson (already filed) stands, now with citable specifics**: any input
  a future Chronicle director trusts as ground truth, the player can and
  will launder, unless that input is either fully visible-and-honest or
  literally manipulation-proof by construction (provenance-tracked
  beliefs, as opposed to a launderable scalar).
- **[BUILD-ON] Sharma et al.'s Anchorhead user study is a positive,
  quantified counterpoint to the DODM failure record already filed** (the
  Nelson & Mateas transfer failure, filed in pass 2). N=20 study: a
  re-implemented drama manager over Anchorhead produced a **~12.5%
  average subjective improvement** with every subject noticing the
  difference and preferring the managed version. The caveat matters as
  much as the result: hints became "frustrating" precisely when players
  could not act on them — an early, specific warning that **interventions
  must be actionable in-world**, not just narratively appropriate. This
  tempers the "invest in intervention vocabulary before selection
  intelligence" lesson (filed in pass 3): a rich vocabulary still fails
  if the player has no path to act on what the GM surfaces.
- **[BUILD-ON] Roberts & Isbell's 2007/2008 desiderata for experience
  managers is a complete, citable requirements checklist**, not
  previously filed as a checklist: speed, NPC coordination, replayability,
  authorial control, player autonomy, ease of authoring, adaptability to
  player traits, amenability to theoretical analysis, **subtlety of the
  DM's interventions**, and measurability of produced experience quality.
  "Subtlety" is explicitly their term for the no-visible-cheating rule
  already central to Chronicle's doctrine — worth citing this checklist
  wholesale if a future GM-layer ADR needs a starting requirements list.
- **[DESIGN-INPUT] Two more concrete 2023–2026 LLM-era data points, both
  new.** **1001 Nights** uses a **symbolic whitelist** mechanism distinct
  from the generate-and-verify pipelines already filed: weapon keywords
  (`sword, shield, dagger`, etc.) detected in LLM-generated text
  *materialize* as actual battle equipment — narrative output is
  continuously constrained and given mechanical teeth by a non-neural
  layer, without a full validate-then-apply pipeline. **The
  Static-vs-Agentic GM study (ChatRPG, N=12)** found an agentic GM with
  separate **narrator and archivist agents** beat a prompt-only GM on
  perceived intelligence, flow, and immersion — direct evidence that
  splitting statekeeping from narration measurably helps even in
  text-only domains, not just in principle. Also newly named: Gallotta et
  al.'s survey identifies LLM **"over-compliance"** as a specific failure
  mode — an LLM that bends the narrative to please the player "may result
  in the game veering drastically from the intended narrative, potentially
  causing irreparable disruptions" — a distinct risk from hallucination or
  drift, worth its own name if Chronicle ever tunes an LLM-framing layer's
  compliance/pushback balance.
- **[RISK] AI Dungeon's own successor supplies the sharpest one-line
  statement of the "infinite accommodation" failure yet filed.** Latitude
  built Voyage explicitly because in AI Dungeon "nothing you do ever
  really matters, because the story bends around you no matter what you
  try or how badly you fail" — fixed with "real dice, skill checks, hit
  points, and permanent character death, so risk and failure carry actual
  weight." Quotable synthesis: **"a director that accommodates everything
  is a director that means nothing."** Also newly filed: AI Dungeon's
  2021 moderation/privacy episode (private stories human-reviewed under
  filtering requirements) "permanently damaged trust" for some users —
  a reminder that **trust in a director is not only about in-fiction
  fairness; it extends to the platform's honesty about what it does with
  play data.** For a local mod this maps to a simple rule: what sim state
  is read and what (if anything) is sent to an external LLM API should be
  part of the player-visible contract, not just the in-fiction fairness
  doctrine.
- **[DESIGN-INPUT] The report's closing synthesis names the gap Chronicle
  would occupy more starkly than any prior pass**: "the upper-right
  quadrant — deep state grounding *and* real dramatic control — is empty
  in the entire surveyed record." Every system reviewed trades one for
  the other (Shadows of Doubt has deep grounding, no recognition/framing
  layer above the sim; Façade has tight dramatic control, near-zero world
  grounding). This is a sharper, more falsifiable version of the "nobody
  has shipped an LLM director verified against a live belief/grudge/
  faction sim" claim already filed in pass 3.

## Not repeated here

Façade's beat manager, DODM's Anchorhead transfer failure and TTD-MDP's
agency critique, Mimesis's accommodate/intervene fork and IPOCL's
intent-driven planning, Left 4 Dead's core pacing FSM, Shadows of Doubt's
provenance-anchored case generator, King of Dragon Pass's conditioned
scene pool, Daggerfall's QBN/QRC template format, PaSSAGE's segment-
limited results, Concordia's `partial_state`/component architecture, AI
Dungeon's core memory-drift failure, Hidden Door's trope-engine
architecture, and the NCP-Bench/TSL-automaton/Slice-of-Life/function-
calling LLM-drift evidence are all already filed across the first three
passes and substantially overlap this report's coverage — not re-filed
here.

## Caveats

- Single-source addition; specific figures (RimWorld's exact wealth
  thresholds, Sharma et al.'s 12.5% figure, KoDP's scene counts) were not
  independently re-verified by this session against their primary
  sources.
- Friends & Fables/ACE-1 is an actively-developed commercial product;
  its architecture description here reflects this report's research
  date and may not remain current.
