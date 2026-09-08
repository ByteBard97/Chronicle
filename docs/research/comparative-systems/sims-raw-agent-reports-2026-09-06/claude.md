# Chronicle Implementation Pass — The Sims Social Mechanics (Claude pass, 2026-09-06)

Input: `sims-social-mechanics-synthesis-2026-09-06.md` (merged 3-agent verdict). Same format as the six-game catalog pass: per-item **Concept** (data / trigger / what the player sees in Skyrim) · **Rating** H/M/L · **Feasibility** against Chronicle's architecture (Python sim as truth, C++ SKSE plugin, Papyrus last resort, no geometry edits, no global reputation, no Nemesis-style rank chains) · **Overlap** (a) covered, needs surfacing / (b) small extension / (c) new subsystem.

---

## Per-item pass

**Directed scalar relationship pair (STR/LTR, daily/lifetime split)**
- Concept: Dual-timescale disposition per NPC→target: a fast layer computed from a recent-belief window (last few days of events) over a slow layer from the full belief store. A heated argument sours an NPC visibly *today* (curt dialogue, refused favors) without instantly destroying years of standing; the fast layer relaxes toward the slow one over days.
- Rating: M — makes individual interactions feel consequential-but-recoverable in every conversation, but it's texture on existing state, not world-in-motion.
- Feasibility: Pure Python derivation given belief timestamps; zero engine work beyond dialogue conditioning.
- Overlap: (b).

**Single consolidated relationship bar + named stages (Sims 3)**
- Concept: Skip the consolidation — it deleted information the dual model carried (the franchise itself reverted in Sims 4). Keep only the named-stage projection, which Chronicle's crystallization design (Friend/Rival/Sworn Friend states) already covers.
- Rating: L — a documented design regression; nothing new to take.
- Feasibility: n/a.
- Overlap: (a).

**Dual independent Friendship/Romance axes (Sims 4)**
- Concept: Independent, separately-decaying social axes so mixed states exist and voice differently: fears-but-respects, loves-but-distrusts, likes-but-despises-your-politics. Merge into Chronicle's typed opinion channels + the fear axis rather than building a Sims-shaped pair.
- Rating: M — the *independence* principle is the keeper; the specific two axes are the least interesting choice of axes for Skyrim.
- Feasibility: Covered by the typed-channels build; config-level.
- Overlap: (b).

**No provenance in the base scalar (unanimous negative finding)**
- Concept: Nothing to build. The most-played social sim in history never made the relationship number carry a reason, across four generations. This is positioning evidence: Chronicle's core differentiator is confirmed unshipped at franchise scale. Quote it in the mod description's comparison section.
- Rating: H as positioning ammunition, L as mechanic.
- Feasibility: n/a.
- Overlap: (a) — it is the existing engine's thesis, externally validated.

**Sims 2 Memories (typed, $Subject slot, valence, salience decay)**
- Concept: Schema corroboration for Chronicle beliefs (type tag, participant refs, valence). The one adoptable behavior: salience decay governs whether a memory still surfaces *unprompted as a conversation topic*, separate from whether the NPC still knows it if asked — bounded salience over unbounded knowledge.
- Rating: M — the salience-to-topic rule is the usable piece; merge with the DF fixed-slot salience design so it's built once.
- Feasibility: Python salience layer feeding LLM prompt context; cheap.
- Overlap: (a) schema / (b) salience rule.

