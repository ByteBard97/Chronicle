# Design prep — ChronicleBridge, a fifth slice: grudge-driven vendor markup

**Status (2026-08-26): the Python-only first cut described below is now
implemented.** `chronicle/vendor_markup.py`'s `markup_multiplier_for(grudge,
*, at_gamets)` resolves this doc's own §1 open question the same way
`chronicle/avoidance.py`'s docstring resolved its analogous question: a
new module, not an addition to `chronicle/hydration.py` -- hydration.py's
job is bucketing a continuous severity into Skyrim's discrete integer
rank scale, and this slice's output is a continuous float multiplier with
no bucket/rank concept at all, so reusing hydration.py's scope would
misdescribe what's here just as it would have for avoidance's boolean
gate. The curve: `1.0` (no markup) for `grudge is None`, below a severity
floor of `0.2` (mirroring `chronicle.hydration.MILD_SEVERITY_THRESHOLD`),
or once the grudge has cooled (`chronicle.social.grudge_cooled` -- the
same "cooled means forgiven" precedent `relationship_rank_for`/
`is_avoiding` both already follow); a linear ramp from `1.0` at the floor
to a placeholder ceiling of `1.5` at a decayed severity of `1.0`
otherwise. Never returns below `1.0`, so it can never imply a price below
`fBarterBuyMin`'s real 1.05 floor, even though enforcing that floor itself
is left to the eventual game-side consumer, per this doc's own §0.

`GET /whiterun/vendor-markup` and `POST /whiterun/vendor-markup/ack`
(`adapters/skyrim/listener/listener.py`) are live, gated identically to
the other two slices (503 without `--live-run`, same shared-secret auth).
Directed, like hydration's `holder_id`/`target_id` (never canonicalized,
per this doc's own §1 ruling) -- NOT symmetric like avoidance. The ack is
two-outcome (`applied`/`retry`), like avoidance and unlike hydration's
three: a vendor-markup write has no `no_relationship`-equivalent
permanent-failure case, since it never depends on an authored vanilla
record that might not exist -- only on whether a live game/actor
reference is available, always a temporary condition. A new
`_VendorMarkupPairState` dataclass implements the same
awaiting_ack/applied/timeout state machine as the other two slices,
reusing `_AWAITING_ACK_TIMEOUT_SECONDS` rather than a second copy of it.

Tests: `chronicle/tests/test_vendor_markup.py` (unit tests for
`markup_multiplier_for`'s curve boundaries, the cooled-means-no-markup
case, and `grudge=None`) and 15 new cases in
`adapters/skyrim/listener/test_listener.py` (endpoint behavior,
idempotency, ack outcomes, dropped-ack timeout, 503 gating,
malformed-body rejection, shared-secret auth), mirroring the
hydration/avoidance test suites' own fixture/style patterns.

**Still not built, same split as hydration/avoidance:** the C++ half (an
actual barter-menu-open price-write poller consuming this state) -- real,
separate future work needing its own research pass on the exact
CommonLibSSE-NG hook, per §0/§3 below.

Original design proposal follows, unchanged except where noted above:
design proposal for a Python-only first cut, mirroring
`docs/design/chronicle-bridge-hydration-out.md`/`chronicle-bridge-
avoidance-out.md`'s precedent exactly. Nothing here is implemented yet.
Produced from `docs/research/23-v03-hysteresis-and-action-verbs.md`'s
Part B, ranked recommendation #2.

**Correction to `docs/design/next-phases-2026-08.md`'s earlier note:**
that doc said this action verb "needs new Chronicle-side state that
doesn't exist yet." Re-checked against the actual research finding —
wrong. The research explicitly says this "matches `Grudge.severity`
almost exactly as-is (**same scalar rule 18 already reads for
avoidance**)." No new rule, no rule-budget spend, no new Chronicle
state: this is the exact same `Grudge`/`grudge_at`/`grudge_cooled`
machinery `chronicle/avoidance.py` and `chronicle/hydration.py` already
read, bucketed a third way.

## 0. What this is

A pure price-markup multiplier derived from decayed grudge severity, the
same "read rule 18's/hydration's already-computed state, don't touch the
rule itself" shape as the other two "Out" slices. `docs/research/
16-skyrim-economy-mods.md`/`18-...-v2.md` (already in this repo, read
before this doc — no new research needed) document the real engine
hooks this would eventually drive: vendor gold caps, the `fBarterBuyMin`
price floor (default 1.05), and a "write vendor gold/prices at
barter-menu open" pattern already surveyed for this project's economy
tier (v0.4) — this slice doesn't touch any of that game-side mechanism
yet, it only computes and exposes the multiplier a future consumer would
apply.

## 1. Scope for the first (Python-only) cut

- **`chronicle/vendor_markup.py`** (or add to `chronicle/hydration.py` —
  decide at implementation time using the same "does the existing
  module's own scope/docstring already describe this kind of question"
  test `chronicle/avoidance.py`'s own design doc used to justify a new
  module): a pure function, e.g. `markup_multiplier_for(grudge: Grudge |
  None, *, at_gamets: float) -> float`, returning `1.0` (no markup) below
  some band, rising toward a placeholder ceiling (e.g. `1.5`, "50% over
  vanilla price," respecting `fBarterBuyMin`'s existing 1.05 floor as a
  documented real constraint, not a number to silently violate) as
  decayed severity increases, and — per the research's own point that
  this "never changes hostility state, only a barter-menu price
  calculation" — deliberately never returns a "refuses to trade
  entirely" boolean in this first cut; a pure continuous multiplier is
  the honestly-scoped smallest real thing, an outright refusal is a
  bigger behavioral claim to defer.
- **`GET /whiterun/vendor-markup`** + **`POST /whiterun/vendor-markup/ack`**,
  the exact same poll/ack protocol shape as hydration/avoidance
  (`_HydrationPairState`/`_AvoidancePairState`'s pattern, including the
  dropped-ack timeout from day one). Directed, not symmetric (unlike
  avoidance) — a grudge holder marking up prices *toward* its target is
  a one-directional fact, matching hydration's own directed shape more
  than avoidance's symmetric one. Response shape:
  `[{"holder_id": str, "target_id": str, "markup_multiplier": float}]`.
- **No C++ work in this first cut** — same split as every other slice.
  The eventual game-side consumer (writing vendor gold/prices at
  barter-menu open) is real future work with its own research pass on
  the exact CommonLibSSE-NG hook, not assumed here.

## 2. Non-goals

- An outright "refuses to trade" boolean — a bigger behavioral claim,
  deferred (see §1).
- Any C++/game-side work.
- Touching `chronicle/rules.py`, rule 18, or any existing rule — this is
  a third independent read of already-computed `Grudge` state, not a
  new mechanism.
