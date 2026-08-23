<script setup lang="ts">
/**
 * TimelineLegend — the bottom legend line of the timeline strip
 * (map-c-skyrim.dc.html:243-253): "MARKERS —" followed by the typed event
 * colors, and the right-aligned typed-marker count.
 *
 * Lane 16: the legend items are the type filter's UI (view-local state
 * lives in `TimelineBar.vue`; this component is a controlled list —
 * `activeTypes` in, `toggle-type` out). Reconciled against the pinned
 * taxonomy (`MARKER_TYPE_REGISTRY`, ui-spec §2:59): the previous 6-entry
 * hardcoded list (`claim born, mutation, grudge, death, carrier,
 * threshold`) is replaced by the registry's 8 entries — `supersession` was
 * previously absent entirely; `death` (real, from `npc_died`) is folded
 * into `events` alongside `crime_witnessed` rather than kept as its own
 * type, since schema v1 has no standalone "death" trace/event category
 * distinct from the canonical events stream; `role vacancy` and `carrier
 * arrival` render as inactive-looking (dimmed, titled) entries with no
 * producer, per the packet's "active-but-empty legend entry, not an
 * error" instruction.
 */
import { MARKER_TYPE_REGISTRY, type MarkerType } from "../../derived/timelineMarkers";

defineProps<{
  eventCount: number;
  activeTypes: Set<MarkerType>;
}>();

const emit = defineEmits<{ (e: "toggle-type", type: MarkerType): void }>();
</script>

<template>
  <div class="timeline-legend">
    <span class="timeline-legend__title">MARKERS</span>
    <a
      v-for="m in MARKER_TYPE_REGISTRY"
      :key="m.type"
      href="#"
      class="timeline-legend__item"
      :class="{
        'timeline-legend__item--inactive': !activeTypes.has(m.type),
        'timeline-legend__item--empty': !m.hasProducer,
      }"
      :style="{ color: m.color }"
      :title="m.hasProducer ? undefined : 'no producer in schema v1 yet'"
      @click.prevent="emit('toggle-type', m.type)"
      >▮ {{ m.legendName }}</a
    >
    <span class="timeline-legend__spacer" />
    <span class="timeline-legend__summary"
      >{{ eventCount }} typed marker{{ eventCount === 1 ? "" : "s" }}</span
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
  cursor: pointer;
}

.timeline-legend__item--inactive {
  opacity: 0.35;
}

.timeline-legend__item--empty {
  font-style: italic;
  opacity: 0.55;
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