**Sims 2 Gossip propagation (token copy; no mutation; no transitive writeback)**
- Concept: Adopt the witness→token→retransmission loop (Chronicle's core) and fix both unanimously-flagged flaws *by explicit rule*: (1) rumors mutate in transit within Chronicle's bounded-mutation classes; (2) **transitive disposition writeback** — hearing "Aldis robbed the widow" lowers the listener's own trust of Aldis, scaled by the rumor's reliability tier and the listener's temperament. The second rule is what upgrades gossip from conversational fuel to an opinion ecology; the synthesis proves no Sims title ever shipped it.
- Rating: H — the transitive-writeback rule is arguably the single crispest sentence of what Chronicle does that nothing else ever has; it belongs in the top 10 of the merged pass.
- Feasibility: Python: rumor receipt applies reliability-scaled belief deltas toward the rumor's subject. Also inherit Kimi's save-bloat warning (unbounded token cloning corrupted Sims 2 saves) directly into Chronicle's GC/serialization test plan.
- Overlap: (a) core loop + (b) writeback rule made an explicit invariant.

**Sims 4 Sentiments (directed, named, cause-labeled, 4-slot cap, proximity effects)**
- Concept: Three adoptions from the closest shipped analogue to Chronicle's belief model: (1) a small named-sentiment vocabulary ("Festering Grudge," "Betrayed") as the player-facing rendering of belief clusters — how players and dialogue *talk about* the state; (2) **proximity-triggered visible reaction** — an NPC cools, glares, barks, or leaves the room when their sentiment-target walks in, delivering the belief system every few minutes of play with no quest machinery; (3) the self-directed "Guilty" sentiment — offender-side state, so the NPC who wronged someone also carries visible weight (avoids the victim, drinks, over-apologizes).
- Rating: H — proximity reaction is the cheapest per-minute legibility in the entire research corpus, and guilt-state doubles the drama of every offense.
- Feasibility: Python clustering to named sentiments; C++ proximity checks + bark/idle/exit-behavior hooks (SkyrimNet-adjacent tech proves the pattern). The 4-slot cap maps onto the DF salience-slot design.
- Overlap: (a) surfacing + (b) self-directed beliefs are a small schema extension.

**Utility-AI smart-object advertisement + stochastic top-N selection**
- Concept: Chronicle's NPC decision function picks stochastically among the top few scored options, never argmax — the 25-year-validated anti-robotic rule. Slot into the ai_chance-style scoring idiom already adopted from CK.
- Rating: M — one config line with a quarter century of shipped precedent behind it.
- Feasibility: Trivial.
- Overlap: (b) rider on the decision-function design.

**Production-rule reaction catalog (ranked, most-specific-wins, neutral fallback)**
- Concept: A deterministic reaction-resolution layer between the sim and the LLM: ranked precondition rules (belief state + disposition + temperament + mood → reaction class) decide *what* an NPC does in response to an event or player line; the LLM only voices the chosen class. Most-specific rule wins; a neutral fallback guarantees coverage. Ship the ruleset as external JSON so the Skyrim modding community can extend it.
- Rating: H — this is the missing middle layer in Chronicle's stack: it enforces the Slice-of-Life "sim decides, LLM renders" division in a proven, moddable format, and moddability is Skyrim-community currency.
- Feasibility: Python rule engine; the authoring of the base ruleset is the real cost.
- Overlap: (c) — Chronicle has beliefs and an LLM but no rule-resolution layer between them.

**Short-Term Context conversational ladder (STC)**
- Concept: Per-conversation escalation state gating big asks: even a Sworn Friend can't be hit with the enormous favor cold — the conversation must climb rungs first (greeting → rapport → openness). The current rung is injected into the LLM's context, which also blocks the classic LLM "instant intimacy" failure where NPCs emote maximally from turn one.
- Rating: M — conversation pacing that makes social wins feel earned; doubles as an LLM-behavior guardrail.
- Feasibility: Python per-conversation state; prompt-context plumbing only.
- Overlap: (b).

**Spatial-emitter witnessing gated by room portals (Gemini-sourced, single-report)**
- Concept: Chronicle already plans LOS witnessing; adopt the portal nuance as the cheap interior-correctness rule — solid walls block witnessing, open archways don't — instead of expensive true LOS raycasts indoors.
- Rating: L–M — one good implementation shortcut; flagged single-source, but the technique stands on its own merits regardless of citation.
- Feasibility: C++ cell/room-bounds checks; verify cost against SkyrimNet's existing perception code.
- Overlap: (a) implementation detail.

**Chemistry/Attraction computed compatibility**
- Concept: Static pairwise affinity priors computed once at init (temperament-dial distance plus a few lore-flavored axes — race relations, faith, profession) seeding *initial* NPC↔NPC dispositions so towns start with social texture (who drinks with whom, who avoids whom) before any Chronicle event fires. Events then dominate. Skip zodiac-style hardcoded matrices and the bolt UI.
- Rating: M — solves the cold-start blandness of day one; invisible after week one, which is correct.
- Feasibility: One-time Python computation; no engine work.
- Overlap: (b).

**Trait-count discrepancy (63 vs ~80–100)**
- Concept: Nothing to build; a citation-hygiene note for the research library. Resolve against The Sims Wiki only if a design doc ever needs the number.
- Rating: L.
- Feasibility: n/a.
- Overlap: n/a.

**Autonomous NPC-to-NPC socializing — real but deliberately throttled**
- Concept: Doctrine confirmation from a second lineage (matches the Nemesis pacing caps): background social autonomy must be temperament-gated and rate-capped, and the Sims 4 community history proves *under*-throttling (random flirting wrecking established couples) is the failure players install mods to remove. Chronicle rule: autonomous romance/feud initiation requires both temperament eligibility and storyteller sign-off above a disruption threshold.
- Rating: M — doctrine with two independent shipped precedents; prevents Chronicle's most predictable community complaint ("your mod broke my headcanon couple").
- Feasibility: Config + one storyteller gate.
- Overlap: doctrine.

**Off-lot Story Progression / Neighborhood Stories (events, not beliefs)**
- Concept: Adopt the tick architecture — coarse scheduled off-screen life events (marriages, moves, deaths, feuds, business changes) for unloaded NPCs — but drive selection from real belief state, which is exactly what vanilla lacked and why it produced absurdities (best friends randomly becoming rivals). Chronicle rule: every off-screen event must cite the beliefs that motivated it, and arrives to the player as news with that provenance attached.
- Rating: H — belief-motivated off-screen life churn delivered as news is the "world moves without me" layer, and the motivation-citing rule is precisely the vanilla failure inverted.
- Feasibility: Python scheduler over the mothballed-NPC tier; events feed the existing rumor-delivery channel.
- Overlap: (b) — the scheduler shape for an already-planned layer.

**NRaas StoryProgression / MCCC modular manager architecture**
- Concept: Structure the off-screen tier as independent managers on independent cycles (Relationships, Movements, Livelihoods, Feuds), each with precondition-gated scenarios ("Consider Marriage" checks standing + compatibility + courtship duration) — the community-proven engineering shape, load-tested for a decade across thousands of saves. Kimi's ceiling statement ("schedules events, not beliefs") marks exactly the line Chronicle crosses.
- Rating: M — engineering shape, not player-facing; adopt the module structure and the per-manager cycle rates.
- Feasibility: Python module organization; free.
- Overlap: (b).

**Clubs (behavior-rule groups, no persistent group state)**
- Concept: Take the encouraged/discouraged behavior-tag idea for Skyrim factions (Companions encourage brawl-settling, Thieves Guild discourages guard contact, Bards College encourages gossip-spreading) as autonomy biases while in faction company. Add what Clubs lacked: persistent group state (cohesion, shared grievances) — already planned via the clan/hold aggregation subsystem, so this item contributes only the behavior-tag flavoring.
- Rating: M — cheap faction personality; the deep half lives in the collective-state build.
- Feasibility: Python behavior-bias tags read by the decision function.
- Overlap: (b).

**Family Dynamics (typed symmetric dyad tags)**
- Concept: Skip. Chronicle's directed beliefs strictly dominate — the interesting case is exactly the asymmetric one Sims forbids by construction (a son who resents the father who adores him). Nothing to take beyond confirmation that typed dyads read well to players, which crystallization already provides.
- Rating: L — superseded by existing design.
- Feasibility: n/a.
- Overlap: (a).

**Households as containers, not social units (unanimous negative finding)**
- Concept: Nothing to copy; the second load-bearing gap confirmation. No Sims title ever gave a family systemic awareness of a member's conflicts — A's spouse knows nothing unless physically present. Chronicle's kin-propagation rule (household members receive high-reliability beliefs about events involving their kin, on a delay) is the direct fix, and the clan-level aggregation has no Sims-lineage competitor.
- Rating: H as gap-confirmation; the kin-propagation rule itself is a small, high-yield build.
- Feasibility: Python: kinship-graph edges get privileged rumor routing; trivial once the relational graph exists.
- Overlap: (b) — kin-priority routing is a natural extension.

**Evans-style Social Practices for factions (Gemini-only, from Versu/Exclusion Logic — not shipped in Sims)**
- Concept: Faction/court state as deontic status sets — obligated/permitted/forbidden — that flip for ALL bound members simultaneously when a triggering fact arrives: a credible murder rumor reaching Dragonsreach flips the player's status to "violator" across the whole court in one operation ("the room turns on you"), no N pairwise updates. A genuine group-level *primitive*, architecturally distinct from aggregation, absent from the entire six-game catalog.
- Rating: H — dramatically legible, computationally cheap, and it solves the "guard captain knows but the steward doesn't" incoherence inside institutions where shared knowledge is the fiction.
- Feasibility: Flag for follow-up research before committing (read Evans's Exclusion Logic papers and the Versu paper) — uncorroborated single-report recommendation, and the interaction with per-individual provenance needs design (institutional status vs personal belief must stay distinguishable).
- Overlap: (c).

**Comme il Faut / City of Gangsters follow-up (Kimi-only precedents)**
- Concept: A dedicated research pass on the post-Sims academic lineage the library lacks: CiF/Prom Week/Ensemble (third-party social reasoning — an uninvolved z inferring "x is cheating on y" — plus a shared social-facts database, both stated in its own paper as missing from Sims 3) and Zubek's City of Gangsters (logic-programming social inference with second-order propagation over ~1,200 NPCs in a shipped commercial game — the closest known precedent to Chronicle's target scale and mechanism).
- Rating: H as a research action — City of Gangsters is likely the single most Chronicle-shaped precedent not yet in the library.
- Feasibility: Research task; the AIIDE papers are public.
- Overlap: library gap (converges with the CiF/Talk-of-the-Town entries already flagged in the six-game pass).

---

## Ranked top 5 (Sims-derived, build-first)

1. **Transitive disposition writeback on rumor receipt** — the one rule that turns gossip into an opinion ecology; unshipped by the entire franchise, native to Chronicle's engine, nearly free to implement.
2. **Sentiments-style proximity reactions + named sentiment vocabulary + guilt-state** — the cheapest per-minute visibility for the belief system anywhere in the research corpus.
3. **Production-rule reaction-resolution layer (moddable JSON)** — the missing deterministic middle layer between sim and LLM, in a proven format the modding community can extend.
4. **Belief-motivated off-screen life-event scheduler (Story Progression, fixed)** — world-moves-without-you churn whose every event can cite its reason, the vanilla failure inverted.
5. **Kin-priority belief routing (Households finding, inverted)** — families that systemically know what happened to their own, on privileged fast/reliable rumor edges; small build, large coherence gain.

## Discard list (don't reconsider)

- **Consolidated single relationship bar** — the franchise's own documented regression; Sims 4 reverted it.
- **Zodiac/turn-on chemistry matrices and bolt UI** — wrong fiction, wrong surface; keep only init-time affinity priors.
- **Family Dynamics symmetric dyad tags** — strictly dominated by directed beliefs.
- **Clubs' no-persistent-state group model** — the behavior tags survive into faction flavoring; the group model itself is the documented shallowness to avoid.
- **Trait-count number (either version)** — unresolved citation dispute; irrelevant to any Chronicle decision.
- **Vanilla Story Progression's state-blind event lottery** — the tick shape survives; the selection policy is the documented failure.

## What the synthesis is missing

- **Sims 2 Wants & Fears (and Sims 4's 2022 Wants & Fears revival)** — per-Sim visible short-term desire/fear slots generated from personality and current state, driving player-legible goals ("wants to make a friend," "fears the death of her spouse"). Directly relevant as a legibility device: an NPC whose current want/fear is inspectable-through-dialogue makes autonomy readable. Absent from the merged table entirely.
- **Sims 4 Get Famous reputation (2018)** — a global public-reputation scalar with tiered perks/penalties: relevant to Chronicle precisely as a *negative example* under the no-global-reputation rule (it exhibits exactly the "everyone telepathically knows" failure Chronicle's provenance model exists to fix), and worth one line in the design doc's comparison section.
- **Sims 2 Apartment Life neighbor reputation** — an earlier, smaller-scoped reputation scalar with the same telepathy flaw; corroborates that the franchise's only reputation attempts were provenance-free broadcasts.
- **Sims 3/4 moodlet/emotion stack as an *output* vocabulary** — the classification section mentions moodlets in passing, but the table never treats the moodlet system itself: typed, cause-labeled, duration-bound mood modifiers with visible icons are the franchise's most successful legibility device, and "cause-labeled temporary state the player can inspect" is a pattern Chronicle's strain/composure system should explicitly borrow (diegetically, via barks and advisor comments rather than icons).
- **Sims 2 Furiosity** — Kimi covered it per the synthesis's own note, but it never made the merged table: a directed, decaying anger state that *gates interaction menus* (a furious Sim refuses certain interactions outright) — a shipped precedent for belief-state hard-gating available player dialogue options, which Chronicle should do (a grieving widow won't discuss trade the week after the funeral).
- **The Sims Medieval (2011)** — a franchise spin-off with quest-structured play, a kingdom-level Aspect/Ambition layer, and NPC roles bound to institutional positions (monarch, priest, knight); thin social sim, but the closest the franchise came to institution-scoped social state, adjacent to the Social Practices question.