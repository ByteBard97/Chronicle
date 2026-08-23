# dashboard

Debug/observability web UI — a first-class deliverable, not an afterthought.
Reads directly off the event log and derived state in `chronicle/`.

Planned views: map with rumor overlay, causality
timeline (trace any belief back through its evidence chain to originating
events), and an injection console for manually firing events into a running
or scenario sim during debugging. The social-graph topology view is
**explicitly deferred** (docs/ui-spec.md §4): it unlocks only if Tier-3+
debugging demands topology the inspector's Relationships tab and the diff
panel can't show — and it may never earn a view, which is an acceptable
outcome per the forcing doctrine.

Build plan: [`../docs/dashboard-build-plan.md`](../docs/dashboard-build-plan.md)
(two tracks — sim-side frame-log substrate first, then the Vue app in tier
order). Stack: Vue 3 + Vite + TS, Pinia, vue-router + `@vueuse/router`'s
`useRouteQuery` for URL state, `@tanstack/vue-virtual`, hand-rolled Canvas2D
map. UI contract:
[`../docs/ui-spec.md`](../docs/ui-spec.md).

## M1 status: scaffold, not views

This is the M1 scaffold milestone (`docs/work-packets/lane-5-m1-scaffold.md`):
the Range spike, the app skeleton, the URL-state module, and typed Pinia
store stubs. The map, encounter feed, variant tree, and provenance drill-
down are still later packets (Tier 1+, ui-spec §3 build order) and are not
built here. `src/views/Shell.vue` now also hosts skinned, static-fixture
demonstrations of the two Tier-0 views (NPC inspector, injection console)
per the design system below — those two views still read only their own
static fixtures; Lane 6's reader wires real per-tick data into them at
integration. Shell.vue's chrome itself, though, does now read a run: the
tick stepper and the LIVE dock (see "Pinia stores" and "Log reader"
below) are wired to `src/log/`'s reader, provable against the committed
`mock-t0` fixture.

(The repo-root `.gitignore` also gained a narrow `!dashboard/public/runs/`
exception — see its comment there — so the committed mock-t0 fixture
below isn't swallowed by the pre-existing, unanchored `runs/` ignore
pattern.)

## Design system

`dashboard/design/` (vendored, read-only) is the approved reference: the
Variant-C mockup `map-c-skyrim.dc.html` and its token contract
`design-tokens.md`. The build lives in two places:

