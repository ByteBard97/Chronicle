# Lane 57 overseer review — provenance popover anchoring + inline mutation (M7 fix)

**Delivered:** `d0b6530` (worker-committed; no delivery report filed
on disk — reviewed directly).

## Battery

Shared run with lane 54/56 (see those reviews): 249 pytest, 608/608
vitest, build/check-range/ruff all clean.

## Claim verified

The worker correctly identified that mutation data already existed on
the hop model (lane 22's `ProvenanceHop.mutation`) and needed no
`derived/provenance.ts` change — confirmed by the diff stat touching
only `ProvenancePanel.vue`/`.test.ts`. The positioning fix's mechanism
(a capture-phase `pointerdown` listener on `document`, since none of
the three host screens are in this lane's edit boundary and a prop
couldn't be threaded down without crossing that boundary) is a
reasonable, well-justified way to solve "anchor near the click" without
touching files outside the packet's boundary — a real design
constraint handled correctly rather than worked around by expanding
scope. The scroll-into-view fix for a long chain (336-column real case)
is a sensible discoverability complement to the positioning fix, not
scope creep. New tests explicitly assert two different trigger
positions land the panel in two different places (proving relative-not-
fixed) and a deep-link-with-no-click fallback — both directly address
the packet's two acceptance criteria.

## File boundaries

`ProvenancePanel.vue`/`.test.ts` only. No Python, no frozen docs, and
explicitly did not touch the tree view (lane 56's territory) despite
mutation narration being relevant to both — correct discipline.

## Ruling

**Accepted. All five M7 fix lanes (54, 55, 56, 57, 58) are now
accepted.**
