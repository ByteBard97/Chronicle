<script setup lang="ts">
/**
 * ScheduleLanes — the shared before/after schedule-diff renderer (lane 41,
 * ui-spec §3.8): "Before/after lanes per NPC, inserted/removed blocks
 * highlighted, causing rule and event linked." Both hosts render this same
 * component (the packet's "two hosts, one component" pin): the inspector's
 * Schedule tab (`NpcInspector.vue`, one NPC, `npcIds` passed as a
 * one-element list) and the standalone `/scheddiff` route
 * (`SchedDiffScreen.vue`, multi-NPC, filterable). Neither host computes
 * presence itself -- both pass `baseSchedule`/`eventRecords`/`tick` straight
 * through to `derived/scheduleDiff.ts`'s `computeScheduleDiff`, the one
 * place that logic lives.
 */
import { computed } from "vue";
import ScheduleLaneRow from "./ScheduleLaneRow.vue";
import { computeScheduleDiff, filterScheduleDiffs, type ScheduleDiffFilters } from "../../derived/scheduleDiff";
import type { FrameRecord, KeyframeScheduleBlock } from "../../log/types";

const props = defineProps<{
  baseSchedule: KeyframeScheduleBlock[];
  eventRecords: FrameRecord[];
  tick: number;
  runId: string | null;
  npcIds?: string[];
  filters?: ScheduleDiffFilters;
}>();

const allDiffs = computed(() => computeScheduleDiff(props.baseSchedule, props.eventRecords, props.tick, props.npcIds));
const diffs = computed(() => filterScheduleDiffs(allDiffs.value, props.filters ?? {}));

const maxTick = computed(() => {
  const ticks = allDiffs.value.flatMap((d) => [...d.before, ...d.after].map((b) => b.endTick));
  return ticks.length > 0 ? Math.max(...ticks) : Math.max(props.tick, 1);
});
</script>

<template>
  <div class="schedule-lanes">
    <div v-if="diffs.length === 0" class="schedule-lanes__placeholder">no schedule data (as of t={{ tick }})</div>
    <template v-else>
      <ScheduleLaneRow v-for="d in diffs" :key="d.npcId" :diff="d" :max-tick="maxTick" :run-id="runId" />
    </template>
  </div>
</template>

<style scoped>
.schedule-lanes {
  display: flex;
  flex-direction: column;
}

.schedule-lanes__placeholder {
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
  padding: 8px 0;
}
</style>
