<script setup lang="ts">
/**
 * MarkerLayer — every cast marker, rendered through NpcMarker at each
 * marker's left/top percent.
 *
 * Lane 14: `markers` is now the real (or synthetic-test) derived model
 * (`derived/mapMarkers.ts`'s `DerivedMarker[]`) instead of always reaching
 * into the fixture. `markers` is optional and, left unset, falls back to
 * the fixture's `buildMarkers(stainLens, showGlyphs)` — the same
 * prop-default idiom `StageLegend`'s `claimId`/`coverage` already use —
 * so MapView/MarkerLayer's existing tests (which never pass `markers`)
 * keep exercising the approved-mockup fixture render unedited. MapScreen
 * always supplies real `markers` in the app itself, which is what
 * "instead of buildMarkers" means for the actual per-tick render path.
 *
 * - stainLens on  → stage fill/ring colors (the "rumor-stage" lens)
 * - stainLens off → the mockup's gray lens-off pair (#79828e / #3a414c)
 * - showGlyphs off → glyph badges hidden
 *
 * Lane 35: a marker carrying `variantClass` (the variant lens is active —
 * see `derived/mapMarkers.ts`) styles via `variantMarkerStyle` instead of
 * the plain stage lookup, and ignores `stainLens` (the variant lens is a
 * separate, mutually-exclusive overlay per ui-spec §7 item 3 — a marker
 * either has a `variantClass` or it doesn't; there's no "variant lens with
 * the stage lens's gray toggle also applied" state). Markers with no
 * `variantClass` (the default, and every pre-lane-35 marker) render exactly
 * as before.
 */
import { computed } from "vue";
import { buildMarkers, STAGE_STYLE, GLYPH_COLOR, type MapMarker } from "../../fixtures/whiterunMock";
import { variantMarkerStyle, type DerivedMarker } from "../../derived/mapMarkers";
import NpcMarker from "./NpcMarker.vue";

const props = withDefaults(
  defineProps<{
    markers?: DerivedMarker[];
    stainLens?: boolean;
    showGlyphs?: boolean;
  }>(),
  { markers: undefined, stainLens: true, showGlyphs: true },
);

const emit = defineEmits<{ select: [id: string] }>();

type RenderMarker = MapMarker & { id?: string };

function renderReal(source: DerivedMarker[]): RenderMarker[] {
  return source.map((m) => {
    if (m.variantClass !== undefined) {
      const st = variantMarkerStyle(m.stage, m.variantClass);
      return {
        id: m.id,
        name: `${m.name} — ${m.stage} — ${m.variantClass}`,
        left: m.left,
        top: m.top,
        fill: st.fill,
        ring: st.ring,
        size: st.size,
        glyph: props.showGlyphs ? m.glyph : null,
        glyphColor: m.glyph ? GLYPH_COLOR[m.glyph] : "#888",
        selected: m.selected,
      };
    }
    const st = STAGE_STYLE[m.stage];
    return {
      id: m.id,
      name: `${m.name} — ${m.stage}`,
      left: m.left,
      top: m.top,
      fill: props.stainLens ? st.fill : "#79828e",
      ring: props.stainLens ? st.ring : "#3a414c",
      size: st.size,
      glyph: props.showGlyphs ? m.glyph : null,
      glyphColor: m.glyph ? GLYPH_COLOR[m.glyph] : "#888",
      selected: m.selected,
    };
  });
}

const markers = computed<RenderMarker[]>(() =>
  props.markers !== undefined ? renderReal(props.markers) : buildMarkers(props.stainLens, props.showGlyphs),
);
</script>

<template>
  <NpcMarker
    v-for="(m, i) in markers"
    :key="m.id ?? `${m.name}-${i}`"
    :marker="m"
    @select="emit('select', $event)"
  />
</template>
