<script setup lang="ts">
/**
 * ScheduleLaneRow — one NPC's before/after schedule lanes (lane 41,
 * ui-spec §3.8), built from `derived/scheduleDiff.ts`'s `NpcScheduleDiff`.
 * Converts that pure model's `before`/`after`/`removed` lists into the
 * `ScheduleBarBlock[]` (before) and `ScheduleBarBlock[]` (after)
 * `ScheduleBlockBar.vue` renders -- `removed` marks blocks present in
 * `before` but pushed out of `after` by an active overlay; `inserted`
 * marks the overlay block itself in `after`, carrying its causal link.
 */
import { computed } from "vue";
import ScheduleBlockBar from "./ScheduleBlockBar.vue";
import type { NpcScheduleDiff } from "../../derived/scheduleDiff";
import type { ScheduleBarBlock } from "./scheduleBarBlock";

const props = defineProps<{
  diff: NpcScheduleDiff;
  maxTick: number;
  runId: string | null;
}>();

const removedKey = (b: { locationId: string; startTick: number; endTick: number }) => `${b.locationId}|${b.startTick}|${b.endTick}`;

const beforeBlocks = computed<ScheduleBarBlock[]>(() => {
  const removed = new Set(props.diff.removed.map(removedKey));
  return props.diff.before.map((b) => ({
    locationId: b.locationId,
    startTick: b.startTick,
    endTick: b.endTick,
    state: removed.has(removedKey(b)) ? "removed" : "unchanged",
  }));
});

const afterBlocks = computed<ScheduleBarBlock[]>(() =>
  props.diff.after.map((b) => {
    const isOverlay = "cause" in b;
    return {
      locationId: b.locationId,
      startTick: b.startTick,
      endTick: b.endTick,
      state: isOverlay ? "inserted" : "unchanged",
      overlay: isOverlay
        ? { cause: b.cause, rule: b.rule, recordTick: b.recordTick, triggerEventKey: b.triggerEventKey }
        : undefined,
    };
  }),
);
</script>

<template>
  <div class="schedule-lane-row" :class="{ 'schedule-lane-row--overridden': diff.overridden }">
    <div class="schedule-lane-row__npc">{{ diff.npcId }}</div>
    <div class="schedule-lane-row__lanes">
      <div class="schedule-lane-row__lane">
        <div class="schedule-lane-row__lane-label">before</div>
        <ScheduleBlockBar :blocks="beforeBlocks" :max-tick="maxTick" :run-id="runId" />
      </div>
      <div class="schedule-lane-row__lane">
        <div class="schedule-lane-row__lane-label">after</div>
        <ScheduleBlockBar :blocks="afterBlocks" :max-tick="maxTick" :run-id="runId" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.schedule-lane-row {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--c-hairline-soft);
}

.schedule-lane-row__npc {
  flex: none;
  width: 84px;
  font-family: var(--font-display);
  font-size: var(--fs-body);
  color: var(--c-text-primary);
  padding-top: 2px;
}

.schedule-lane-row--overridden .schedule-lane-row__npc {
  color: var(--c-accent-hover);
}

.schedule-lane-row__lanes {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.schedule-lane-row__lane-label {
  font-size: var(--fs-micro);
  color: var(--c-text-faint);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 2px;
}
</style>
