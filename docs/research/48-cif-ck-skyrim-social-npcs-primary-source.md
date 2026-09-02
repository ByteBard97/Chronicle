# CIF-CK / "Social NPCs": direct primary-source read

**Date:** 2026-09-01
**Method:** Direct primary-source reads by Claude (not an external dispatch — both sources
turned out to be freely accessible, so no research agent was needed): the full text of
Guimarães, Santos & Jhala, "Prom Week meets Skyrim: Developing a Social Agent Architecture in
a Commercial Game" (AAMAS 2017, fetched in full via PDF), and a WebFetch-summarized read of
the 2022 follow-up, "Emergent social NPC interactions in the Social NPCs Skyrim mod and beyond"
(arXiv:2207.13398). Answers Prompt 48 from `notes/deep-research-prompts-2026-08-31.md`,
which reports 42/43 both flagged as the most relevant unread prior art in this whole research
batch. **The mod itself is real and downloadable** — see "Availability" below.

---

## Availability

"Social NPCs" is a real, publicly shipped Skyrim mod (not just a paper), released 2016-08-25/26:
- Steam Workshop: [steamcommunity.com/sharedfiles/filedetails/?id=751622677](https://steamcommunity.com/sharedfiles/filedetails/?id=751622677)
- Nexus Mods (original Skyrim): [nexusmods.com/skyrim/mods/77792](https://www.nexusmods.com/skyrim/mods/77792)
- Nexus Mods (Special Edition, two listings): [mods/70520](https://www.nexusmods.com/skyrimspecialedition/mods/70520), [mods/96446](https://www.nexusmods.com/skyrimspecialedition/mods/96446)

The underlying social-reasoning architecture (Comme il Faut, reimplemented in C#) is open source
as part of the FAtiMA Toolkit: [github.com/GAIPS/FAtiMA-Toolkit](https://github.com/GAIPS/FAtiMA-Toolkit)
(the toolkit's own site lists "Comme il Faut (CiF-CK Asset)" as a bundled component). The
Skyrim-specific Papyrus/SKSE glue code's public availability as a standalone repo was not
confirmed — not found in search — but Skyrim mods conventionally ship `.psc` script source
alongside compiled `.pex` files inside the mod archive itself, so downloading "Social NPCs"
directly may hand over that layer even without a dedicated GitHub repo.

---

## 1. The volition-to-Skyrim mapping, exactly

This is fully and explicitly specified in the paper's Table 1 (reproduced below) — there is no
ambiguity here, unlike what a secondhand read suggested.

| CiF concept | Creation Kit mapping |
|---|---|
| Social Exchange (Name) | **Quest ID** |
| Intent | Declared in the quest's **final stage**, guaranteeing it only fires if the quest completed |
| Preconditions | **Quest Start Conditions**, declared in the initial stage |
| Initiator Influence Rules | A separate **"Influence Rules" script**, computed *before* the Social Exchange starts |
| Responder Influence Rules | Computed *after* the Social Exchange starts |
| Effects | Creation Kit's built-in **Success/Failure quest stages** |
| Instantiations (the actual performance) | **Quest Scenes** — the dialogue/movement/animation Skyrim already has as a native construct |

The decision rule itself is a simple greedy argmax, stated verbatim: *"the character calculates
the volition of the possible actions and chooses to execute the one with the highest positive
volition."* Twelve social-move types exist as twelve distinct quests (`SocialMoveFlirt`, etc.),
each filling an **Initiator Alias** and **Target Alias** — Skyrim's native quest-alias mechanism,
used exactly as designed (aliases let one quest be reused with different participants at
runtime rather than being hand-authored per NPC pair).

Character-level state (Table 2 in the paper): Traits and Status are "a list of variables that
affect social exchanges" (5 traits: Friendly/Charming/Hostile/Shy [+1 unnamed]; 4 statuses:
Embarrassed/Angry At/Drunk/Dating), each with a direct, named numeric effect on volition (e.g.
"Friendly: higher volition for Friendly Social Exchanges"; "Drunk: higher probability of
performing any Social Exchange"). **Prospective Memory** — an NPC's standing desire to perform
a future social move toward a specific target — is implemented as literally "a set of quests
with specific actors (Targets)," i.e. pre-instantiated, not-yet-started quest instances sitting
ready with their aliases filled.

**Direct relevance to Chronicle's own open menu-ranking question**: CIF-CK's answer is the
simplest possible one — compute volition (a rule-weighted scalar) for every eligible move,
pick the single highest. There is no reported ranking/shortlisting logic beyond that, and no
evidence they needed one at their scale (7 NPCs, 12 move types). This is a *much* simpler
mechanism than Chronicle's own scenario-ladder's rule registry, but it validates the core shape
Chronicle already assumed: an inspectable, rule-computed score standing in for "what should
this character do," decided *before* any rendering happens.

## 2. Social Facts Database storage — the real mechanism, and what's unresolved

The Creation Engine has no database concept and Papyrus (Skyrim's scripting language) is
explicitly described in the paper as "quite limited" for complex data structures. CIF-CK's
actual workaround, stated directly: **the Player actor is the only entity guaranteed to always
exist and be reachable from any script, at any time**, via `Game.GetPlayer()`. So:

- **Public state** (Relationships, the Social Facts Knowledge Base itself) is stored as static
  data attached to the **Player entity**, reachable globally.
- **Private state** (Social Networks — the two pairwise scalars, Attraction and Friendship —
  and the Cultural Knowledge Base) is stored **per-Character**, i.e. as script variables local
  to each individual social NPC's own script instance, not centralized at all.

There is no "database" in Chronicle's sense — it's two script-variable storage tiers (one
actor, many actors), not an event log or queryable store. **Persistence across save/reload is
not discussed by either paper as a design decision** — it's neither confirmed working nor
flagged as broken. The likely (unconfirmed) reality: Papyrus script variables attached to
persistent-reference actors are automatically part of Skyrim's save-file serialization as a
basic engine property, so this plausibly worked "for free" without the authors needing to
solve it deliberately — but this is inference, not something either paper states.

**Direct relevance to Chronicle**: this confirms (does not just suggest) that Chronicle's own
hardest unsolved problem — save/reload-safe, queryable, provenance-tracked social state at
scale — was never actually attempted by CIF-CK. They found a clever but narrow trick (piggyback
on the Player actor's guaranteed reachability) for a 7-NPC deployment; nothing here scales to
Chronicle's "every named NPC, provenance chains, propagating claims" ambition. This sharpens,
rather than undercuts, report 37's finding that nobody in this space has solved ADR-0005.

## 3. What a player actually saw and clicked

Confirmed exactly — this is a native Skyrim dialogue menu, not a custom UI. When talking to a
modded NPC, the player got these injected dialogue topics (paper's own list, verbatim):
Greet (if not yet met), Offer a gift (from inventory), Compliment, Insult, Flirt, Ask out,
Propose, Break up (if dating), "Bad Mouth" another nearby NPC, "Recommend" another nearby NPC
to this one. Each choice fires the matching Social Move quest exactly as NPC-initiated moves
do (same `CIFCKRules` scoring for accept/reject), and the response comes back as ordinary
Skyrim dialogue. **No free text, no special interface — plain topic-list dialogue, populated
dynamically per-NPC by the mod.** This is a real, shipped precedent for exactly Chronicle's
own "engine computes a menu, player taps an option" design, at the crudest possible fidelity
(fixed generic verbs, not grounded parameterized intents).

## 4. Scale and scope actually shipped

Small and explicit: **7 NPCs across 2 locations** (Honningbrew Meadery, and a custom-built
"Comme il Faut House"), 12 social move types, 5 traits, 4 statuses, tested via two scenarios —
a scripted "Quest Scenario" (a bounded narrative built around specific characters) and an
"Open Scenario" (sandbox, closer to Prom Week's own design, to see whether players create
their own stories with no directed goal). The paper is explicit that this is a proof of
concept, not full-game coverage — and notably, a later attempt (per the 2022 follow-up) to
port the same architecture to Conan Exiles/UE4 reportedly still had the Cultural Knowledge
Base and Social Facts Database "not yet fully implemented," suggesting the scaling/porting
problem was real and not just a Skyrim-Papyrus-specific artifact.

## 5. The actual evaluation — methodology and real numbers

This is much more rigorous than "positive Steam reviews," and worth citing precisely now that
the real numbers are in hand:

**Adoption (first 40 days):** 6,000+ unique players, 70,000+ mod-page visits, 93% Steam
approval (181 positive / 13 negative of 194 ratings), "Top Mod of the Week," 180+ comments
across Steam/Nexus/Reddit, "vast majority... very positive."

**A real voluntary survey**, linked from the mod page (self-selection bias acknowledged
implicitly, not corrected for): 124 respondents answered demographic questions (the typical
respondent: 5+ hours/week Skyrim player, 100+ hours total, 80% running 20+ other mods
concurrently); 23 respondents answered Quest-Scenario-specific questions (73% found the
CIF-CK-authored quest "more flexible" than a normal Skyrim quest; 95% enjoyed interacting with
the NPCs; 91% tried to manipulate NPCs toward their own goals).

**The Open Scenario comparison is the methodologically real result**: a 5-point Likert battery
was administered *twice* — once about "normal" Skyrim NPCs, once about the same NPCs with
CIF-CK enabled — and compared via Wilcoxon Signed-Rank tests, all significant at p<0.01:

- **NPC predictability dropped** with Social NPCs enabled (T=26, p=0.008, r=0.487) — players
  found them *less* predictable.
- **Comprehension of NPC behavior rose significantly** (T=24, p=0.001, r=0.582) — despite being
  less predictable, players understood *why* NPCs did what they did better than with vanilla
  NPCs.
- **Enjoyment rose significantly, with the strongest effect of the three** (T=0, p=0.000007,
  r=0.819).

The authors' own reading: NPCs did things players didn't expect, but the actions "made sense
and were plausible" — i.e. surprising in outcome, comprehensible in cause.

**This is a direct, real-data validation of Chronicle's own stated design doctrine.**
`docs/vision-v2.2.md` §5 names "Expected randomness" (credited to Fåhraeus) as a load-bearing
doctrine: *"surprising in outcome, retroactively explainable in cause."* CIF-CK's own survey,
independently and years earlier, measured exactly this pattern with real players and found it
produces higher enjoyment despite lower predictability. This isn't just thematically similar —
it's the same claim, empirically tested, by a system with a real (if small) player base.

## 6. Documented limitations and failure modes

Named directly by the authors, not inferred:

- **Papyrus is "quite limited"** for anything beyond simple script data — the entire
  Player-entity storage workaround (§2 above) exists because of this constraint specifically.
- **The engine only processes scripts for NPCs co-located with the player.** Quoted directly:
  *"any script associated with an NPC that is in a different place as the player will not be
  processed."* CIF-CK's NPCs only reason about other NPCs physically present with the player —
  there is no off-screen social simulation at all. This is the opposite of Chronicle's own
  design (which explicitly runs a headless math tier for off-screen NPCs) — CIF-CK simply
  didn't attempt that problem.
- **A deliberate performance compromise on trigger-rule timing**: ideally (per the authors)
  exchange outcomes would be computed *after* the initiating NPC's performance plays, but "this
  puts too much of a strain on the engine," so outcomes are computed *before* the scene plays
  and the scene is purely cosmetic playback of an already-decided result. Trigger rules
  (cascading consequences) are also evaluated only at quest-end, not continuously, for the same
  reason.
- **The project's own honest framing of its scope**, quoted verbatim from the conclusion: *"If
  a MSc student can do a project such as this one in nine months, with no budget whatsoever and
  no access to the source code, and can have very popular and successful results..."* — this
  was one person, one thesis, nine months, with no access to Bethesda's actual engine source
  (only the public Creation Kit modding surface). It is a proof of concept at real but modest
  scale, not a validated architecture for anything close to Chronicle's ambition.
- No bug reports, edge cases, or emergent-behavior failure modes are documented in either paper
  — this is a genuine gap in the source material, not something withheld.

## Verdict: does CIF-CK's mechanism transfer to Chronicle's menu-ranking design?

**Partially, and it's more useful as a confidence signal than as a mechanism to copy wholesale.**
The core shape — rule-computed, inspectable scores decide what's sayable; performance is
decided before it plays; the player interacts through ordinary dialogue topics — is exactly
Chronicle's own already-adopted principle, now with real shipped precedent and real (if
small-sample) player data behind it, including the specific "expected randomness" doctrine.

What does *not* transfer: CIF-CK's argmax-over-a-dozen-moves scoring is too simple for
Chronicle's much larger and more grounded intent space (parameterized tuples like
`(confront, rumor_id=X)`, not bare verbs), its storage trick doesn't scale past a handful of
NPCs and was never asked to survive save/reload, and its co-location-only constraint sidesteps
exactly the off-screen simulation problem Chronicle has already solved differently (the
headless math tier). Chronicle isn't missing a mechanism CIF-CK has and could borrow outright —
it's already past CIF-CK's scale and has already made different, deliberate choices (event
log instead of two script-variable tiers, off-screen simulation instead of co-location-only,
grounded parameterized intents instead of twelve fixed verbs) for the reasons CIF-CK's own
limitations demonstrate were necessary at any larger scale.
