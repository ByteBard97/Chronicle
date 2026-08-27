# ChronicleBridge listener

Receives ChronicleBridge's outbound POSTs
(`adapters/skyrim/contracts/chronicle-bridge.openapi.yaml`) on two routes:

- **`/whiterun/positions`** -- the spatial-streamer's rolling snapshot
  (`docs/design/chronicle-bridge-spatial-streamer.md`). Writes a JSON file
  the dashboard's existing polling machinery reads -- per that doc's B4
  decision, a file-polling side-channel, not a live push server, so the
  dashboard's static-read/no-backend property never changes.
- **`/whiterun/events`** -- discrete game events: NPC deaths
  (`docs/design/chronicle-bridge-death-extraction.md`) and crime-witness
  events (`docs/design/chronicle-bridge-crime-witness-out.md`). Appends to a
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

- **`GET /whiterun/avoidance`** -- the avoidance ("cold shoulder") slice's
  pending queue (`docs/design/chronicle-bridge-avoidance-out.md`), for a
  future C++ AI-package-override poller to consume (not built yet -- this
  is Python-only, same split as hydration). Reads the live run's current
  on-disk state the same way `/whiterun/hydration` does, groups every
  grudge between two named-cast NPCs by its unordered pair, and computes
  whether that pair is currently avoiding each other via
  `chronicle.avoidance.is_avoiding` (reusing `chronicle.driver`'s own
  rule-18 `_avoidance_thresholds` condition, never a second copy of it).
  Returns only the `{npc_a, npc_b, avoiding}` pairs whose value differs
  from what's currently tracked. **Symmetric, unlike hydration's directed
  `holder_id`/`target_id`** -- rule 18 treats a grudge pair as mutual for
  avoidance purposes, so `npc_a`/`npc_b` are always canonicalized
  lexicographically (`sorted((a, b))`), never holder/target order. Gated
  identically to `/whiterun/hydration` (503 without `--live-run`, same
  auth).
