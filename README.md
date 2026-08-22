# Chronicle

![status](https://img.shields.io/badge/status-research%20complete%2C%20entering%20build-blue)
![python](https://img.shields.io/badge/python-3.12%2B-blue)

**A world that remembers.** Chronicle is an external social-simulation
service for Skyrim SE/AE: it gives every named NPC beliefs with
provenance and strength, lets rumors spread and mutate as they pass from
person to person, tracks grudges and obligations from what actually
happened, and feeds all of it back into the game as behavior the player
can perceive and shape.

The north star: if the player assassinates the Jarl of Whiterun, that
should cascade — a succession contest driven by the court's real
relationships, an economic ripple through dependent merchants, a rumor
that mutates as it travels to Riften, guard patrols that shift as a
*consequence* of the simulation, not a scripted quest branch.

## Read next

| | |
|---|---|
| [`docs/vision.md`](docs/vision.md) | What this is and why, anchored on the north-star scenario. |
| [`docs/architecture.md`](docs/architecture.md) | The event-sourced core, the three-tier belief architecture, the Substrate Abstraction Layer, deployment target. |
| [`docs/decisions/`](docs/decisions/) | Numbered ADRs and `open-questions.md` — the project's working memory for every design tension research surfaced. |
| [`docs/research/00-index.md`](docs/research/00-index.md) | Every research report behind this design, with tagged findings and merged build-on/risk lists. |

## Status

Research phase complete — 11 reports across 6 batches, 8 accepted ADRs.
`docs/v0.1-spec.md` is accepted, and its full ~20-rule budget is now
implemented and scenario-proven headless: the claim/variant/belief store
with the rumor stage machine (`chronicle/claims.py`), the social-state
store — relationships, grudges, obligations, observer-local reputation
(`chronicle/social.py`) — and schedule-driven encounter sampling
(`chronicle/schedule.py`, `chronicle/propagate.py`), which replaces
hand-picked teller/hearer pairs with real NPC-schedule-based propagation.
Schedules and relationships are still hand-seeded for the v0.1 Whiterun
cast (`chronicle/fixtures/`) rather than derived from a full math-tier
simulation — the sampling mechanics don't change shape when that data
source does, only the caller supplying them.

v0.1 is **headless**: no Skyrim installation required to build, run, or
test it. The `adapters/skyrim/` SKSE seam only becomes relevant at v0.2.

## Development

Requires [uv](https://docs.astral.sh/uv/) — it installs the right Python
(3.12+) automatically.

```sh
uv sync      # install dependencies
make test    # uv run pytest
make lint    # uv run ruff check .
make sim     # uv run python -m chronicle (currently a stub)
```

**Layout**: `chronicle/` is the pure-Python simulation engine — it never
imports anything Skyrim-specific. `adapters/skyrim/` is the only place
allowed to know Skyrim exists. `dashboard/` is the debug/observability web
UI (first-class, not an afterthought — see `docs/vision.md`).
`scenarios/` holds headless regression scenarios with asserted outcomes.
`notes/` is working memory: `inbox/` for unprocessed material, `daily/`
for session notes, `ideas.md` for unsorted ideas and action items.
