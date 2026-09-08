<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/chronicle-title-light.svg">
  <img src="docs/assets/chronicle-title-dark.svg" alt="Chronicle" height="80">
</picture>

![status](https://img.shields.io/badge/status-v0.1%20done%2C%20v0.2%20bridge%20building-blue)
![python](https://img.shields.io/badge/python-3.12%2B-blue)
[![docs site](https://img.shields.io/badge/docs-bytebard97.github.io%2FChronicle-8892c9)](https://bytebard97.github.io/Chronicle/)

Chronicle is an external social-simulation service for Skyrim SE/AE.
Every named NPC gets beliefs with provenance and strength attached.
Rumors spread and mutate as they pass from person to person. Grudges and
obligations build up from what actually happened, not from a quest flag,
and all of it feeds back into the game as behavior you can actually see.
Full docs live on the [GitHub Pages site](https://bytebard97.github.io/Chronicle/).

Here's the scenario I keep testing against: you assassinate the Jarl of
Whiterun. In vanilla Skyrim that's a quest trigger. In Chronicle it's a
succession contest shaped by the court's real relationships, an economic
hit to merchants who depended on him, a rumor that's already mutated by
the time it reaches Riften, and guard patrols that shift because of what
the simulation computed, not because a script branch fired.

**Where this is going next:** the headline is shifting from "NPCs
remember what you did to them" to **the world has its own agenda, and
you can watch it move.** The civil war and dragon attacks turn into
living, multi-phase conflicts, delivered through Bethesda's own Radiant
Story engine, cast with real named NPCs whose grievances the player
actually shaped. Everything above (belief, rumor, grudge) isn't going
away. It becomes the epistemology underneath that headline instead of
the headline itself. See [`docs/vision-v3.0.md`](docs/vision-v3.0.md)
for the full pitch, and [Where this is going](#where-this-is-going)
below for the three-phase build order, including where an LLM enters
at all. That's later than you'd think.

## How it works

Chronicle is really two programs talking over plain HTTP: a small C++
plugin living inside the Skyrim process, and a Python simulation service
running natively on the host. The plugin doesn't simulate anything, it
just reads and writes game state and relays events. Every bit of actual
social reasoning (who believes what, how a rumor mutates, when a grudge
cools) happens outside the game entirely. That's the part that let me
test and replay the whole simulation for months before ever pointing it
at a running copy of Skyrim. Everything under `chronicle/` never
imports anything Skyrim-specific -- it would run the exact same way
against a different game entirely. The only place allowed to know
Skyrim exists is `adapters/skyrim/`.

These mechanisms are all built, compiled, and now confirmed writing
correctly against a real, running game. See Project status below for
exactly what's verified and what's still open.

The full architecture diagram, and the state machines for how a rumor
spreads and mutates, how a rumor ages (heard, repeated, dormant,
forgotten), and how a grudge turns into visible avoidance, all live on
the [docs site's diagram page](https://bytebard97.github.io/Chronicle/diagrams.html) --
kept off this page so the front door stays readable.

## Read next

| | |
|---|---|
| [`docs/vision-v3.0.md`](docs/vision-v3.0.md) | The current pitch: the world has its own agenda. What changed from v2.2 and why, the three-phase build order, the two north-star tests. |
| [`docs/vision-v2.2.md`](docs/vision-v2.2.md) | Superseded, kept for history: the original belief/rumor/grudge-first pitch. Still accurate about the machinery, just no longer the headline. |
| [`docs/architecture.md`](docs/architecture.md) | The event-sourced core, the three-tier belief architecture, the Substrate Abstraction Layer, deployment target. |
| [`docs/decisions/`](docs/decisions/) | Numbered ADRs and `open-questions.md`: the project's working memory for every design tension research surfaced. |
| [`docs/research/00-index.md`](docs/research/00-index.md) | Every research report behind this design, with tagged findings and merged build-on/risk lists. |

## Project status (August 2026)

Short version: the headless engine works, the Skyrim bridge compiles and
deploys, and every write path has now been checked against a real,
running game. Here's where each piece actually stands.

The v0.1 headless sim is done. `docs/v0.1-spec.md`'s ~20-rule budget is
implemented and scenario-tested: the claim/variant/belief store with the
rumor stage machine (`chronicle/claims.py`), the social-state store for
relationships, grudges, obligations and observer-local reputation
(`chronicle/social.py`), and schedule-driven encounter sampling
(`chronicle/schedule.py`, `chronicle/propagate.py`). None of it needs a
Skyrim install to build, run, or test. Schedules and relationships for
the v0.1 Whiterun cast are still hand-seeded (`chronicle/fixtures/`)
rather than derived from a full simulation.

ChronicleBridge builds and deploys. Its 7 SKSE slices (C++,
CommonLibSSE-NG) cover live position streaming, death events, hydration,
avoidance, vendor markup via a barter-menu price hook, a crime-witness
cascade, and diegetic evidence, and the whole tree compiles clean. The
DLL plus a real 171-pair patched ESP install into a real MO2/Proton setup
and load correctly.

In-game validation is confirmed at the data level. A pytest harness
drives every slice against a live, running game over DevBench
(`adapters/skyrim/livetest/`), and 14 of its 16 checks pass: a real death
event lands in the run log under the right identity, a Chronicle grudge
turns into an actual vanilla relationship rank, an avoidance pair's
AI-package flag really flips, a vendor's markup multiplier caches
correctly off a barter-directed grudge, and an evidence object spawns
and survives a cell reload. The 2 failing checks share one bug: reloading
a save through the test harness currently silently does nothing, I've
dug into it a while and still haven't root-caused it (see
`docs/design/simple-modlist-milestone.md` for the gory details).

What's not confirmed yet is whether any of this is visible to a player.
Everything above proves ChronicleBridge's writes land correctly in game
state, not that you'd notice a change on screen, e.g. two NPCs actually
walking apart in real time rather than a flag flipping somewhere. Closing
that gap is M5.

Named-cast coverage sits at 19 of 28: `IdentityMap.cpp`'s `kNamedCast`
resolves 19 of Whiterun's 28 live-captured NPCs to a Chronicle identity
(up from 1 at the start of this), and the rest stream as generic
fallbacks the current rules can't act on yet.

| Milestone | What it means | Status |
|---|---|---|
| M0: Headless proof | Belief cascade (Jarl dies → rumors spread → grudges form), scenario-tested, no game required | Done |
| M1: Bridge compiles | All 7 ChronicleBridge slices build clean against CommonLibSSE-NG | Done |
| M2: Bridge deploys | DLL + patched ESP in a real MO2 install, listener wired, ready to launch | Done |
| M3: In-game validation | Every slice confirmed live via an automated test harness | Substantially done (14/16 checks pass; save/load persistence is the one open bug) |
| M4: Named-cast coverage | Resolve the remaining 9 of 28 Whiterun NPCs to Chronicle identities | Mostly done (19/28, 9 remaining, see `docs/design/next-phases-2026-08.md` §0c) |
| M5: Visible "out" direction | A player watching the screen actually perceives the sim's effect, not just the underlying state change | Next |
| M6: Player-shareable | Downloadable artifact, install instructions, save-safety guarantee | Blocked on M5 |

See `adapters/skyrim/README.md` for per-slice status and
`docs/design/next-phases-2026-08.md` for the current plan.

## Where this is going

The headless engine and bridge are the foundation, not the goal. The
plan is three phases, and I drew the dividing lines on purpose. Most
importantly: **no LLM appears until Phase 2, and no LLM is ever
allowed to decide simulation outcomes, only to render or voice ones the
deterministic engine already computed.** Each phase is a designed,
claimable problem, not a vibe (see `docs/vision-v3.0.md`,
`docs/decisions/`, and the open issues).

### Phase 1: the world, with no LLM anywhere

This is the current headline (`docs/vision-v3.0.md`): the civil war and
dragon crisis become **multi-phase conflicts with real casualties and
consequences**, delivered through Bethesda's own Radiant Story engine
rather than a competing quest system, and cast with real named NPCs
whose grievances and loyalties the player actually shaped. Everything
already shipped (belief, rumor, grudge, obligation, roles and
succession, the "How it works" section above) becomes the
epistemology underneath that headline: the data the world-event layer
draws on to decide who gets cast, what a rumor says by the time it
reaches the third county, and why a given NPC broke down instead of
shrugged.

Still to build in this phase, all of it deterministic and headless-
testable: storylet role-casting on Radiant Story, named relationship
states with a founding memory a player can ask about ("Crystallization,"
basically why the market turns to look at you), a production-rule reaction
layer mapping event + belief + sentiment to a bark/expression/approach/
exit tier, per-observer Dread (the same rumor lands as fear in one NPC
and respect in another), Secrets/Hooks leverage (the player's one
outward-acting verb), an off-screen pacing director, and a
conversational-ladder gate that makes NPCs take warming up. Design work
for the shared foundation these lean on is filed at
[`docs/design/social-mechanics-v3-foundation.md`](docs/design/social-mechanics-v3-foundation.md).
A player could run the entire Phase 1 pitch with zero language models
installed.

### Phase 2: the simulation gets a voice, and I'm keeping it narrow on purpose

Two things, and only two things.

First, NPC dialogue rendering: a local LLM speaks an NPC's already
computed belief state out loud. It never decides anything, since the
deterministic engine upstream already did that; it just renders.
Sized for consumer hardware on your own LAN (targeting a 27B-class
open-weights model on about 64GB of unified memory), not a cloud API.

Second, player persona and intent-driven dialogue
([ADR-0011](docs/decisions/0011-player-persona-and-voice.md)). You
author your character's personality once, the way you already author
their face: a trait profile (Big Five plus a few D&D-fluent stats),
mannerisms, a voice. That compiles into a "voice card" the model never
sees raw trait numbers from. In conversation you pick an intent
(negotiate, deceive, intimidate, charm, and so on) and the engine
generates 3-5 candidate lines in your character's actual voice, in one
call, so you confirm the real words instead of a paraphrase. That's
the Fallout 4 dialogue-wheel failure this is meant to avoid. Committed
lines feed straight into the rumor engine as claims. A boast you make
in Whiterun can end up in Riften, mutated along the way, with
deception scaled by your charisma stat and the listener's existing
disposition toward you. What you say has consequences because what
you say becomes evidence.

Left out of Phase 2 entirely: an LLM authoring or deciding any story
content. That's Phase 3, and it waits until this phase's NPC voice and
player dialogue are proven against a world that's already fully
reactive without them. That gives the much harder GM problem a stable
foundation instead of a moving target.

Down the line inside this phase, committed dialogue also gets rendered
as audio through a small local voice model, one original synthetic
voice per NPC. One hard line I'm not moving on: no cloning Skyrim's
voice actors, or anyone's voice, without documented consent. Every
voice Chronicle ships will be original or properly licensed.

### Phase 3+: the LLM storyteller, and the harness that makes it safe

An LLM-authored director layered on top of Phase 1's world-event
machinery. It generates storylet content and scene framing beyond
template interpolation, not just casting real NPCs into pre-authored
shapes. The harder engineering problem, and the bulk of the work here,
is the harness underneath it: a **hierarchy of GM agents operating at
different timescales.** A slow campaign-architect tier holds a loose,
evolving premise. A mid tier advances hold-by-hold state. A fast
per-scene renderer handles the moment-to-moment. Keeping all three
synchronized, without the prose-replanning drift that sinks naive
versions of this idea, is most of the actual challenge. See
`docs/research/49-56` (HAMLET, StoryVerse, Dramatron, Story2Game) for
the comparative-systems research this design will draw on.

This is genuinely open-ended, not one clean milestone. I'd guess it
runs Phase 3 through 5 or 6 by the time it's actually built. Candidate
shape, not a committed plan: an early phase getting one timescale
working end to end (probably the mid, hold-advancing tier, since
Phase 1 already gives it real state to advance), then adding the slow
campaign-architect tier once that's proven, then the fast per-scene
renderer, then a phase purely on keeping the tiers synchronized
without drift. Each one only gets scoped for real once the phase
before it ships and shows what the next one actually needs.

### Getting involved

If you want to get involved, the open problems worth collaborating on
are co-save sync across save/reload (ADR-0005's C++ half), runtime
package injection to replace NPC-record overrides, in-game validation
of the write paths, and Phase 1's new world-event-layer design work.
Each one has its own issue with acceptance criteria.

## Development

Requires [uv](https://docs.astral.sh/uv/), which installs the right Python
(3.12+) automatically.

```sh
uv sync      # install dependencies
make test    # uv run pytest
make lint    # uv run ruff check .
make sim     # uv run python -m chronicle -- inspect/trace/feed/inject subcommands (chronicle/cli.py)
```

**Layout**: `chronicle/` is the pure-Python simulation engine. It never
imports anything Skyrim-specific. `adapters/skyrim/` is the only place
allowed to know Skyrim exists. `dashboard/` is the debug/observability web
UI (first-class, not an afterthought, see `docs/vision-v3.0.md` §4).
`scenarios/` holds headless regression scenarios with asserted outcomes.
`notes/` is working memory: `inbox/` for unprocessed material, `daily/`
for session notes, `ideas.md` for unsorted ideas and action items.
