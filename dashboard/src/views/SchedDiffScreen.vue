<script setup lang="ts">
/**
 * SchedDiffScreen — the standalone multi-NPC schedule-diff comparison
 * (lane 41, ui-spec §3.8: "...and as a standalone multi-NPC comparison").
 * Chrome (RunPicker/ViewSwitcher, the combined `[run, t]` watcher for
 * `frameLog.ts`'s documented load-before-tick ordering hazard) is mirrored
 * from `RuleLogScreen.vue`/`DiffScreen.vue` verbatim.
 *
 * Data: reuses `stores/mapData.ts` (read-only, lane 14/30 precedent) for
 * `socialState.baseSchedule` (the run's immutable base schedule, hydrated
 * once from a keyframe) and `eventRecords` (the full events stream, from
 * which `derived/scheduleDiff.ts` extracts every `schedule_rewrite` --
 * see that module's header for why `eventRecords` rather than
 * `socialState.scheduleOverlays` alone). `ScheduleLanes.vue` (the same
 * component `NpcInspector.vue`'s Schedule tab renders, per the packet's
 * "two hosts, one component" pin) does the actual per-NPC diff
 * computation via `computeScheduleDiff` -- this screen only supplies
 * inputs and the NPC filter.
 */
import { computed, watch } from "vue";
import RunPicker from "../components/RunPicker.vue";
import ViewSwitcher from "../components/ViewSwitcher.vue";
import ScheduleFilterBar from "../components/scheddiff/ScheduleFilterBar.vue";
import ScheduleLanes from "../components/scheddiff/ScheduleLanes.vue";
import { useUrlState } from "../state/urlState";
import { useMapDataStore } from "../stores/mapData";
import { computeScheduleDiff, type ScheduleDiffFilters } from "../derived/scheduleDiff";

const urlState = useUrlState();
const mapData = useMapDataStore();

// Single combined [run, t] watcher (same idiom as RuleLogScreen.vue/
// DiffScreen.vue): loading the run always finishes before a tick
// decision is made against it.
watch(
  [urlState.run, urlState.t],
  async ([runId, t], oldValue) => {
    const oldRunId = oldValue?.[0];
    if (runId !== oldRunId || oldValue === undefined) {
      await mapData.load(runId);
    }
    if (t === null) {
      await mapData.dockToLatest();
    } else {
      await mapData.setTick(t);
    }
  },
  { immediate: true },
);

const hasLoadedRun = computed(() => mapData.status === "loaded");
const atTick = computed(() => mapData.socialState.tick);

const allDiffs = computed(() =>
  hasLoadedRun.value ? computeScheduleDiff(mapData.socialState.baseSchedule, mapData.eventRecords, atTick.value) : [],
);

const activeFilters = computed<ScheduleDiffFilters>(() => ({
  npc: urlState.filters.value.npc,
}));

function onFiltersUpdate(next: ScheduleDiffFilters) {
  const merged = { ...urlState.filters.value };
  if (next.npc === undefined || next.npc === "") {
    delete merged.npc;
  } else {
    merged.npc = next.npc;
  }
  urlState.filters.value = merged;
}
</script>

<template>
  <div class="sched-diff-screen">
    <header class="sched-diff-screen__chrome">
      <div class="sched-diff-screen__wordmark">CHRONICLE</div>
      <RunPicker v-model="urlState.run.value" />
      <span class="sched-diff-screen__meta">as-of t={{ atTick }}</span>
      <div class="sched-diff-screen__spacer" />
      <ViewSwitcher current="scheddiff" />
    </header>

    <ScheduleFilterBar :diffs="allDiffs" :filters="activeFilters" @update:filters="onFiltersUpdate" />

    <div v-if="!hasLoadedRun" class="sched-diff-screen__placeholder">no run loaded</div>
    <div v-else class="sched-diff-screen__body">
      <ScheduleLanes
        :base-schedule="mapData.socialState.baseSchedule"
        :event-records="mapData.eventRecords"
        :tick="atTick"
        :run-id="urlState.run.value"
        :filters="activeFilters"
      />
    </div>

    <footer class="sched-diff-screen__footer">
      <span class="sched-diff-screen__count">{{ allDiffs.length }} NPC{{ allDiffs.length === 1 ? "" : "s" }}</span>
    </footer>
  </div>
</template>

<style scoped>
.sched-diff-screen {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--c-page-bg);
  overflow: hidden;
  font-size: var(--fs-body);
}

.sched-diff-screen__chrome {
  height: 44px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 16px;
  border-bottom: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-strong);
}

.sched-diff-screen__wordmark {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.3em;
  color: var(--c-accent-hover);
}

.sched-diff-screen__meta {
  color: var(--c-text-dim);
  white-space: nowrap;
  font-size: var(--fs-secondary);
}

.sched-diff-screen__spacer {
  flex: 1;
}

.sched-diff-screen__placeholder {
  padding: 24px;
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}

.sched-diff-screen__body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 16px;
}

.sched-diff-screen__footer {
  flex: none;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 16px;
  border-top: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-inspector);
  font-size: var(--fs-secondary);
  color: var(--c-text-dim);
}
</style>
