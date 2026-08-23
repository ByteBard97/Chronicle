# Chronicle — UI Doctrines (v1)

**Status:** Constitution document. Compiled from the five reports in
[`research/dashboard-ui-prior-art/`](research/dashboard-ui-prior-art/)
(two god-view/replay surveys, the AI Town architecture read, two
causality/lineage/diff passes). This is the source of the "ui-doctrines"
citations in `scenario-ladder.md` (v0.4), `vision-v2.1.md`, and
`ui-spec.md` (v1.2+). Doctrines are rules with named precedents and named
failure modes; each cites its evidence. Amend by editing this file, never
by letting a downstream document invent a doctrine inline.

---

## 1. Time and replay

**D1 — Every view renders as-of-tick-T.** A single shared time control
governs every view; nothing renders "now" while another view renders
history. *Precedent:* the cross-tool convergent grammar (pattern-matrix
§: "a single shared time control governing every view" appears in every
successful tool); the ABM family's counter-example — NetLogo/GAMA/
AnyLogic inspectors are live-state only, no history at all.

**D2 — The scrubber is an event index, not a position control.** Typed
event markers stripe the bar; the user navigates incident-to-incident.
A bare slider is prototype smell. *Precedent:* the RTS/esports timeline
grammar — Dota 2 ("navigate to kills, objectives, or team fights without
scrubbing blindly"), SC2, CS2 `demo_gototick` (the tick as the
addressable unit of time), Hudl Sportscode segment stepping.

**D3 — Build the scrubber against the log, never the live engine.**
Every working replay tool in the prior art reads files; every
live-coupled tool failed at time travel. *Precedent:* Smallville's
replay works precisely because it reads per-step files; Mesa/SolaraViz
carries a "pause before switching pages" warning and threading fixes;
the ABM platforms offer no rewind at all.

**D4 — Random access is keyframes + deltas; forward-only replay is a
named failure.** Replay bolted on as start-at-step-N-and-play-forward
does not get retrofitted into random access. *Precedent:* Smallville's
forward-only replay with start-at-step-N URLs (its roughest documented
edge); RTS engines' deterministic command logs + periodic full-state
keyframes as the positive model.

**D5 — Never show mid-tick state; render only settled frames.**
Simulation speed, render cadence, and displayed tick are three separate
numbers. On a scrub drag, render the settled frame (or a coarse
intermediate), not every intermediate tick. *Precedent:* NetLogo's own
docs — continuous updates "show misleading mid-tick states"; tick-based
updates are "consistent, predictable" and faster.

## 2. Observability

**D6 — Every rendered field links to its cause.** No dead-end numbers.
*Precedent:* the RimWorld "Modern Social Tab" mod exists because vanilla
"gives you a list of names and a number beside each one. It never tells
you why" — provenance is the #1 missing affordance in the surveyed
tools; Pernosco's click-a-value → dataflow chain is the positive model.

