# Lane 24 — delivery report (accumulation-threshold escalation, T3.1)

Worker: Kimi (Track A). Packet: `docs/work-packets/lane-24-accumulation-threshold.md`.
Committed path-scoped as `1f47752` (local; not pushed).

## Delivered

- **`chronicle/events.py`** — `EscalationWarning` event dataclass per
  §3:95's filled fields (`holder_id`, `grievance_kind`, `count`,
  `threshold`), engine-internal by design (origin None).
- **`chronicle/framelog.py`** — the `event_payload` serialization branch.
  **Boundary extension, flagged:** the packet's Edit list is
  rules.py/driver.py/events.py, but `event_payload` dispatches per event
  type and *raises* on unknown types (`framelog.py:353` — whose own error
  message says "extend chronicle/framelog.py"). The branch is mechanical
  and field-for-field with §3:95; framelog.py was on neither the Edit nor
  the Do-not-touch list. If the coordinator prefers this reverted and
  re-landed as its own micro-lane, it's a clean revert of one elif.
- **`chronicle/rules.py`** — `AccumulationThresholdRule` replaces the
  rule-11 stub: fires when `count >= threshold` and not latched, all from
  caller-assembled inputs (the rule never queries stores).
- **`chronicle/driver.py`** — `accumulation_thresholds: Mapping[str,
  tuple[str, int]]` ctor mapping (claim kind → victim slot + per-kind
  threshold; the mutation_candidates idiom); `_evaluate_accumulation`
  hooks on the witness and retell belief-forming paths (evaluate-on-change,
  R5 — retell's re-hearing carve-out is detected and skipped); the
  store-derived latch (`_escalation_latched`); the R6 cascade (event →
  witness-off-its-key → `threshold_crossed` per §4:123, with the produced
  event key + claim id in `produced`). Driver now stores `save_uuid`/
  `generation` for engine-internal event stamping.
- **`scenarios/test_tier3_accumulation.py`** — the T3.1 rung: annoyance-
  only at 3 thefts (the 1,2,3 counter visible in fired=false
  `rule_evaluated` rows); exactly one `escalation_warning` +
  `threshold_crossed` at 4, both field-for-field; the warning claim hangs
  off the event's canonical key (asserted); the peer merchant holds
  nothing until the tick loop runs, then learns via `transmitted` records
  only; theft five (between run phases, T2.7 idiom) fires nothing and the
  latch row shows `count=5, latched=true, fired=false`; plus the
  reconstruction-parity test (`state_at` rebuilds exactly one escalation).
- **`chronicle/tests/test_rules.py`** — the mechanical stub-migration
  consequence again (packet pin "rule 11 registers replacing the stub"):
  stub assertions moved to rule 12, enabled count 11→12.

## Acceptance

- `uv run pytest -q`: **200 passed, 0 failed** (198 + 2 new). `uv run ruff
  check .`: clean. No behavior change at defaults — with no accumulating
  kinds registered the hooks no-op, and the pre-existing suite is
  unedited except the stub-migration assertions above.
- Both new record shapes verified field-for-field against §3:95/§4:123 by
  assertion.
- No new RNG purposes (the rule is deterministic — no roll site); §3:95
  itself untouched (coordinator-filled).

## Findings

1. **The latch is store-derived, not trace-record-derived — a deliberate
   deviation from the pin's letter, flagged for ruling.** R5's pin says
   the latch is "the existence of a `threshold_crossed` record for the
   key." That fails twice in practice: (a) the writer buffers, so a latch
   read from the trace file misses unflushed same-phase records (theft 5
   scripted immediately after theft 4 would double-fire); (b) a
   start-from-keyframe driver writes a *new* run dir — the old run's
   trace isn't there to scan, while the store (which `state_at`
   reconstructs exactly) carries over. The escalation belief's existence
   is itself log-derived state (rebuilt from `belief_formed` at replay),
   so it serves the pin's stated purpose — "reconstruction can't
   double-fire" — strictly better. The replay-parity test proves the
   property. If the coordinator wants the pin's letter instead, the
   flush-then-scan-own-trace path is implementable but strictly weaker.
2. **Engine-internal events consume branch seqs.** The escalation event
   takes the next seq on the branch (max+1), so scenario fixtures that
   hand-number seqs must skip past it (the rung test's theft five uses
   seq 6). Worth one line in the scenario-authoring doc if L-E/L-F
   cascades follow the same pattern.
3. **Mid-construction trace reads need a flush.** The writer's per-tick
   flush means scripted pre-run writes aren't visible to
   `FrameLogReader` until a flush — the test flushes explicitly (and
   tolerates the closed-file case after `close()`). Not a defect (the
   liveness contract is about the tick loop), but the idiom is now
   documented in the test's helper for future rung tests.
4. **Rule 11 has no roll site** — accumulation is deterministic given the
   log, so no RNG purpose was needed (ADR-0009 untouched). The
   `rule_evaluated` rows for it carry the full accumulator state in
   `inputs` per the "visible, not silent" contract.
