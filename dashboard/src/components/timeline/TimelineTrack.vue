<script setup lang="ts">
/**
 * TimelineTrack — the timeline bar itself (map-c-skyrim.dc.html:220-234):
 * baseline, the D8–D9 heat-stripe cluster, day ticks D1–D15, typed event
 * markers with title tooltips, and the playhead with its tick-label chip.
 * Positions come pre-computed from the fixture (buildEvents / DAY_TICKS);
 * the LIVE state (position, color, chip label) comes from LIVE_STATES.
 */
import { computed } from "vue";
import type { TimelineEvent, LIVE_STATES } from "../../fixtures/whiterunMock";

const props = defineProps<{
  events: TimelineEvent[];
  days: { pos: number; n: number }[];
  live: (typeof LIVE_STATES)[keyof typeof LIVE_STATES];
  docked: boolean;
}>();

/** playhead glow (map-c-skyrim.dc.html:296 — not part of LIVE_STATES) */
const phGlow = computed(() =>
  props.docked ? "rgba(224,82,82,.6)" : "rgba(232,226,212,.5)",
);
</script>

<template>
  <div class="track">
    <div class="track__baseline" />
    <div
      class="track__heat"
      title="187 events D8–D9 · heat"
      data-testid="heat-stripe"
    />
    <div
      v-for="d in days"
      :key="d.n"
      class="track__tick"
      :style="{ left: d.pos + '%' }"
    >
      <div class="track__tick-mark" />
      <div class="track__tick-label">D{{ d.n }}</div>
    </div>
    <a
      v-for="e in events"
      :key="e.label"
      href="#"
      class="track__event"
      :style="{ left: e.pos + '%', background: e.color }"
      :title="e.label"
      @click.prevent
    />
    <div
      class="track__playhead"
      data-testid="playhead"
      :style="{
        left: live.phPos + '%',
        background: live.phColor,
        boxShadow: '0 0 6px ' + phGlow,
      }"
    />
    <div
      class="track__chip"
      data-testid="playhead-chip"
      :style="{ left: live.phPos + '%', background: live.phColor }"
    >
      {{ live.phLabel }}
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
  left: 51%;
  width: 8.5%;
  bottom: 13px;
  height: 6px;
  background: linear-gradient(
    90deg,
    rgba(255, 82, 51, 0.25),
    rgba(255, 82, 51, 0.85),
    rgba(255, 82, 51, 0.3)
  );
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
}
</style>
