# Lane 53 — M7 Release Gate: the stranger walkthrough

**Date:** 2026-08-24
**Run under test:** `runs/north-star-01` (stranger walkthrough), `runs/whiterun-jarl-01` + `runs/tier3-demo-01` (developer-twin sweep)
**Dashboard:** `dashboard/`, `npm run dev` on `http://localhost:5173`

Screenshots referenced below are in `./screenshots/` alongside this dossier (copied from the session's `.playwright-mcp/` working directory, which is gitignored and not otherwise part of the commit).

---

## GATE: FAIL

**5 of 6** stranger-walkthrough steps fail as literally specified. ui-spec §5 grades each step binary ("failure of any step is a spec bug, not a user error") — no partial credit, so steps 4 and 5 (where the underlying data is present but the delivery is broken) are graded FAIL below, not "pass with a bug." Developer-twin sweep: all three named landing cases land the offending record within one click; one UI-internal inconsistency was found and filed separately (not a §1.2 pytest-emitter defect — see its own section).

| # | ui-spec §5 step | Result |
|---|---|---|
| 1 | find the assassination on the timeline | **FAIL** — timeline exists but is not reachable from the landing view |
| 2 | scrub and watch the rumor overlay spread, incl. carrier hop | **FAIL** — the only map+timeline view found is Whiterun-only; Markarth never renders |
| 3 | click a Markarth believer, read belief, notice variant badge | **FAIL** — no Markarth marker exists to click; only reachable via the feed, which §5 says should be unnecessary |
| 4 | open variant tree, identify which slot changed at which hop | **FAIL** — the tree's visual rendering is illegible; the correct answer exists only in non-visible tooltip/accessibility data |
| 5 | drill provenance from belief to dagger through the mutation | **FAIL** — the provenance popover is mispositioned and doesn't narrate the mutation |
| 6 | copy the URL, have it reproduce the view | **PASS** — verified with a fresh-context navigation of a captured URL; full state (filters, tick, both selections, and the open provenance popover) restored exactly |

Developer twin: **T1.3 rolled-against** — PASS (lands within one click once the correct filter value is used); **T3.4 declined-by-rule** — clean PASS, Lane 30's claim holds, no regression; **nothing-salient** — PASS (same one-click-away caveat as T1.3). **Caveat that applies to all three:** the packet asked for "the exact deep-link URL a failing test/assertion would produce." No scenario test currently calls `deep_link.set(filters=...)` for any of these three named cases (confirmed by reading `scenarios/test_tier1_transmission_trace.py` and `scenarios/test_tier3_tell_decision.py`) — the URLs graded above were hand-constructed against the dashboard's own filter UI, not emitted by any existing test. So while the *landing mechanism itself* works once you have a correct URL, §5's "every ladder assertion type's failure deep link lands within one click" is **unverified in practice** for these three cases, not verified end-to-end.

---

## Phase 1 — the stranger walkthrough, blind, full narration

*(Unfiltered, timestamped narration written live during the blind attempt, before `docs/ui-spec.md` or any dashboard source was read.)*

Task given: "the Jarl was assassinated — find out what Markarth believes and why it's wrong."

### T+0:00 — Navigate to `http://localhost:5173/?run=north-star-01`

Landed on a view the nav bar marks as "console" (nav: console, map, feed, tree, diff, rules, compare, scheddiff, roles). Top bar shows the CHRONICLE wordmark, a run selector (north-star-01 already selected — the URL param worked), a salience filter group (DEV / OBSERVER / STORY, OBSERVER pressed by default), and the view-switcher.

Below that: a scrubber with a "t" spinbutton and ◀ ▶ buttons, a *second*, separate "salience" dropdown, and a status line: "LIVE — docked · following newest frame · +0 events · scrub to detach" / "state as of t=239: 1 claims, 14 beliefs".

Then a large panel: an "INJECTION CONSOLE (developer-only)" — event-type dropdown, JSON payload textarea, generated CLI invocations for `chronicle inject`. This is a developer authoring tool, not player/observer-facing, and it dominates the page.

Beside it: an NPC inspector panel (tabs BELIEFS / RELATIONSHIPS / SCHEDULE / HISTORY) showing "select an NPC" placeholder text.

**Stumbling block #1.** No visible timeline. Step 1 of the brief says "find the assassination on the timeline" — what's on screen is a bare numeric "t" spinbutton, not a scrubbable track with markers. The word "timeline" does not appear anywhere on this page or in the nav.

*(LLM-vs-human note: I read the accessibility tree first, which surfaces content a human wouldn't scan the same way. Took screenshot `screenshots/01-landing-console.png` to confirm the rendered page matches — it does. The injection console visually dominates; a first-time human user would very plausibly conclude "this is a dev tool" and bounce.)*

**Stumbling block #2** (would-give-up moment). The landing view is developer-facing with no timeline in sight. Nothing in the 9-tab nav is labeled "timeline." I have to guess which tab might contain it — a real stranger faces the same blind guess.

### T+0:02 — Clicking "feed" (guess #1 for "the timeline")

`/feed?run=north-star-01` (screenshot `screenshots/02-feed.png`). This is a dense raw table (TICK/LOCATION/PARTICIPANTS/OUTCOME, "4318 of 4318 rows"), grouped by tick with collapsible "N trace rows" summaries. Not a timeline — a log/spreadsheet.

I can already see the assassination rumor in the raw rows: t0, temple_of_kynareth, frothar↔priest, transmitted, "claim claim-balgruuf-assassination · variant variant-auto-1", then more at t24-25 in whiterun_market. So the claim is discoverable here, and the spread is traceable tick-by-tick — but only as data, not as a visual overlay.

**Stumbling block #3.** 4318 rows, no full-text search for a claim name. I only recognized "claim-balgruuf-assassination" as *the* claim because "Balgruuf" is a Skyrim name I already knew — a Skyrim-illiterate stranger has a slightly harder time, though the slug is still legible.

### T+0:05 — Filtering the feed

Selected claim filter = `claim-balgruuf-assassination`. The row count stayed "4318 of 4318 rows." *(Correction after Phase 2 verification below: this run has exactly one claim value, so filtering to it and seeing no count change is the correct behavior, not a bug — confirmed separately by testing the same filter against `tier3-demo-01`, which has 7 distinct claims: selecting `claim-theft-1` there dropped the count from 2156 to 308, proving the claim filter works correctly.)*

The NPC filter, tried next (`markarth_resident_1`), worked correctly (386 of 4318 rows). Scrolling the collapsed groups: t76, markarth_city, markarth_resident_1↔2/3, nothing-salient/"neither-informed" — residents 2/3 hadn't heard it by t76. Then: **t96, markarth_city, caravaneer↔markarth_resident_1, TRANSMITTED, variant-auto-7** — the carrier hop, a caravaneer carrying the rumor from Whiterun to Markarth.

Clicked that row. URL became `...&t=96&sel=caravaneer,markarth_resident_1` (selection round-trips to the URL — good sign for step 6). Screenshot `screenshots/06-row-selected-inspector.png` shows two stacked "DRILL claim-balgruuf-assassination" belief cards:

- **CARAVANEER**: badge "REPEATED", variant-auto-4, belief text "deceased: jarl_balgruuf, cause: assassination, location: dragonsreach, weapon: a dagger, killer: the_player", confidence 0.56/verbatim 0.35/gist 0.92, "told-by ← proventus · t 24 · reported".
- **MARKARTH_RESIDENT_1**: badge "HEARD", variant-auto-7, *identical* belief text, confidence 0.45/verbatim 0.24/gist 0.87, "told-by ← caravaneer · t 96 · reported".

This inspector card is genuinely well-designed once found: claim id, status badge, variant id, belief text, three fidelity meters, and a provenance line.

**Open question at the time:** resident_1's belief text is byte-identical to caravaneer's, including "killer: the_player" — not obviously "wrong" yet. This is taking much longer than ten minutes' worth of a real user's patience — filter-and-scroll archaeology on a 4300-row table that a real stranger would likely have abandoned already.

### T+0:07 — Checking markarth_resident_2 and the provenance drill-down

NPC=markarth_resident_2, outcome=transmitted → "1 of 4318 rows" (confirms the *outcome* filter works too). Found t96, caravaneer↔markarth_resident_2, variant-auto-8 — belief text again identical to resident_1's and caravaneer's.

Clicked the small "drill" button above the belief card (a distinct affordance from clicking the row). Opened a floating **PROVENANCE** popover (screenshot `screenshots/09-drill-provenance.png`): "PROVENANCE belief-auto-markarth_resident_2-8 (MARKARTH_RESIDENT_2) as-of t=96", "MARKARTH_RESIDENT_2 ← 1 CHAIN", "— 2 retellings —", "proventus witnessed t 0 · conf 0.64 · WITNESSED EVENT · PROVENTUS".

**Stumbling block #4.** This popover renders pinned near the top-right of the viewport, overlapping the header/nav rather than anchored near the button clicked, and its content is thin (2 lines) for a claim I'd traced through 4+ hops. "proventus witnessed t 0" is confusing against the feed's earlier data, where proventus first appears at t24 in whiterun_market receiving from someone else, not "witnessing" at t0. It does not diff variant-auto-4 vs -8 side by side — no visible "which slot changed" answer here.

### T+0:10 — "tree" nav tab: the variant tree, a mixed bag

`/tree?run=north-star-01` (screenshot `screenshots/10-tree-view.png`).

**Stumbling block #5 — the worst thing found in the whole walkthrough.** The rendered page is visually broken: a "canonical" root branches into small numbered node bubbles (variant-auto-1, -2, -4, -9…), but behind/under them is a dense, illegible wall of overlapping text — hundreds of stacked copies of the string "evidence-type-ordering+v1 (dent 0.1)" covering the lower two-thirds of the screen, diagonally smeared, completely unreadable. A human stranger would almost certainly conclude the page is broken and leave.

Underneath the visual mess (found via the accessibility tree, not by eye — a technique available to me as an LLM agent but not to a sighted human scanning the page), each variant node carries a full descriptive tooltip/accessible name, e.g. `"variant-auto-9 | holders 2 | deceased=jarl_balgruuf, cause=assassination, location=dragonsreach, weapon=a poisoned blade, killer=the_player | dent 0.1"`. Compared against canonical's tooltip (`weapon=a dagger`), this reveals the actual mutation: **weapon: "a dagger" → "a poisoned blade"** — confirmed by an explicit hidden label on the tree, `"weapon: a dagger → a poisoned blade (mut-38f1c74e1c06)"`.

Clicked variant-auto-9 (screenshot `screenshots/11-tree-variant9-holders.png`). A side panel opened: "VARIANT-AUTO-9 — 2 HOLDERS": **relief_caravaneer** and **markarth_resident_3** (both showing confidence 0.00). So the actual Markarth NPC holding the *wrong* belief is **markarth_resident_3**, not the residents 1/2 already inspected via the feed (whose beliefs still matched canonical truth).

*(Note on the 0.00 confidence: checked after Phase 1, in Phase 3's follow-up — this is not a display bug. `runs/north-star-01/trace.jsonl` shows 117 `supersession` records for `relief_caravaneer` and 335 for `markarth_resident_3` on this claim, each carrying `"confidence_dent": 0.1` (matching the tree's "dent 0.1" labels) — these two NPCs are locked in a repeated back-and-forth re-telling loop (variant-auto-6 ↔ variant-auto-9 ↔ variant-auto-4 ↔ ...) that dents confidence downward every time, which floors out at 0.00 given that many repetitions. Confirmed via `chronicle/claims.py`'s decay constants — time-based decay alone would not explain 0.00 at this elapsed tick range, but repeated contradiction-denting does. Genuinely surfaces a "grudge/contested-belief" dynamic, not a bug.)*

The panel also had a working "view on map ▸" deep link: `/map?run=north-star-01&filters={"variant":"variant-auto-9"}`.

### T+0:13 — "map" nav tab: the real timeline lives here

Screenshot `screenshots/12-map-variant9.png`. A well-built, detailed painterly top-down map of **Whiterun** (Dragonsreach, Temple of Kynareth, the Market, Warmaiden's, Main Gate, Stables — all lore-recognizable but also plainly labeled on the map itself). A "LENS — ONE OVERLAY ACTIVE" panel shows "variant: variant-auto-9 · C-114 'Jarl Balgruuf is dead'", claim-stage counts ("unheard 2 · heard 7 · repeated 7 · dormant 0 · forgotten 0 · coverage 14/16").

At the bottom: a genuine horizontal scrubbable **timeline** — playback controls (◀◀ ◀ ▶ ▶▶, 1×/4×/8×), a scrub track from tick 0 to the current t=239, and a marker-type legend (claim born · mutation · supersession · threshold crossed · role vacancy · carrier arrival · events). **This is what ui-spec §2 calls "the timeline"** and it lives only on `/map`, not the console landing page — three navigation hops deep (console → feed → tree → map, or similar).

**Stumbling block #6.** Checked the map's marker list directly (accessibility tree): only 5 NPC markers exist on the canvas — **Priest, Frothar, Irileth, Nelkir, Jarl Balgruuf** — all Whiterun residents. **Zero Markarth markers.** No `markarth_resident_1/2/3`, no `caravaneer`/`relief_caravaneer` appear anywhere on this map, filtered to variant-auto-9 or not. The map is architecturally Whiterun-only. There is no way to visually watch the carrier hop complete, nor to click a Markarth believer on the map, because Markarth simply isn't rendered.

I stopped active exploration here, having found: the assassination claim, the rumor's spread (via the feed, not a visual overlay), the wrong fact and its holder (markarth_resident_3, weapon="a poisoned blade"), the variant tree (data-complete, rendering-broken), a provenance drill-down (works but thin/mispositioned), and the real timeline (exists, but 3 hops deep and Whiterun-only).

### T+0:15 — Quick URL-reproducibility spot check

Every meaningful action (row click, filter change, NPC selection, map variant) visibly updated the URL (`?run=`, `&filters={...}`, `&t=`, `&sel=`, `&panels=drill%3A...`). Strong positive signal for step 6, verified formally in Phase 2 below.

**Total elapsed:** roughly 15 real navigation/interaction steps across 4 views (console, feed, tree, map) before reaching a confident answer, several of them dead ends or guesses. Extrapolated to a human's likely pace, a genuine first-time user attempting this literally would need on the order of 15-25 minutes to reach where this walkthrough got to — if they didn't give up earlier at stumbling block #2 (developer console landing page) or #5 (the broken tree visual).

---

## Phase 2 — self-grading against ui-spec §5 (verbatim, all six steps)

> "the Jarl was assassinated — find out what Markarth believes and why it's wrong" — (1) find the assassination on the timeline; (2) scrub and watch the rumor overlay spread, including the carrier hop; (3) click a Markarth believer, read the belief, notice the variant badge; (4) open the variant tree, identify which slot changed at which hop; (5) drill provenance from belief to dagger through the mutation; (6) copy the URL and have it reproduce the view.

ui-spec §5 states failure of any step is a spec bug, and grades the walkthrough as a sequence of pass/fail usability test cases — no partial-credit grade is offered in the spec, so each step below is graded strictly pass or fail.

### Step 1 — find the assassination on the timeline: **FAIL**

The timeline (§2 global chrome: playhead, play/pause, speed presets, typed event markers) exists and is well-built, but it is not part of the default landing view. The landing view (`/?run=...`, "console") shows only a bare tick spinbutton, not a timeline. The real timeline is on `/map`, which required going through `feed` → `tree` → the tree's "view on map" link to reach in this walkthrough — a stranger given "find it on the timeline" has no cue in the nav (no tab literally says "timeline") that `map` is where it lives.

- **Evidence:** `screenshots/01-landing-console.png` (no timeline on landing view), `screenshots/12-map-variant9.png` (timeline visible at the bottom of `/map`).
- **Did I need to already know something a stranger wouldn't?** No domain knowledge needed — this is a pure information-architecture gap. I found it by exhaustively clicking every tab; a real stranger would need to do the same, which the ten-minute budget does not obviously afford given step 1 is meant to be first and fast.
- **Genuine usability gap, not an LLM artifact.** A human would face exactly this: no "timeline" label anywhere, a developer-facing console as the front door.
- **Spec bug:** violates §0's "every view renders as-of-tick-T... at Tier 2 it grows into the timeline" intent (§2) insofar as the timeline should be discoverable as *the* primary orientation device, not a feature buried on one non-default view. Also arguably violates §0's "Three audiences, one artifact" doctrine — the *default* view serves the developer audience (injection console) rather than being audience-neutral chrome with salience-filtered defaults.
- **Proposed fix lane:** make the timeline part of persistent global chrome across all views (as §2 describes it), so it's visible on the landing/console view too, not map-only; and/or change the default landing route for the Observer/Story salience defaults away from the injection console.

### Step 2 — scrub and watch the rumor overlay spread, including the carrier hop: **FAIL**

The only place a "rumor overlay spread" + timeline coexist is `/map`, and that map is Whiterun-only. The two holders of the "wrong" variant (variant-auto-9) — `relief_caravaneer` and `markarth_resident_3` — are not represented as markers anywhere on the visible canvas. It is therefore structurally impossible to "watch the rumor overlay spread ... including the carrier hop" into Markarth on this view: Markarth does not exist on the map.

- **Evidence:** `screenshots/12-map-variant9.png` and the accompanying accessibility-tree marker list (5 markers total: Priest, Frothar, Irileth, Nelkir, Jarl Balgruuf — all Whiterun).
- **Did I need to already know something a stranger wouldn't?** No — this is directly observable by anyone who opens the map and looks for a Markarth building. I only additionally knew (from this project's own prior research notes, out of scope for a true stranger) *why* — no permissive 2D Markarth map/coordinate fixture exists yet — but the failure itself needs no such context to observe.
- **Genuine usability gap**, and a severe one: this isn't a rendering nit, it's a missing map region for exactly the location the walkthrough's whole premise depends on.
- **Spec bug:** violates ui-spec §3.4/§0's map coverage assumption implicit in the acceptance test itself — the frozen walkthrough names Markarth explicitly, so the map substrate must cover it.
- **Proposed fix lane:** extend the map location/coordinate fixture to include Markarth (or, short of a full second map bake, add an abstracted/off-map "elsewhere: Markarth" region that still places markers and lets the overlay show claims arriving there) — this is a data/asset lane, not a rendering-logic lane.

### Step 3 — click a Markarth believer, read the belief, notice the variant badge: **FAIL**

Directly downstream of step 2's failure: there is no Markarth marker to click on the map. The only way I found any Markarth believer's belief was via the feed's NPC filter + row click, which surfaces the same belief-card/variant-badge UI (I did see "HEARD"/"REPEATED" badges and variant ids in the inspector cards) — but ui-spec §5 explicitly says **"The encounter feed is deliberately absent — it's plumbing; the drill-down narrates transmission history in the form a stranger needs."** That sentence tells me my actual working path (feed-driven archaeology) is exactly the workaround the spec says shouldn't be necessary. The "intended" path — click on the map — does not exist for Markarth.

- **Evidence:** feed-derived belief card (see Phase 1, T+0:05); absence of any Markarth marker in `screenshots/12-map-variant9.png`'s marker list.
- **Did I need to already know something a stranger wouldn't?** I had to intuit that the feed's NPC dropdown could substitute for a map click, and specifically that outcome=transmitted narrows to exactly the row I wanted — a stranger would need to discover the outcome filter's effect through trial and error.
- **Genuine usability gap.** The spec's own text confirms the feed was never meant to carry this weight.
- **Spec bug:** direct consequence of step 2's bug (no Markarth on the map) plus a design assumption gap — §5's parenthetical explicitly assumes the map+inspector click path suffices without the feed; it currently does not for this run/claim.
- **Proposed fix lane:** same as step 2's fix (Markarth map coverage) — once markers exist, this step should pass for free via the existing inspector-click mechanism, which itself is well-built (see the belief cards' quality, above).

### Step 4 — open the variant tree, identify which slot changed at which hop: **FAIL**

The tree view (`/tree`) does technically contain the answer — canonical vs. variant-auto-9 tooltips show `weapon: a dagger` → `weapon: a poisoned blade`, and the tree carries an explicit `"weapon: a dagger → a poisoned blade (mut-38f1c74e1c06)"` label; clicking the node surfaces its holders including `markarth_resident_3`. But the visible, rendered page is dominated by an illegible wall of hundreds of overlapping copies of "evidence-type-ordering+v1 (dent 0.1)" text — a genuine rendering defect, not a design-taste quibble. I only recovered the correct answer by reading the accessibility tree/hover-tooltip data directly, a technique unavailable to a sighted human user working from the rendered page. Per ui-spec §5's own framing ("each step is a usability test case; failure of any step is a spec bug, not a user error"), a step whose correct answer is inaccessible to an actual human through the rendered UI is a failed usability test case, regardless of whether the underlying data model is correct.

- **Evidence:** `screenshots/10-tree-view.png` (the illegible rendering), `screenshots/11-tree-variant9-holders.png` (the holder panel, reachable only by clicking through the visual mess).
- **Did I need to already know something a stranger wouldn't?** No domain knowledge — but I used a technique (reading accessibility-tree tooltips) a human stranger cannot use to bypass this rendering defect.
- **Genuine usability gap: YES, and severe.**
- **Spec bug:** violates §0's renderer-split doctrine ("SVG for panels, labels, tooltips... no SVG-per-marker past ~1,000") — the edge-label elements are clearly not being deduplicated or laid out, producing hundreds of stacked, illegible copies of the same string. This is a Tier-2 (§3.5 variant tree) rendering defect.
- **Proposed fix lane:** fix the variant-tree edge-label layout/dedup logic in `dashboard/` (whatever renders `evidence-type-ordering+v1 (dent 0.1)` labels) so each edge label renders once, positioned near its own edge, not stacked at a fixed origin.

### Step 5 — drill provenance from belief to dagger through the mutation: **FAIL**

The drill-down mechanism exists (clicking "DRILL claim-balgruuf-assassination" above a belief card) and opens a PROVENANCE popover with a retelling chain and confidence numbers. But it does not narrate "belief → dagger → mutation" as a coherent, readable story: the chain shown ("proventus witnessed t 0 · conf 0.64") is thin, seemingly compressed/summarized rather than a full hop-by-hop trace, and doesn't call out the weapon mutation inline at all (that information lived only in the separate tree view, not in this popover). The popover is also visually mispositioned — pinned top-right, overlapping the header, rather than anchored to what was clicked. A stranger following step 5 in isolation, using only what this popover shows, cannot get from "belief" to "dagger" through "the mutation" — they'd have to already have visited the tree view (step 4) and mentally stitch the two together, which is not what "drill provenance... through the mutation" describes as a single guided action.

- **Evidence:** `screenshots/09-drill-provenance.png`.
- **Did I need to already know something a stranger wouldn't?** No, but I had to independently correlate this popover's sparse output against what I'd already learned from the feed and the tree to make sense of it — a stranger arriving at this popover cold would likely find "proventus witnessed t 0" cryptic and unable to answer "why is it wrong" from this view alone.
- **Genuine usability gap.**
- **Spec bug:** violates §3.6's framing of the drill-down as the mechanism that "narrates transmission history in the form a stranger needs" (§5) — it narrates a chain, but not the mutation that makes the belief wrong; and violates the popover-positioning expectation implicit in a "drill-down" gesture by not anchoring to the invocation point.
- **Proposed fix lane:** (a) fix the popover's anchor/positioning to appear near the clicked drill affordance, not pinned to a fixed screen corner; (b) extend the provenance chain's content to surface the mutation event (slot, old value, new value) inline, not only in the separate tree view.

### Step 6 — copy the URL and have it reproduce the view: **PASS**

Verified directly, not just inferred: captured a full-state URL from an active session —

```
http://localhost:5173/feed?run=north-star-01&filters={"claim":"claim-balgruuf-assassination","npc":"markarth_resident_2","outcome":"transmitted"}&t=96&sel=caravaneer,markarth_resident_2&panels=drill%3Abelief-auto-markarth_resident_2-8
```

— and opened it fresh (a new navigation, no prior in-session state). The result (screenshot `screenshots/20-url-reproduce-test.png`) restored the view correctly: all three filters set as specified, tick at 96, both NPCs (caravaneer and markarth_resident_2) selected with their belief cards open, and — critically — **the PROVENANCE popover from `&panels=drill%3A...` reopened automatically**, matching the original session's content. This also incidentally confirms the `panels` param's percent-encoding round-trips correctly even though the originally-captured URL from the live session double-encoded the colon (`%253A`) — the router handles it either way.

- **Evidence:** `screenshots/20-url-reproduce-test.png`, fresh-navigation test as described above.
- **Did I need to already know something a stranger wouldn't?** No.
- **Assessment:** genuine, verified pass, no fix lane needed.

---

## Phase 3 — the developer-twin sweep

Checked `runs/north-star-01`, `runs/tier3-demo-01`, and (after grepping all fixtures) `runs/whiterun-jarl-01` via `jq` against `trace.jsonl` for each named record type before constructing deep links. Also checked `scenarios/conftest.py` (the `deep_link` fixture) and the actual T1.3/T3.4 scenario test files (`scenarios/test_tier1_transmission_trace.py`, `scenarios/test_tier3_tell_decision.py`) to see whether either currently emits a `filters=` deep link for these landing cases: **neither does** — both tests assert directly against the trace's `record_type`/`encountered` fields and never call `deep_link.set(filters=...)`. So the deep links below are hand-constructed against the dashboard's own filter UI, exactly as a developer or a future test author would have to do today; they are not literally "the URL a failing test currently produces" (no such test exists yet for these three cases), which the finding below reflects precisely.

### T1.3 — rolled-against (encounter-rolled-but-not-encountered)

- **Source record:** `runs/whiterun-jarl-01/trace.jsonl`, tick 0, `dragonsreach`, `irileth`↔`proventus`, `record_type: encounter_rolled`, `outcome: no_encounter`, `encountered: false`, `value: 0.523`, `threshold: 0.35`.
- **Working deep link:** `http://localhost:5173/feed?run=whiterun-jarl-01&filters={"npc":"irileth","outcome":"rolled_against"}` (underscore).
- **Result:** the record lands within one click (expand the collapsed "tick 0 · 1 trace row" group): "t0 dragonsreach irileth ↔ proventus rolled-against 0.523 vs. threshold 0.350" (screenshot `screenshots/16-t1.3-tick0-expanded.png`).
- **Verdict: PASS.**
- **Filed alongside (not a step failure, a UI-consistency finding):** the outcome filter's `<select>` renders its dropdown *label* with a hyphen (`rolled-against`) but its underlying `value` (and therefore the URL-serialized filter) with an underscore (`rolled_against`) — confirmed at the source, `dashboard/src/components/feed/FeedFilterBar.vue:73`: `<option v-for="o in OUTCOME_OPTIONS" :key="o" :value="o">{{ o.replace("_", "-") }}</option>`. Typing the hyphenated form that's visibly shown in the UI into a URL by hand (e.g. `outcome":"rolled-against"`) silently returns "0 of 520 rows" with the dropdown showing as unselected (screenshot `screenshots/13-t1.3-rolled-against.png`, taken during Phase 1's exploration). This is a real footgun for anyone constructing a URL from what they see on screen, but it is **not** a violation of §1.2's "pytest-emitted deep link is resolvable by construction," since no scenario test currently emits a `filters` deep link for this case at all — filing it as a UI internal-consistency bug instead.
- **Proposed fix lane:** normalize `FeedFilterBar.vue`'s outcome option so the displayed label matches its value (drop the `.replace("_", "-")` cosmetic transform, or apply the same transform when parsing filters back out of the URL) — small, contained fix.

### T3.4 — declined-by-rule

- **Source record:** `runs/tier3-demo-01/trace.jsonl`, tick 4, `bannered_mare`, `hulda`↔`olfrid`, `record_type: transmission_declined`, `rule: tell-decision-policy`.
- **Deep link:** `http://localhost:5173/feed?run=tier3-demo-01&filters={"npc":"hulda","outcome":"declined"}`.
- **Result:** clean pass. All 44 matching rows render immediately, ungrouped (not hidden behind a collapsed "N trace rows" summary), with the rule name `tell-decision-policy` printed directly on the row, fully visible without scrolling (screenshot `screenshots/17-t3.4-declined.png`).
- **Verdict: PASS.** Confirms Lane 30's claim still holds — no regression found. (`declined` has no hyphen/underscore variant, so it doesn't hit the T1.3 footgun.)

### nothing-salient

- **Source record:** `runs/tier3-demo-01/trace.jsonl`, tick 4, `warmaidens`, `adrianne`↔`proventus`, `record_type: nothing_salient`, `reason: neither-informed`.
- **Working deep link:** `filters={"npc":"adrianne","outcome":"nothing_salient"}` (underscore) → 614 of 2156 rows render (screenshot `screenshots/19-nothing_salient-working.png`).
- The hyphenated form (`"nothing-salient"`, matching the visible dropdown label) hits the same footgun as T1.3 — "0 of 2156 rows," dropdown shows unselected.
- Even with the correct filter, matching rows are batched 12-14 per collapsed tick group (nothing-salient traffic is dense, as expected) — landing "within one click" holds (one click expands the group), but the specific target pair isn't singled out or highlighted among the ~14 rows revealed in that group, requiring a manual scan.
- **Verdict: PASS**, with the same UI-consistency finding as T1.3 (same root cause, same fix lane) plus a minor secondary note (no auto-highlight of the specific matched record inside an expanded group).

---

## Summary of filed spec bugs

1. **No timeline on the default landing view** — violates §0 audience-neutral-chrome doctrine and the walkthrough's step 1. Fix lane: promote the timeline to global chrome across all views.
2. **Map has no Markarth coverage** — blocks steps 2 and 3 outright. Fix lane: extend the map coordinate fixture to include Markarth (or an off-map placeholder region).
3. **Variant tree's edge labels render as an illegible overlapping text mass** — a severe rendering bug that makes step 4's correct underlying data undiscoverable by a sighted human. Fix lane: dedupe/reposition edge-label rendering in the tree view.
4. **Provenance drill-down popover is mispositioned and under-informative** — doesn't visibly complete the "belief → dagger → mutation" story in one place, and floats detached from its invocation point. Fix lane: reposition the popover and extend its content to include the mutation event inline.
5. **Outcome filter dropdown label/value mismatch** (`rolled-against` displayed vs. `rolled_against` stored, same for `nothing-salient`/`nothing_salient`) — a UI-consistency footgun, not a §1.2 pytest-emitter defect (confirmed no current scenario test emits these links). Fix lane: drop the cosmetic label transform in `FeedFilterBar.vue`, or make filter parsing accept both forms.

**Retracted during Phase 2/3 verification (recorded here for transparency, not filed as bugs):**
- *"Claim filter is inert"* — false positive. `north-star-01` has exactly one claim value, so filtering to it produces no visible count change by design. Confirmed working correctly against `tier3-demo-01` (7 distinct claims; selecting one dropped the row count from 2156 to 308).
- *"Confidence 0.00 display bug"* — not a bug. `relief_caravaneer` and `markarth_resident_3` are locked in a genuine repeated-contradiction loop (117 and 335 `supersession` records respectively, each carrying `confidence_dent: 0.1`), which floors their confidence at 0 as intended by the model, not a rendering defect.

## What worked well (for the record)

- The NPC belief-card inspector (claim id, HEARD/REPEATED badge, variant id, full belief text, confidence/verbatim/gist meters, "told-by ← X · t N" provenance line) is well-designed and, on its own, nearly carries steps 3 and 5 once you can reach it.
- URL-state round-tripping (step 6) worked consistently and robustly, verified with an actual fresh-context navigation restoring full state including an open drill-down popover.
- The map's visual design (painterly Whiterun render, glyph legend, lens/overlay panel, coverage stats) is polished where it has data to show.
- T3.4's declined-by-rule landing case is clean and regression-free.
- The confidence/verbatim/gist decay and dent mechanics are working as designed and produce a genuinely interesting emergent dynamic (a contested-belief tug-of-war between two Markarth-adjacent NPCs) — this is a system strength, not a bug, once surfaced correctly.
