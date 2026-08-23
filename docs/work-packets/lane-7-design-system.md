# Lane 7 — Design-system extraction + M1 view styling

**Status:** Ready to start immediately. Parallel-safe with Lanes 4 and 6 —
you own `dashboard/src/styles/**` and `dashboard/src/components/**`;
Lane 6 owns logic (`src/log/`, `src/derived/`, stores) and builds chrome
*behavior* with deliberately unstyled markup that you then skin.
**Effort:** medium.

## Context

The M3 map-view design is approved and vendored at `dashboard/design/`:
`map-c-skyrim.dc.html` (the approved merged variant), `storyboard-stain.dc.html`,
variants A/B for reference, and **`design-tokens.md` — the contract for this
lane**. The build order is unchanged (map = M3/Tier 2): this lane does **not**
build the map view. It converts the design's *language* into the app's
foundation and applies it to the M1 surface.

## Read first (in order)

1. `dashboard/design/design-tokens.md` — every value you need; the
   "conventions that must survive the build" section is doctrine, not
   advice.
2. `dashboard/design/map-c-skyrim.dc.html` (+ `support.js`) — the approved
   markup/register to translate.
3. `docs/ui-doctrines.md` (skim D5/D11/D14/D15/D22) and `docs/ui-spec.md`
   §2, §3.1–3.2 (the M1 views you're styling).
4. Lane 5/6's code in `dashboard/src/` — follow its conventions; skin, don't
   restructure.

## Task

1. **Tokens:** `src/styles/tokens.css` — every value in `design-tokens.md`
   as CSS custom properties (palette, stage colors, glyph colors, timeline
   event colors, type scale, spacing, marker geometry constants). Fonts:
   Google Fonts link for dev (Cinzel / IBM Plex Mono / Alegreya, all OFL);
   note self-hosting as a distribution-time task in the README.
2. **Base components** (`src/components/`): PanelGlass (the
   `rgba(10,12,14,.82)` + blur panel), Chip, StrengthBar (with inline
   sparkline slot), StageDot (legend/DOM version of the five stage
   markers), GlyphBadge (12×12 letter badge, D/G/S/N), LegendStrip,
   SalienceSwitch (developer/observer/story). Typed props, no logic beyond
   presentation.
3. **Skin the M1 surface** per the approved register: app chrome (top bar,
   run picker), the stepper/time control, and the **NPC inspector** shell —
   four tabs, moodlet-style belief cards with the three bars, provenance
   block, derived-state honesty ("derived: last rehearsed … · half-life …").
   Static/schema-typed data is fine; Lane 6's reader wires real data at
   integration. The **injection console** has no mockup — build it in the
   same token language (form + event-JSON preview + the `chronicle inject`
   CLI invocation display), simplest thing consistent with the design.
4. **Do not build:** the map canvas, the timeline widget, the variant
   tree, the drill-down. Those are M3+ and their forcing tiers haven't
   arrived. The mockups are reference for them later, nothing more.

## Acceptance

- `npm run build` / `npm test` / `npm run check-range` green; a component
  test per base component (props → classes/structure).
- Visual parity with `map-c-skyrim.dc.html` for the inspector and chrome —
  the overseer verifies with a UI snapshot tool; keep components
  screenshot-stable (no random keys, no Date.now in render).
- Every token value traces to `design-tokens.md`; deviations are findings
  in your report, not silent choices.

## File boundaries

- **Create/edit:** `dashboard/src/styles/**`, `dashboard/src/components/**`,
  skins of existing views; `dashboard/README.md` (design section).
- **Do not touch:** `src/log/`, `src/derived/`, `src/state/` (Lane 6),
  `chronicle/`, `docs/`, `dashboard/design/**` (vendored reference —
  read-only), `dashboard/map/**`.

## Conventions

- Commits: follow the owner's current practice (agents commit; the
  overseer reviews what lands).
- No new dependencies — the design needs none beyond what's installed
  (fonts via link). If you believe one is needed, it's a finding.