**D7 — Negative results are first-class.** Non-encounters, declined
transmissions, and evaluated-but-not-fired rules render with equal
weight to positive events. *Origin:* Chronicle's own (ladder §4.4) — no
surveyed tool does this; the debugging questions that matter ("why
didn't the rumor spread?") are invisible without it.

**D8 — Salience filter first, "all events" toggle second.** No
unfiltered state dumps. *Precedent:* Smallville's persona-state page —
pages of "X is idle" noise; readers immediately asked for salience
filtering (HN thread on the paper).

**D9 — Provenance is a DAG; render all parents.** Never a spanning tree
that hides a cause. *Precedent:* Jaeger arbitrarily picks one reference
as the tree parent and shows no visual relationship for non-primary
references (jaeger-ui #299) — the documented warning for belief chains
with multiple causes; OpenTelemetry span links as the data-model fix.

**D10 — Provenance walks auto-skip trivial relays.** Unchanged
retellings collapse behind a count; mutations and resolutions stay
expanded. *Precedent:* Pernosco's dataflow view auto-continues backward
past trivial copies, even through pipes/sockets.

## 3. Rendering

**D11 — Renderer split: canvas for the map and markers, DOM/SVG for
panels, labels, tooltips.** *Precedent:* SVG/DOM per-entity marks hit a
hard ceiling around a few thousand nodes (SVG-vs-canvas benchmarks);
AI Town runs its town view on PixiJS and fits in <1 GB RAM.

**D12 — Picking is a hidden-canvas color-key pass**, not DOM hit-testing
over hundreds of markers. *Precedent:* standard canvas god-view
practice; keeps the interactive surface and the painted surface the same
object.

**D13 — Pin node positions across ticks.** Layouts never re-initialize
on data change; only genuinely changed elements animate. *Precedent:*
GraphDiaries (staged transitions, layout-stability slider; outperformed
other techniques on task time and errors — Bach, Pietriga & Fekete, IEEE
TVCG 2014) and the d3-force failure it fixes: new nodes enter at random
positions, "huge wobble," mental map destroyed.

**D14 — Glyphs are worst-case-first and toggleable.** The ambient marker
encodes the most salient active state, and ambient chrome is optional.
*Precedent:* the Sims plumbob reflects the *lowest* need (25 years of
stable semantics); players mod bubbles/plumbobs off for screenshots —
glanceable precisely because they're optional, so they're a layer.

**D15 — Two-level reading: glyph for ambient awareness, click for the
full content.** *Precedent:* Smallville's emoji-in-a-speech-bubble
(LLM-translated action, click avatar for the full sentence) — itself
the Sims thought bubble applied to machine agents.

**D16 — Visual styling is an attribute projection, never a class
distinction.** *Precedent:* AnyLogic's documented pitfall of sub-classing
agents purely to display distinct shapes/colors — severe memory and
complexity overhead.

**D17 — Sim rate, render rate, and displayed tick are decoupled.**
*Precedent:* NetLogo's most-documented performance trap — render
coupling freezes the GUI above ~3,000 agents; its FAQ has to tell users
"watch the tick counter"; the JASSS profiling study measured display
code at over half a model's runtime (12.9 s vs 5.1 s with updates off).
Mesa 3's explicit engine/frontend decoupling is the positive model.

## 4. Interaction and process

**D18 — One global selection, highlighted across every view.** Select
anywhere → highlighted everywhere (map marker, table row, graph node,
timeline markers). *Precedent:* GAMA's agent inspector "highlight the
agent across all displays."

**D19 — Camera commitment comes in levels: watch / follow.** (Ride is
out of scope for a read-only v1.) *Precedent:* NetLogo's
watch/follow/ride triad; GAMA's highlight/focus; AnyLogic's click →
popup — so proven that deviating needs a reason.

**D20 — Inspectors accumulate; provide bulk close.** *Precedent:*
NetLogo monitors close individually, in bulk, or filtered to dead
agents — an acknowledgment that observers accumulate open inspectors.

**D21 — Moments are addressed by URL.** Replay state serializes into the
route, making any moment shareable and bookmarkable. *Precedent:*
Smallville's one good replay idea (sim name and step as route
parameters), generalized from "starting step" to the entire view state.

**D22 — The log format is frozen; the UI iterates.** Schema versioned
from day one; derived state appears in the log only as acceleration
(ui-spec §1.1's three-things rule). *Precedent:* Mesa's visualization
churn — custom JS viz replaced by SolaraViz, "API breaking changes in
minor releases" — is what happens when the visualization layer is where
the stability lives. In Chronicle the stability lives in the log.

## 5. The mistake catalog (prohibitions)

Each prohibition names the documented failure it prevents:

1. **No render-rate/sim-rate coupling** — NetLogo's frozen-GUI trap
   (D17).
2. **Mid-tick state never shown** — NetLogo's misleading-frames warning
   (D5).
3. **No whole-state-per-tick storage** — Smallville's storage bloat and
   its manual compress step; the hospital re-implementation's fix was
   delta-encoding plus a single static replay artifact (D4).
4. **No forward-only replay** — Smallville's roughest edge (D4).
5. **No SVG-per-marker past ~1,000** — the SVG node ceiling (D11).
6. **No unfiltered state dump without a salience filter first and an
   "all events" toggle second** — the persona-state page (D8).
7. **Derived state in the log only as acceleration** — rebuildable from
   events + trace, never sampled histories (D22).
8. **No per-tick force re-layout** — the d3-force wobble (D13).
9. **No visual sub-classing of entities** — AnyLogic's over-classing
   pitfall (D16).
10. **No replay coupled to a live engine process** — Mesa/SolaraViz and
    the entire live-only ABM family (D3).
