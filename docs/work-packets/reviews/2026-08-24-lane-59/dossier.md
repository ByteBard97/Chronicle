# Lane 59 — M7 Release Gate: formal re-run

**Date:** 2026-08-24
**Run under test:** `runs/north-star-01` (stranger walkthrough), `runs/whiterun-jarl-01` + `runs/tier3-demo-01` (developer-twin sweep)
**Dashboard:** `dashboard/`, `npm run dev` on `http://localhost:5173`
**Prior run:** `docs/work-packets/reviews/2026-08-24-m7/dossier.md` (original gate, FAIL 5/6)

Screenshots referenced below are in `./screenshots/` alongside this dossier (copied from the session's `.playwright-mcp/`-style working directory, which is gitignored and not otherwise part of the commit).

This is a **verification lane, not a feature lane** — no code changes were made in the course of this run. All six ui-spec §5 steps and the three developer-twin cases were re-executed for real, in a real browser, against the same one-sentence prompt used originally: *"the Jarl was assassinated — find out what Markarth believes and why it's wrong."*

---

## GATE: PASS

**6 of 6** stranger-walkthrough steps pass. All three developer-twin cases pass, including confirmation that lane 58's outcome-filter label/value fix is live and correct. No regressions found.

| # | ui-spec §5 step | Result | Fix lane |
|---|---|---|---|
| 1 | find the assassination on the timeline | **PASS** — timeline is now part of global chrome, visible on the landing view (`/?run=north-star-01`) with no navigation needed | 54 |
| 2 | scrub and watch the rumor overlay spread, incl. carrier hop | **PASS** — Markarth NPCs render as markers in an "elsewhere: Markarth" off-map inset region on `/map`; scrubbing to t=96 shows the carrier's arrival | 55 |
| 3 | click a Markarth believer, read the belief, notice the variant badge | **PASS** — clicking `markarth_resident_3` opens the inspector with real belief data (HEARD badge, "weapon: a poisoned blade" variant badge, confidence/verbatim/gist meters, provenance line) | 55 |
| 4 | open the variant tree, identify which slot changed at which hop | **PASS** — `/tree?run=north-star-01` renders the `weapon: a dagger → a poisoned blade (mut-38f1c74e1c06)` mutation label directly and legibly on the page | 56 |
| 5 | drill provenance from belief to dagger through the mutation | **PASS** — genuine interactive click-through confirmed (see Phase 2 below): popover opens anchored near the clicked drill button, content shows the mutation inline | 57 |
| 6 | copy the URL and have it reproduce the view | **PASS** — verified with the exact step-5 popover state; a fresh navigation (new tab) reproduces the same PROVENANCE content | (pre-existing, re-confirmed) |

Developer twin: **T1.3 rolled-against** — PASS, using the now-underscored dropdown option; **T3.4 declined-by-rule** — clean PASS, no regression; **nothing-salient** — PASS, using the now-underscored dropdown option. Lane 58's fix (dropdown option label now matches its stored value) confirmed directly in the accessibility tree for all three affected outcome values (`rolled_against`, `nothing_salient`, and unaffected `declined`).

---

## Phase 1 — the six ui-spec §5 steps, with evidence

### Step 1 — find the assassination on the timeline: PASS

Navigated to `http://localhost:5173/?run=north-star-01`. The landing ("console") view now has a full **TIMELINE** section as persistent global chrome directly below the injection console — playback controls (◀◀D ◀| ▶ |▶ D▶▶, ¼×/1×/4×/8×), a scrub track, a marker-type legend (claim born · mutation · supersession · grudge formed · threshold crossed · role vacancy · carrier arrival · events), and "457 typed markers." The very first marker button on the track is labeled `"claim born: claim-balgruuf-assassination · grudge: frothar → the_player · grudge: nelkir → the_player · death: jarl_balgruuf"` — the assassination is findable on the timeline with zero navigation from the landing URL.

- **Evidence:** `screenshots/01-landing-timeline.png`.
- **Assessment:** Lane 54's fix (promoting the timeline to global chrome across all views, including the landing/console view) fully resolves the original stumbling block. No stranger needs to guess which of the 9 nav tabs hides "the timeline" — it's present from the first screen.

### Step 2 — scrub and watch the rumor overlay spread, including the carrier hop: PASS

Navigated to `/map?run=north-star-01`. The map now shows the original Whiterun render plus a distinct **"MARKARTH — elsewhere"** off-map inset region (`generic "Markarth (off-map inset region)"` in the accessibility tree), containing marker links for Markarth Resident 1, 2, 3, and (nearby) Relief Caravaneer. The lens panel confirms "26 tracked" variants and claim-stage coverage "14/16." Scrubbing to `t=96` (the tick of the original carrier hop, per the prior dossier) shows Markarth Resident 2 and 3 both transitioning to "heard" with an "N" (new belief) glyph, consistent with the caravaneer's arrival completing the hop into Markarth at that tick.

- **Evidence:** `screenshots/02-map-markarth-inset.png` (full map with Markarth inset, t=239), `screenshots/03-map-t96-carrier-hop.png` (scrubbed to t=96).
- **Assessment:** Lane 55's fix (an off-map "elsewhere: Markarth" inset region with real markers) closes the original bug completely — Markarth is no longer invisible on the map, and the spread including the carrier hop is now visually observable.

### Step 3 — click a Markarth believer, read the belief, notice the variant badge: PASS

With the map at t=96, clicked the `markarth_resident_3` marker link directly (URL became `...&t=96&sel=markarth_resident_3`, confirming the click-to-select mechanism). The inspector panel opened with real belief data:
- Badge: **HEARD**
- Variant badge: **"weapon: a poisoned blade"** shown directly next to the claim name
- Full belief text: `deceased: jarl_balgruuf, cause: assassination, location: dragonsreach, weapon: a poisoned blade, killer: the_player`
- Confidence 0.37 / verbatim 0.24 / gist 0.87
- Provenance line: `told-by ← caravaneer · t 96 · reported`

- **Evidence:** `screenshots/04-inspector-resident3-belief.png`.
- **Assessment:** This is exactly what the original walkthrough could only reach via the feed (which §5 says should be unnecessary). With Markarth now on the map, the intended click-on-map-marker path works directly, no feed detour required. This resolves the original step 2/3 chained failure.

### Step 4 — open the variant tree, identify which slot changed at which hop: PASS

Navigated to `/tree?run=north-star-01`. The rendered page shows the canonical → variant lineage tree with node bubbles (variant-auto-1 through -9). Critically, the `"weapon: a dagger → a poisoned blade (mut-38f1c74e1c06)"` mutation label is now rendered once, directly and legibly on the page near the variant-auto-6/7 edge — confirmed by a 2x zoom crop of the rendered screenshot (not the accessibility tree). This is a dramatic improvement over the original bug (hundreds of stacked, illegible copies of a different label, `evidence-type-ordering+v1 (dent 0.1)`, covering two-thirds of the screen).

Some residual visual crowding remains among the `evidence-type-ordering+v1 (dent 0.1)` labels near variant-auto-7/8/9 (they overlap each other and the node numbers somewhat) — but this is a distinct, secondary label from the one the walkthrough needs, and does not obscure the primary mutation-slot answer. Clicking variant-auto-9 in the tree opens a holder table showing `relief_caravaneer` and `markarth_resident_3` as the two holders of the wrong variant, both at confidence 0.00 (same genuine contested-belief dynamic noted in the original dossier, not a bug).

- **Evidence:** `screenshots/05-tree-view.png` (full page), `screenshots/05-tree-crop.png` (2x zoom crop showing the mutation label is legibly rendered as real pixels, not just accessible-name metadata).
- **Assessment:** Lane 56's fix closes the severe rendering defect for the specific label the walkthrough depends on. A sighted human can now read "weapon: a dagger → a poisoned blade" directly off the rendered page, which was previously impossible without reading hidden tooltip/accessibility data.

### Step 5 — drill provenance from belief to dagger through the mutation: PASS (genuine interactive click-through)

This is the step the lane packet flagged as needing a real click, not a diff read or an inspection of the accessibility tree's hidden titles. Here is exactly what was done:

1. On `/tree?run=north-star-01`, clicked the `variant-auto-9` node button (the real mutation case, matching the original dossier's finding).
2. This opened a **"holder table panel"** in the top-right complementary region, showing "VARIANT-AUTO-9 — 2 HOLDERS" with a table of `relief_caravaneer` and `markarth_resident_3`, each with a confidence column and a **provenance column containing a real `<button>` element** labeled `"drill into markarth_resident_3's provenance"` (rendered as a `⤷` glyph in the row).
3. Read the accessibility snapshot first to confirm this button — not an SVG `<title>` — was the real interactive drill affordance.
4. Clicked that button directly (`browser_click` on the button's ref, not a coordinate guess).
5. The URL updated to `?run=north-star-01&panels=drill%253Abelief-auto-markarth_resident_3-9` and a **PROVENANCE popover opened immediately below/beside the holder table**, i.e. anchored near the actual click location (top-right of the viewport, where the holder table itself sits) — **not** pinned to a fixed screen corner unrelated to the click.
6. The popover's content (verified both from the accessibility tree and from a 2x-zoomed screenshot crop) reads:
   > `caravaneer reported t 96` / `markarth_city  conf 0.00 (-0.31)` / **`mutation mut-38f1c74e1c06 — weapon: a dagger → a poisoned blade`** / `proventus reported t 24` / `whiterun_market conf 0.31 (-0.04)` / `proventus witnessed t 0 conf 0.35` / `WITNESSED EVENT · PROVENTUS`

   The mutation is narrated **inline**, in the popover itself — `weapon: a dagger → a poisoned blade` — with no need to separately visit the tree view's tooltip data to complete the "belief → dagger → mutation" story.

- **Evidence:** `screenshots/06-step5-provenance-popover.png` (full page, popover visible next to the holder table it was invoked from), `screenshots/06-step5-crop.png` (2x zoom crop of the popover proving the mutation text renders as real, readable pixels).
- **Did this require any workaround?** No. The real DOM button (`"drill into markarth_resident_3's provenance"`) was found via the accessibility snapshot and clicked directly — no SVG `<title>` click attempts, no locator hangs, no fallback to source-reading. This is the specific gap the lane packet called out as needing to close, and it closed cleanly on the first attempt.
- **Assessment:** Lane 57's fix (reposition the popover near its invocation point; extend the provenance content to narrate the mutation inline) fully resolves the original bug. Both halves of the original complaint — mispositioning and thin/missing mutation content — are fixed.

### Step 6 — copy the URL and have it reproduce the view: PASS

Captured the live URL from the exact step-5 state:

```
http://localhost:5173/tree?run=north-star-01&panels=drill%253Abelief-auto-markarth_resident_3-9
```

Opened it via two independent fresh-navigation methods: (a) a same-tab `goto` to the URL with no prior state, and (b) a brand-new browser tab pointed directly at the URL. Both reproduced the identical PROVENANCE popover with the same content (`mutation mut-38f1c74e1c06 — weapon: a dagger → a poisoned blade` visible inline), confirming the `panels=drill%3A...` deep-link parameter round-trips and restores state exactly, consistent with lane 53's original step-6 finding (no regression).

One minor, non-blocking observation: on the fresh reload, the tree's holder-table panel reverted to its default "click a node to see its holders" placeholder rather than re-showing the variant-auto-9 holder table, because the URL that was actually generated by the UI only serializes the `panels=` (popover) state, not a `sel=`-equivalent for the tree's node selection. This is not a regression — it's the same scope the original URL itself carried — and does not affect the passing grade for this step, since the specific state that matters (the open provenance popover with its content) reproduces exactly as required.

- **Evidence:** `screenshots/07-step6-url-reproduce.png`.
- **Assessment:** Clean pass, matching lane 53's original finding — no regression from any of the five fix lanes.

---

## Phase 2 — the developer-twin sweep

### T1.3 — rolled-against (encounter-rolled-but-not-encountered)

- **Source record:** `runs/whiterun-jarl-01/trace.jsonl`, tick 0, `dragonsreach`, `irileth`↔`proventus`, `record_type: encounter_rolled`, `outcome: no_encounter`, `encountered: false`, `value: 0.523`, `threshold: 0.35`.
- **Fix confirmed:** navigated to `/feed?run=whiterun-jarl-01` and inspected the outcome `<select>` via the accessibility tree. The dropdown option now reads `"rolled_against"` (underscore) — matching its stored value exactly, no cosmetic hyphen transform. This confirms lane 58's fix (`FeedFilterBar.vue`'s `.replace("_", "-")` cosmetic label transform is gone).
- **Deep link (exact underscored form now shown in the dropdown):** `http://localhost:5173/feed?run=whiterun-jarl-01&filters={"npc":"irileth","outcome":"rolled_against"}`.
- **Result:** the dropdown shows `rolled_against` selected (round-trips correctly from the URL), and the record lands within one click (expanding "tick 0 · 1 trace row"): `"t0 dragonsreach irileth ↔ proventus rolled-against 0.523 vs. threshold 0.350"`.
- **Verdict: PASS.**

### T3.4 — declined-by-rule

- **Source record:** `runs/tier3-demo-01/trace.jsonl`, tick 4, `bannered_mare`, `hulda`↔`olfrid`, `record_type: transmission_declined`, `rule: tell-decision-policy`.
- **Deep link:** `http://localhost:5173/feed?run=tier3-demo-01&filters={"npc":"hulda","outcome":"declined"}`.
- **Result:** clean pass, unchanged from lane 53's original finding. All matching rows render immediately, ungrouped, with `rule: tell-decision-policy` printed directly on each row. `declined` has no hyphen/underscore variant, so it was never affected by the T1.3-class bug.
- **Verdict: PASS.** No regression.

### nothing-salient

- **Source record:** `runs/tier3-demo-01/trace.jsonl`, tick 4, `warmaidens`, `adrianne`↔`proventus`, `record_type: nothing_salient`, `reason: neither-informed`.
- **Fix confirmed:** the outcome dropdown option for this value now also reads `"nothing_salient"` (underscore), matching its stored value.
- **Deep link:** `http://localhost:5173/feed?run=tier3-demo-01&filters={"npc":"adrianne","outcome":"nothing_salient"}`.
- **Result:** `614 of 2156 rows`, dropdown shows `nothing_salient` selected — matches the original dossier's row count exactly, now with the option label/value consistent.
- **Verdict: PASS.**

---

## Summary

All five fix lanes (54–57 for the stranger walkthrough, 58 for the developer-twin outcome-filter bug) verified as fully closing their respective bugs, with no new regressions found. Step 5 — the one gap left open by the prior informal spot-check — received a genuine, first-attempt-successful interactive click-through: the real "drill into markarth_resident_3's provenance" button (found via the accessibility snapshot, not an SVG title) was clicked directly, and both the popover's anchored position and its inline mutation content (`weapon: a dagger → a poisoned blade`) were confirmed live.

**No new spec bugs filed.** One minor, non-blocking observation is recorded under step 6 (the tree's holder-table selection state isn't part of the URL's serialized state, only the popover is) — this does not affect any passing grade and is not a regression from any of the five fix lanes; it is out of scope for this gate re-run to file as a new bug since it does not violate any ui-spec §5 acceptance criterion as written.

**GATE: PASS.**
