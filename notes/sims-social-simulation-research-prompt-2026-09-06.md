# The Sims social-mechanics research prompt (2026-09-06)

One self-contained prompt for external web-research agents (Gemini, ChatGPT
with browsing, Perplexity, Claude, etc.) — paste as-is. Written because a
prior internal research pass found **no dedicated Sims research anywhere in
this project**, despite The Sims being repeatedly named as inspiration
("the Sims in Skyrim" is Chronicle's own vision-doc shorthand). The one hit
found was an incidental citation (Richard Evans's AIIDE paper on Sims 3's
AI) inside an unrelated paper, which claims Sims 3 scoped its social
simulation to only the currently-loaded lot — real, but thin, and not a
mechanics inventory.

Run this through 2-3 different tools if possible (matching how prior
research batches for this project were cross-checked) so findings can be
compared rather than trusted from a single pass.

---

## Prompt

I'm researching **The Sims franchise's social-simulation mechanics** — not
gameplay impressions or a fan-wiki summary, but the actual underlying
systems: what state is tracked, how it's structured, what triggers it, and
what it produces. This feeds a comparative-systems research library for
**Chronicle**, an external social-simulation mod for Skyrim SE/AE that
gives NPCs beliefs with provenance, lets rumors mutate as they spread
person-to-person, and tracks grudges/obligations that write back into
behavior (schedules, dialogue, disposition). The goal is to find out which
of The Sims' social mechanics are genuinely novel or well-designed enough
to be worth adapting into a walk-around, first-person RPG world, as
opposed to only working because Sims is a top-down household-management
game.

**Known starting point, don't re-report this, do go past it:** Richard
Evans (Sims 3's AI lead) published an AIIDE paper describing Sims 3's
architecture as forward-simulation plus a rule-based/utility-AI system,
and — this is the specific claim to verify or correct — that social
simulation was scoped only to Sims physically present on the
currently-loaded lot, with off-lot Sims essentially abstracted away rather
than simulated. If this is accurate, it matters a lot: it would mean even
The Sims never attempted "the whole town's social web evolves whether or
not you're watching," which is closer to what Chronicle is trying to do
than what Sims actually built. Confirm, correct, or add nuance to this
claim with a citable source (the paper itself, a GDC talk, a developer
interview), and say plainly if the claim doesn't hold up.

**Investigate, across as many Sims titles/expansions/mods as relevant
(base games, especially where a specific title changed the model
meaningfully — e.g., Sims 2's memory/aspiration systems, Sims 3's
personality/traits and open-world attempt, Sims 4's emotions/moodlets and
Get Together/City Living style group content, and well-documented
community overhaul mods like MCCC or WonderfulWhims if they meaningfully
extend the base social model):**

1. **Relationship representation.** How is the friendship/romance
   relationship between two Sims actually stored (a single scalar? a
   vector of multiple tracked axes? does it have anything resembling
   provenance — do Sims "know why" they like or dislike someone, or is it
   purely an accumulated number)? How does it decay, and under what rules?
2. **Social interaction catalog.** What is the actual menu/generation
   system behind an "interaction" (a scripted list picked by context, a
   scored/ranked autonomous choice, something generative)? How does an
   NPC-to-NPC (not player-involved) interaction get chosen and resolved
   autonomously, if it does at all?
3. **Memories and moodlets/needs.** How do specific remembered events (a
   fight, a wedding, a death) get represented, and how long do they
   persist and influence behavior? Is there anything like an evidence
   chain (a Sim "witnessing" something and forming a belief because of it,
   as opposed to a global flag)?
4. **Autonomous relationship formation and gossip.** Do Sims form or
   change relationships with each other independent of direct player
   action — e.g., two background Sims becoming friends or enemies on their
   own, an NPC learning something secondhand from another NPC (gossip)
   rather than only from directly witnessing it? If this exists, what
   triggers it and how far does it propagate?
5. **Personality/trait compatibility.** How do fixed traits modulate social
   outcomes (compatible vs. clashing personalities), and is this authored
   per-pair or computed from a general compatibility function?
6. **Group/household/family dynamics.** How are multi-Sim social units
   (households, friend groups, feuds) represented as more than the sum of
   pairwise relationships, if at all?
7. **The off-lot/background-simulation question** (the core thing to
   verify against Evans's claim above): what actually happens, mechanically,
   to a Sim's relationships and social state while they are not on the
   currently-loaded lot? Fully frozen? Some lightweight abstraction?
   Anything resembling Chronicle's own "fake movement, honestly simulate
   belief" split?

Cite specific sources wherever possible: developer talks (GDC vault),
published interviews, patch notes, wiki pages with primary sourcing, or
academic papers analyzing Sims AI. General impressions without a citable
source are much less useful than "the Sims 4 wiki's Emotions page
describes mechanic X" or "EA's own Sims 3 postmortem states Y."

**End with a verdict:** which of the mechanics above, if any, are
genuinely "world-scale" (the social web evolves believably without the
player watching or participating), versus "player-scale" (only meaningful
because the player is directly steering one household)? Given that
Chronicle's own gap is specifically "the world reacts to the player and to
big events, autonomously, whether or not the player is present," state
plainly whether The Sims is strong precedent for that goal or weak
precedent (as the one existing citation suggests), and which specific
mechanic, if any, is the strongest candidate worth adapting despite that.
