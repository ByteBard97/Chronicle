# NPC social-mechanics → Skyrim implementation brainstorm prompt (2026-09-06)

One self-contained prompt to run independently through several external
agents (Kimi, Fable, ChatGPT, or similar). **Attach or paste the full
contents of `docs/research/comparative-systems/npc-social-mechanics-catalog-2026-09-06.md`
alongside this prompt** — that catalog is the actual input; this file is
only the task instructions. Run each agent separately, without letting one
see another's output, so the independent passes can be compared and
synthesized afterward rather than converging on each other's phrasing.

---

## Prompt

### Background

I'm building **Chronicle**, a mod for Skyrim SE/AE: an external
social-simulation service (a Python engine) paired with a C++ game plugin
that reads/writes live game state. Its current core mechanic is that NPCs
form **beliefs with provenance** (they know things because they witnessed
them or were told, and the system never forgets which), beliefs travel as
**rumors that mutate as they spread**, and accumulated beliefs become
**grudges/obligations/reputations** that write back into behavior
(schedules, dialogue, disposition).

**The problem I need help solving:** I've decided grudge-tracking-between-
individual-NPCs, on its own, is not a compelling headline feature. My own
words on why: "boring — nobody will install a mod because grudges between
you and NPCs gets tracked." It's too small-scale (personal ledgers, not a
world in motion), too slow/invisible to notice moment-to-moment, and too
player-centric (only meaningful because of what *I* specifically did to
one NPC), rather than making the *world* feel alive and reactive on its
own — to the player's actions **and** to big world events like the civil
war advancing or a dragon attacking a town.

To find better material, I had a research pass compile an exhaustive,
uncurated catalog of every named NPC-social-system mechanic from six other
games/systems already studied in depth for this project: **Crusader Kings
II/III, Kenshi, Shadows of Doubt, the Nemesis System (Shadow of Mordor/
War), RimWorld, and Dwarf Fortress** — plus a cross-cutting section on
academic/shipped **AI-director and drama-management** systems (Façade,
Left 4 Dead's Director, RimWorld's Storyteller, DeepMind Concordia,
symbolic narrative planning, and a quantified record of LLM-narrator
failure modes from AI Dungeon through 2026 benchmarks). That catalog is
attached. It's deliberately not filtered or ranked — every mechanic the
source research turned up is in there, from the obviously-relevant to the
obscure.

### Your task

Go through **every single item** in the attached catalog — do not skip any
for brevity, do not pre-filter to "the interesting ones," treat the whole
document as the worklist. For each item, produce:

1. **One or more concrete Skyrim/Chronicle implementation concepts.** Not
   "this could inspire something" — an actual, specific mechanic: what data
   Chronicle would track, what would trigger it, what the player would
   concretely see/experience in Skyrim (a quest, a visible world change, an
   NPC behavior, a UI/dashboard element, a dialogue option). Ground it in
   Skyrim's real shape (holds, factions, the civil war questline, dragon
   attacks, radiant quest generation, NPC schedules/AI packages) rather
   than abstract game-design language.
2. **A compelling/fun rating** — High / Medium / Low — with a one-sentence
   justification tied specifically to: does this make the *world* feel
   alive and in motion (reactive to the player AND to independent events
   like the civil war or a dragon attack), or does it just add another
   personal-scale ledger entry? Be honest and critical here — I'd rather
   you flag an item as Low/skippable with a clear reason than force
   everything into being exciting.
3. **Feasibility notes**, specific to Chronicle's actual architecture: a
   headless Python sim as source of truth, a C++ SKSE plugin as the only
   game-aware code, Papyrus scripting as a last resort (slow, ~1.2ms/frame
   VM budget), no ability to alter Skyrim's base assets/geometry, and a
   design rule already in force that global reputation and Nemesis-style
   automatic rank-rewriting chains are both explicitly disallowed (patent
   and design-doctrine reasons). Flag anything that would need new
   research to implement responsibly (an unfamiliar Skyrim modding
   technique, an unverified claim, a legal/patent question) rather than
   guessing.
4. **Overlap check against what Chronicle already has.** State plainly
   whether this mechanic is (a) already essentially covered by Chronicle's
   existing belief/rumor/grudge/provenance engine and just needs better
   surfacing, (b) a natural small extension of that engine, or (c) a
   genuinely new subsystem Chronicle doesn't have any version of yet.

At the end of your pass, after covering every item:

5. **Your own ranked top 10** across the *entire* catalog (all games, not
   per-game quotas) — the ten you'd actually build first if you were
   picking Chronicle's new headline feature(s), each with a one-sentence
   reason.
6. **An explicit discard list** — items you rated Low that you think
   shouldn't even be reconsidered later, with why (this is as valuable as
   the top 10 — I specifically want a second opinion on what to cut, not
   just what to keep).
7. **Anything the catalog is missing** — if a mechanic you know of from one
   of these six games/systems (or a close relative) isn't in the catalog
   at all, say so and describe it; don't silently ignore gaps.

### Format requirements (important — this output gets merged with two other independent agents' passes)

Keep your per-item entries **short and structurally consistent** — a
title line matching the catalog's own item name, then the four numbered
fields above as a tight bulleted block, not prose paragraphs. This is
going to be diffed and merged against two other agents' independent
passes over the same catalog, so consistent structure matters more than
literary quality. Do not add a long introduction or conclusion beyond
what's asked for in items 5-7 above.
