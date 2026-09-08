---
date: 2026-09-06
sources:
  - "Gemini deep research report, prompt 2 of notes/gm-agent-harness-research-prompts-2026-09-06.md (owner-run, delivered as 'In-Game LLM Game Masters.md')"
  - "Claude deep research report, same prompt (owner-run, delivered as 'claude gm prompt 2.md')"
  - "MinLL/SkyrimNet-GamePlugin README and source archive (owner-downloaded, vbeta25-rc6), directly inspected this session — confirmed no C++ source, no compiled binary, no LICENSE file present"
topic: "Does real precedent exist for an LLM Game Master agent authoring original, emergent quest/story content grounded in an existing video game's real assets, locations, and lore, reacting to player behavior — in Skyrim or any other engine?"
status: filed
---

# LLM GMs authoring content in existing game worlds — two independent passes

Two independent deep-research passes (Gemini, Claude) answering prompt 2 of
`notes/gm-agent-harness-research-prompts-2026-09-06.md`. Both land on the same
single closest precedent by name, from different research paths — the
strongest convergence of this whole research thread.

## Verdict

**Real precedent exists, and it's more mature than expected — but nothing
combines it with a persistent, evolving campaign premise or a genuinely open
license.** The gap both passes independently identify is exactly the one this
whole brainstorm keeps circling back to: an autonomous, asset-grounded,
in-world GM is a solved-enough problem; a GM that also *holds a long-horizon
story it's telling*, not just a queue of isolated beats, is not.

## The closest precedent: IntelEngine (a SkyrimNet plugin)

Both passes name **`galanx/IntelEngine-GamePlugin`** as the standout, citing
near-identical specifics independently:

- Runs an autonomous **"Story Tick Interval"** (default ~3 in-game hours) —
  no player prompt required. Evaluates live world state (location, time, NPC
  memories/relationships, idle time) and either dispatches one of ~9-11
  parameterized story types or does nothing.
- **Story types, with real physical grounding**: Rescue (victim pre-placed in
  a real dungeon, bound to a prisoner-furniture marker or found injured in
  the boss room), Find Item (quest chest spawned in the boss room with a
  guardian), Combat (clear-this-location commissions), and "emergent
  interventions" — Ambush (from NPCs you actually wronged), Stalker, Courier,
  Informant, Road Encounter, NPC Gossip.
