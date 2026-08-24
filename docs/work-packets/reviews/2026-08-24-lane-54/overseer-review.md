# Lane 54 overseer review — timeline as global chrome (M7 fix)

**Delivered:** `921bfe4` (worker-committed; no delivery report filed
on disk — reviewed directly).

## Battery, re-run independently (covers lanes 54/56/57 together)

- `uv run pytest -q`: 249 passed (untouched).
- `uv run ruff check .`: clean.
- `npm test`: 608/608 across 87 test files (confirmed the full suite
  genuinely includes the three new test files — `find src -name
  "*.test.ts" | wc -l` → 87, matching exactly; standalone run of
  `App.test.ts` alone also green, 4/4).
- `npm run build`: clean.
- `npm run check-range --both`: 206 dev+preview.

## Claim verified against the repo

`dashboard/src/App.vue:58` mounts `<TimelineBar />` directly, and the
file's own header comment (confirmed by reading it) explains the real
subtlety correctly: `App.vue` — not `Shell.vue`, despite its name — is
the actual router-outlet wrapper common to every route, and the
watcher that populates `stores/mapData.ts` now lives there but steps
aside when `/map` is active so `MapScreen.vue`'s own standalone-tested
watcher keeps sole ownership. This is a genuine, correctly-diagnosed
data-ownership hazard, not a superficial "just mount it everywhere"
fix that would have raced two watchers against the same store.

## File boundaries

`App.vue`/`App.test.ts`, `TimelineBar.vue`, `MapScreen.vue`/
`MapScreen.test.ts` — all reasonable given the packet's own framing
("the shell/layout component, the timeline component ... `MapScreen.vue`
only to remove a now-duplicate mount"). No Python, no frozen docs.

## Ruling

**Accepted.**
