# Chronicle — Dashboard Build Plan (v1.3 — final, approved)

**Status:** v1.3, approved. v1.2: two independent code-grounded reviews
  applied — fork re-sim split out of M1 into §3 (deferred, gated on a real
  need; M0 keeps the start-from-keyframe driver shaping); Range spike made
  M1's task zero; prerequisite 4 expanded to name the constant rebaseline
  the tick quantum forces (verified: the fixture is quantum-agnostic bare
  ints and `RUMOR_DORMANT_AFTER = 5000` ≈ 208 days at an hour-quantum);
  M2 instruments only the three encounter outcomes with Tier-1 producers
  (declined reserved in schema, instrumented at M4 with its Tier-3
  producer); static-server wiring for `runs/` and atomic index writes made
  explicit; keyed-RNG bullet retargeted from `propagate.py` (which has no
  randomness) to `schedule.py`'s `sample_encounters()` (the codebase's
  only dice roll, verified); the Range assumption promoted from one-time
  spike to standing automated 206 assertion in M1's acceptance (now
  ui-spec v1.2.1 §1.3). v1.3: the approval review's three closing
  additions — prerequisite 0 (the constitution commit); the keyframe
  payload placed in the schema catalog as versioned-and-extensible
  (additive per tier, never breaking); the social-graph README deferral
  note (landed with the constitution commit).

Written against `docs/ui-spec.md` (v1.2.1),
`docs/scenario-ladder.md` (v0.4 FINAL), `docs/vision-v2.1.md`, and research
reports 12–14. The UI spec freezes *what must not churn*; this plan sequences
*what gets built, in what order, with what acceptance*. Build order equals
ladder tier order; no view before its forcing tier (ui-spec §6).

**Structure:** two tracks sharing one contract. **Track A (sim-side)** builds
the frame-log substrate the UI spec presumes — none of it exists today;
`chronicle/` is pure-function stores driven by scenario tests. **Track B
(dashboard)** builds the Vue app that reads the logs. Track A leads; every B
milestone is gated on the A work its tier needs.

---

## 0. Binding decisions made by this plan

These were deliberately left open by the spec; decided here so nobody
relitigates them mid-build:

- **Stack (binding):** Vue 3 (`<script setup>`, Composition API) + Vite +
  TypeScript, strict mode. Owner's working stack.
- **URL state (§1.2 of the spec):** vue-router query params via VueUse's
  `useRouteQuery` — typed, bidirectional, defaults omitted from the URL. The
  whole view-state contract (`run/branch/t/view/sel/panels/filters`) is one
  composable module, `dashboard/src/state/urlState.ts`, the single place
  query keys are defined.
- **Non-URL state:** Pinia (selection model, run registry cache, loaded-frame
  caches).
- **Tables at 10⁵–10⁶ rows:** `@tanstack/vue-virtual` (official Vue adapter,
  headless). No table framework — our columns are few and bespoke.
- **Map:** hand-rolled Canvas2D + hidden-canvas color-key picking. No
  rendering library. WebGL quarantined per spec §0.
- **Component library:** none. This is a bespoke observability tool; panels,
  chips, bars, and tooltips are hand-rolled DOM/SVG per spec §0's renderer
  split. (If a primitive ever fights back, reach for Reka UI headless — not
  before.)
- **Supply chain (2026 lesson — the May npm takeovers hit TanStack's Vue
  packages specifically):** minimal dependency set, exact version pins,
  committed lockfile, `npm ci` everywhere, no install scripts from deps
  (`--ignore-scripts` in `.npmrc`).
- **Repo layout:**
  - `dashboard/` — the Vue app (Vite root), plus the existing `map/` assets.
  - `chronicle/framelog.py` — the writer (Track A).
  - `chronicle/driver.py` — the tick loop (Track A).
  - `runs/` — frame logs, gitignored, path overridable via one env var
    (`CHRONICLE_RUNS_DIR`) shared by pytest and the dashboard.
- **Run enumeration, statically:** the writer maintains `runs/index.json`
  (run registry: id, seed, created, tick range, stream files). A static
  server can't list directories; the registry is how the run picker works
  without a backend.

