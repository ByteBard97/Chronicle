# Master Feature Synthesis: What Chronicle Should Build (2026-09-06)

**Entry point for this whole research effort.** Read this first; the other
files in this directory (and `docs/research/51`-`56` on the separate
GM/storyteller-agent thread) are supporting detail this document cites by
name rather than repeats.

**The question this answers**: the owner rejected personal-scale
grudge-tracking as Chronicle's premier feature ("boring... too small-scale,
too slow to notice, too player-centric") and wants a world reactive to the
player *and* to independent events like the civil war and dragon attacks.
Eight comparative-systems documents, five external-agent brainstorm
batches, and one primary-source verification later, this is the synthesis.

---

## TL;DR

**The headline feature is not one mechanic — it's a confirmed, two-part
architecture, and both parts now have real shipped precedent to build on
rather than invent:**

1. **Storyteller-driven storylet role-casting**, built directly on top of
   **Bethesda's own Radiant Story engine** (confirmed, not just similar —
   Radiant Story's "Find Matching Reference" alias-fill is a near-verbatim
   match to the academic "parametrized storylet" definition). Chronicle's
   belief/grudge/provenance graph picks *who* and *where*; Radiant Story's
   existing quest/alias/scene machinery does the casting and execution.
2. **The civil war (and, by extension, dragon attacks) as a multi-phase,
   belief-driven conflict** rather than a binary questline, using **CK3's
   Struggle system** as a concrete, fully-specified template (named phases,
   catalyst-point accumulation, a debounce timer, a documented balance trap
   to avoid) — not a vague "make the war more dynamic" aspiration.

These two were the top two picks independently, repeatedly, across every
research pass this session ran. What changed between the early passes and
now is that both went from "the research suggests this" to "this is a
verified, shippable integration path" — see §4.

This also resolves cleanly against the separate GM/storyteller-agent
research thread (`docs/research/51`-`56`): that thread found IntelEngine,
HAMLET, and IBSEN as academic/community precedent for an autonomous
story-director layer, and named "no scheduled tier, no design started" as
the gap. **This document closes a big piece of that gap**: the
scene-casting layer such a director needs isn't hypothetical — it's
Radiant Story, already shipped, already battle-tested across three
Bethesda titles, waiting to be driven by Chronicle's own belief state
instead of its native (memoryless) selection logic.

---

## 1. Unified Ranked Feature List

Merges the six-game brainstorm's top-15
(`skyrim-implementation-brainstorm-synthesis-2026-09-06.md` §6) with the
Sims-implementation brainstorm's findings
(`sims-implementation-brainstorm-synthesis-2026-09-06.md`), resolving
overlaps into single lines. Convergence counts are cumulative across every
independent agent/document that touched the item.