- **`POST /whiterun/avoidance/ack`** -- the same ack protocol as
  `/whiterun/hydration/ack`, applied to avoidance's symmetric pair shape.
  Body: a JSON array of `{"npc_a": str, "npc_b": str, "outcome":
  "applied" | "retry"}` objects (`npc_a`/`npc_b` may be given in either
  order; canonicalized before lookup). Only two outcomes, not hydration's
  three: avoidance has no `no_relationship`-equivalent permanent-failure
  case, since it depends only on both NPCs being named-cast (already
  filtered) and a live game/actor reference being available (`retry`,
  temporary) -- never on an authored vanilla record that may not exist.
  `applied` settles the pair at its current `avoiding` value; `retry`, or
  a dropped/timed-out ack, forgets the pair for fresh re-evaluation next
  poll (`listener.py`'s `_AvoidancePairState`, same dropped-ack timeout
  mechanism as hydration's `_HydrationPairState`).

Like the hydration routes, neither avoidance route's in-memory state
survives a listener restart -- same named gap, same "identical to a
`retry` ack" restart behavior.

- **`GET /whiterun/vendor-markup`** -- the grudge-driven vendor-markup
  slice's pending queue (`docs/design/chronicle-bridge-vendor-markup-
  out.md`), for a future C++ poller to consume at barter-menu open (not
  built yet -- Python-only, same split as hydration/avoidance). Reads the
  live run's current on-disk state the same way `/whiterun/hydration`
  does, and computes each named-cast grudge's price-markup multiplier via
  `chronicle.vendor_markup.markup_multiplier_for` (a continuous curve
  over decayed grudge severity -- `1.0` below its severity floor or once
  cooled, ramping linearly to a placeholder ceiling of `1.5` at maximum
  severity; see that module's own docstring for the exact band). Returns
  only the `{holder_id, target_id, markup_multiplier}` pairs whose value
  differs from what's currently tracked. **Directed, like hydration's
  `holder_id`/`target_id` -- NOT canonicalized like avoidance's
  `npc_a`/`npc_b`** -- a grudge holder marking up prices toward its target
  is a one-directional fact. Gated identically to `/whiterun/hydration`
  (503 without `--live-run`, same auth).
- **`POST /whiterun/vendor-markup/ack`** -- the same ack protocol as the
  other two ack routes, applied to vendor-markup's directed pair shape.
  Body: a JSON array of `{"holder_id": str, "target_id": str, "outcome":
  "applied" | "retry"}` objects. Only two outcomes, like avoidance and
  unlike hydration's three: a vendor-markup write has no
  `no_relationship`-equivalent permanent-failure case (it never depends on
  an authored vanilla record that might not exist -- only on whether a
  live game/actor reference is available, which is always temporary).
  `applied` settles the pair at its current multiplier; `retry`, or a
  dropped/timed-out ack, forgets the pair for fresh re-evaluation next
  poll (`listener.py`'s `_VendorMarkupPairState`, same dropped-ack timeout
  mechanism as the other two state machines).

Like the other two slices, vendor-markup's in-memory state does not
survive a listener restart -- same named gap, same "identical to a
`retry` ack" restart behavior.

- **`GET /whiterun/evidence`** -- the diegetic-evidence slice's pending
  queue (`docs/design/chronicle-bridge-diegetic-evidence-out.md`), for a
  future C++ poller to consume (not built yet -- Python-only, same split
  as the other three). Reads the live run's current on-disk state the
  same way `/whiterun/hydration` does, loops `NAMED_CAST_NPC_IDS`, and
  calls `ClaimStore.beliefs_of(holder_id)` for each -- not the `for grudge
  in state.social.grudges()` scan the other three use, since this reads
  `chronicle.claims.ClaimStore`, not `chronicle.social.SocialStateStore`.
  Computes each belief's `chronicle.diegetic_evidence.
  should_reveal_evidence` (a decayed-confidence threshold gate, reusing
  the already-public `chronicle.claims.decay()`, never a second decay
  formula). Returns only the `{holder_id, belief_id, claim_id}` entries
  that just crossed the threshold. **Single-key, not a pair** -- there is
  no second party (design doc §2: "near the NPC who now believes it," not
  "near the claim's subject"). **One-shot, with no re-offer on decay** --
  unlike the other three, an entry that reaches `applied` is a true
  terminal state and is never re-offered again, even if the belief's
  confidence later decays below threshold and rises back above it (a
  named, deliberate limitation, not a bug -- design doc §3). Gated
  identically to `/whiterun/hydration` (503 without `--live-run`, same
  auth).
- **`POST /whiterun/evidence/ack`** -- the same ack protocol as the other
  three, applied to evidence's single-key shape. Body: a JSON array of
  `{"holder_id": str, "belief_id": str, "outcome": "applied" | "retry"}`
  objects. Only two outcomes, like avoidance/vendor-markup: a
  `PlaceObjectAtMe` call has no `no_relationship`-equivalent permanent-
  failure case. `applied` here is TERMINAL, not just settled-at-a-value
  like the other three's `applied` -- there is no condition that ever
  re-offers an applied entry again; `retry`, or a dropped/timed-out ack,
  forgets the entry for fresh re-evaluation next poll (`listener.py`'s
  `_EvidenceEntryState`, same dropped-ack timeout mechanism as the other
  three state machines).

Like the other three slices, evidence's in-memory state does not survive
a listener restart -- same named gap, same "identical to a `retry` ack"
restart behavior (which, for evidence, also means a restart forgets even
an already-`applied` entry -- there is no persistence layer for any of
these state machines to make that limitation more or less severe than the
others').

Not part of `chronicle/` -- this is Skyrim-adapter-side plumbing, per
`adapters/skyrim/README.md`'s charter. `/whiterun/events` does not import
`chronicle/` either; it shells out to the same `chronicle inject` CLI
write path a human uses at the console, the documented seam boundary.
`/whiterun/hydration`, `/whiterun/avoidance`, `/whiterun/vendor-markup`,
and `/whiterun/evidence` are the deliberate exceptions to that
never-import boundary: none has a write path (each only reads a run's
existing on-disk state and computes a pure function over it), so there is
nothing for the CLI boundary to protect -- a fresh `python -m chronicle`
subprocess would still pay interpreter startup on top of the same log
replay a direct import already does, for no safety benefit in exchange.
Write access to a run still goes through the CLI exclusively -- see the
exceptions' full rationale in `listener.py`'s own module docstring.

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
