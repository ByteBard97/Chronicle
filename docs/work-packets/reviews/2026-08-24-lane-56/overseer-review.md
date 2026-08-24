# Lane 56 overseer review — variant tree edge-label rendering (M7 fix)

**Delivered:** `d7f61eb` (worker-committed; no delivery report filed
on disk — reviewed directly).

## Battery

Shared run with lane 54 (see that review): 249 pytest, 608/608 vitest,
build/check-range/ruff all clean.

## Claim verified

The root-cause diagnosis is precise and specific, not vague: one
`VariantTreeCrossLink` per raw `supersession` record was correct
upstream (`derived/variantTree.ts`, unedited, confirmed by the diff
stat showing zero changes there), but `TreeSvg.vue` rendered one
path+label per record instead of per distinct visual edge — against
`runs/north-star-01`, 452 supersession records on one claim collapse
to only 5 distinct (loser, winner) pairs, one carrying 190 records
alone. That number range (452 records, ~190 for the dominant pair) is
consistent with the earlier north-star delivery reports' own noted
"452 supersessions of live resolution churn" figure from lane 49's
review — a real, cross-checkable number, not invented. The fix
aggregates by `(fromId, toId, resolutionRule, confidenceDent)` rather
than just the node pair, with a `×N` suffix — correctly preserves the
repeated-contradiction signal instead of silently flattening it.

## File boundaries

`TreeSvg.vue`/`TreeSvg.test.ts` only — exactly the packet's Edit list
("the variant-tree view's rendering module/component only"). No
changes to `derived/` per the packet's own preference. No Python, no
frozen docs.

## Ruling

**Accepted.**
