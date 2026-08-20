# Chronicle

An external Python social-simulation service for Skyrim SE/AE: NPC
beliefs (with provenance and strength), rumor propagation with mutation,
grudges, obligations, and reputation across a game world, injected back
into the game as behavior the player can perceive and shape.

Start here:

- **`docs/vision.md`** — what this is and why, anchored on the north-star
  scenario (the Jarl of Whiterun assassination cascade).
- **`docs/architecture.md`** — the event-sourced core, the three-tier
  belief architecture, the Substrate Abstraction Layer, deployment target.
- **`docs/decisions/`** — numbered ADRs (0001-0007 and amendments) and
  `open-questions.md`, the project's working memory for research-surfaced
  tensions.
- **`docs/research/00-index.md`** — every research report that's shaped
  this design, with tagged findings and merged build-on/risk lists.

## Status

Research phase complete (10 reports, 5 batches). Currently scoping the
v0.1 spec — see `docs/decisions/open-questions.md` and the most recent
entries in `claude-sessions/` for where that stands.

v0.1 is headless: no Skyrim installation is required to build or test it.
The `adapters/skyrim/` SKSE seam (and the Proton/Linux deployment target
in `docs/architecture.md`) only becomes relevant at v0.2.

## Development

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+ (uv will
install the right Python automatically).

```sh
uv sync          # install dependencies
make test        # run the test suite (uv run pytest)
make lint         # uv run ruff check .
make sim          # uv run python -m chronicle (currently a stub)
```

Layout: `chronicle/` is the pure-Python simulation engine (never imports
anything Skyrim-specific); `adapters/skyrim/` is the only place allowed to
know Skyrim exists; `dashboard/` is the debug/observability web UI;
`scenarios/` holds headless regression scenarios with asserted outcomes;
`notes/` is working memory (`inbox/` for unprocessed material, `daily/`
for session notes, `ideas.md` for unsorted ideas and action items).
