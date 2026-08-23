# Lane 9 — M1 completion: agent-debug CLI + pytest deep links

**Renumbered from Lane 8** (2026-08-23): a second, independently-dispatched
initiative claimed "Lane 8" for map conversion + visual parity
(`docs/work-packets/lane-8-map-conversion.md`, foundation commit
`28b81d6`) at essentially the same time this packet was written. This
packet and its delivered commit (`f8e68f9`, originally titled "lane 8" in
its own commit message) are the same body of work — renumbered here to
resolve the collision, not a re-scoping.

**Status:** Ready to start immediately. Depends only on Lane 4 (landed,
commit `15cb866`) — you build entirely on `chronicle/framelog.py`'s reader.
No dashboard/frontend work; no file overlap with any other lane.
**Effort:** medium.

## Context

`docs/dashboard-build-plan.md` §2 M1 lists two acceptance items that no
lane has picked up yet, both unblocked now that Lane 4 landed the M0
reader:

1. **Agent-debug CLI** (`python -m chronicle …`): minimal read-only
   subcommands over the M0 reader — `inspect`, `trace`, `feed` — plus the
   `inject` event-composition path the dashboard's injection console
   already assumes exists. Build plan's own framing: "cheap here because
   Lane 4 built the reader; expensive to retrofit."
2. **pytest deep links**: `docs/ui-spec.md` §1.2's "runs-directory
   contract" — a failing scenario assertion's output includes a URL that
   opens the dashboard at the failing tick, entity selected, offending
   record highlighted. "Ships with the first view" (ui-spec line 47) —
   the first view has now shipped (Lanes 5-7).

## Read first (in order)

1. `docs/dashboard-build-plan.md` §2 M1 (the two bullets above, verbatim
   acceptance criteria) and M2 (so you don't build M2's encounter-feed
   scope by mistake — `feed` here is a CLI read, not the dashboard's
   virtualized table).
2. `docs/ui-spec.md` §1.2 (URL-state contract: `run`, `branch`, `t`,
   `view`, `sel`, `panels`, `filters`, `runB`/`alignment` — the exact
   query keys a deep link must use) and the runs-directory contract
   (same section, "a pytest-emitted deep link is therefore resolvable by
   construction").
3. `chronicle/framelog.py` — `FrameLogReader` (`state_at(tick) ->
   ReconstructedState` with `.claims`, `.social`, `.schedule`;
   `records(stream, upto_tick=...)` for raw trace/event iteration;
   `read_index()`/`rebuild_index()`). This is your only new dependency —
   everything else is read-only over what Lane 4 already built.
4. `chronicle/claims.py`'s `ClaimStore.beliefs_of()`, `chain_for()` (or
   equivalent evidence-walk method — check current signatures, don't
   assume) — what `inspect`/`trace` report on.
5. `dashboard/src/components/InjectionConsole.vue` — **read the exact CLI
   invocation string it already composes** (`chronicle inject --run
   <runId> --at <atTick> --type <eventType> …`). Your `inject` subcommand's
   flag names must match this string exactly, or the console's own
   copy-paste affordance is a lie. If the component's format is ambiguous
   or incomplete, that's a finding to report, not something to silently
   improvise past.
6. `docs/dashboard-build-plan.md` M1's injection-console scope note: "No
   live coupling, no fork path — see §3 for why fork-at-T is split out of
   this milestone." Your CLI's `inject` inherits the same scope limit —
   it composes and prints/validates the canonical-event JSON; it does
   **not** perform a live fork-write into an existing run. Actually
   writing an injected event is the deferred fork milestone's job, not
   this lane's.

## Task

1. **`chronicle/__main__.py`** gains subcommands (argparse or stdlib is
   fine — no new dependency without naming it in your report):
   - `inspect <npc_id> --run <run_id> --at <tick>`: reconstructs state at
     that tick via `FrameLogReader`, prints that NPC's beliefs (claim,
     variant, confidence/verbatim/gist strengths, rumor stage via
     `stage_at()`) and any social-layer records naming them
     (relationships, grudges, obligations, reputations they hold or are
     subject to).
   - `trace <claim_id> --run <run_id> --at <tick>`: walks and prints the
     claim's full evidence/variant lineage (witness → retellings →
     corroborations → supersessions) as of that tick.
   - `feed --run <run_id> [--location <id>] [--npc <id>] [--from-tick
     <t>] [--to-tick <t>]`: prints matching trace-stream records in tick
     order — a read-only CLI view of the same `trace.jsonl` the dashboard's
     future encounter feed (M2) will render, filtered by the given
     criteria. This is not the M2 feed itself — no pagination/virtualization
     concerns, just filtered iteration.
   - `inject --run <run_id> --at <tick> --type <event_type> [--payload-json
     <json>]`: composes and pretty-prints the canonical-event JSON for the
     given type/payload (validate against `chronicle/events.py`'s known
     event kinds; reject unknown types with a clear error), matching the
     flag names `InjectionConsole.vue` already assumes. Does not write to
     the run's log.
2. **pytest deep links** (`scenarios/conftest.py`, which Lane 4 already
   created — extend, don't replace): a fixture or hook that, on assertion
   failure in a scenario test, appends a dashboard URL to the failure
   output — built from `run_id` (from the test's own driver/writer),
   failing `tick`, and (where the test can name one) the entity/record to
   select, using ui-spec §1.2's exact query-param names. Check whether
   pytest's `pytest_exception_interact` hook or a fixture-level
   try/except is the better fit given this project's existing test
   structure — your call, report which you picked and why.
3. Unit/integration tests for all four subcommands and the deep-link
   mechanism, following this project's existing test conventions
   (`chronicle/tests/`, plain assertions, no new test framework).

## Acceptance

- `uv run pytest` stays green — including a new test proving a
  deliberately-failed scenario assertion's output contains a
  correctly-formed deep link.
- `uv run ruff check .` clean.
- Each CLI subcommand has at least one test exercising it against a
  small hand-built or fixture run log.
- `inject`'s flag names verified against `InjectionConsole.vue`'s
  composed string — call this out explicitly in your report (match or
  mismatch, and if mismatch, which side you believe is right and why).

## File boundaries

- **Create/edit:** `chronicle/__main__.py`, new `chronicle/*.py` modules
  as needed for CLI subcommand logic (keep it out of `claims.py`/
  `social.py`/`schedule.py` — read-only consumers, don't add methods to
  the stores unless a genuinely missing read-only accessor is a finding),
  `scenarios/conftest.py`, new tests under `chronicle/tests/`.
- **Do not touch:** `chronicle/claims.py`, `chronicle/social.py`,
  `chronicle/schedule.py`, `chronicle/driver.py`, `chronicle/framelog.py`,
  `chronicle/rng.py` (Lane 4's, accepted — if you find a missing
  accessor you need, report it, don't add it yourself), `dashboard/`
  (any lane's), frozen docs.

## Conventions

- Follow existing code style: dataclasses, type hints, docstrings citing
  spec rules where applicable.
- Commits: this project's current convention is agents commit their own
  work; the overseer reviews what lands.
