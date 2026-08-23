# Lane 20 — delivery report (grudge decay)

Worker: Kimi (Track A). Packet: `docs/work-packets/lane-20-grudge-decay.md`.
Committed path-scoped as `231aceb` (local; not pushed).

## Delivered

- `chronicle/social.py`: ruled constants block (`GRUDGE_EMOTIONAL_HALF_LIFE
  = 672.0`, `GRUDGE_EVIDENTIARY_HALF_LIFE = 336.0`, placeholder-status
  comments with game-day derivations per ADR-0010); `grudge_at(grudge,
  at_gamets)` — pure decay-at-read via `claims._decay` from
  `last_rehearsed`, severity recomputed from decayed strengths with the
  formation weights; `grudge_cooled(grudge, at_gamets)` — the
  forgiveness-threshold floor predicate. No records, no mutation, no store
  access. `form_grudge` untouched.
- `chronicle/tests/test_social.py`: 4 new tests (append + import list
  only): both strengths decay and emotional > evidentiary (ordering
  assert); both decay slower than belief confidence over the same window
  (T3.2 at the constants level); cooled-floor flips at the computed
  crossing (~1060 ticks for severity 0.9 / threshold 0.2); no-mutation.

## Acceptance

- `uv run pytest -q`: **190 passed, 0 failed** (186 + 4). `uv run ruff
  check .`: clean.
- Constants match the ruled table; ordering asserts green.
- No schema/frozen-doc edits; boundary files only.

## Findings

1. **Cooled-floor comparison basis (in-lane judgment, flagged):** the
   packet left "the decayed grudge is below it" open on *which* strength
   compares to `forgiveness_threshold`. I used decayed **severity** — the
   record's own composite — rather than either component. If a behavior
   rule (T4b avoidance) wants component-level gating instead, that's a
   one-line change when that lane lands.
2. **Expected finding, answered:** no existing caller should read
   `grudge_at` yet — the only current consumers of `Grudge` are the
   scripted `form_grudge` wrapper and replay, both of which need stored
   (not decayed) values. The first real consumer is T4b's avoidance rule
   (and T3.2's scenario assert). Wiring consumers is those lanes' call.
3. `grudge_at` imports `claims._decay` (a private name, same package) per
   the packet's explicit "applying `claims._decay`" — no circular import
   (claims never imports social).
