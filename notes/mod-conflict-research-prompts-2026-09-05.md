# Chronicle mod-conflict research prompts

Four prompts for external web-research agents (Gemini, ChatGPT with browsing,
Perplexity, etc.), investigating which popular Skyrim mods Chronicle's
game-side write paths could conflict with. Background section first, then
one self-contained prompt per subsystem — paste each prompt individually
into a research agent, they don't need to be run together.

## Background (read this before researching any of the four prompts below)

Chronicle is a Skyrim SE/AE mod that runs an external social-simulation
service (beliefs, rumors, grudges, obligations for named NPCs) outside the
game process, and a C++ SKSE plugin (`ChronicleBridge`) that relays events
in and writes simulated consequences back into the live game. The
simulation side is not relevant to these conflict questions — what matters
is the four concrete ways ChronicleBridge writes into Skyrim's own game
state today. All four are already built (verified from source, not
inferred from documentation), though not yet verified against a live,
long-running playthrough.

**Scope is narrow and specific, not "the whole game."** Every write path
below currently touches only 19 named NPCs, all residents of Whiterun:

> Ysolda, Idolaf Battle-Born, Saffir, Carlotta Valentia, Amren, Adrianne
> Avenicci, Lars Battle-Born, Braith, Fralia Gray-Mane, Nazeem, Lillith
> Maiden-Loom, Brenuin, Anoriath, Lucia, Heimskr, Sigurd, Olava the Feeble,
> Danica Pure-Spring, Olfina Gray-Mane

Research should focus on what happens when other popular mods also touch
these specific NPCs or these specific game mechanisms, not general Skyrim
compatibility theory. Cite specific mod pages, source repos, wikis, or
compatibility-patch threads wherever possible — general impressions
without a citable source are much less useful than "mod X's page says Y"
or "mod X's source does Z."

The four write paths:

1. **AI package / schedule override.** A headless Mutagen (C#, .NET)
   patcher authors new "Flee" packages and directly overrides the
   `AIPackages` list on the 19 NPCs' base records, gated by global
   variables the C++ plugin flips at runtime (calling
   `Actor::EvaluatePackage` to force reevaluation). This is a direct edit
   to each NPC's base record's package list, not a runtime alias
   injection — meaning it's a normal Bethesda-plugin-format record edit,
   subject to ordinary load-order "last plugin wins" conflict rules.
2. **Native vendor-price hook.** The C++ plugin overwrites a function
   pointer in `RE::BarterMenu`'s C++ vtable (the slot for `PostCreate`) to
   intercept and adjust displayed buy/sell prices in the vanilla barter
   UI, based on the player's social standing with the vendor. This is a
   binary-level hook (CommonLibSSE-NG/SKSE64), not a Papyrus script or a
   record edit.
3. **Relationship-rank writes.** The C++ plugin writes vanilla NPC
   relationship rank (the same field read/written by
   `GetRelationshipRank`/`SetRelationshipRank` — values like
   Confidant/Ally/Lover/Friend/Neutral/Rival/Enemy/Archnemesis) for the 19
   named NPCs at runtime, driven by simulated grudges and rumors.
4. **Persistent object spawning.** The C++ plugin spawns physical
   "evidence" objects into the world at a believer NPC's live position via
   `PlaceObjectAtMe(..., forcePersist=true)`, i.e. a permanent, save-bloat-
   relevant created reference, not a temporary/toggleable one.

Two other things ChronicleBridge does are **not** worth researching —
they're passive, multi-subscriber SKSE event listeners with no write
behavior and essentially zero conflict risk: a `TESDeathEvent` sink and a
`MenuOpenCloseEvent` (BarterMenu open/close) sink. A position-tracking
poller that only reads NPC coordinates is similarly zero-risk. Don't spend
research budget on these.

---

## Prompt 1 — AI package / schedule conflicts (highest risk)

I'm building a Skyrim SE/AE mod, Chronicle, that authors a patch (via
Mutagen, headless) directly overriding the `AIPackages` list on 19
specific named NPC base records in Whiterun: Ysolda, Idolaf Battle-Born,
Saffir, Carlotta Valentia, Amren, Adrianne Avenicci, Lars Battle-Born,
Braith, Fralia Gray-Mane, Nazeem, Lillith Maiden-Loom, Brenuin, Anoriath,
Lucia, Heimskr, Sigurd, Olava the Feeble, Danica Pure-Spring, and Olfina
Gray-Mane. It adds new Flee-type packages gated by a global variable, and
calls `Actor::EvaluatePackage` at runtime to force reevaluation.