## 1. Prerequisites (blocking, none are code)

0. **The constitution commit.** This plan cites `docs/scenario-ladder.md`
   (v0.4), `docs/ui-doctrines.md`, `docs/vision-v2.1.md`, and
   `docs/ui-spec.md` (v1.2.1) — none of which can be "written against"
   until they're in the repo. One commit, in the vision's precondition
   order: ladder → doctrines → vision → spec (v1.2.1, so the addendum
   items this plan incorporated have their source on disk). Nothing else
   in this plan honestly claims "written against" until this lands.
   *(Landed — see git history.)*
1. **Compile `docs/ui-doctrines.md`** — ui-spec's merge precondition;
   mechanical compilation from `docs/research/dashboard-ui-prior-art/`.
   *(Landed in the constitution commit.)*
2. **Keyed-randomness ADR** — ladder §5 flags this as an open decision. The
   derivation trace records roll values, so RNG must be keyed per
   (entity, tick, purpose) before the writer emits anything. Deciding this is
   prerequisite to M0; implementing it is part of M0.
3. **Payload schema catalog** — the spec froze the record *envelope*, not the
   payloads. First design artifact of the build: one record type per ladder
   rung (encounter-rolled, transmission, declined, rule-evaluated,
   mutation-applied, supersession, …), derived from ladder §2's machinery
   inventory. **The keyframe is itself a record type in the catalog** — its
   payload (the full derived-state snapshot shape) is the one most likely
   to churn as tiers add state (grudges at Tier 3, schedule overrides at
   Tier 4a, roles at Tier 5), so the catalog defines it as
   versioned-and-extensible from v1: additive fields per tier, never
   breaking, or M3-era logs become unreadable by M5-era readers. Written
   as `docs/frame-log-schema.md` v1 with the version integer the spec
   demands. M0 implements against it.
4. **Tick quantum and the constant rebaseline.** Decide what a tick is
   (proposal: one game-hour) — and note that this is not a documentation
   detail. The schedule fixture is quantum-agnostic bare ints
   (`start_tick=0, end_tick=200`, no unit anywhere), so landing the quantum
   **re-baselines every time constant in the codebase**:
   `CONFIDENCE_DECAY_HALF_LIFE = 500`, `VERBATIM/GIST_DECAY_HALF_LIFE =
   200/2000`, `RUMOR_DORMANT_AFTER = 5000` (claims.py:57–67 — 5,000 ticks ≈
   208 days at an hour-quantum; is that the intended dormancy horizon?), the
   30/90-quiet-day scenario durations, T2.1's 10-game-day spread. Several
   will turn out to be wrong in the new units. The schema doc records both
   the quantum and the re-derived constants — otherwise M0's
   "reconstruction matches exactly" acceptance bakes placeholder numbers in
   as if they were chosen.

## 2. Milestones

Acceptance for every milestone: its ladder rungs green **and** its
developer-twin deep links landing per ui-spec §5. Rolling wave: M0–M2 in
execution detail; M3+ deliberately coarse — later tiers earn the right to
replan by the time we arrive.

### M0 — Frame-log substrate (Track A only)

The sim learns to write the log the spec froze.

- `chronicle/driver.py`: the tick loop — advance tick, sample encounters,
  apply retellings/decay/thresholds, emit records. Existing scenario tests
  become driver runs.
- Keyed RNG landed where the randomness actually lives:
  `chronicle/schedule.py`'s `sample_encounters()` (today the codebase's
  only dice roll — a caller-supplied `random.Random` rolled sequentially,
  schedule.py:73–95) becomes keyed-hash rolls per
  hash(seed_id, purpose, tick, site, participants) per the ladder's design
  principle 4 / the prerequisite-2 ADR. `propagate.py` has no randomness
  today (`teller_and_hearer` is a pure lookup); it gets its own keyed rolls
  when Tier 2/3 machinery (variant resolution, tell-decision gating) gives
  it something to roll.
