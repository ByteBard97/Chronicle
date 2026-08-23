# Chronicle map view — design tokens (variant C, approved direction)

Handoff for the Vue/Canvas2D build. Every value below is what the approved
mockup (`map-c-skyrim.dc.html`) actually uses.

## Palette

Chrome:
- page / canvas bg: `#060809` (map well: `#04060a`)
- panel glass: `rgba(10,12,14,.82)` + `backdrop-filter: blur(10px)` (DOM panels only — never per-marker)
- hairline (panel borders, dividers): `rgba(201,168,106,.26)`; inner dividers `.16`
- text primary `#e8e2d4` · body `#d6d0c2` · secondary `#bdb6a4` · dim `#857f70` · faint `#6b6558`
- link / accent gold: `#c9a86a`, hover `#e6c88f`
- active-chip fill: `rgba(201,168,106,.14)`, border `.4`

Rumor stages (fill / ring / diameter px) — separated by hue + value + shape, deuteranopia-checked:
- unheard: hollow — fill `rgba(0,0,0,.12)`, ring `#9aa3ad`, 9px
- heard: `#e3b34c` / `#141008`, 11px
- repeated: `#ff5233` / cream ring `#ffe8d9`, 13px (the cream ring + size is the infectious signal, not the hue)
- dormant: `#8fb4d9` / `#16202b`, 10px
- forgotten: `#565b63` / `#20242a`, 7px

Glyphs (worst-case precedence D ▸ G ▸ S ▸ N): D `#ffd166` · G `#e05252` · S `#ff9a3d` · N `#7fd1b9`

Timeline event types: claim born `#d9a441` · mutation `#c678dd` · grudge `#e05252` · death `#e8e2d4` · carrier `#58c1d4` · threshold `#9d7fd1`. Heat stripe: `rgba(255,82,51,.25→.85)` gradient. LIVE: `#e05252`.

## Type scale

- Cinzel 600 — display only: wordmark 13px/.3em, NPC name 14px, panel titles 8–8.5px/.16–.22em caps, map location labels 8.5px/.18em
- IBM Plex Mono — all data: body 11px, secondary 9.5px, micro 9px, chips 9–10px
- Alegreya 500 — narrative moments only: claim text 13.5px, story-salience provenance 12px italic

## Spacing & geometry

- spacing grid: 4/8/12/16; panel padding 9–11px; radius: chips 3px, panels 8px
- marker: filled circle Ø7–13 by stage + 2px stage ring + 2px flat dark halo `rgba(3,5,8,.65)` — all flat strokes, canvas-drawable, **no shadows or blur per marker**
- selection: 26px ring, 1.5px `#e6c88f`
- glyph badge: 12×12, 1px border in glyph color, 8px 600 letter, offset (+8,−11) from marker center
- world→screen: crop rect (330,90,3000,3000) of the 4096 bake; positions from `whiterun_map.json`'s transform block (source of truth), door-anchored, jitter seeded by (npc_id, location_id)

## Conventions that must survive the build

- derived states show their derivation inputs (dormant: last-rehearsed tick + half-life)
- stage counts always reconcile to the tracked cast (5+12+7+1+1 = 26)
- every rendered number links somewhere (D6)
- salience (developer/observer/story) is a switch over one design, never a fork
