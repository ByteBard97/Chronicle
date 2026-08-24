<script setup lang="ts">
/**
 * ScheduleBlockBar — one before/after lane for one NPC (lane 41, ui-spec
 * §3.8): a proportional horizontal timeline (`[0, maxTick]`) with each
 * schedule block positioned/sized by its own `[startTick, endTick)`.
 * `state` drives the highlight: "inserted" (accent gold, the overlay
 * ui-spec §3.8 calls out) / "removed" (grudge red, the base span the
 * active overlay pushed out) / "unchanged" (a quiet hairline block,
 * unaffected either way). An inserted block's rule + a link to the
 * `schedule_rewrite` event's own tick in the feed render inline (mirrors
 * `DiffRow.vue`'s `eventHref` idiom, lane 30) -- the causal link ui-spec
 * §3.8 names ("causing rule and event linked").
 */
import { computed } from "vue";
import type { ScheduleBarBlock } from "./scheduleBarBlock";

const props = defineProps<{
  blocks: ScheduleBarBlock[];
  maxTick: number;
  runId: string | null;
}>();

function pct(tick: number): number {
  if (props.maxTick <= 0) return 0;
  return Math.min(100, Math.max(0, (tick / props.maxTick) * 100));
}

const positioned = computed(() =>
  props.blocks.map((b) => ({
    ...b,
    leftPct: pct(b.startTick),
    widthPct: Math.max(0.6, pct(b.endTick) - pct(b.startTick)),
  })),
);

function eventHref(recordTick: number): string {
  const params = new URLSearchParams();
  if (props.runId !== null) params.set("run", props.runId);
  params.set("t", String(recordTick));
  return `/feed?${params.toString()}`;
}
</script>

<template>
  <div class="schedule-block-bar">
    <div class="schedule-block-bar__track">
      <div
        v-for="(b, i) in positioned"
        :key="i"
        class="schedule-block-bar__block"
        :data-state="b.state"
        :style="{ left: `${b.leftPct}%`, width: `${b.widthPct}%` }"
        :title="`${b.locationId} [${b.startTick}, ${b.endTick})`"
      >
        {{ b.locationId }}
      </div>
    </div>
    <ul class="schedule-block-bar__legend">
      <li v-for="(b, i) in positioned" :key="i" :data-state="b.state">
        <span class="schedule-block-bar__swatch" :data-state="b.state" />
        {{ b.locationId }} [{{ b.startTick }}, {{ b.endTick }})
        <template v-if="b.overlay">
          · <span class="schedule-block-bar__cause">{{ b.overlay.cause }}</span> ·
          <a :href="eventHref(b.overlay.recordTick)" class="schedule-block-bar__event-link">
            {{ b.overlay.rule }} @t{{ b.overlay.recordTick }}
          </a>
        </template>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.schedule-block-bar__track {
  position: relative;
  height: 20px;
  border: 1px solid var(--c-hairline-soft);
  border-radius: var(--radius-chip);
  background: var(--c-chip-active-fill);
  overflow: hidden;
}

.schedule-block-bar__block {
  position: absolute;
  top: 2px;
  bottom: 2px;
  border-radius: 2px;
  font-size: var(--fs-micro);
  color: var(--c-text-body);
  padding: 0 4px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  border: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-strong);
}

.schedule-block-bar__block[data-state="inserted"] {
  border-color: var(--c-accent-hover);
  background: var(--c-chip-active-fill);
  color: var(--c-accent-hover);
}

.schedule-block-bar__block[data-state="removed"] {
  border-color: var(--ev-grudge);
  color: var(--ev-grudge);
  opacity: 0.6;
  text-decoration: line-through;
}

.schedule-block-bar__legend {
  list-style: none;
  margin: 3px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
  font-size: var(--fs-micro);
  color: var(--c-text-dim);
}

.schedule-block-bar__legend li[data-state="removed"] {
  color: var(--c-text-faint);
  text-decoration: line-through;
}

.schedule-block-bar__swatch {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 1px;
  margin-right: 3px;
  border: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-strong);
}

.schedule-block-bar__swatch[data-state="inserted"] {
  border-color: var(--c-accent-hover);
  background: var(--c-chip-active-fill);
}

.schedule-block-bar__swatch[data-state="removed"] {
  border-color: var(--ev-grudge);
  background: transparent;
}

.schedule-block-bar__cause {
  color: var(--c-text-secondary);
}

.schedule-block-bar__event-link {
  color: var(--c-accent-hover);
  font-size: var(--fs-micro);
}
</style>
