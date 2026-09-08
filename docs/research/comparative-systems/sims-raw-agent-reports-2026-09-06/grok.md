**8. The Sims (synthesized coverage, 2026-09-06)**

### Relationship scalars & stages

**Directed scalar relationship pair (STR/LTR or daily/lifetime).**  
- Concepts: Maintain two directed floats per NPC pair in Chronicle (short-term fast-decay, long-term slow trail); project discrete stages (Acquaintance → Friend → Ally / Rival) that gate dialogue packages and AI packages. Triggers: any witnessed interaction or rumor receipt. Player sees: disposition changes that feel immediate then settle, plus stage-locked options (“Ask for favor” only after Friend threshold).  
- Rating: Medium — solid substrate but still personal-scale ledger unless tied to hold events.  
- Feasibility: Pure Python data model + SKSE disposition write-back; no new assets.  
- Overlap: (b) natural extension of existing opinion aggregation.

**Single consolidated relationship bar + named stages (Sims 3).**  
- Concepts: Collapse to one 0–100 bar with named stages; add a “Long Distance Friend” style exemption flag that freezes decay for key NPCs (e.g., housecarls or quest-critical allies).  
- Rating: Low — simplification of the dual-scalar model already above.  
- Feasibility: Trivial.  
- Overlap: (b).

**Dual independent Friendship/Romance bars (Sims 4).**  
- Concepts: Separate Friendship and Romance scalars so an NPC can be high-friend/zero-romance or the reverse; combinatorial labels (“Uneasy Ally,” “Hostile Lover”) drive dialogue.  
- Rating: Medium — useful for Skyrim’s marriage/follower systems.  
- Feasibility: Two floats + label table; SKSE can influence marriage dialogue conditions.  
- Overlap: (b).

**No provenance in the base scalar.**  
- Concepts: Explicit negative lesson — never store a bare number; every score must be the sum of provenance-tagged beliefs.  
- Rating: High (design constraint).  
- Feasibility: Already Chronicle core doctrine.  
- Overlap: (a).

### Memories, gossip, sentiments

**Sims 2 Memories (typed, per-Sim, durable event records).**  
- Concepts: Attach typed memory objects (Won a Fight, Relative Died, Married) with $Subject slot and valence; surface in dialogue and in a Memory Viewer. Salience decay controls whether the topic is still raised.  
- Rating: High — closest early analogue to Chronicle memories.  
- Feasibility: Direct map onto existing memory system.  
- Overlap: (a).

**Sims 2 Gossip propagation.**  
- Concepts: Witness forms original memory → “Gossip/Tell Secret” packages event ID + subject into a token that copies into listener’s memory and can retransmit. Fix the two named flaws: (1) allow mutation/distortion in transit, (2) force transitive belief update so the listener adjusts disposition toward the subject.  
- Rating: High — implementable proof of person-to-person transmission on constrained hardware; the fixes are exactly Chronicle’s design goals.  
- Feasibility: Python token objects + dialogue package; SKSE for conversation start. Research needed only for safe multi-NPC conversation interruption.  
- Overlap: (b) small extension that adds the missing mutation + transitive write-back.

**Sims 4 Sentiments (directed, named, cause-labeled, capped).**  
- Concepts: Per-(A→B) named states (“Festering Grudge,” “Betrayed by Cheating,” “Guilty”) with short/long duration, hard 4-slot cap (weakest evicted), proximity moodlets, and autonomy bias. Extend with third-party propagation and mutation (the two missing pieces).  
- Rating: High — unanimous strongest individual mechanic; near 1:1 sketch of belief-with-provenance.  
- Feasibility: Python sentiment objects + duration timers; SKSE for proximity moodlet triggers and AI package bias. Cap prevents unbounded growth.  
- Overlap: (a) already essentially covered; needs the two extensions Chronicle already intends.

### Interaction selection & conversational stack

**Utility-AI / smart-object interaction selection.**  
- Concepts: NPCs score available interactions by need-deltas, traits, mood, relationship, distance; stochastic pick among top few. Use for autonomous on-lot (or in-cell) socializing.  
- Rating: Medium — good autonomy substrate but player-scale only.  
- Feasibility: Python scoring; SKSE can inject temporary AI packages. Throttle heavily to stay inside Papyrus/SKSE budget.  
- Overlap: (c).

**Production-rule / precondition-gated interaction catalog.**  
- Concepts: Hand-authored reaction rules (most-specific wins) that resolve how an NPC reacts to a joke, insult, or rumor given current beliefs + disposition + mood.  
- Rating: High — clean, moddable pattern for belief-driven dialogue.  
- Feasibility: Python rule table evaluated on dialogue start; output selects dialogue topic or AI reaction.  
- Overlap: (c).

**Short-Term Context (STC) conversational ladder.**  
- Concepts: Fast-resetting per-conversation state (Boring → Friendly → Very Friendly, or Hostile ladder) that gates escalation even when lifetime relationship is high. Prevents instant intimacy.  
- Rating: High — solves a real Skyrim dialogue problem.  
- Feasibility: Per-conversation Python state; cleared on conversation end.  
- Overlap: (c).

### Witnessing, chemistry, autonomy

**Witnessing via spatial emitters (not pure LOS).**  
- Concepts: Event (kiss, murder, theft) spawns a radius scanner gated by room/portal boundaries; flags infidelity or crime memory for any nearby NPC with relevant relationship bits.  
- Rating: Medium — useful alternative/complement to pure LOS.  
- Feasibility: SKSE cell/portal queries possible; research needed for reliable room-boundary detection.  
- Overlap: (b).

