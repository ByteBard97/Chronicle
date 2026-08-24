# Lane 22 pre-dispatch review v2 — provenance drill-down, post lane-27/28

Packet reviewed: `docs/work-packets/lane-22-provenance-drilldown.md` (as
amended 2026-08-23, post lane-27/28 landing). Reviewer: Claude
(Sonnet 5), same verification method as prior pre-dispatch reviews —
every checkable claim verified against the live repo and real run data.
**Following the lane-11 protocol: implementation is NOT dispatched
pending this review.**

The original (v1) review at `2026-08-23-lane-22/pre-dispatch-review.md`
covered the packet before lanes 27/28 existed; both have since landed
(`ec4c41b`, `b91b1d5`). This is a fresh review of the packet as amended,
not a continuation of v1's findings (both of which the coordinator
already ruled on and resolved).

---

## Finding — the packet's own amendment contradicts itself on file boundaries

The "Key design facts" section, under "Invocation points (amended
2026-08-23)", reads:

> a "drill" affordance on belief elements in (a) the real `NpcInspector`
> (both host screens — post-lane-28, its Beliefs-tab cards are real,
> drill-invokable elements) and (b) the **variant tree's holder table**
> (lane 21, landed — real holders; the earlier deferral is moot). Same
> component, all hosts.

But the "File boundaries" section, unchanged since before this
amendment:

- **Edit** list names only `FeedScreen.vue`, `MapScreen.vue`, and
  conditionally `urlState.ts` — no tree file, no `HolderTable.vue`,
  appears anywhere as editable.
- **Do not touch** still reads: "tree files (lane 21, in flight —
  invocation there is a follow-up)."

Lane 21 is landed (`bc3ede4`), not in flight, and the design-facts
section explicitly says the earlier deferral is moot — so the "Do not
touch" line's own stated reason no longer holds. The amendment updated
the design section to require wiring the tree's holder table as a
second invocation point, but never updated the boundary section that
would authorize touching the file that lives in. As written, the
packet asks for something its own file boundaries forbid.

Confirmed this isn't a blocker of convenience — `HolderTable.vue`
(lane 21, landed) already has exactly what's needed: each row is a
`HolderRow { holderId, confidence, beliefId }` with a real `beliefId`,
directly attachable to a drill click handler. There's no technical
obstacle, only a governance one: I don't have authorization to edit
`components/tree/HolderTable.vue` or `views/VariantTreeScreen.vue`
under the packet as currently written.

### Confirmed accurate (everything else)

- `SocialState.evidence` (`reconstruct.ts:22,40`) is `Map<string,
  KeyframeEvidence>` keyed by evidence id, not belief id — no index for
  "all evidence for belief X," a scan/filter is still required (same
  finding as v1, still true, not blocking — the packet's own design
  section already accounts for a chain walk, not an index lookup).
- `chain_for` is `claims.py:850`; `Evidence` is `claims.py:137-153`.
  Neither lane 27 nor lane 28 touched `claims.py` (confirmed via git
  log — last touch was lane 12's `6235a1a`), so the packet's citations
  are unshifted and accurate.
- `panels` codec (`urlState.ts:40,155,228,276-281`) is a plain
  comma-joined `string[]` via `stringArrayCodec` — confirmed it can
  already carry a composite drill-target string (e.g.
  `"drill:belief-x"`) with **zero codec changes needed**, resolving the
  packet's own flagged open risk exactly as v1 found.
- `dashboard/src/derived/inspectorBeliefs.ts`'s `InspectorBelief` has a
  real `beliefId: string` field (`:49`, populated `:120`) — a real,
  drill-invokable id on every rendered card, confirming lane 28 closed
  the gap it was created to close.
- Real DAG-honesty test data confirmed: `belief-auto-relief_caravaneer-4`
  has 5 Evidence records, `belief-auto-ysolda-2` has 4 — both satisfy
  the "2+ parents" requirement for the corroborated-belief test.
- `docs/ui-spec.md` §3.6 matches the packet's quote verbatim. The
  packet's "§1.2" citation for the `panels` key is a paraphrase (the
  doc doesn't print that literal section number next to the key list)
  — cosmetic looseness, not a substance discrepancy.

## Verdict

**Not safe to dispatch as written**, for one reason only: the file
boundaries don't permit the invocation point the design facts require.
Two ways to resolve, either is fine from where I sit:

1. Amend the File boundaries section to add `dashboard/src/components/
   tree/HolderTable.vue` and/or `dashboard/src/views/
   VariantTreeScreen.vue` to the Edit list (drill-affordance wiring
   only, same scope discipline as the Feed/Map inspector wiring), and
   drop the stale "in flight — follow-up" language from "Do not touch."
2. Descope invocation point (b) out of this lane entirely (implement
   only the NpcInspector invocation now, file the tree's holder table
   as a fast, well-scoped follow-up lane — it's a small addition once
   `ProvenancePanel.vue` exists, since "same component, all hosts" means
   the hard part is built either way).

Everything else in the packet is confirmed accurate and ready. Once
this is resolved, implementation can begin without any other blocking
issue.

---

## Coordinator — response

*(pending)*

---

## Coordinator ruling — 2026-08-23 (second round)

Accepted — a genuine packet self-contradiction from my own amendment.
**Ruling: amend the boundaries** (not descope) — the tree holder table
was a deliberate invocation-point amendment (lane 21 landed `bc3ede4`;
its rows already carry real `beliefId`s, as the review verified). The
packet's File boundaries now name `components/tree/HolderTable.vue`
(drill affordance) and `views/VariantTreeScreen.vue` (panel mount only)
as editable, the stale "lane 21 in flight" do-not-touch is removed, and
the Task text is aligned. Lane 22 is cleared for implementation against
the amended packet.

Also recorded here: lanes 27 and 28 verified and accepted (369/369
vitest, build clean, check-range 206, 203 pytest, ruff clean — battery
re-run by the coordinator). Lane 28's FeedScreen store-load fix
(pre-existing gap: the screen never loaded the shared store) confirmed
in commit `b91b1d5` and in scope for the lane's purpose.
