# Contributing to Chronicle

Chronicle is an external social-simulation service for Skyrim SE/AE: a pure-Python
simulation engine, a small SKSE C++ plugin that relays events in and state out, a
Mutagen-based ESP patcher, and a Vue debug dashboard. Contributions are welcome.
This file gets you from `git clone` to a running simulation in about five minutes,
then points you at work that's actually claimable.

**Status honesty up front:** the headless sim is done and scenario-tested; the SKSE
bridge compiles and deploys; in-game validation against a live game is the current
milestone. See the [README's Project status](README.md#project-status-august-2026)
section, it's always the source of truth for what works today.

## 5-minute quickstart (no Skyrim install needed)

Requires [uv](https://docs.astral.sh/uv/), which installs the right Python (3.12+)
automatically.

```bash
git clone https://github.com/ByteBard97/Chronicle.git
cd Chronicle
uv sync        # install dependencies
make test      # 431 tests should pass
make lint      # ruff
make sim       # CLI: inspect/trace/feed/inject subcommands (chronicle/cli.py)
```

Then the dashboard (requires Node 20+):

```bash
cd dashboard
npm ci
npm run dev    # opens on mock run data, no Skyrim or sim needed
```

You should now be looking at the Whiterun rumor cascade in the debug UI. From
there, `make sim` + `chronicle/cli.py --help` shows how to inspect a run, trace a
belief back through its provenance chain, and inject events by hand.

Run a scripted demo end to end:

```bash
uv run python scenarios/run_jarl_death_demo.py   # the north-star scenario, headless
```

## The one architectural rule

`chronicle/` is the pure-Python simulation engine. **It never imports anything
Skyrim-specific.** The only place allowed to know Skyrim exists is
`adapters/skyrim/`. If a PR puts a game concept into the engine core, it will be
bounced regardless of how well it works. That separation is what makes the whole
simulation testable and replayable without launching the game, see
`docs/architecture.md`.

## Repo layout

| Path | What it is | Stack |
|---|---|---|
| `chronicle/` | Simulation engine (claims/beliefs, rumors, grudges, schedules, RNG) | Python 3.12, zero runtime deps |
| `scenarios/` | Headless regression scenarios with asserted outcomes | pytest |
| `adapters/skyrim/ChronicleBridge/` | SKSE plugin (7 slices: positions, deaths, hydration, avoidance, vendor markup, barter detect, evidence) | C++23, CommonLibSSE-NG, cpp-httplib |
| `adapters/skyrim/listener/` | HTTP listener between bridge and engine | Python stdlib + pydantic |
| `tools/chronicle-patcher/` | Authors `ChroniclePatcher.esp` programmatically | C#, Mutagen |
| `dashboard/` | Debug/observability UI | Vue 3 + Vite + TS, Pinia, Canvas2D |
| `docs/` | Vision, architecture, ADRs (`decisions/`), research reports | MkDocs Material |

## Building the game-side pieces

These need Windows and a Skyrim SE/AE install. The Python engine, scenarios, and
dashboard don't, and most contributions never touch this side.

**ChronicleBridge (C++):** see `adapters/skyrim/ChronicleBridge/README.md`.
Short version: Visual Studio 2022, vcpkg, then
`cmake --preset release && cmake --build build/release`. Set `SKYRIM_FOLDER` or
`SKYRIM_MODS_FOLDER` to drop the DLL straight into your install.

**chronicle-patcher (C#):** `dotnet build` in `tools/chronicle-patcher/`. Mutagen
is MIT-licensed and cross-platform; this half does not need Windows or the
Creation Kit.

## How to pick up work

- **Issues labeled `good first issue`** are scoped to be completable without
  deep project context. They include acceptance criteria and the exact files
  to touch.
- **Issues labeled `help wanted`** are the hard, interesting problems (co-save
  sync, runtime package injection, in-game verification). If one of these is why
  you're here, comment on the issue and say so first, design discussion happens
  there before code.
- `docs/decisions/open-questions.md` is the project's working memory of every
  unresolved design tension. If you want to change a decision, the ADR that made
  it is the thing to argue with, cite it in the issue.

## PR expectations

- `make test` and `make lint` pass. CI runs both plus the dashboard build/tests.
- New sim behavior comes with a scenario test in `scenarios/` with asserted
  outcomes, not just unit tests. The scenario ladder (`docs/scenario-ladder.md`)
  is the regression contract.
- Determinism is a hard requirement: all randomness goes through
  `chronicle/rng.py`'s keyed rolls (ADR-0009). No `random`, no time-dependent
  behavior in the engine.
- The frame-log schema (`docs/frame-log-schema.md`) is versioned; changing an
  encoding it pins is a schema break and needs an ADR.
- Commit messages and comments explain *why*, citing docs/research where the
  answer came from investigation. The existing codebase is the style guide.

## Where to talk

Open a GitHub issue for anything concrete. For broader design discussion, start
a GitHub Discussion, or find us in [Discord server / community link, TBD].
