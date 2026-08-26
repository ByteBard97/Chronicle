# ChronicleBridge listener

Receives ChronicleBridge's outbound POSTs
(`adapters/skyrim/contracts/chronicle-bridge.openapi.yaml`) on two routes:

- **`/whiterun/positions`** -- the spatial-streamer's rolling snapshot
  (`docs/design/chronicle-bridge-spatial-streamer.md`). Writes a JSON file
  the dashboard's existing polling machinery reads -- per that doc's B4
  decision, a file-polling side-channel, not a live push server, so the
  dashboard's static-read/no-backend property never changes.
- **`/whiterun/events`** -- discrete game events, currently NPC deaths only
  (`docs/design/chronicle-bridge-death-extraction.md`). Appends to a
  single, developer-designated live run via `python -m chronicle inject`
  (shelled out to, never imported -- see below), stamped
  `--origin-kind adapter`. Disabled (503) unless the listener is started
  with `--live-run <run_id>`; there is deliberately no default and no
  auto-selection of an existing run -- **never point it at a fixture/demo
  run the M7 release gate or the ladder's scenario tests depend on** (e.g.
  `runs/north-star-01`), always a dedicated live-play run.
- **`GET /whiterun/hydration`** -- the Python-only first cut of the "Out"
  direction (`docs/design/chronicle-bridge-hydration-out.md` §3b): the
  pending-hydration queue a not-yet-built C++ poller would call to drive
  `Actor.SetRelationshipRank`. Reads the live run's current on-disk state
  (`FrameLogReader.state_at()` at the run's max tick, same pattern
  `chronicle sync-check`/`chronicle inspect` use), buckets every grudge
  between two named-cast NPCs via `chronicle.hydration.relationship_rank_for`
  (reputation is deferred for this first cut -- grudge-only), and returns
  only the `{holder_id, target_id, relationship_rank}` pairs whose bucket
  changed since the last poll. The "last pushed" dedupe cache is
  in-memory only and does **not** survive a listener restart -- a real,
  named gap (design doc §3), not solved here. Disabled (503) unless the
  listener is started with `--live-run <run_id>`, the same gating
  `/whiterun/events` uses. Nothing calls this endpoint yet; the C++
  poller and any `SetRelationshipRank` calls are still to be built.

Not part of `chronicle/` -- this is Skyrim-adapter-side plumbing, per
`adapters/skyrim/README.md`'s charter. `/whiterun/events` does not import
`chronicle/` either; it shells out to the same `chronicle inject` CLI
write path a human uses at the console, the documented seam boundary.
`/whiterun/hydration` is the one deliberate exception to that
never-import boundary: it has no write path (it only reads a run's
existing on-disk state and computes a pure function over it), so there is
nothing for the CLI boundary to protect -- a fresh `python -m chronicle`
subprocess would still pay interpreter startup on top of the same log
replay a direct import already does, for no safety benefit in exchange.
Write access to a run still goes through the CLI exclusively -- see the
exception's full rationale in `listener.py`'s own module docstring.

## Testing

Not under `chronicle/tests/` or `scenarios/` -- `pyproject.toml`'s
`testpaths` deliberately excludes this directory, the same boundary. Run
explicitly:

```
uv run --with pydantic --with pytest pytest adapters/skyrim/listener/test_listener.py
```

## Regenerating the model from the contract

The Pydantic model is generated from the OpenAPI spec, not hand-written --
that's the whole point of having one shared source of truth instead of
two independently-maintained schemas:

```
uv run datamodel-codegen \
    --input adapters/skyrim/contracts/chronicle-bridge.openapi.yaml \
    --input-file-type openapi \
    --output adapters/skyrim/listener/models.py
```

Regenerate and commit `models.py` whenever the contract changes -- never
hand-edit it.
