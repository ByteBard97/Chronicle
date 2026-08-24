# docs

Index of everything under `docs/`. Rebuilt 2026-08-24 — the previous
version predated most of the project (no mention of the v2 visions,
the constitution docs, the dashboard spec, or `work-packets/`).

## Vision and constitution

- **`vision-v2.2.md`** — **current.** What Chronicle is and why,
  anchored on the Jarl-of-Whiterun north-star scenario, the demand
  case, the road (v0.1 → v0.4). Supersedes `vision-v2.1.md`, which
  supersedes `vision.md` (v1) — kept for history, not current.
- **`scenario-ladder.md`** (v0.4, FINAL) — the constitution's
  mechanism plan: Tiers 0–6, each introducing exactly one new
  mechanism, a §6 explicit deferrals list ("do not review as gaps"),
  and a §8 rule-budget table. All 19 named rules are now live
  (2026-08-24) — see `work-packets/reviews/README.md`.
- **`ui-doctrines.md`** (v1) — the dashboard's constitution: time/
  replay rules, renderer-split doctrine, prohibitions, each with a
  named precedent and failure mode. Amend here, never inline
  downstream.
- **`ui-spec.md`** — the frozen dashboard contract (views, global
  chrome, deep-link/URL-state contract, the M7 stranger/developer
  walkthroughs). Owner-review-only; findings route to the coordinator.
- **`architecture.md`** — deployment target (native Linux + Proton),
  the event-sourced core, the three belief tiers, the two integration
  seams (game adapter, dashboard).

## Engine spec and decisions

- **`v0.1-spec.md`** — the six design decisions gating the first code
  milestone (claims.py). Accepted.
- **`frame-log-schema.md`** — coordinator-owned. The physical log
  layout, the full events/trace payload catalog, keyframes, the run
  registry and sidecar index. Amendments are dated and review-noted.
- **`decisions/`** — ADRs, numbered 0001–0010 (service architecture,
  event sourcing, substrate choice, timeline branching, sync
  handshake, data-ownership layers, inspectability, game-version pin,
  keyed randomness, tick quantum). `decisions/open-questions.md` — the
  research-phase tension tracker; fully resolved except the
  deliberately-deferred economy tier (v0.4).
- **`design/`** — accepted design docs bridging a scenario-ladder tier
  to its implementation lane: Tier 3 (rule registry + tell-decision),
  Tier 4a (schedule write-back), Tier 4b (avoidance), Tier 5 (roles +
  vacancy), the north-star fixture, and a trace-volume measurement
  note for the ui-spec §1.1 figure.

## Dashboard build process

- **`dashboard-build-plan.md`** (v1.3, approved) — the milestone plan
  M0–M7, now complete (2026-08-24; the M7 release gate formally PASS,
  6/6 steps — see the board). §3 names two deferred milestones (an MCP
  server over the frame log; fork re-sim/`chronicle serve`), each
  gated on an unlock condition that hasn't fired — not oversights.

## Multi-agent governance

- **`../AGENTS.md`** (repo root) — the coordinator/lane-worker model,
  frozen-document list, the battery commands, repo conventions.
- **`work-packets/README.md`** — the packet index (one row per lane,
  1–60 as of this writing) and worker-facing rules.
- **`work-packets/lane-N-*.md`** — individual lane packets.
- **`work-packets/reviews/README.md`** — **the board.** Lane status,
  governance rulings (including the 2026-08-24 coordinator
  reassignment), the overseer protocol. Start here for current state.
- **`work-packets/reviews/<date>-lane-N/`** — delivery reports and
  overseer reviews per lane.

## Research

- **`research/00-index.md`** — one filed, findings-tagged summary per
  incoming research report (substrate choice, save/reload sync, the
  SkyrimNet health/version-pin follow-ups, dashboard map data, native
  SKSE plugin prior art, Skyrim social-reactivity/economy/quest-
  injection mod surveys).
- **`research/comparative-systems/`** — cross-game prior art (AI
  directors/drama management, Crusader Kings mechanics and failure
  modes, spatial-sim legal boundaries, *Shadows of Doubt*/*Nemesis*/
  *Kenshi*).
- **`research/dashboard-ui-prior-art/`** — the five reports
  `ui-doctrines.md` was compiled from (god-view/replay surveys, AI
  Town architecture, causality/lineage/diff prior art).
- **`research/papers/`** — academic sources (Gossamer, observe-tell-
  misremember-lie, City of Gangsters social modeling, AI design
  lessons).