| # | Feature | Skyrim implementation, one line | Convergence | Readiness |
|---|---|---|---|---|
| 1 | **Storylet role-casting, hooked to Radiant Story** (absorbs the six-game batch's separately-ranked "Provenance-anchored Case Generator" — confirmed the same mechanism) | Chronicle's belief engine picks a real grudge-holder/witness/location; fires it into a Chronicle-authored quest via `SendStoryEvent` + "From Event" alias fill; `ForceRefIfEmpty`/`ForceRefTo` for overrides; `OnStory*` for observation | **5/5 six-game agents** (unanimous #1) + **2/2 Radiant AI reports** independently confirming shipped precedent | **Ready to design now** — integration surface is fully specified, vanilla Papyrus, no SKSE hard-dependency |
| 2 | **Civil war (+ dragon attacks) as a multi-phase conflict**, using CK3's Struggle system as the template (absorbs "faction discontent→civil-war coupling" and "CK3 Struggle/Phase system") | Named phases (e.g. Opportunity→Hostility/Conciliation→Compromise→decay), driven by weighted "catalyst" point contributions from real belief/rumor events, transitioning on a debounce timer, each phase gating which quests/crimes/alliances are legal | **3-5/5 six-game agents** + **2/2 misc-gaps reports** independently naming it "the single most transferable pattern," genuinely distinct from anything else in the catalog | **Political/phase logic ready to design now** (fully specified: phase names, catalyst mechanism, debounce, a documented balance trap to avoid — see §8); the *visible* hold/settlement world-state swap component (below) needs its own spike |
| 3 | **Power vacuums + "broken squad" degradation** | Defeated factions leave weaker remnants; neighboring factions expand into vacated territory as spawn-table/encounter-weight logic | 4-5/5 | Ready now |
| 4 | **Named relationship crystallization, with Sims 4 Sentiments as the concrete data model** | Discrete Friend/Rival/Lover/Nemesis flags (individual + house/clan-level) implemented as a 4-slot-capped, directed, cause-labeled sentiment inventory per NPC, with proximity-triggered visible reactions and a self-directed "Guilty" state for offenders | Universal High across both six-game and Sims batches; Sentiments gives this item a concrete, already-shipped data-model sketch it didn't have before | Ready now |
| 5 | **Gossip mutation + mandatory transitive belief writeback** | When a rumor is heard, its content mutates per Chronicle's existing bounded-mutation classes *and* — the specific new rule — the listener's own disposition toward the rumor's subject shifts, scaled by the rumor's reliability tier and the listener's temperament | **3/3 Sims-implementation agents, unanimous, independently identical fix.** Claude: "arguably the single crispest sentence of what Chronicle does that nothing else ever has." No shipped game (Sims, DF, CK) does both halves at once — only Talk of the Town's mutation-with-provenance comes close, and even it doesn't explicitly write back into a listener's own disposition scalar | Ready now — pure Python rule on top of the existing belief-propagation path |
| 6 | **Production-rule reaction-resolution layer** | A deterministic, most-specific-wins rule table sitting between belief state and the LLM: given (belief + disposition + temperament + mood), decide *what class of reaction* an NPC has before the LLM decides *how to voice it* — shippable as external, community-moddable JSON | **3/3 Sims-implementation agents, unanimous, no equivalent in the six-game top-15.** Directly enforces the "sim decides, LLM renders" invariant Fable named as load-bearing across three separate AI-director systems in the six-game synthesis (Concordia/Slice-of-Life/Orchestrated-Reality) — this is the concrete implementation of that invariant, and the layer ADR-0011's conversation tier needs underneath it | Ready to design now; authoring the base ruleset is the real cost, not the architecture |
| 7 | **Dual-axis stress/mental-break system with catharsis** | World events (war, dragon attacks, bereavement) erupt into visible NPC breakdowns with a built-in recovery mechanism; build once as a single unified subsystem (CK's Stress engine + RimWorld's Mood bands + DF's dual-axis stress are the same mechanism under three names — Fable's finding) | 4/5 explicit | Ready now; exact package-override mechanism needs SKSE verification |
| 8 | **Non-telepathic, witness-gated crime**, using portal-gated spatial-emitter witnessing as the concrete technique | Fixes vanilla's "guards psychically know" problem; witnessing checked via a radius-scan gated by room-portal boundaries (a solid wall blocks it, an open archway doesn't) rather than expensive true line-of-sight raycasting | Near-unanimous across the six-game batch (sleeper pick, every agent rated High) + corroborated as a concrete technique by the Sims research | "Architecturally bigger than it looks," per repeated flag — but now has a cheap concrete technique instead of an open question |
| 9 | **Secrets/Hooks leverage economy** | Chronicle's existing provenance becomes spendable currency (blackmail, exposure, forced compliance), ideally as tangible tradeable inventory objects rather than a UI number | 3/5 explicit, universal high | Ready now |
| 10 | **Dread/intimidation as a second social axis** | Fear-based compliance driven by known deeds, never a global score, separate from Opinion | 3/5 explicit, universal high | Ready now |
| 11 | **Social/world-event pacing director**, with mandatory belief-citation on every off-screen event | A Left 4 Dead–style Quiet→Build→Crisis→Aftermath throttle governing how many Chronicle events intrude at once; every off-screen life-event the scheduler fires must cite the specific belief that motivated it — the direct inversion of Sims' own worst failure mode (best friends randomly becoming rivals for no visible reason) | 2-3/5 (six-game) + reinforced by the Sims off-lot-scheduler finding | Ready now as a pure Python throttle |
| 12 | **Physical/cultural provenance objects** | DF-style generated engravings/memorials/artifact histories tied to real events, plus RimWorld-style Tale-driven art descriptions and a bard's song about a real event that itself becomes a spreadable rumor-object. Preserve DF's sharper distinction: reactive (an NPC's mood responds to seeing evidence of something they personally experienced) vs. RimWorld's merely descriptive Tale-art link | 3/5 explicit + universal high (six-game) + corroborated by the misc-gaps RimWorld/DF comparison | **Needs a spike**: persistent dynamic-text object injection via SKSE, specifically safe bard-performance injection (flagged by Fable) |
| 13 | **Short-Term Context (STC) conversational ladder** | A fast-resetting per-conversation escalation state (greeting→rapport→openness) gating big asks — even a Sworn Friend can't be hit with an enormous favor cold. Feeds directly into ADR-0011's conversation tier as a guardrail against the "instant intimacy" LLM failure mode | New; mostly High (2/3), Claude Medium | Ready now — pure Python per-conversation state |
| 14 | **Kin-priority belief routing** | Household/kin members receive high-reliability beliefs about events involving relatives on privileged, faster rumor edges — a concrete build extracted from the "households are economic containers, not social units" negative finding across every Sims generation | New (Claude only, in the Sims batch) | Small extension of #4/#5; ready now |
| 15 | **Third-party symbolic-inference substrate**: City of Gangsters/BotL as the primary study target; Versu-style deontic "Social Practices" (group obligations that shift for every bound member on one triggering fact) via the Praxish/RePraxis reconstructions, *not* the lost original engine | Not a single mechanic — a possible architectural layer for how uninvolved NPCs reason about facts and how obligations gate action space at group scale (a court, a guild) rather than only pairwise | Now a **triple-independent convergence**: Fable (six-game batch) → Kimi's original Sims-research report → all 3 Sims-implementation agents, each independently naming Comme il Faut/City of Gangsters | **Big architectural bet, gated on research**: read `github.com/ianhorswill/BotL` (City of Gangsters' engine, source-available, proven at ~1,200 NPCs) and the Praxish/RePraxis repos (MIT-licensed Versu reconstructions) directly before treating Social Practices as a real design candidate — this is exactly the "verify before designing" discipline that already paid off on Talk of the Town |

**Held in reserve, not adopted now:** Watch Dogs: Legion's Census/"lazy
uprezzing" architecture (generate NPC depth only on-demand rather than
Chronicle's always-simulated premise) — both misc-gaps reports agree this
is a real fallback, not a template to adopt, and should only be reached
for if Chronicle's persistent simulation actually misses Skyrim's
frame-time budget.

---

## 2. Design constraints and confirmed anti-patterns

Not features — hard lessons this research converged on that should shape
*how* the above gets built:

- **The Dwarf Fortress "loyalty cascade"** (Toady One's own "civil war
  bug"): a forced execution can recursively flip the executioners into
  enemies of their own civilization, cascading until the settlement
  destroys itself. Direct design constraint on item #2 above and on any
  faction-membership mechanic: flag transitions must be damped and scoped
  to actual witnesses/participants, never allowed to cascade unbounded.
- **RimWorld's wealth-gaming exploit**: any director input the player can
  launder (raw wealth) will be laundered. Use un-launderable inputs
  (deaths, completed events, provenance-verifiable state) for the pacing
  director (#11), never raw player-visible resources.
- **Oblivion's Radiant AI cascade failures**: only the skooma-merchant
  story is soundly attributed (Pagliarulo, 2006/2010); the rest are
  folklore. The real, confirmed lesson from Bethesda's own design response
  (Nesmith, 2012): bound the write-back to a curated list of triggers,
  never let a grudge/belief system reach directly into native
  Aggression/Faction-Enemy variables without an insulated abstraction
  layer in between.
- **Nemesis-style automatic rank-rewriting chains**: still explicitly
  disallowed (patent + doctrine), unanimous across every agent that
  touched it. Keep "succession-as-story" (a storyteller-chosen successor,
  no cascading parameter rewrites) as the compliant version.
- **CK2's "opinion-modifier soup"**: uncapped additive stacking becomes
  unreadable. Every item above that touches a scalar (#4, #9, #10) needs
  capped, itemized, causally-labeled state from day one, not
  precision-tuned later.

---

## 3. Build Order Sketch

Not a full implementation plan — that's a later step, once a direction is
picked. Rough sequencing only:

1. **Pure-Python, zero-engine-risk items first, buildable in parallel**:
   #5 (gossip writeback), #6 (production-rule reaction layer), #9
   (Secrets/Hooks), #10 (Dread axis), #11 (pacing director), #13 (STC
   ladder), #14 (kin routing). None of these touch SKSE/Papyrus and all
   extend the existing belief engine directly.
2. **Radiant Story integration is the architectural linchpin — do this
   early.** It's vanilla Papyrus, low engineering risk, and item #1
   (the confirmed headline mechanic) depends on it. This should not wait
   behind #2's design work.
3. **Civil-war-as-Struggle-system (#2) design pass**: adapt CK3's
   phase/catalyst model to Skyrim's actual civil war questline. Doesn't
   block #1 or the pure-Python items; can proceed in parallel.
4. **Named technical spikes, before committing full design budget**:
   the visible hold/settlement world-state swap (#2's other half) — safe
   respawn-table-override and actor/cell-swap-across-saves technique;
   persistent dynamic-text object injection for #12, specifically safe
   bard-performance injection.
5. **Academic-engines follow-up reads, in parallel, not blocking
   anything**: `ianhorswill/BotL` and the Praxish/RePraxis repos, before
   committing engineering budget to #15's deontic Social Practices layer.
6. **#7's unified stress/mental-break subsystem** and **#8's witness-crime
   fix** are both "ready now" but non-trivial — reasonable candidates for
   the second wave, after #1/#6 prove the pattern out.

---

## 4. What We Now Know That We Didn't At The Start

The hard-won, verified findings worth remembering — several of them
corrections to what looked true from secondary summaries alone:

- **Chronicle's own foundational citation (Talk of the Town) is
  accurate and, if anything, understated** — direct source verification
  (cloned repo, read the dissertation and 2017 paper) confirmed "belief
  facet" and "predecessor" are Ryan's own literal terms, and found four
  independent distortion mechanisms (Mutation, Transference, Confabulation,
  Lie) richer than the vision doc's short summary implies. **But the
  public repo doesn't contain the belief system itself** — deliberately
  stripped before publishing, confirmed by a dangling code reference and
  the author's own comment. Design from the papers, not the repo.
- **Radiant Story is real, shipped, verified precedent for Chronicle's
  #1 mechanic** — not a comparison target, a foundation to build on.
  This closes a real gap the separate GM-agent research thread
  (`docs/research/51`-`56`) had flagged but not resolved.
- **The Sims is weak precedent for Chronicle's actual goal** (a world
  that reacts independent of the player watching) despite being the most
  iconic reference the owner named — three independent reports converged,
  almost verbatim, on "even at its most autonomous, a Sims world never
  *thinks* off-screen; it merely *happens*." But **Sims 4 Sentiments** is
  a genuinely strong individual mechanic worth adapting regardless.
- **CK3's Struggle system is a fully-specified, concrete template** for
  civil-war-as-conflict — not a vague aspiration. Phase names, a
  catalyst-point mechanism, a debounce timer, and a documented balance
  trap (late-game Conciliation dominance) all transferred directly from
  primary-source reading.
- **Research-agent claims about licensing/maintenance status keep not
  holding up under direct verification** — this happened three separate
  times this session (HAMLET's empty repo; Talk of the Town's
  stripped-out belief code; Ensemble's disputed maintained/abandoned
  status, CiF/Prom Week's disputed source-readability). The pattern is
  consistent enough to treat as a standing rule: never design against a
  "this is open-source and maintained" claim without a direct check.
- **Every quality-flagged/thin agent pass this session still landed on
  roughly the right answer even when its format or sourcing broke down**
  (Gemini's contaminated Sims pass still independently named the same
  core items as the other three) — a mild point of reassurance that the
  *content* judgments across this whole effort are more robust than any
  single agent's presentation quality.

---

## 5. Remaining Open Questions (owner decisions, not research gaps)

No further research resolves these — they need the owner to decide:

- **Is this (role-casting + Radiant Story + civil-war-as-Struggle) the
  actual headline, a co-equal pillar next to the already-designed voiced,
  reactive-NPC conversation tier (ADR-0011), or does the conversation tier
  come first?** Worth naming explicitly: this research suggests these
  aren't actually competing pillars — item #6 (the production-rule
  reaction layer) and item #13 (the STC ladder) are the exact middle
  layer ADR-0011's conversation tier needs underneath it, and the
  GM-agent research thread's own multi-timescale hierarchy (slow
  campaign-architect / fast scene-director / per-line renderer) already
  has a natural slot for both: the storyteller layer this document
  describes is the "scene-director" tier, and ADR-0011 is the "per-line
  renderer" tier of the same stack, not a separate track. But whether to
  *build* them in that combined order, market them as one pitch, or
  sequence them separately is still the owner's call.
- **How much of item #15's bet (a group-level deontic obligation layer)
  is worth taking** once the Praxish/RePraxis and BotL reads happen —
  research can narrow this to "here's what's really there," not decide
  whether it's worth the architectural cost for Chronicle specifically.
- **Whether item #2's visible world-state-swap half is worth the SKSE
  risk** at all, versus shipping the political/phase layer without the
  visible town-record change — a scope decision once the spike (§3 item
  4) reports back, not a research question itself.
- **Sequencing against the mod-conflict mitigation thread** (the other,
  fully separate work thread this project has open) and the Mac-Mini
  hardware-arrival timing — unrelated to this research, not re-litigated
  here, but still open per the standing project handoff record.

---

## 6. Document Map

| Document | Covers |
|---|---|
| `npc-social-mechanics-catalog-2026-09-06.md` | The original ~100-item uncurated catalog (CK, Kenshi, Shadows of Doubt, Nemesis, RimWorld, DF, AI-directors) |
| `skyrim-implementation-brainstorm-synthesis-2026-09-06.md` | Five-agent brainstorm against the catalog; its own top-15 (§6) is superseded by §1 above |
| `sims-social-mechanics-synthesis-2026-09-06.md` | The Sims' actual mechanics, verdict: weak precedent, Sentiments the exception |
| `sims-implementation-brainstorm-synthesis-2026-09-06.md` | Skyrim-implementation brainstorm against Sims mechanics specifically |
| `talk-of-the-town-primary-source-verification-2026-09-06.md` | Direct verification of Chronicle's own foundational citation |
| `academic-social-simulation-engines-synthesis-2026-09-06.md` | Comme il Faut, Prom Week, Ensemble, Versu, City of Gangsters |
| `radiant-ai-radiant-story-synthesis-2026-09-06.md` | Confirms Radiant Story = storylet role-casting, gives the integration surface |
| `misc-game-mechanics-gaps-synthesis-2026-09-06.md` | CK3 Legends/Struggle, Nemesis intel, RimWorld Ideology/Tales, DF Villains, Watch Dogs: Legion |
| `docs/research/51`-`56` (separate thread) | GM/storyteller-agent precedent: IntelEngine, HAMLET, IBSEN, hierarchical multi-timescale architectures — this document's §4 (Radiant Story finding) directly closes a gap that thread's own "next steps" flagged as unresolved |