**Chemistry/Attraction algorithm.**  
- Concepts: Compatibility from personality distance, trait/zodiac-style matrix, Turn-On/Off bits, repulsion override; surface as Chemistry Bolts or Social Compatibility tier that biases romance/friendship gains.  
- Rating: Medium — nice flavor for marriage and follower recruitment.  
- Feasibility: Pure data; no geometry change.  
- Overlap: (c).

**Trait count discrepancy.**  
- Concepts: Flag only — resolve exact Sims 3 trait count against wiki before any design doc cites a number.  
- Rating: Low (meta).  
- Feasibility: N/A.  
- Overlap: N/A.

**Autonomous NPC-to-NPC socializing (throttled).**  
- Concepts: Allow background NPCs on the loaded cell to chat/flirt/fight via utility scoring, but trait-gate romance initiation and provide MCM toggles to rein in indiscriminate flirting.  
- Rating: Medium — world-feels-alive win when throttled correctly.  
- Feasibility: Same as utility-AI above; community-mod lesson (MCCC-style toggles) is directly applicable.  
- Overlap: (c).

### World-scale / group constructs

**Off-lot life-event engine (Story Progression / Neighborhood Stories).**  
- Concepts: Coarse daily/hourly demographic manager that marries, moves, kills, or promotes unplayed NPCs on timers, scored loosely by traits. Use only as a *scheduling/tick-rate architecture pattern* for Chronicle’s off-screen tier; never as a model of what to simulate (it schedules events, never beliefs or rumors).  
- Rating: Medium (architecture only).  
- Feasibility: Python daily tick already planned; keep it demographic, not social.  
- Overlap: (b) for the tick pattern; (c) if any demographic events are added.

**NRaas / MCCC community overhauls.**  
- Concepts: Modular manager architecture (independent Career/Relationship/Population cycles) with precondition-gated scenarios (“Consider Marriage” checks LTR + traits + courtship duration). Still only schedules discrete life events.  
- Rating: Medium — richer scheduling pattern, still not belief-level.  
- Feasibility: Same as above.  
- Overlap: (b).

**Clubs (Get Together).**  
- Concepts: Up to N members, eligibility rules, encouraged/discouraged behavior tags that temporarily override individual traits during gatherings; inter-group hostility flags. No persistent cohesion or memory of past meetings.  
- Rating: Low — shallow group construct; Chronicle needs lasting faction state.  
- Feasibility: Easy flags, but deliberately limited.  
- Overlap: (c).

**Family Dynamics (Growing Together).**  
- Concepts: Named pairwise dyad tags (Close/Distant/Supportive/…) that bias autonomy; forced symmetric and kinship-only.  
- Rating: Low — still just typed pairwise, not group state.  
- Feasibility: Easy.  
- Overlap: (b).

**Households as economic/spatial containers only.**  
- Concepts: Negative lesson — no family-level morale or disposition toward outsiders. Chronicle must supply the missing faction/court-level state (Jarl’s Court, Companions, Thieves Guild) that Sims never modeled.  
- Rating: High (design constraint).  
- Feasibility: N/A.  
- Overlap: (a) confirms the gap Chronicle is filling.

### Additional precedents surfaced

**Evans-style Social Practices (group deontic status).**  
- Concepts: Model Skyrim factions/courts as Social Practices: a single triggering fact (murder rumor reaching Dragonsreach) flips obligated/permitted/forbidden status for *all* bound members simultaneously, rather than N pairwise updates.  
- Rating: High — architecturally distinct from everything in the six-game catalog; clean group-level primitive.  
- Feasibility: Python group-state object; SKSE can broadcast disposition or AI-package changes to all members in the loaded cell. Requires follow-up reading of Evans Exclusion Logic / Versu papers.  
- Overlap: (c).

**Comme il Faut (McCoy et al., AIIDE 2011).**  
- Concepts: Genuine third-party social reasoning (“X is cheating on Y” inferable by uninvolved Z) + shared social-facts database.  
- Rating: High — closer academic precedent for Chronicle’s actual goal than The Sims itself.  
- Feasibility: Research pass required; logic-programming layer on top of existing belief graph.  
- Overlap: (c).

**City of Gangsters logic-programming social inference (Zubek et al., AIIDE 2021).**  
- Concepts: Second-order propagation over ~1,200 NPCs via logic programming; explicit reaction to Sims 3’s off-lot limitations.  
- Rating: High — same citation that corrected the off-lot claim; directly relevant scale.  
- Feasibility: Research pass required; may inform Chronicle’s off-screen inference engine.  
- Overlap: (c).

---

**Updated top-10 considerations (Sims additions)**  
The unanimous strongest Sims mechanic (Sentiments) and the gossip-transmission loop (with the two fixes) both reinforce items already in the previous top 10 (provenance-anchored beliefs, atomic memory units). The genuinely new high-value entry is **Evans-style Social Practices** for faction/court group state — that should be considered for a future top-10 slot once the Exclusion Logic papers are reviewed. The demographic Story Progression pattern is useful only as a tick-rate template, not as content.

**Updated discard reinforcement**  
- Bare relationship scalars without provenance (the franchise-wide negative finding).  
- Clubs / Family Dynamics as group models (no accumulated state).  
- Any off-lot system that only schedules demographic events and never propagates beliefs or rumors.

**Catalog gap closure**  
The Sims material is now covered. The two academic systems (Comme il Faut, City of Gangsters) plus Evans’s post-Sims Exclusion Logic / Versu work are explicit new research targets that sit outside the original six-game + AI-director set and should receive a dedicated follow-up pass.