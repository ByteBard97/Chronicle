# Design prep — ChronicleBridge, a fourth slice: avoidance ("cold shoulder")

**Status (2026-08-26): the Python-only first cut described below is now
implemented.** `chronicle/avoidance.py`'s `is_avoiding(grudge, *,
at_gamets, threshold=chronicle.driver.AVOIDANCE_GRUDGE_THRESHOLD)` reuses
rule 18's own `_avoidance_thresholds` condition (decayed severity ≥
threshold and not `grudge_cooled`) without duplicating it -- a new module
rather than an addition to `chronicle/hydration.py`, since hydration.py's
job is bucketing a continuous severity into Skyrim's integer rank scale
and avoidance is a plain boolean gate with no bucketing involved (see
`avoidance.py`'s own docstring for the fuller reasoning). `GET
/whiterun/avoidance` and `POST /whiterun/avoidance/ack`
(`adapters/skyrim/listener/listener.py`) are live, gated identically to
`/whiterun/hydration` (503 without `--live-run`, same shared-secret
auth), with the ack protocol built in from the start as directed -- no
"delivered before confirmed" gap to retrofit later. Two differences from
hydration's shape, both load-bearing: the response is symmetric
(`{npc_a, npc_b, avoiding}`, canonicalized lexicographically, since rule
18's own `frozenset((npc_a, npc_b))` treats a grudge pair as mutual for
avoidance), and the ack has only two outcomes (`applied`/`retry`, not
hydration's three) since avoidance has no `no_relationship`-equivalent
permanent-failure case -- it never depends on an authored vanilla record
that might not exist. Tests: `chronicle/tests/test_avoidance.py` (unit
tests for `is_avoiding`) and 15 new cases in
`adapters/skyrim/listener/test_listener.py` (endpoint behavior, symmetric
canonicalization, idempotency, ack outcomes, dropped-ack timeout, 503
gating, malformed-body rejection, shared-secret auth), mirroring the
hydration test suite's own fixture/style patterns.

**Still not built, same split as hydration:** the C++ half (an actual
AI-package/behavior-override poller consuming this state) -- real,
separate future work needing its own research pass on which
CommonLibSSE-NG package-condition mechanism to use, per §0/§3 below.

Original design proposal follows, unchanged except where noted above:
Python-only first cut, mirroring
`docs/design/chronicle-bridge-hydration-out.md`'s own precedent exactly.
Produced from `docs/research/23-v03-hysteresis-and-action-verbs.md`'s
Part B, ranked recommendation #3.

Sources: `chronicle/driver.py`'s rule 18 (`PairwiseEncounterWeightingRule`,
`_grudge_severities`/`_avoidance_thresholds`/`_evaluate_avoidance`) — the
state this slice exposes already exists, computed, tested, and
ladder-gated; `docs/design/chronicle-bridge-hydration-out.md` — the
poll/ack protocol shape and the "Python-only first cut" split this
mirrors line for line; `docs/research/23-...md`'s ranking rationale
(extends an already-built mechanism rather than inventing new Chronicle
state, unlike ranked #2's vendor-price idea).

## 0. What this is, precisely

Rule 18 already computes, every tick, exactly which NPC pairs should be
avoiding each other (decayed grudge severity ≥ `avoidance_grudge_threshold`
and not cooled) and uses that *inside the headless sim* to suppress
encounter sampling between them. This slice does not change that
mechanism at all — it exposes the same computed pairs so a live game can
*also* express avoidance visibly (an AI package override making one NPC
flee/avoid the other), the same "smallest real thing, name the rest
honestly" split as every other slice.

## 1. The dependency this slice deliberately does not build

Real AI-package overrides in Skyrim (making an NPC's package selection
respond to a runtime condition) is the higher-risk, bigger-scoped
category `docs/research/19-skyrim-quest-injection-machinery.md`'s
three-tier taxonomy names — this doc's own §0 already flagged it as a
non-goal for the hydration slice, and it stays a non-goal here too for
the *first cut*: the C++/game-side package-condition work is real,
separate, future work. This design-prep doc, like hydration-out's own
§3b, only scopes the **Python-only half**: computing and serving the
avoidance-pair state a future C++ slice would consume.

## 2. Scope for the first (Python-only) cut

- **`SocialStateStore` already has everything needed** — `grudges()`
  (existing) plus the exact severity/cooled logic `_grudge_severities`/
  `_avoidance_thresholds` already implement in `driver.py`. This slice
  should NOT duplicate that logic in a second place; either expose a
  thin wrapper reusing `chronicle.social.grudge_at`/`grudge_cooled`
  directly (mirroring `chronicle/hydration.py`'s own shape — a new,
  small, pure function, e.g. `chronicle/avoidance.py`'s
  `is_avoiding(grudge, *, at_gamets, threshold) -> bool`), or confirm
  during implementation that `chronicle.hydration`'s existing helpers
  already cover this and no new module is needed at all — check before
  writing new code.
- **A new listener endpoint**, `GET /whiterun/avoidance`, mirroring
  `/whiterun/hydration`'s exact shape (gated on `--live-run`, named-cast
  filtered, an ack protocol from day one this time — no repeating the
  "delivered before confirmed" mistake `/whiterun/hydration` had to
  retrofit, per `docs/design/chronicle-bridge-hydration-out.md`'s own
  now-fixed gap): response is `[{"npc_a": str, "npc_b": str,
  "avoiding": bool}]` for named-cast pairs whose avoidance state changed
  since last acked, symmetric (unlike hydration's directed holder/
  target — avoidance per rule 18's own `frozenset((npc_a, npc_b))` is
  about the pair, not a direction).
- **No C++ work in this first cut** — the game-side consumer (an actual
  AI package condition reading this state) is real future work, same
  split as hydration-out.

## 3. Non-goals

- Any AI-package/behavior-override C++ work — future slice, needs its
  own design pass on which CommonLibSSE-NG package-condition mechanism
  to use (a custom condition function? a global variable a vanilla
  package already conditions on? needs research, not assumed here).
- Changing rule 18's headless behavior in any way — this is a read-only
  export of state that already exists and is already tested.
- Vendor-price/refusal mechanics (research report's ranked #2) — a
  separate future slice needing new Chronicle-side state (nothing
  currently tracks "would this NPC refuse to trade"), out of scope here.