- `chronicle/framelog.py`: run-directory writer — `runs/<run_id>/` with
  `events.jsonl` / `trace.jsonl` split, `index.json` (tick → byte offset per
  stream + keyframe offsets) written incrementally with **atomic
  write-temp-rename** (a torn index mid-run would wedge the reader until a
  rescan; rename costs nothing), keyframes every K ticks (default one
  game-day), newline framing with torn-tail-safe reads, run registered in
  `runs/index.json`.
- Driver shaped for **start-from-keyframe + injected events** from the
  beginning — cheap now, and it's what the deferred fork milestone (§3)
  will need. Shaping is kept; building the fork path is not.
- Python-side reader: random access to derived state at any T from log alone
  (keyframe + delta replay + analytic decay at read time).
- **Acceptance:** the three existing `scenarios/` tests emit frame logs;
  reader reconstruction at arbitrary T matches the in-memory run exactly;
  scanning the streams rebuilds an identical `index.json` (index is pure
  acceleration, spec §1.1 three-things rule); trace volume measured and the
  exact figure recorded into ui-spec §1.1 as it requests.

### M1 — Dashboard skeleton + Tier 0 views (Track B leads)

- **Task zero, before anything else is built: the Range spike.** Five
  minutes: `curl -H "Range: bytes=0-99"` against `vite dev` and
  `vite preview` serving a run log, record the result in the README. The
  entire log-reader client (byte-offset fetch, torn-tail guard, LIVE
  polling) is designed on this assumption, and Vite's static middleware has
  historically had Range gaps for arbitrary files. If it fails, the fallback
  — a tiny static file server for `runs/`, which is file-serving, not the
  forbidden application backend — is chosen **before** the reader client
  exists, not after it breaks.
- Vite scaffold in `dashboard/`. Wiring, one line so every checkout doesn't
  rediscover it: the app is served from `dashboard/`, the logs live in
  gitignored `runs/` at repo root — expose them via `server.fs.allow` +
  symlink (or serve the repo root with `dashboard/dist` as the app path);
  the chosen mechanism is recorded in the README alongside the spike result.
- Log reader client: fetch via `index.json` byte offsets, JSONL parse,
  torn-tail guard, LIVE tailing by byte-offset poll.
- Global chrome v1: run picker (reads `runs/index.json`), time stepper +
  direct tick entry (spec §2 Tier-0 form), selection model (one global
  selection, in URL), salience filter with the three defaults.
- **NPC inspector** (spec §3.2): four stable tabs, moodlet beliefs with
  analytically-derived sparklines, dormant/forgotten shown with derivation
  inputs, five-state obligation enum with greyed no-producer states.
- **Injection console** (spec §3.1), M1 scope: the console composes
  canonical-event JSON and the exact `chronicle inject` CLI invocation
  (one-click copy/run). No live coupling, no fork path — see §3 for why
  fork-at-T is split out of this milestone.
- pytest deep links: a conftest hook builds dashboard URLs from assertion
  context + the runs registry. Ships here, per spec §1.2 consequence 1.
