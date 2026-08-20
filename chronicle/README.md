# chronicle

The pure-Python simulation package. Engine-agnostic — this package must never
import anything Skyrim-specific (no Papyrus bindings, no SKSE types, no game
paths). All game-specific glue lives in `adapters/skyrim/`, so the substrate
choice (Skyrim vs. something else) stays reversible.

Core pattern: event-sourced. `events.py` defines the append-only log; all
derived state (beliefs, rumors, grudges, reputation) is computed by folding
over the log, not mutated in place. See `docs/architecture.md`.
