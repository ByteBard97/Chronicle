# Dashboard UI prior art

Research on how other tools and games solve the interaction-design problem
of *observing* a running multi-agent simulation — god-view maps, replay/
scrubbing, per-entity inspectors, causality/provenance drill-down, and
run-to-run diffing. Collected to inform Chronicle's own `dashboard/`
design (see `docs/vision.md`'s "Tooling as a first-class artifact" and
`dashboard/README.md`'s planned views). This is raw comparative material,
not yet-synthesized decisions: nothing here is an ADR.

Distinct from:
- The main `docs/research/00-index.md` numbered series, which already
  filed two dashboard-adjacent reports (12: map assets/coordinates/
  telemetry; 13: WS protocol/replay schema/projection) tied to specific
  accepted conclusions. This folder is upstream, broader raw material —
  interaction-pattern prior art, not architecture decisions.
- `docs/research/comparative-systems/`, which covers *reactivity design*
  (how belief/grudge state should drive NPC behavior) via Crusader Kings
  and spatial-sim genre neighbors — a different design question than "how
  do you build the UI to observe it."

## God-view / replay UI surveys

| File | Covers |
|------|--------|
| [godview-replay-pattern-matrix.md](godview-replay-pattern-matrix.md) | Broad survey: ABM platforms (NetLogo, Mesa/SolaraViz, GAMA, AnyLogic, Agents.jl), Stanford's Smallville, commercial god-games (Sims/Dwarf Fortress/RimWorld), RTS/esports replay. Original scoring-matrix diagram across 13 tools (`figures/godview-replay-pattern-matrix/`). |
| [godview-replay-abm-games-esports-survey.md](godview-replay-abm-games-esports-survey.md) | Second independent pass over the same four domains. |
| [godview-replay-ai-town-architecture.md](godview-replay-ai-town-architecture.md) | Narrower and deeper: a16z's AI Town as the closest existing template for "every view renders as of tick T" (its `HistoricalObject` delta-compression pipeline), plus SVG/Canvas/WebGL rendering benchmarks. |

## Causality / time-travel / lineage / diff UI

| File | Covers |
|------|--------|
| [causality-timetravel-lineage-diff-prior-art.md](causality-timetravel-lineage-diff-prior-art.md) | Pernosco (belief-provenance drill-down), Nextstrain/Auspice (mutating-rumor lineage trees), Redux DevTools/Temporal (time-travel + diff), ESMValTool/pytest-benchmark/LiveSplit (run-to-run diffing), GraphDiaries (stable social-graph deltas). |
| [causality-tracing-taxonium-lineage-prior-art.md](causality-tracing-taxonium-lineage-prior-art.md) | Second independent pass on the same ground; adds Taxonium's screen-space sparsification for very large lineage trees and a sharper Jaeger/Pernosco/Redux/Replay.io comparison table. |

Several files intentionally cover overlapping ground from independent
research passes (cross-checking, not redundant filing) — read the
provenance header at the top of each for what's distinctive about it.

More reports along these lines are expected — add new files here with the
same filed-date/provenance header (see any file's top blockquote for the
template) rather than starting a separate location.
