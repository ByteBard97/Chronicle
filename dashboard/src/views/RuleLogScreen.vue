<script setup lang="ts">
/**
 * RuleLogScreen -- the rule-firing log (ui-spec §3.7 second half, lane
 * 31): every registry evaluation, activations with inputs *and*
 * evaluated-but-not-fired rows with their current accumulator values, a
 * fire-frequency histogram at top (the fires-too-often detector), and a
 * rule filter that is also lane 30's rule-chip deep-link target
 * (`/rules?filters={"rule":"<name>"}`). The companion to `DiffScreen.vue`
 * (lane 30, "what changed") -- this screen answers "what did the rules
 * *do*". Chrome (RunPicker/ViewSwitcher, the combined `[run, t]` watcher
 * for `frameLog.ts`'s documented load-before-tick ordering hazard) is
 * mirrored from `DiffScreen.vue` verbatim.
 *
 * Data: reuses `stores/mapData.ts` (read-only, lane 14/30's precedent)
 * for its full-range `traceRecords` -- the same "own store" freedom the
 * packet leaves open ("A new Pinia store if you judge one is needed...
 * your call on structure") is exercised here by *not* building one:
 * `mapData` already owns exactly the trace-stream load + live-tail this
 * screen needs (feed.ts's own pagination idiom, already wired), so a
 * second store duplicating that fetch would only be more code for the
 * same data. `derived/ruleLog.ts` filters the shared `traceRecords` to
 * `rule_evaluated` and maps/buckets them; this screen never touches
 * `mapData.socialState`.
 *
 * Run-id note (the other half of lane 30's rule-chip contract, FINDING
 * for the dispatcher): `DiffRow.vue`'s rule-chip href is
 * `/rules?filters={"rule":...}` -- deliberately `run`-less (that link
 * itself is lane 30's file, out of this lane's boundary). A plain
 * `<a href>` click is a full page navigation (same reasoning
 * `ViewSwitcher.vue`'s own doc gives for using plain anchors), so it
 * destroys every bit of Pinia state, `run` included -- this screen then
 * has no way to recover which run the user came from. An earlier
 * revision of this file guessed `runsStore.mostRecentRunId` as a
 * fallback; a live-browser check caught that this actively lies when
 * more than one run is registered (it silently loaded a *different*
 * run and rendered a confident "0 of N evaluations" for the clicked
 * rule, instead of admitting no run context survived the navigation).
 * Reverted: this screen reads `urlState.run` only, exactly like
 * `DiffScreen.vue`, and shows the same honest "no run loaded"
 * placeholder any other view would. The real fix (carrying `run`
 * forward in `DiffRow.vue`'s `ruleHref`) is a one-line change in a file
 * this lane cannot touch -- filed for the coordinator.
 */
import { computed, watch } from "vue";
import RunPicker from "../components/RunPicker.vue";
import ViewSwitcher from "../components/ViewSwitcher.vue";
import RuleFilterBar from "../components/rulelog/RuleFilterBar.vue";
import RuleHistogram from "../components/rulelog/RuleHistogram.vue";
import RuleLogTable from "../components/rulelog/RuleLogTable.vue";
import { useUrlState } from "../state/urlState";
import { useMapDataStore } from "../stores/mapData";
import { computeRuleHistogram, filterRuleLogRows, mapTraceRecordsToRuleLogRows, type RuleLogFilters } from "../derived/ruleLog";

const urlState = useUrlState();
const mapData = useMapDataStore();

// Single combined [run, t] watcher (same idiom as DiffScreen.vue/
// MapScreen.vue/VariantTreeScreen.vue): loading the run always finishes
// before a tick decision is made against it.
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

const allRows = computed(() => (hasLoadedRun.value ? mapTraceRecordsToRuleLogRows(mapData.traceRecords) : []));

const histogram = computed(() => computeRuleHistogram(allRows.value));

const activeFilters = computed<RuleLogFilters>(() => ({
  rule: urlState.filters.value.rule,
}));

const filteredRows = computed(() => filterRuleLogRows(allRows.value, activeFilters.value));

function setRuleFilter(rule: string | null) {
  const next = { ...urlState.filters.value };
  if (rule === null || rule === "") {
    delete next.rule;
  } else {
    next.rule = rule;
  }
  urlState.filters.value = next;
}

function onFiltersUpdate(next: RuleLogFilters) {
  setRuleFilter(next.rule ?? null);
}
</script>

<template>
  <div class="rule-log-screen">
    <header class="rule-log-screen__chrome">
      <div class="rule-log-screen__wordmark">CHRONICLE</div>
      <RunPicker v-model="urlState.run.value" />
      <div class="rule-log-screen__spacer" />
      <ViewSwitcher current="rules" />
    </header>

    <RuleHistogram :buckets="histogram" :active-rule="activeFilters.rule" @select-rule="setRuleFilter" />
    <RuleFilterBar :rows="allRows" :filters="activeFilters" @update:filters="onFiltersUpdate" />

    <div v-if="!hasLoadedRun" class="rule-log-screen__placeholder">no run loaded</div>
    <RuleLogTable v-else :rows="filteredRows" />

    <footer class="rule-log-screen__footer">
      <span class="rule-log-screen__count">{{ filteredRows.length }} of {{ allRows.length }} evaluations</span>
    </footer>
  </div>
</template>

<style scoped>
.rule-log-screen {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--c-page-bg);
  overflow: hidden;
  font-size: var(--fs-body);
}

.rule-log-screen__chrome {
  height: 44px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 16px;
  border-bottom: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-strong);
}

.rule-log-screen__wordmark {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.3em;
  color: var(--c-accent-hover);
}

.rule-log-screen__spacer {
  flex: 1;
}

.rule-log-screen__placeholder {
  padding: 24px;
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}

.rule-log-screen__footer {
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