Research which of the most popular Skyrim SE mods (by Nexus download
count / endorsement count) also edit the AI packages, schedules, or base
records of these exact 19 NPCs, or move Whiterun NPCs between
locations/schedules generally. Specifically check: AI Overhaul (SE),
Immersive Citizens - AI Overhaul, Populated Cities Towns Villages, JK's
Whiterun (record-level, not just visual), Cutting Room Floor, and any
Whiterun-specific overhaul mods. For each, report: (a) does it touch these
specific NPCs' AIPackages/schedule records, (b) is the conflict a "last
plugin in load order wins" record-level clash (silently drops one mod's
edits) or something patchable via a bashed/xEdit merge patch, (c) does the
wider modding community already have an established compatibility patch
pattern for mods that touch this same territory (e.g. a standard "load
after" convention, or a known patch hub). Cite specific mod pages, wikis,
or compatibility-patch threads, not general impressions.

---

## Prompt 2 — Native vendor-price hook conflicts

Chronicle, a Skyrim SE/AE SKSE plugin (built on CommonLibSSE-NG),
installs a price-markup feature by overwriting a function pointer in
`RE::BarterMenu`'s C++ vtable (specifically the slot for `PostCreate`) to
intercept and adjust displayed buy/sell prices in the vanilla barter UI,
based on the player's social standing with the vendor.

Research: (1) are there other popular, currently-maintained SKSE plugins
or native DLL mods that also hook, detour, or vtable-patch
`RE::BarterMenu` or otherwise programmatically alter vendor prices at the
native code level (not through Papyrus `SetActorValue` scripts) — check
things like Trade & Barter-style economy overhaul mods, "Better Barter",
"Trade Routes", or any mod using CommonLibSSE-NG/SKSE64 with barter/vendor
in its feature list; (2) is there a known-safe pattern in the SKSE plugin
community for multiple plugins hooking the same vtable slot without one
silently overwriting the other (e.g. calling through to the previous
function pointer, or a shared detouring convention like SKSE's
`Trampoline`); (3) are there any GitHub issues, mod comments, or
compatibility reports describing crashes or price-calculation conflicts
between two native plugins both touching BarterMenu. Cite specific repos,
mod pages, or issue threads.

---

## Prompt 3 — Relationship-rank writes vs. dialogue/marriage/follower mods

Chronicle, a Skyrim SE/AE mod, writes vanilla relationship rank (the same
field used by `GetRelationshipRank`/`SetRelationshipRank`, values like
Confidant/Ally/Lover/Friend/Neutral/Rival/Enemy/Archnemesis) for 19
specific named Whiterun NPCs at runtime, driven by its own simulated
grudges and rumors — potentially overwriting or being overwritten by other
systems that touch the same field.

Research which popular Skyrim SE mods read or write relationship rank at
runtime for generic/named townsperson NPCs (not just the player's official
spouse or followers), including: Relationship Dialogue Overhaul (RDO), any
"Interesting NPCs" relationship-tracking systems, marriage-expansion mods,
and follower-trust/loyalty frameworks (e.g. Extensible Follower Framework,
Amazing Follower Tweaks) if they touch non-follower townsfolk. For each,
determine whether it's a genuine race condition (two systems repeatedly
overwriting the same value, "flapping" behavior) or a one-directional
dependency (one reads what the other sets, safely). Cite specific mod
pages, forum threads, or source code if available.

---

## Prompt 4 — Physical object spawning + NPC relocation conflicts

Chronicle, a Skyrim SE/AE mod, spawns persistent physical "evidence"
objects into the world at the live position of specific named Whiterun
NPCs at runtime, via `PlaceObjectAtMe(..., forcePersist=true)`.

Research whether popular city/settlement overhaul mods that relocate,
re-schedule, or replace these NPCs (Immersive Citizens - AI Overhaul,
Populated Cities Towns Villages, JK's Whiterun, Alternate Start - Live
Another Life) could cause evidence objects to spawn in the wrong
location, inside geometry, or in a cell the NPC no longer regularly
occupies. Also check: is there a known Skyrim save-bloat problem
specifically from `forcePersist`/`0xFF`-prefixed created-reference objects
accumulating over a long playthrough, and do any popular mods or
community guides (e.g. FallrimTools/ReSaver documentation) describe this
as a real, player-visible issue worth avoiding. Cite specific sources.
