<script setup lang="ts">
/**
 * NpcMarker — one cast marker on the map, ported from
 * map-c-skyrim.dc.html:62-72: the stage dot (fill/ring/size from the
 * rumor stage, or the gray lens-off pair) with its flat dark halo, a
 * 26px selection ring when selected, and the 12x12 worst-case glyph
 * badge offset (+8,-11). Positioning is in percent of the crop square.
 *
 * Dynamic geometry (position, stage colors, glyph color) is data-driven
 * so it stays as inline style, exactly like the mockup.
 */
import type { MapMarker } from "../../fixtures/whiterunMock";

defineProps<{
  marker: MapMarker;
}>();
</script>

<template>
  <div
    class="npc-marker"
    :style="{ left: `${marker.left}%`, top: `${marker.top}%` }"
  >
    <div v-if="marker.selected" class="npc-marker__selection" />
    <a
      href="#"
      class="npc-marker__dot"
      :title="marker.name"
      :style="{
        width: `${marker.size}px`,
        height: `${marker.size}px`,
        background: marker.fill,
        borderColor: marker.ring,
      }"
      @click.prevent
    />
    <div
      v-if="marker.glyph"
      class="npc-marker__glyph"
      :style="{ borderColor: marker.glyphColor, color: marker.glyphColor }"
    >
      {{ marker.glyph }}
    </div>
  </div>
</template>

<style scoped>
.npc-marker {
  position: absolute;
  transform: translate(-50%, -50%);
}

.npc-marker__selection {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: var(--selection-ring-size);
  height: var(--selection-ring-size);
  border: var(--selection-ring-width) solid var(--c-selection-ring);
  border-radius: 50%;
  pointer-events: none;
}

.npc-marker__dot {
  display: block;
  border-radius: 50%;
  border: var(--marker-ring-width) solid;
  box-shadow: 0 0 0 var(--marker-halo-width) var(--c-marker-halo);
}

.npc-marker__glyph {
  position: absolute;
  left: var(--glyph-badge-offset-x);
  top: var(--glyph-badge-offset-y);
  width: var(--glyph-badge-size);
  height: var(--glyph-badge-size);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--glyph-badge-font);
  font-weight: 600;
  /* rgba(8,10,13,.9) badge plate — no token; literal from
   * map-c-skyrim.dc.html:69 */
  background: rgba(8, 10, 13, 0.9);
  border: var(--glyph-badge-border-width) solid;
  border-radius: 2px;
  pointer-events: none;
}
</style>
