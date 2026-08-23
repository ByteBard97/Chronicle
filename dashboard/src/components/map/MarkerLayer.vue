<script setup lang="ts">
/**
 * MarkerLayer — every cast marker, built from the fixture's
 * buildMarkers(stainLens, showGlyphs) (the exact port of the mockup's
 * renderVals marker logic) and rendered through NpcMarker at the
 * fixture's left/top percents.
 *
 * - stainLens on  → stage fill/ring colors (the "rumor-stage" lens)
 * - stainLens off → the mockup's gray lens-off pair (#79828e / #3a414c)
 * - showGlyphs off → glyph badges hidden
 */
import { computed } from "vue";
import { buildMarkers } from "../../fixtures/whiterunMock";
import NpcMarker from "./NpcMarker.vue";

const props = withDefaults(
  defineProps<{
    stainLens?: boolean;
    showGlyphs?: boolean;
  }>(),
  { stainLens: true, showGlyphs: true },
);

const markers = computed(() => buildMarkers(props.stainLens, props.showGlyphs));
</script>

<template>
  <NpcMarker v-for="m in markers" :key="m.name" :marker="m" />
</template>
