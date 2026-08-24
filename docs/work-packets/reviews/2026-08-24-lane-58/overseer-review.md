# Lane 58 overseer review — outcome filter label/value mismatch (M7 fix)

**Delivered:** `74d1b40` (worker-committed; no delivery report filed
on disk — reviewed directly against the commit and packet).

## Battery, re-run independently

Same run as lane 55 (both landed together): `uv run pytest -q` 249
passed; `uv run ruff check .` clean; `npm test` 608/608; `npm run
build` clean; `npm run check-range --both` 206 dev+preview.

## Claim verified against the repo

`dashboard/src/components/feed/FeedFilterBar.vue:74` now renders
`{{ o }}` directly — the `.replace("_", "-")` cosmetic transform is
gone, confirmed by direct read. The dropdown label and the
URL-serialized value are now the same string for every option
(`rolled_against`, `nothing_salient`, etc.) — approach (a) from the
packet, as recommended. New `FeedFilterBar.test.ts` (57 lines) covers
it.

## File boundaries

Two files, both in the packet's Edit list (`FeedFilterBar.vue` + its
test). No Python, no frozen docs, no `runs/`.

## Ruling

**Accepted.** Small, contained, exactly the fix the dossier's finding
called for.
