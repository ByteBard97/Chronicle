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
- **`GET /whiterun/hydration`** -- the "Out" direction's pending-hydration
  queue (`docs/design/chronicle-bridge-hydration-out.md` §3b), polled by
  ChronicleBridge's `HydrationPoller` to drive `Actor.SetRelationshipRank`.
  Reads the live run's current on-disk state (`FrameLogReader.state_at()`
  at the run's max tick, same pattern `chronicle sync-check`/`chronicle
  inspect` use), buckets every grudge between two named-cast NPCs via
  `chronicle.hydration.relationship_rank_for` (reputation is deferred for
  this first cut -- grudge-only), and returns only the `{holder_id,
  target_id, relationship_rank}` pairs whose bucket differs from that
  pair's currently tracked state. Disabled (503) unless the listener is
  started with `--live-run <run_id>`, the same gating `/whiterun/events`
  uses.
- **`POST /whiterun/hydration/ack`** -- closes the "delivered before
  confirmed" gap named in `fad0d79`'s commit message: the GET above used
  to mark a pair "delivered" the instant it was served, before the C++
  poller ever confirmed the write actually succeeded. Now a pair served
  by the GET is tracked as "offered-awaiting-ack" until this endpoint
  reports what happened. Body: a JSON array of `{"holder_id": str,
  "target_id": str, "outcome": "applied" | "no_relationship" | "retry"}`
  objects -- `applied` (the write succeeded), `no_relationship`
  (`RE::BGSRelationship::GetRelationship()` returned null -- a PERMANENT
  condition, since this project never creates a relationship record, only
  updates an existing one), or `retry` (either NPC failed to resolve or no
  game was active at all -- a TEMPORARY condition). A pair's state
  machine (`listener.py`'s `_HydrationPairState`) uses this to decide
  whether to ever re-offer that exact rank again: `applied`/
  `no_relationship` settle the pair at its current rank (a
  `no_relationship` skip is scoped to that one rank -- a later rank change
  is offered fresh); `retry`, or no ack ever arriving at all (e.g. the
  C++ side crashing/restarting mid-poll), simply forgets the pair, making
  it eligible to be offered again next poll. Gated identically to the GET
  above (503 without `--live-run`, same auth check). Not part of the
  OpenAPI contract -- same ad hoc hand-rolled-JSON precedent as the GET
  response it acks.

Neither hydration route's in-memory state survives a listener restart --
a real, named gap (design doc §3), not solved here. A restart is handled
identically to a `retry` ack: the pair is simply forgotten and
re-evaluated fresh on the next poll.

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
