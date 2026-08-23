# Lane 6 — M1: log-reader client + global chrome (Track B, part 2)

**Status:** Ready to start immediately. Builds on Lane 5's accepted scaffold;
runs in parallel with Lane 4 (you read the *schema*, not its code — mock
logs until real ones exist).
**Effort:** medium-large.

## Context

Lane 5 delivered the shell: Vite + Vue 3 + TS + Pinia + vue-router,
`src/state/urlState.ts`, RunPicker, the `serveRuns` Range middleware, and
`scripts/check-range.mjs`. This lane teaches the app to *read* frame logs
per `docs/frame-log-schema.md` v1 and adds the Tier-0 global chrome. Views
(inspector, console) are the next lane — not this one.

## Read first (in order)

1. `docs/frame-log-schema.md` — your contract. Payload field names, the
   sidecar index, the registry, reader rules (§7: ignore-unknown, never
   error).
2. `docs/ui-spec.md` §1.2–§1.3, §2 (chrome semantics), §0 (constraints).
3. `docs/decisions/0009-keyed-randomness.md` (roll_key shape, for the
   trace-row renderer's roll display).
4. Lane 5's code: `dashboard/src/` (all of it) — follow its conventions.

## Task

1. **Log-reader client** (`src/log/`):
   - Registry reader: fetch `runs/index.json`, tolerate absence/malformed
     entries (schema §6).
   - Stream reader: Range-fetch via the run's `index.json` byte offsets;
     JSONL parse with the torn-tail guard (a non-terminated tail is
     not-yet-written, skip it); LIVE tailing by byte-offset poll
     (~1 s cadence).
   - State reconstruction: nearest keyframe ≤ T + replay deltas to T +
     analytic decay at read time (decay is closed-form; port the formula
     from `chronicle/claims.py:71` — `value * 0.5 ** (elapsed / half_life)`
     — reading the constants from the keyframe record, not hardcoding).
   - Unknown record types / fields / keyframe keys: skip-and-continue
     (schema §7). Unit-test this against records from a fictional
     `schema_version: 2` future.
2. **Mock-run fixture**: a hand-written `runs/mock-t0/` (events + trace +
   index + registry entry) exercising every Tier-0/1 record type, including
   negative rows (`encountered: false`, `nothing_salient`) and a keyframe.
   This is the dev/test fixture until Lane 4 emits real logs — and it
   stays as the CI fixture afterward.
3. **Global chrome v1** (ui-spec §2, Tier-0 forms):
   - Time control: tick/day stepper + direct tick entry, driving the
     playhead in `urlState` (`t`). No timeline widget yet (that's Tier 2).
   - Selection model: one global selection in Pinia, mirrored to `sel` in
     the URL.
   - Salience filter: the three defaults (developer/observer/story) as a
     store + segmented control; lists downstream will consult it. Lane 7
     owns the `SalienceSwitch` component's markup/class structure — build
     the store and wire the control's behavior, but don't preempt its
     visual structure; land it as minimal unstyled markup Lane 7 skins in
     place, not a second competing implementation.
   - LIVE dock state: follow-newest vs. detached, per the approved design
     (`LIVE — docked · following newest frame · +N events · scrub to
     detach`).
4. **Derived-state module** (`src/derived/`): rumor stage at T
   (unheard/heard/repeated stored; dormant/forgotten derived per
   `claims.py` rule 16/19 — mirror the logic, don't invent thresholds;
   read them from the keyframe/schema constants), confidence decay at T.

## Acceptance

- `npm run build` + `npm test` + `npm run check-range` green from a fresh
  checkout; new unit tests for the reader (torn tail, unknown fields,
  keyframe+delta reconstruction equals a hand-computed expectation).
- The shell renders the mock run: stepper moves T, state at T reflects
  keyframe+deltas, LIVE tail picks up an appended record within ~2 s.
- No views. If you're styling an inspector, stop.

## File boundaries

- **Create/edit:** `dashboard/src/`, `dashboard/public/` or mock-fixture
  location per Lane 5's wiring, `dashboard/README.md` (document the mock
  run).
- **Do not touch:** `chronicle/` (Lane 4's), `docs/` (findings to the
  coordinator), Lane 5's `scripts/check-range.mjs` semantics (you may
  extend, not weaken).

## Conventions

- Commits: follow the owner's current practice (agents commit their own
  work; the overseer reviews what lands).
- TypeScript strict; no new dependencies without naming them in your
  report with a one-line justification each.
