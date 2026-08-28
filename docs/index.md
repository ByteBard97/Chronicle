# Chronicle

**A world that remembers.** Chronicle is an external social-simulation
service for Skyrim SE/AE: it gives every named NPC beliefs with
provenance and strength, lets rumors spread and mutate as they pass from
person to person, tracks grudges and obligations from what actually
happened, and feeds all of it back into the game as behavior the player
can perceive and shape.

The north star: if the player assassinates the Jarl of Whiterun, that
should cascade -- a succession contest driven by the court's real
relationships, an economic ripple through dependent merchants, a rumor
that mutates as it travels to Riften, guard patrols that shift as a
*consequence* of the simulation, not a scripted quest branch.

[:material-github: View on GitHub](https://github.com/ByteBard97/Chronicle){ .md-button .md-button--primary }
[Read the architecture](architecture.md){ .md-button }

## Try it yourself

The headless simulation runs on any machine with no Skyrim install --
clone it, run three commands, watch 358 scenario tests pass in under
four seconds:

```sh
git clone https://github.com/ByteBard97/Chronicle.git
cd Chronicle
uv sync && make test
```

## The dashboard, live against a real run

![Chronicle dashboard map view: real Whiterun geography with rumor-stage overlay glyphs, live NPC markers, and a scrubbable timeline](assets/dashboard-map-screenshot.png)

*The map view of `dashboard/`, showing rumor-stage glyphs (unheard, heard,
repeated, dormant, forgotten) and NPC markers over a real Whiterun layout,
against the `north-star-01` scenario run. Not a mockup -- a screenshot of
the actual debug UI running against real simulation output.*

## How it works

{% include-markdown "../README.md" start="## How it works" end="## Read next" %}

## Project status

{% include-markdown "../README.md" start="## Project status (August 2026)" end="## Development" %}

*(This section is transcluded directly from the repository's own README
-- one source of truth, always current with the codebase.)*
