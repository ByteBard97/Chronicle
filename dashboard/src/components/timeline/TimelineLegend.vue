<script setup lang="ts">
/**
 * TimelineLegend — the bottom legend line of the timeline strip
 * (map-c-skyrim.dc.html:243-253): "MARKERS —" followed by the six typed
 * event colors, and the right-aligned cluster summary. The typed count
 * reflects the rendered event set (10 observer / 8 story).
 */
defineProps<{ eventCount: number }>();

const MARKER_LEGEND = [
  { name: "claim born", color: "var(--ev-claim-born)" },
  { name: "mutation", color: "var(--ev-mutation)" },
  { name: "grudge", color: "var(--ev-grudge)" },
  { name: "death", color: "var(--ev-death)" },
  { name: "carrier", color: "var(--ev-carrier)" },
  { name: "threshold", color: "var(--ev-threshold)" },
];
</script>

<template>
  <div class="timeline-legend">
    <span class="timeline-legend__title">MARKERS</span>
    <a
      v-for="m in MARKER_LEGEND"
      :key="m.name"
      href="#"
      class="timeline-legend__item"
      :style="{ color: m.color }"
      @click.prevent
      >▮ {{ m.name }}</a
    >
    <span class="timeline-legend__spacer" />
    <span class="timeline-legend__summary"
      >{{ eventCount }} typed · cluster D8–D9 heat (187 evt)</span
    >
  </div>
</template>

<style scoped>
.timeline-legend {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: var(--fs-micro);
  color: var(--c-text-dim);
  flex: none;
  min-width: 0;
}

.timeline-legend__title {
  font-family: var(--font-display);
  color: var(--c-panel-title);
  flex: none;
  white-space: nowrap;
  font-size: 8px;
  letter-spacing: 0.16em;
}

.timeline-legend__item {
  flex: none;
  white-space: nowrap;
}

.timeline-legend__spacer {
  flex: 1;
}

.timeline-legend__summary {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