- `dashboard/README.md` reflects the social-graph view's explicit
  deferral (ui-spec §4's commitment). *(Landed with the constitution
  commit — done early so it can't be rediscovered as a "promised view
  vanished" finding.)*
- **Acceptance:** Tier-0 rungs green; a deliberately-failed T0 assertion's
  emitted URL opens the dashboard at the failing tick with the entity
  selected and the offending record highlighted, one click from the record.
  Plus the **standing Range assertion**: an automated check (run in CI and
  on checkout) that fetches a run log with a `Range` header against the
  dev server and asserts **206** — the spike verifies the assumption once;
  this catches it silently breaking later (a proxy, a Vite upgrade, a new
  middleware) before tailing mysteriously stops working.

### M2 — Tier 1: derivation trace + encounter feed

- Track A: `propagate.py` instruments the encounter outcomes **that have
  Tier-1 producers** as trace records: transmitted / rolled-against (value
  vs. threshold) / nothing-salient. The fourth outcome, declined-with-rule,
  requires the tell-decision policy, which the ladder places at Tier 3 —
  the **schema reserves the outcome type now** (so the feed's four-state
  rendering is built once, per spec §3.3) but the instrumentation lands at
  M4 with its producer. Pulling it forward would smuggle Tier-3 machinery
  into Tier 1.
- Track B: encounter feed (spec §3.3) — virtualized table over
  `trace.jsonl` paginated by the sidecar index, four outcome states with
  equal weight, filters, row-click → both inspectors + timeline jump.
- **Acceptance:** T1.x green; developer twin extended to one named landing
  case per negative-row type (T1.3 rolled-against, nothing-salient), per
  ui-spec §5.

### M3 — Tier 2: timeline, map, variant tree, drill-down (coarse)

Timeline widget (typed event markers, heat-stripe degradation, LIVE dock) ·
map god-view (backdrop + 26-location fixture already exist in
`dashboard/map/`; door-anchored markers, jitter seeded by
`(npc_id, location_id)`; overlay registry multi-layer-capable, one active) ·
variant tree (fixed generational layout, hand-rolled SVG, supersession
cross-links) · provenance drill-down (DAG-honest span list). Ladder T2.x
green, including supersession rungs.

### M4 — Tier 3: diff panel + rule-firing log (coarse)

Signed-Δ social-state table · rule-evaluation log with
evaluated-but-not-fired rows and fire-frequency histogram · **the
declined-with-rule encounter outcome gets its instrumentation here**
(schema type reserved since M2; its producer, the tell-decision policy,
is Tier-3 machinery). Ladder T3.x green.

### M5 — Tier 4: schedule diff + run comparison (coarse)

Before/after schedule lanes · ranked-divergence-list run comparison with
aligned scrubbers and merge-scan first-divergent-roll finder. T4a.x/T4b.x
green.

### M6 — Tier 5: role inspector (coarse). T5.x green.

### M7 — Tier 6: the walkthroughs (release gate)

The stranger walkthrough, executed by an actual stranger, six steps, ten
minutes, zero coaching; failure of any step is a spec bug. Dashboard v1
ships when this passes.

## 3. Deferred milestones (gated on a real need, not a tier)

- **Fork re-sim (formerly M1b).** A minimal local runner
  (`chronicle serve`) accepting event appends at LIVE and forks at
  historical T (re-sim from keyframe + injected events → `generation+1`,
  per ui-spec §3.1's fork semantics — the spec defines the semantics, this
  plan chooses when to build them). **Why deferred:** nothing forces it —
  no Tier 0/1 rung needs interactive injection into history (scenarios are
  scripted, and the M1 console's CLI composition satisfies the tier's
  tooling requirement), and it was the item most likely to blow up its
  milestone while sitting between M0 and the map/scrubber milestones where
  the product value lives. **Unlock condition:** the first debugging
  session that wants what-if injection, or the save/reload work that
  exercises forking anyway. M0's driver is already shaped for
  start-from-keyframe, so this is a contained build when it earns its way
  in. This is the sim's write API, not a dashboard backend — the dashboard
  still reads only files.

## 4. Risks and named unknowns

- **Fork determinism, whenever it lands** — depends on keyed RNG being
  right (prerequisite 2). A fork that diverges from an identical re-run is
  a bug in the RNG keying, and T4a.2's counterfactual assertion is its
  detector.
- **Trace volume** — 10⁵–10⁶ rows is the estimate; M0 measures the real
  figure. If it lands far above, the sidecar index + split streams absorb it
  (that collision was settled in the spec); if it lands far below, nothing
  was wasted.
- **Scope discipline** — the spec's deferred list (social graph, interview
  mode, retroactive probes, Story surface, in-game overlay) stays deferred
  until its named unlock condition fires. This plan adds nothing to it.

## 5. What this plan deliberately does not contain

Visual design (downstream of the spec, freely iterable), later-tier
execution detail (rolling wave), the ui-doctrines content itself
(prerequisite 1 compiles it), and any backend — none is needed until
measured volume forces one, which the substrate is designed to postpone
indefinitely.
