<script setup lang="ts">
/**
 * TimelineTrack — the timeline bar itself (map-c-skyrim.dc.html:220-234):
 * baseline, the heat-stripe cluster (or individual markers when sparse),
 * day ticks, typed event markers with title tooltips, and the playhead
 * with its tick-label chip.
 *
 * Props boundary (lane 16 keeps this intact, per the packet): the parent
 * (`TimelineBar.vue`) computes every percent and derives the markers/
 * days/heat-stripe result via `src/derived/timelineMarkers.ts` — this
 * component only renders what it's given. It does not read any store or
 * derived module itself except `MARKER_TYPE_REGISTRY`, which is static
 * per-type color/legend metadata, not per-record derivation.
 *
 * Markers are real clickable buttons now (lane 16; previously
 * `@click.prevent` no-ops, same pattern lane 14 fixed on `NpcMarker.vue`):
 * clicking one emits `marker-click` with the marker's tick so the parent
 * can write `urlState.t` ('replace' mode).
 */
import { computed } from "vue";
import { MARKER_TYPE_REGISTRY, type DayTick, type HeatStripe, type TimelineMarker } from "../../derived/timelineMarkers";

const props = defineProps<{
  days: DayTick[];
  heat: HeatStripe;
  playheadPos: number;
  playheadLabel: string;
  docked: boolean;
}>();

const emit = defineEmits<{ (e: "marker-click", tick: number): void }>();

function colorFor(type: TimelineMarker["type"]): string {
  return MARKER_TYPE_REGISTRY.find((m) => m.type === type)?.color ?? "var(--c-text-faint)";
}

/** playhead glow (map-c-skyrim.dc.html:296 — not part of any store) */
const phGlow = computed(() => (props.docked ? "rgba(224,82,82,.6)" : "rgba(232,226,212,.5)"));
const phColor = computed(() => (props.docked ? "#ff8a80" : "#e8e2d4"));
</script>

<template>
  <div class="track">
    <div class="track__baseline" />
    <template v-if="heat.dense">
      <div
        v-for="(b, i) in heat.buckets"
        :key="i"
        class="track__heat"
        :style="{ left: b.pos + '%' }"
        :title="`${b.count} events`"
        data-testid="heat-stripe"
      />
    </template>
    <template v-else>
      <button
        v-for="m in heat.markers"
        :key="`${m.tick}-${m.type}-${m.label}`"
        type="button"
        class="track__event"
        :style="{ left: m.pos + '%', background: colorFor(m.type) }"
        :title="m.label"
        @click="emit('marker-click', m.tick)"
      />
    </template>
    <div
      v-for="d in days"
      :key="d.n"
      class="track__tick"
      :style="{ left: d.pos + '%' }"
    >
      <div class="track__tick-mark" />
      <div class="track__tick-label">D{{ d.n }}</div>
    </div>
    <div
      class="track__playhead"
      data-testid="playhead"
      :style="{
        left: playheadPos + '%',
        background: phColor,
        boxShadow: '0 0 6px ' + phGlow,
      }"
    />
    <div
      class="track__chip"
      data-testid="playhead-chip"
      :style="{ left: playheadPos + '%', background: phColor }"
    >
      {{ playheadLabel }}
    </div>
  </div>
</template>

<style scoped>
.track {
  flex: 1;
  position: relative;
  height: 46px;
  min-width: 0;
}

.track__baseline {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 12px;
  height: 1px;
  background: rgba(201, 168, 106, 0.28);
}

.track__heat {
  position: absolute;
  width: 3px;
  bottom: 13px;
  height: 6px;
  transform: translateX(-50%);
  background: rgba(255, 82, 51, 0.65);
  border-radius: 2px;
}

.track__tick {
  position: absolute;
  bottom: 0;
  transform: translateX(-50%);
  text-align: center;
}

.track__tick-mark {
  width: 1px;
  height: 5px;
  background: rgba(201, 168, 106, 0.35);
  margin: 0 auto;
}

.track__tick-label {
  font-size: 8px;
  color: var(--c-text-faint);
}

.track__event {
  appearance: none;
  border: none;
  padding: 0;
  cursor: pointer;
  position: absolute;
  bottom: 15px;
  width: 3px;
  height: 15px;
  border-radius: 1px;
  transform: translateX(-50%);
  box-shadow: 0 0 4px rgba(0, 0, 0, 0.6);
}

.track__playhead {
  position: absolute;
  bottom: 2px;
  top: 0;
  width: 2px;
  transform: translateX(-50%);
  /* Full-height decorative line only -- must never steal clicks from a
     marker button that shares its tick (e.g. this run's t=0, where the
     crime/death markers sit at the same position as the initial playhead). */
  pointer-events: none;
}

.track__chip {
  position: absolute;
  top: -2px;
  transform: translateX(-100%);
  color: var(--c-surface-deepest);
  font-size: var(--fs-micro);
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 2px;
  white-space: nowrap;
  pointer-events: none;
}
</style>