- `src/styles/tokens.css` — every design-tokens.md value as a CSS custom
  property, in a TRACED section, plus an EXTENDED section for values that
  only exist in the mockup's inline styles/JS (not written out in the
  tokens doc's prose) — e.g. the belief-bar colors, the panel-title color,
  the per-tone belief-card chip triads, and the fact that panel alpha
  actually varies by chrome role (.82/.85/.9/.92) rather than the doc's
  single .82. `src/styles/global.css` loads the three OFL font families
  (Cinzel / IBM Plex Mono / Alegreya) from Google Fonts for dev
  convenience, matching the mockup's `<link>`. **Self-hosting these fonts
  is a distribution-time task**, not done here — fetch the three families'
  static/variable `.woff2` files, serve them from `dashboard/public/fonts/`
  (or wherever the build's static assets land) and swap the `@import` for
  local `@font-face` rules before shipping somewhere that can't reach
  Google Fonts or shouldn't depend on a third-party font CDN.
- `src/components/` — base presentational components (PanelGlass, Chip,
  StrengthBar, StageDot, GlyphBadge, LegendStrip, SalienceSwitch), each
  with a component test asserting props → classes/structure, plus the
  Tier-0 view skins built on top of them (NpcInspector, BeliefCard,
  InjectionConsole). `RunPicker.vue`'s existing `<select>` was skinned in
  place, not rebuilt, to keep its structure/id/store contract (and the
  Shell.vue tests that depend on it) intact.

`SalienceSwitch` is a plain props-in/emit-out component (`mode` +
`update:mode`), typed against `SalienceLevel` from `src/stores/salience.ts`
so either side of the store wiring works. `Shell.vue` keeps the original
`<select id="salience-level">` (visually hidden via `.sr-only`) bound to the
same store as the visible `SalienceSwitch`, so the existing
`Shell.test.ts` assertion on that select's options and the new skinned
control can never disagree.

## Getting started

```
npm ci
npm run dev        # http://localhost:5173
npm run build      # type-checks (vue-tsc -b) then builds to dist/
npm run preview    # serves dist/ at http://localhost:4173
npm run typecheck  # vue-tsc -b --noEmit, no emit
npm test           # vitest run (includes the URL-state round-trip test)
npm run check-range  # the standing Range/206 assertion (dev + preview)
```

Node 22.16 was used to build and verify this milestone. A few transitive
dev dependencies (vitest's `jsdom`, `undici`, `@babel/*`) declare a slightly
higher minimum (`>=22.18`–`22.22`) and `npm install`/`npm ci` emit
`EBADENGINE` warnings for them; nothing broke in practice (build, typecheck,
tests, and the Range checks above all pass), but it's worth bumping the
local Node version at some point so those warnings go away rather than
becoming background noise.

## Range spike

**Task zero, per the build plan.** The entire log-reader design (byte-offset
fetch, torn-tail guard, LIVE polling) depends on the serving setup answering
**206** to a `Range` request. This was tested, not assumed, in two stages.

**Stage 1 — native Vite serving.** `dashboard/runs` symlinked to the
repo-root `runs/` directory, with `server.fs.allow` covering the repo root
so Vite's dev server would follow the symlink. Fixture: `runs/dummy-run/events.jsonl`
(80,670 bytes) and `runs/index.json`, both served through this path.

```
$ curl -sS -D - -o /dev/null -H "Range: bytes=0-99" \
    http://localhost:5173/runs/dummy-run/events.jsonl   # vite dev
HTTP/1.1 206 Partial Content
Content-Length: 100
Content-Range: bytes 0-99/80670
Accept-Ranges: bytes
...

$ curl -sS -D - -o /dev/null -H "Range: bytes=0-99" \
    http://localhost:4173/runs/dummy-run/events.jsonl   # vite preview, same fs.allow config
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 329
...
```

**Result: `vite dev` passes natively (206, correct `Content-Range`); `vite
preview` fails.** `vite preview` only serves its build output (`dist/`) and
does not honor `server.fs.allow` at all — the request falls through to the
SPA's `index.html` fallback (200, `text/html`, 329 bytes) instead of ever
reaching the file. `preview` is meant to be the closer-to-production check,
so this is the one that would have shipped a broken assumption.

**Stage 2 — the fallback, applied to both servers.** Per the spec
("If either fails ... the fallback ... is chosen before the reader client
exists"), rather than build two different code paths — Vite's built-in
static handling for `dev`, nothing for `preview` — this milestone ships a
single hand-rolled, Range-aware static middleware
(`vite-plugins/serveRuns.ts`) mounted identically in Vite's
`configureServer` (dev) and `configurePreviewServer` (preview) hooks. It
serves `/runs/*` directly from the filesystem (resolving symlinks, guarding
path traversal), with proper `Range`/`206`/`416` handling, `Content-Range`,
and `Accept-Ranges: bytes`. This is file-serving, not an application
backend — the ui-spec §1.3-permitted fallback.

Re-running the same two requests with the plugin active:

```
$ curl -sS -D - -o /dev/null -H "Range: bytes=0-99" \
    http://localhost:5173/runs/dummy-run/events.jsonl   # vite dev
HTTP/1.1 206 Partial Content
Accept-Ranges: bytes
Content-Type: application/x-ndjson
Content-Range: bytes 0-99/80670
Content-Length: 100

$ curl -sS -D - -o /dev/null -H "Range: bytes=0-99" \
    http://localhost:4173/runs/dummy-run/events.jsonl   # vite preview
HTTP/1.1 206 Partial Content
Accept-Ranges: bytes
Content-Type: application/x-ndjson
Content-Range: bytes 0-99/80670
Content-Length: 100
```

Both servers now answer 206 identically, through the same code path.
`runs/index.json` was also checked directly (not just its byte-Range
behavior): it comes back as `Content-Type: application/json` with the raw
JSON body, not wrapped by any Vite JSON-module transform — confirmed at
both `/runs/index.json` (`vite dev`) and after the plugin change
(`vite preview`).

## Static wiring — chosen mechanism

`runs/` lives at the repo root (gitignored, `CHRONICLE_RUNS_DIR`-overridable
per the build plan), one level above `dashboard/`. It's exposed to both
`vite dev` and `vite preview` by `vite-plugins/serveRuns.ts` (see above),
which intercepts any request under `/runs/*` before Vite's own middleware
and serves it straight from `CHRONICLE_RUNS_DIR` (default: `<repo-root>/runs`),
independent of the current working directory or of Vite's `fs.allow`/public-dir
rules. An earlier iteration of this spike used a `dashboard/runs -> ../runs`
symlink plus `server.fs.allow` to prove `vite dev` could reach the file
natively (see the "Range spike" section above); once the plugin above took
over serving, that symlink and `fs.allow` config were removed — the plugin
resolves `runs/` directly and does not need either.

This means: no `public/` copy-into-`dist/` problem (a gitignored, potentially
large run-log directory never gets baked into the build output), and no
divergence between what `dev` and `preview` can see.

## Standing Range assertion

`scripts/check-range.mjs` (wired as `npm run check-range`) is the automated,
CI-runnable check the spec asks for (ui-spec v1.2.1 §1.3): it boots `vite
dev` and/or `vite preview` itself (no server assumed to be already running),
waits for the port, writes a small fixture run under `CHRONICLE_RUNS_DIR` if
one doesn't already exist, fetches it with a `Range` header, asserts `206`
and a present `Content-Range`, then tears the server down. Run modes:

```
node scripts/check-range.mjs           # vite preview only
node scripts/check-range.mjs --dev     # vite dev only
node scripts/check-range.mjs --both    # both (the npm script's default)
```

This is the regression catcher, not the one-time spike above — a future
Vite upgrade, a proxy in front of it, or a middleware-order change should
fail this check rather than silently breaking LIVE tailing.

## URL state

`src/state/urlState.ts` is the single place the URL-state contract
(ui-spec §1.2: `run`, `branch`, `t`, `view`, `sel`, `panels`, `filters`,
`runB`/`alignment`) is defined. It's split into a pure codec
(`encodeUrlState`/`decodeUrlState`, tested directly in
`src/state/urlState.test.ts` — no router mount needed) and a thin
`useUrlState()` composable that binds each field to `useRouteQuery`
(`@vueuse/router`) using that same codec. Defaults are omitted from the URL;
for the collection fields (`sel`, `panels`, `filters`) that specifically
means empty-collection encodes to "absent" and absent decodes back to
empty — not to some other default — which is what the round-trip tests for
those fields check explicitly (see `urlState.test.ts`'s "empty collections"
and delimiter-character cases). `useUrlState()` is exercised both ways: the
pure codec directly, and mounted through a real `vue-router` (memory
history) in `urlState.mount.test.ts` — including the read shapes a live
router hands a decoder that a hand-built query record never does (a bare
`?sel` decodes as `null`, a repeated `?t=1&t=2` as `string[]`), and the
write path (`ref.value = ...`), which is the direction every call site in
this app actually uses.

**History mode (`push` vs `replace`) is a decision, not a default.**
`useRouteQuery` defaults to `'replace'` (checked against
`@vueuse/router`'s source, not assumed) — which would silently break
ui-spec §1.2 consequence 3 ("back/forward buttons are time-and-focus
history for free") for every field if left alone. `urlState.ts` sets
`t` to `'replace'` (a scrubber updates it continuously; every scrub frame
becoming a history entry is not what the spec means by "history") and
every other field to `'push'` (a run switch, view switch, selection, or
panel open is the kind of navigation a back button should undo). Verified
empirically, not just asserted: `urlState.mount.test.ts`'s last two cases
push `run` twice and confirm `router.back()` restores the prior value,
then write `t` twice under `'replace'` and confirm `back()` skips over
both. This mapping is a default per field, not frozen — a later view is
free to override `mode` at a specific call site — but the starting point
is decided here rather than per call site.

## Pinia stores (M1: typed stubs only)

`src/stores/selection.ts` (global selection + follow-mode target),
`src/stores/salience.ts` (the three salience-filter defaults +
"all events" toggle), and `src/stores/runs.ts` (the run registry cache,
fetches `runs/index.json` and tolerates its absence as a `"missing"` status,
not an error) are typed Pinia stores with no UI beyond `Shell.vue`'s
smoke-test wiring. Views that actually use these are later packets.

`src/stores/liveDock.ts` (LIVE dock state: docked/detached + the pending
new-event count, driving the approved chrome text
`LIVE — docked · following newest frame · +N events · scrub to detach`)
and `src/stores/frameLog.ts` (wires `src/log/`'s reader to `urlState.run`/
`urlState.t`: picking a run and moving the tick stepper drive
`RunReader.stateAt(T)`, and leaving `t` at `null` docks the LIVE tail) are
this lane's additions. `frameLog.ts`'s `bindToUrlState` watches `run` and
`t` together in one async handler (see its docstring for why watching
them independently is a hazard); `frameLog.test.ts` proves LIVE tailing
end to end against the committed fixture: dock, wait for the poller to
start, append a record to the served files, advance real time by the ~1s
cadence, and assert the LIVE dock's new-event count moved.

Both stores are in the same "typed store, minimal/no view" spirit as
`selection.ts`/`salience.ts` above. `Shell.vue`'s `#frame-log-readout`
element (plain claim/belief counts, no styling) is the M1 smoke-test proof
that the wiring works end to end —
not the NPC inspector, which is a later lane's view.

## Log reader (`src/log/`)

The client side of `docs/frame-log-schema.md` v1, split by concern:

- `types.ts` — the schema's envelope, payload catalog, keyframe shape, and
  the two JSON files (run registry + per-run sidecar index), typed loosely
  (index signatures) on purpose: schema §7 requires readers to *ignore*
  unknown record types/fields/keyframe keys, and an exact TypeScript type
  would fight that at the type level for the same fields the runtime is
  supposed to tolerate.
- `jsonl.ts` — the torn-tail guard: `splitCompleteLines`/`parseJsonlLines`
  are pure; `JsonlTailReader` is the stateful incremental reader both the
  full-stream reader and the LIVE poller build on, so a record split across
  two fetch boundaries is reassembled rather than dropped.
- `rangeFetch.ts` — the one seam that touches `fetch`'s `Range` header
  directly.
- `registry.ts` — `fetchRunRegistry()`: tolerates a missing/malformed
  `runs/index.json` and skips individual malformed entries (schema §7
  applied at the registry level, not just the record level) without
  dropping the well-formed ones. It also always merges in the mock-t0
  fixture's registry entry (see below) from a path outside `/runs/*`, so
  the fixture is reachable regardless of whatever the real, gitignored
  `runs/index.json` does or doesn't contain at the time — see "Mock run
  fixture" below for why that matters.
- `sidecarIndex.ts` — `fetchSidecarIndex()` plus `tickAtOrBefore`/
  `keyframeAtOrBefore`, the byte-offset lookups the sidecar index exists
  for.
- `streamReader.ts` — `readByteRange` (one-shot Range read + torn-tail
  parse) and `LiveTailPoller` (repeats that from the last consumed byte on
  a ~1s timer — ui-spec §1.3's LIVE-tailing cadence).
- `reconstruct.ts` — state reconstruction: `fromKeyframeState` (keyframe →
  working state) and `replayTo` (fold trace/event deltas into it,
  dispatching per `record_type`; an unrecognized type — including a
  fictional future `schema_version: 2` addition — is skipped, not an
  error).
- `runReader.ts` — `RunReader.stateAt(t)` ties it together: nearest
  keyframe ≤ t (via the sidecar's byte offset, not a scan from 0) +
  replayed deltas; `startLiveTail()` starts pollers on both streams.

`src/derived/` mirrors the read-time derivations `docs/ui-spec.md` §1.1
requires: `decay.ts` ports `chronicle/claims.py`'s exact formula (`value *
0.5 ** (elapsed / half_life)`, cited at `docs/frame-log-schema.md` §8) and
`rumorStage.ts` ports `stage_at()`'s dormant/forgotten derivation (rule
16/19). `constants.ts` mirrors `claims.py`'s module-level tunables
(`WITNESS_CONFIDENCE`, the retell decay factors, the three half-lives, the
rumor-stage thresholds) — see that file's header for a real finding: the
frame-log schema's keyframe payload doesn't carry these constants anywhere,
so "read them from the keyframe record" (as this lane's work packet asked)
isn't possible against the schema as written; mirroring is the fallback,
with the drift risk that implies if the Python side ever recalibrates them.

## Mock run fixture (`public/runs/mock-t0/`)

The dev/test fixture until Lane 4 emits real logs, and the fixture this
project intends to keep using in CI afterward (per the work packet). It
exercises every Tier-0/1 record type in `docs/frame-log-schema.md` §3/§4 —
`npc_died`, `crime_witnessed`, `rumor_heard`, `belief_formed`,
`belief_corroborated`, `encounter_rolled` (both a positive row and the
negative `encountered: false` row), `transmitted` (including a mutated
retelling), `nothing_salient`, and a keyframe (with a deliberately
unknown, Tier-5-shaped `roles` key, to exercise schema §7's "unknown
keyframe keys" tolerance against real content, not just a synthetic test)
— across two branches of reconstruction: replay-from-empty for `t <= 3`
(no keyframe exists yet) and keyframe-plus-delta for `t` up to 96 (the
keyframe sits at tick 24; one `transmitted` record follows it at tick 96).
`src/log/reconstruct.test.ts` and `src/log/runReader.test.ts` both exercise
it directly — the latter through the same Range-fetch code path the app
uses, via a stub that serves the real committed files with real
`Content-Range` semantics, not a shortcut.

It lives under `public/` (not the gitignored, repo-root `runs/`) so it's
committed and reachable via Vite's ordinary static-file serving in both
`vite dev` and `vite preview`, at `/runs/mock-t0/*` — no changes to
`vite-plugins/serveRuns.ts` were needed: that plugin only intercepts
requests under `/runs/*` that resolve under `CHRONICLE_RUNS_DIR`, and falls
through (`next()`) to Vite's normal handling — which serves `public/` —
whenever the file isn't there.

**The one wrinkle:** the *registry* for it, unlike the run's own files,
can't simply sit at `public/runs/index.json` — that path collides with the
real, gitignored `runs/index.json`, and `serveRuns.ts` would serve the real
file (once one exists, e.g. after `npm run check-range` seeds its own tiny
fixture) and never fall through to the one in `public/`, silently dropping
mock-t0 from the registry the moment any real run appears. Its registry
entry instead lives at `public/mock-fixtures/mock-t0.registry-entry.json`
— outside `/runs/*` entirely — and `src/log/registry.ts`'s
`fetchRunRegistry()` always merges it into whatever the real registry
returns (or into an empty list, if the real one 404s). Verified both ways
in `registry.test.ts`.

`RunPicker.vue`'s dropdown reads `useRunsStore.pickableRuns`, a getter that
appends the mock-t0 fixture (in the store's own display shape — it only
needs to round-trip through `<option>`, not satisfy
`fetchRunRegistry()`'s schema-accurate validation) to whatever `runs`
loaded, without duplicating it or changing `runs`/`load()` itself — so
`runs.test.ts`'s existing assertions on `store.runs` are untouched. mock-t0
is therefore pickable from the actual dropdown regardless of whether a
real `runs/index.json` exists yet, the same "never silently shadowed out"
property `src/log/registry.ts`'s merge gives the schema-accurate reader.

**Finding — two registry shapes exist on disk.** `docs/frame-log-schema.md`
§6 defines the registry entry as `{run_id, seed_id, created_wall_ts,
branches, tick_range: {start, end}, streams: {events, trace}, status}`.
`src/stores/runs.ts`'s `RunRegistryEntry` (and what `scripts/check-range.mjs`
actually writes to the real, gitignored `runs/index.json`) instead uses
`{run_id, seed_id, created, tick_range: [start, end], streams:
string[]}` — different field names, different `tick_range` shape, no
`branches`/`status`. `src/log/registry.ts`'s `isValidEntry()` is written
against the schema document, so it correctly rejects the
`check-range.mjs`-style entry as malformed (visible in `registry.test.ts`'s
"is still present after a real run has been registered" case, which uses
exactly that shape for the *other* entry in the list). Not fixed here —
`stores/runs.ts` is Lane 5's accepted code and `check-range.mjs`'s
semantics are explicitly out of this lane's file boundary — but real, and
worth reconciling before Lane 4's actual writer and this reader both exist
and need to agree.

## Supply chain

Exact version pins (no `^`/`~`) in `package.json`, a committed
`package-lock.json`, `npm ci` for reproducible installs, and
`ignore-scripts=true` in `.npmrc` (2026 lesson: the May npm takeovers hit
TanStack's Vue packages specifically). Verified: `npm ci` with
`ignore-scripts` still produces a working `esbuild` binary (installed via
`optionalDependencies`, not a postinstall script) and a working `@vueuse/*`
(this version of `@vueuse/core`/`@vueuse/router` has no `vue-demi`
dependency, so there's no postinstall-shim step to skip). If a future
dependency bump reintroduces a real postinstall need, add a repo-local
script for it rather than dropping the `ignore-scripts` rule.

## map/

WhiterunWorld backdrop + spatial fixture for the map view:

- `whiterun_map.json` — committed. World→pixel calibration for the backdrop
  (`px = s·x + offsX + W/2`, `py = −s·y + offsY + H/2`) plus exterior
  world-unit and pixel coordinates for 26 named locations (load-door REFRs
  resolved via XTEL teleport links, plus named markers: market, Gildergreen,
  Skyforge, main gate, Heimskr's shrine). The sim's location IDs
  (`chronicle/fixtures/whiterun_schedule.py`) map onto these keys.
- `bake_whiterun_map.sh` — regenerates the backdrop with fo76utils from the
  user's own game files. Renders are deterministic run-to-run.
- `whiterun_topdown_4k.png` — gitignored (Bethesda-derived, internal use
  only; never commit). Regenerate with the bake script.

Extraction pipeline (esmdump REFR/XTEL dump → door resolution → JSON) is
ad-hoc in /tmp for now; productionize it if the location set needs to grow.
See docs/research/14-isometric-render-foundations.md for the render
foundations and verification.