- **Native C++ asset grounding**: indexes the *actual load order* at launch
  (every cell, actor, tavern, home, shop) so semantic references ("the old
  tavern down the road") resolve to real FormIDs/coordinates instead of
  hallucinating them. Fuzzy/semantic spatial resolution for directional
  references ("go upstairs," "go outside").
- **Not pure LLM freeform** — the Claude pass adds a detail the Gemini pass
  didn't surface: the actual selection is a **multi-pass candidate filter**
  (Pass1/2/3 score and log every NPC as `ACCEPTED`/`skipped-<reason>`,
  building a pool of loaded-actor and location-mate candidates) and *then*
  the LLM picks a story type from a constrained "Available Story Types" menu,
  steered by anti-repetition and scarcity rules ("strike where it hurts,
  roughly 1 in 4-6 dispatches"). Same "engine filters/decides, LLM renders or
  selects" pattern found everywhere else in this research arc.
- **Navmesh/travel recovery**: soft package resets, progressive teleportation
  (nudging a stuck NPC toward their destination in decaying hops), and a
  safety timeout that cleans up and logs a "no-show" if an encounter times out
  unattended — solves the real problem of dispatching NPCs across unloaded
  cells without them getting stuck.
- **The identified gap, independently, in both reports**: IntelEngine is
  *episodic*. Each story beat is generated, resolved, and forgotten as an
  isolated occurrence — no slow-tick "campaign architect" synthesizes
  completed beats into an evolving multi-act premise, manages long-horizon
  pacing, or cascades a completed rescue's political fallout into later
  events. The Claude pass estimates this at "70-75% of a full tabletop-style
  Dungeon Master architecture" — strong, but missing exactly the piece this
  brainstorm keeps landing on as the actually novel part.

## Licensing — confirmed directly, not just cited

Both external reports and this session's own direct inspection of the
SkyrimNet source archive agree: **SkyrimNet and IntelEngine ship no LICENSE
file anywhere** (all rights reserved by default). This session downloaded and
extracted `SkyrimNet-GamePlugin-vbeta25-rc6.zip` directly — confirmed no
`.cpp`/`.h`/`.dll`/`.pex`, no LICENSE, only prompt templates, Papyrus scripts,
and web-dashboard assets ("public facing files" only; the actual native C++
engine is closed and never published as source). **Study the architecture
freely, do not depend on or copy the code.**

## Other real precedent, ranked below IntelEngine

- **SkyrimNet's own built-in GameMaster** — the substrate IntelEngine builds
  on. Autonomous, but dialogue-level only: it "does not generate dialogue
  directly, it selects high-level actions" (StartConversation/
  ContinueConversation/Narrate/None) from a "Scene Plan" (summary, tone,
  central_tension, ordered beats, potential_escalations) — the published
  `gamemaster_action_selector.prompt` schema is a genuinely reusable *idea*
  (it's a public prompt, not proprietary code) for what a "loose evolving
  premise" data shape could look like.
- **CHIM/HerikaServer** — "Director Mode," an "AI Quest Manager," "AI Quests
  V1 (BETA)" — real, open repo (`abeiro/HerikaServer`, MIT per earlier
  research), but the quest-authoring layer is explicitly beta and thin on
  documentation relative to IntelEngine.
- **Calradia Chronicle's "The Living Saga"** (Mount & Blade II: Bannerlord,
  Claude pass only, not found by Gemini) — an AI authors serialized campaign
  chapters ("a real, playable event... grounded in what you have actually
  done, your grudges, your nemesis, the fiefs you took... two real choices
  and real consequences"), each chapter remembering the last. **Its safety
  invariant is the single most quotable design rule from either report: "The
  AI only ever writes the narrative and the two choices; the mod owns every
  mechanic and validates every name against the real world."** Restrictively
  licensed (no redistribution/modification) — idea-only, not code to reuse.
  A companion project (`NpcMemoryService` SDK, LogRaam) is architecturally
  close to Chronicle's own social-sim service.
- **Ashby et al., CHI 2023** (BYU) — knowledge-graph-grounded quest
  generation: the LLM is *prohibited* from emitting quest text directly,
  instead selects valid entity tuples from a knowledge graph that guarantee
  every generated objective references a real, obtainable asset. Code is
  public, paper is citable — the single cleanest, license-safe academic
  precedent for the "never hallucinate a non-existent quest target" problem.
- **Borawski et al. 2026** ("From World-Gen to Quest-Line," arXiv) — a
  4-stage dependency pipeline (World Construction → Entity Generation →
  Campaign DAG → Quest Expansion) enforcing structured JSON between each
  stage so a macro campaign planner and a local quest expander can't
  contradict each other. Text/JSON only, no live 3D world, but the layering
  concept is exactly the "slow campaign architect + fast local expander"
  split this brainstorm's third research prompt is chasing.
- **Cautionary tale**: GTA V's "Sentient Streets" (Inworld Character Engine,
  hand-authored mission + LLM dialogue only, not quest authoring) reached
  ~100,000 YouTube views before Take-Two DMCA'd it in 2023. A real example of
  a AAA publisher enforcing IP against an LLM-narrative mod — worth keeping
  in mind if Chronicle's GM layer ever ships publicly, though Bethesda's
  modding community operates under much more tolerant norms than GTA
  Online's live-service economy.
- Mantella, Baldur's Gate 3 and Bannerlord's Inworld mods, and Cyberpunk
  2077's LLM-NPC mods were all checked and confirmed to do dialogue/ambient
  behavior only, explicitly rejecting dynamic quest/world-state authoring
  (Mantella's own GitHub issue #628 states this as an out-of-scope design
  choice, citing save-bloat and Papyrus-stability risk).

## Relevance to Chronicle

Confirms the verdict from report 51 (NarrativeEngine-P survey) a second time,
independently: **no surveyed system combines (a) a persistent, evolving
campaign premise, (b) real open-world asset grounding, and (c) a genuinely
open license.** IntelEngine nails (b) but not (a) and fails (c); SENNA/report
52's academic candidates nail (a) in a text-only or tabletop context but not
(b); NarrativeEngine-P is the only MIT-licensed system with any version of
(a). The gap is real, not a research-agent artifact — three independent
research passes (this session's own fork, plus Gemini and Claude on this
specific prompt) now agree on it.
