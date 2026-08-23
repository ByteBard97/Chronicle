# Chronicle — Dashboard UI Specification (v1.2.1)

**Status:** Revised after three independent reviews of v1 and one code-grounded review of v1.1 (which verified the closed-form-decay claim at claims.py:71 and found the five-state obligation enum already in social.py:137's type — the greyed rendering matches the domain model, not speculation). Written against scenario-ladder.md (v0.4 FINAL), vision.md (v2.1), and ui-doctrines.md. **Precondition satisfied (v1.2.1):** ui-doctrines.md is compiled from docs/research/dashboard-ui-prior-art/ and merges in the same constitution batch as this document.
**Changed from v1.2 (the v1.2.1 addendum):** three items the build plan independently arrived at, promoted into the frozen contract so the citations resolve on disk — (a) the **runs registry** (`runs/index.json`, §1.2): static run enumeration without a backend; (b) the **Range requirement as a standing assertion** (§1.3): the dev server must answer 206 to Range requests, verified by an automated check, not assumed; (c) the **runner-is-not-a-backend framing** (§3.1): the eventual injection runner is the sim's write API — the dashboard still reads only files.
**Changed from v1.1:** the §0/§1.1 self-contradiction fixed (the log's contents defined as exactly three things — inputs, derivations-with-inputs, acceleration — replacing the over-broad "no stored derived state" phrasing that outlawed its own keyframes); the volume/process-model collision resolved inside static-first (per-run directory with physically split stream files + a sidecar byte-offset index, frozen as writer-side contract); jitter seeding and transform-as-source-of-truth made precise.
**Changed from v1:** numeric histories cut from the frozen schema (belief curves are closed-form at read time; storing sampled derived state violated the event-sourcing discipline this spec inherits); runs-directory contract added (deep links resolved, not 404ing); injection-at-historical-T defined as a fork; §1.3 simplified to static+Range with torn-record framing; trace volume corrected to 10⁵–10⁶; map backdrop dependency closed (dashboard/map/ exists — 4K bake + 26-location coordinate fixture with door coords); Allport-Postman demoted to derived classification; merge-scan not binary search; social-graph view explicitly deferred; Tier-0 time control named; glyph precedence written; obligation enum completed; adapter-websocket clarification; open questions resolved with the convergent review answers.

**What this document is:** the buildable specification for Chronicle's observation dashboard — substrate contracts first (the parts that must not churn), then global chrome, then each view with its forcing tier, named precedent, interactions, and salience defaults, ending with the acceptance walkthrough. Build order equals ladder tier order; no view is built before its forcing tier needs it.
**What it is not:** a visual design document. Colors, typography, and layout polish are downstream and freely iterable; everything in §1 is not.

---

## 0. Ruling constraints (inherited, cited)

- **Three audiences, one artifact** (vision §4): developer debugging, player observation, second-screen. Never forked — audience differences are *salience filter defaults*, not separate UIs.
- **Every view renders as-of-tick-T** (ladder §4.1), including Tier 0's inspector before the scrubber widget exists.
- **The scrubber is an event index, not a position control** (ui-doctrines; CS2/Hudl grammar).
- **Negative results are first-class** (ladder §4.4): non-encounters, declined transmissions, evaluated-but-not-fired rules render with equal weight.
- **Every rendered field links to its cause** (ladder §4.3 / ADR-0007). No dead-end numbers.
- **Renderer split** (ui-doctrines): canvas for map and markers (Canvas2D at v0.1 scale — WebGL is quarantined behind the map surface and revisited at the 1,000-NPC milestone); DOM/SVG for panels, labels, tooltips, inspector; hidden-canvas color-key picking. Graph layouts pin node positions across ticks.
- **Prohibitions** (ui-doctrines mistake catalog): no render-rate/sim-rate coupling; mid-tick state never shown; no whole-state-per-tick storage; no forward-only replay; no SVG-per-marker past ~1,000; no unfiltered state dump without a salience filter first and an "all events" toggle second; **derived state appears in the log only as acceleration** — rebuildable from events + trace, never as sampled histories (v1.2 — see §1.1's three-things rule).

## 1. Substrate contracts (frozen before any UI work)

### 1.1 The frame log

One versioned, append-only log per run. **The log contains exactly three kinds of thing, and nothing else:** (1) **inputs** — canonical events; (2) **derivations with their inputs** — the trace; (3) **acceleration structures** — keyframes and indexes, which are rebuildable by scanning (1)+(2) and carry no information of their own. This is the precise form of the event-sourcing invariant: derived state appears only as acceleration, never as an independent source of truth.

**Physical layout (frozen as writer-side contract):** one directory per run — `runs/<run_id>/` — with **physically split stream files**: `events.jsonl` (small; what the world did) and `trace.jsonl` (large; why the sim did it). Logically they remain sibling streams on one timeline; physically, the majority of views that need only canonical events never touch the big file. Alongside them, a **sidecar index** (`index.json`: per stream, tick → byte offset, plus keyframe offsets), written incrementally by the sim and rebuildable by a scan — pure acceleration. The index is what makes keyframe random access, encounter-feed pagination, and LIVE tailing all work over plain HTTP Range requests: without byte offsets, "seek to tick 4,183's keyframe" is unimplementable statically, and the volume figure below would silently force the backend §1.3 forbids.

- **Record envelope:** `(schema_version, seed_id, save_uuid, generation, tick, stream, seq, payload)`. The branch key `(save_uuid, generation)` is present from record one (ladder Tier 1 commitment) even though headless v0.1 runs a single branch.
- **Record framing:** newline-delimited (JSONL or length-prefixed equivalent). Readers treat a non-terminated tail as not-yet-written — tailing a growing log must never yield a torn record. Cheap now, painful to retrofit.
- **Keyframes:** full derived-state snapshot every K ticks (K default one game-day, adaptive to cast size). Any tick renders as keyframe + replayed deltas — random access to any T is the acceptance test.
- **No sampled histories.** Belief strength/confidence curves are closed-form functions of elapsed time since last rehearsal, computed at read time (verified: claims.py's decay is `value * 0.5^(elapsed/half_life)`); reputation and grudge values are event-driven step functions. All inspector sparklines and scrub-smooth bars **derive analytically at render time** — nothing is sampled, quantized, or cached into the log. Keyframes are not an exception to this: they are acceleration under the three-things rule, not a second source of truth. (The AI-Town compressed-history technique remains the fallback for a future genuinely non-analytic quantity; it is not part of this schema.)
- **The trace is always-on** (ladder Tier 1) — and its volume is real: every co-presence roll is a record, so a 25-NPC, 10-game-day Tier-2 run produces on the order of **10⁵–10⁶ trace rows** (exact figure to be computed from T2.1's tick rate and cast at implementation and recorded here). Virtualized tables handle this; the number is stated so storage, tailing, and table decisions are made against reality rather than the v1 draft's 10⁴ guess.
- **Schema versioning:** version integer and migration note from day one. UI iterates; the log format does not.

### 1.2 The URL-state contract and the runs directory

The dashboard's entire view state serializes into the URL: `run`, `branch` (save_uuid.generation), `t`, `view`, `sel`, `panels`, `filters`, and for run-comparison `runB`/`alignment`.

**The runs-directory contract (v1.1 — the missing operational link):** scenario and sim runs write frame logs to a single known directory (`runs/`, gitignored, path configurable via one env var shared by pytest and the dashboard). The dashboard enumerates it for its run picker and serves any log in it by run id. A pytest-emitted deep link is therefore resolvable by construction: the test wrote the log where the dashboard looks. The dev workflow assumes the dashboard server is up during test work; if it isn't, the link is still valid the moment it starts.

**The runs registry (v1.2.1):** a static server cannot list directories, so the writer maintains `runs/index.json` — run id, seed, created, tick range, stream files — registered on run creation. The registry is how the run picker enumerates runs over plain static serving; no backend is smuggled in through enumeration.

Consequences, in order of importance:
1. **Failing assertions emit deep links** (ladder §4.2): failure output includes a URL opening the dashboard at the failing tick, entity selected, offending record highlighted. Ships with the first view.
2. Every interesting moment is shareable/bookmarkable.
3. Back/forward buttons are time-and-focus history for free.

### 1.3 Process model

**Log-first, static-first.** v0.1's dashboard is a client-side web app served statically; it reads run logs over plain HTTP **Range requests** — which any static file server provides — polling with a byte offset to tail a growing log. No application backend until server-side filtering is forced by measured volume, not before. **The Range requirement is verified, not assumed (v1.2.1):** the serving setup must answer 206 to a Range request against a run log, and a standing automated check asserts exactly that — static middleware has historically had Range gaps, and the entire reader design (byte-offset fetch, torn-tail guard, LIVE polling) is load-bearing on this one behavior. "Watch it run" is the LIVE dock: the view follows the newest complete record when the playhead is docked at LIVE and detaches into history the moment the user scrubs. One code path, two behaviors.

**Scope clarification (v1.1):** the no-live-coupling rule governs the **dashboard↔sim** path only. It does not contradict the adopted adapter↔core transport (the game-side websocket telemetry for v0.2+ live play): the adapter feeds the *sim*, the sim writes the *log*, the dashboard reads the *log*. Three components, two seams, one direction of flow.

## 2. Global chrome

- **Time control.** From Tier 0: a minimal tick/day stepper plus direct tick entry — the operable form of as-of-T before the timeline exists. At Tier 2 it grows into **the timeline**: playhead; play/pause; speed presets (¼×–8×, shown as multipliers, never tick rates); segment stepping at game-day and schedule-block boundaries; ±1 day skip; **typed event markers striped on the bar** — claim born, mutation, supersession, grudge formed, threshold crossed, role vacancy, carrier arrival — clickable, type-filterable, degrading to a heat stripe when dense. LIVE dock at the right end when tailing.
- **Selection model** (GAMA's highlight-across-views): one global selection; selecting an entity anywhere highlights it everywhere. Selection is in the URL.
- **Salience filter** (global, three defaults): *Developer* (everything, trace rows included), *Observer* (semantic events and state changes; trace collapsed behind expanders), *Story* (the sifted surface — mutations, contested resolutions, grudges, vacancies). Every raw list obeys the filter and carries an "all events" toggle.
- **Worst-case glyph precedence (v1.1, written so it can't churn):** a marker's glyph shows the NPC's highest-precedence active state, in this order: (1) active schedule deviation (mourning, avoidance — behavior changed), (2) grudge above threshold, (3) actively spreading a rumor, (4) newly formed belief this game-day, (5) none. Revisable by amending this list, never per-view.
- **Follow mode:** watch/follow toggle on any NPC; the map keeps a followed NPC centered through scrubs.

## 3. Views, in build order

### 3.1 Injection console — Tier 0

Headless event entry: a form/DSL for appending canonical events to a run, plus scenario-file load/run/re-run with seed control. **Fork semantics (v1.1):** appending while the playhead is docked at LIVE on a running/tailing sim appends to the current branch. Appending at any historical tick T (< end of log) **creates a fork** — `(save_uuid, generation+1)`, re-simulated from T — because injecting into settled history invalidates every frame after it. The branch key exists for exactly this; the console surfaces it (a "forking from tick T" confirmation naming the new generation) rather than inventing log surgery. **The runner is not a backend (v1.2.1):** when live append/fork is eventually built, the process accepting events is the sim's own write API — the dashboard's read path remains files-only regardless; §1.3's no-backend rule is about the read path and is not relaxed by the write path existing. Developer-only salience.

### 3.2 NPC inspector — Tier 0

**Precedent composite:** RimWorld tabbed inspect pane × Sims moodlets × AnyLogic three-mode popover × CK itemized tooltip.

- Pinnable (multiple pins; bulk-close). Stable tabs: **Beliefs / Relationships / Schedule / History**.
- **Beliefs:** each belief moodlet-style — claim summary, variant badge, confidence bar, verbatim/gist strength bars with inline sparklines (derived analytically per §1.1), evidence-type icon, rumor-stage chip (the real five states — with **dormant/forgotten rendered as derived states showing their derivation inputs**: last-rehearsed tick and the decay parameters, not presented as stored facts). Every element links: claim → variant tree; evidence icon → provenance drill-down; source → that NPC.
- **Relationships:** sparse edges with type chips; grudges with two bars (emotional/evidentiary); obligations as ledger rows with the **full five-state status enum — active / fulfilled / violated / expired / excused** — noting that only fulfilled/violated are producible under the current rule set (expired/excused render greyed with a "no producer yet" tooltip rather than being omitted and rediscovered later).
- **Schedule:** the block strip at T; rewritten blocks (Tier 4a+) highlighted, causing rule linked.
- **History:** this NPC's event stream, salience-filtered, Legends-style inline entity links.
- **As-of-T from day one**, driven by the §2 stepper until the timeline arrives.

### 3.3 Encounter feed — Tier 1

Chronological table over the trace stream: tick, location, participants, outcome — **four outcome states with equal visual weight**: transmitted (claim/variant), rolled-against (roll value vs. threshold), declined (rule name — tell-decision rows land here from Tier 3), nothing-salient. Filterable by NPC/location/outcome/claim. Row click → both inspectors + timeline jump. Story salience shows transmissions and declines only.

### 3.4 Map god-view — Tier 2

**Precedent composite:** Smallville/AI Town town view × Sims plumbob × CS2 X-ray overlays.

- **Canvas2D surface; multi-hold from day one** (ladder T2.6 export). **The backdrop and coordinate dependency is closed:** dashboard/map/ contains the fo76utils-baked 4096×4096 WhiterunWorld render (user's own game files, deterministic, zero redistributed assets) and `whiterun_map.json` — the world→pixel transform plus 26 named locations with real coordinates, including exterior door positions. Carrier-route destinations render as labeled schematic satellite nodes with route lines; road locations as points on the lines (other holds get real bakes only if observation ever demands them).
- **NPC markers anchor at their location's actual door coordinate** (v1.1 upgrade the fixture enables — truth-anchored, not centroid-guessed), with deterministic jitter — **seeded by (npc_id, location_id)** so a marker never swims between scrubs when nothing moved — in a small radius around the door for co-present NPCs. No fabricated indoor movement. (Fixture note: the JSON's world→pixel **transform block is the source of truth**, not the baked pixel fields — anyone rebaking at a different resolution regenerates pixels from the transform.)
- Marker anatomy: dot + worst-case glyph per §2's precedence, toggleable as a layer.
- **Overlay layers, one active at a time** via a selector naming the lens (rumor state for a selected claim — the spreading-stain view; grudge intensity; schedule-deviation highlights at Tier 4a+). **The overlay registry is built multi-layer-capable** (a second concurrent layer is a config change, not a rewrite) even though v1 activates one — the future "did the grudge cause the reroute, and did the reroute change who heard" question is real; it just hasn't forced a composite yet.
- Interactions: click → select+inspect (hidden-canvas picking); hover → label; follow mode; scrub-while-watching is the signature moment.

### 3.5 Variant tree — Tier 2

**Precedent:** Nextstrain/Auspice — mutations annotated on branches; recolorable; desaturation for low confidence.

- One tree per claim: root = canonical; nodes = variants; **edges labeled with what the sim actually did** — mutated slot, old→new value, seeded mutation id, firing rule. (The Allport-Postman taxonomy — leveling/sharpening/assimilation — is *not* schema: the mechanism performs slot substitution, and borrowing distortion-psychology vocabulary the mechanism doesn't implement is a category error. If wanted later, it's a derived classification layer over the real labels.)
- **Supersession records as dashed cross-links** (separate visual element matching their separate-record schema); node anatomy: variant summary, holder count at T, contested-claim dent where present. Node click → holder table + map overlay switches to this variant.
- Recolor modes: by hold, first-appearance time, holder count. **Fixed generational left-to-right layout, hand-rolled SVG** — positions stable across scrubs; no graph library, no force-direction.

### 3.6 Provenance drill-down — Tier 2 (view), universal (gesture)

**Precedent:** Pernosco dataflow. Invoked from any belief/evidence element. Vertical span list: belief ← retelling (teller, tick, location, confidence delta) ← … ← witnessed event; unchanged retellings collapsed behind a count; mutations and resolutions always expanded. **DAG-honest** (Jaeger #299): corroborated beliefs render all incoming chains as parallel columns converging — never a spanning tree hiding a parent; superseded chains appear grayed with the resolution record between. Developer-excellent first; the Story-salience "lie has a biography" surface is a presentation pass over identical structure, deferred to the player-facing milestone (vision §3 Bet 2 discipline).

### 3.7 Diff panel + rule-firing log — Tier 3

- **Diff panel:** T₁/T₂ (default playhead vs. one game-day earlier); every social-state delta with signed Δ, firing-rule chip, triggering-event link. Filter by NPC/rule/type.
- **Rule log:** every registry evaluation — activations with inputs *and* evaluated-but-not-fired rows with current accumulator values. Fire-frequency histogram at top (the fires-too-often detector). Rule chip anywhere → this log filtered to that rule.

### 3.8 Schedule diff — Tier 4a

Before/after lanes per NPC, inserted/removed blocks highlighted, causing rule and event linked. Lives in the inspector's Schedule tab and as a standalone multi-NPC comparison.

### 3.9 Run comparison — Tier 4a (forced by T4a.2)

- Two runs (same seed_id, differing fixture/config), **aligned scrubbers**, three panes — but **the ranked divergence list is primary** (v1.1, per all three reviews): entities whose state differs, sorted by first-divergence tick then blast radius, each row narrating the counterfactual cascade and linking both maps to center-and-mark on click. The maps are the selection target and spatial context, not the primary rendering — divergence is sparse and entity-centric; making the user visually hunt a map for a table query is the wrong primary. Signed Δ tables beneath.
- **First-divergent-roll finder: a linear merge-scan** of the two trace streams for the earliest keyed roll whose value differs (not binary search — divergence is not monotone and nothing guarantees it), jumping both playheads there. T4a.2's assertion is this tool automated; the list is scriptable so CI can read it.

### 3.10 Role inspector — Tier 5

Role, holder (linked), duties with lapse state, vacancy history, succession record drill-down-able like any derivation. Role rows join the diff panel. Compositions only.

## 4. Deferred views (unlock conditions named)

- **Social graph view** (v1.1 — previously promised by dashboard/README, now explicitly deferred rather than silently dropped): a topology rendering of the relationship graph. Unlocks **only if** Tier-3+ debugging demands topology the inspector's Relationships tab and the diff panel can't show — per the forcing doctrine it may never earn a view, and that is an acceptable outcome; the README updates to match.
- **Interview mode** — unlocks with the conversation-LLM tier; a chat panel bound to selected NPC + playhead.
- **Retroactive probes** — post-hoc queries over a recorded run; cheap any time after Tier 3, scheduled when a real need forces it.
- **Story surface** — the sifted player-facing feed as a primary view; unlocks with the narrative/query layer. Until then, Story salience on existing views is the placeholder.
- **In-game overlay** — v0.2+ (adapter milestone), thin by prior decision.

## 5. Acceptance: the walkthroughs

**The stranger walkthrough** (vision §7, operationalized): a person who has never seen the tool, given a completed Tier-6 run and one sentence ("the Jarl was assassinated — find out what Markarth believes and why it's wrong"), can within ten minutes and zero coaching: (1) find the assassination on the timeline; (2) scrub and watch the rumor overlay spread, including the carrier hop; (3) click a Markarth believer, read the belief, notice the variant badge; (4) open the variant tree, identify which slot changed at which hop; (5) drill provenance from belief to dagger through the mutation; (6) copy the URL and have it reproduce the view. Each step is a usability test case; failure of any step is a spec bug, not a user error. The encounter feed is deliberately absent — it's plumbing; the drill-down narrates transmission history in the form a stranger needs. (Optional bonus checkpoint, not required: a curious stranger who opens the feed can identify what it shows without explanation.)

**The developer twin** (v1.1, strengthened): every ladder assertion type's failure deep link lands within one click of the offending record — **including one named landing case per negative-row type**: T1.3's rolled-against row, T3.4's declined-by-rule row, and a nothing-salient row; and from T3.4's deep link, the declining rule's name is readable **without scrolling**. Negative results are the feed's reason to exist, and nobody tests them unless the acceptance list names them.

## 6. Build order and non-goals

**Order = forcing order:** §1 substrate → 3.1 + 3.2 (Tier 0 green) → 3.3 (Tier 1) → 3.4 + timeline + 3.5 + 3.6 (Tier 2) → 3.7 (Tier 3) → 3.8/3.9 (Tier 4) → 3.10 (Tier 5). The stranger walkthrough is the release gate for dashboard v1.

**Non-goals for v1:** no application backend until measured volume forces one; no dashboard→sim coupling beyond the injection console's event path (with §3.1's fork semantics); no editing sim state from panels (read-only wins first; NetLogo-style variable editing noted as a possible later power tool); no 3D; no in-dashboard fixture authoring; no player-facing polish before the developer twin passes.

## 7. Resolved questions (formerly open)

1. **Stack** (convergent recommendation recorded as the non-binding default): TypeScript + Vite + React or Preact; TanStack Router for URL-state (its search-param serialization nearly implements §1.2 verbatim) + a small store for non-URL state; TanStack Virtual (or hand-rolled windowing) for trace tables at the corrected 10⁵–10⁶ scale; plain Canvas2D with manual hit-testing for the map. Boring wins; the log schema is the thing that matters and it's frozen regardless of stack.
2. **Keyframe cadence:** K = one game-day, comfortable at 25 NPCs — and better after the numeric-histories cut, since scrub latency is event lookup, not replay. Revisit trigger is a measurement, not a guess: when time-to-render-arbitrary-T exceeds ~100 ms or delta count per interval exceeds ~10⁵, halve K; make K adaptive to cast size at the math-tier milestone.
3. **Overlays:** one at a time via the selector; the worst-case glyph is the compositing channel. The registry stays multi-layer-capable so a future named debugging need is a config change.
4. **Difference pane:** ranked list primary, maps as selection targets (§3.9).
5. **Feed in walkthrough:** stranger no (optional bonus checkpoint only); developer twin yes, with the named negative-row landing cases (§5).
