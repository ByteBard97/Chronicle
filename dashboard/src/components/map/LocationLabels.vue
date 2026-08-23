<script setup lang="ts">
/**
 * LocationLabels — the Cinzel place-name labels over the bake, ported
 * from map-c-skyrim.dc.html:59-61. Positions come from MAP_LABELS in
 * the whiterun mock fixture (percent of the crop square). Labels never
 * intercept pointer events.
 */
import { MAP_LABELS } from "../../fixtures/whiterunMock";
</script>

<template>
  <div
    v-for="[name, x, y] in MAP_LABELS"
    :key="name"
    class="location-label"
    :style="{ left: `${x}%`, top: `${y}%` }"
  >
    {{ name }}
  </div>
</template>

<style scoped>
.location-label {
  position: absolute;
  transform: translate(-50%, 0);
  font-family: var(--font-display);
  font-size: var(--fs-map-label);
  letter-spacing: var(--ls-map-label);
  /* rgba(226,219,203,.66) — no token for label text; literal from
   * map-c-skyrim.dc.html:60 */
  color: rgba(226, 219, 203, 0.66);
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.95);
  white-space: nowrap;
  pointer-events: none;
}
</style>
