<script setup lang="ts">
/**
 * ComparePane — one aligned map pane (run A or run B), ui-spec §3.9: "the
 * maps are the selection target and spatial context, not the primary
 * rendering." Reuses `views/MapView.vue` wholesale at low ceremony (per
 * the packet: "aligned panes reusing the map at low ceremony") rather than
 * rebuilding a second map renderer -- this pane only supplies that run's
 * own `markers` (derived the same way `MapScreen.vue` does, via
 * `derived/mapMarkers.ts`) and a label.
 */
import MapView from "../../views/MapView.vue";
import PanelGlass from "../PanelGlass.vue";
import type { DerivedMarker } from "../../derived/mapMarkers";

defineProps<{
  label: string;
  tick: number | null;
  markers: DerivedMarker[];
  hasRun: boolean;
}>();

const emit = defineEmits<{ select: [id: string] }>();
</script>

<template>
  <div class="compare-pane">
    <PanelGlass tone="strong" class="compare-pane__label" :padded="false">
      <span class="compare-pane__label-text">{{ label }}</span>
      <span v-if="hasRun" class="compare-pane__tick">t {{ tick }}</span>
    </PanelGlass>
    <div v-if="!hasRun" class="compare-pane__placeholder">no run loaded</div>
    <MapView v-else :markers="markers" :has-carrier="false" @select="emit('select', $event)" />
  </div>
</template>

<style scoped>
.compare-pane {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  position: relative;
  border: 1px solid var(--c-hairline);
}

.compare-pane__label {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 10px;
  font-size: var(--fs-secondary);
}

.compare-pane__label-text {
  color: var(--c-accent-hover);
  font-family: var(--font-data);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.compare-pane__tick {
  color: var(--c-text-dim);
  font-family: var(--font-data);
}

.compare-pane__placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}
</style>
