<script setup lang="ts">
/**
 * DiffScreen — the two-tick social-state diff panel (ui-spec §3.7 first
 * half, lane 30): T1 (playhead)/T2 (default one game-day earlier, ADR-0010)
 * controls, every social-state delta with a signed Δ, a best-effort
 * firing-rule chip, and a triggering-event link, filterable by NPC/rule/
 * type. Chrome mirrors MapScreen/FeedScreen/VariantTreeScreen's (RunPicker,
 * ViewSwitcher, the combined `[run, t]` watcher for `frameLog.ts`'s
 * documented load-before-tick ordering hazard).
 *
 * Data: reuses `stores/mapData.ts` (read-only, lane 14) purely for its
 * full-range `eventRecords`/`traceRecords` (loaded once by `load()`,
 * kept live-updated by `dockToLatest()`'s tail when docked) -- this
 * screen never reads `mapData.socialState` itself. Per the packet's
 * pinned "two-tick state problem": the store's own `setTick`/`socialState`
 * can only ever hold ONE reconstructed state at a time, so both T1 and T2
 * states are reconstructed independently, here, via
 * `derived/socialDiff.ts`'s `computeSocialDiff` -- not through the store.
 * `setTick`/`dockToLatest` are still called (for their side effect of
 * keeping `traceRecords`/`eventRecords` current and settling
 * `mapData.socialState.tick` to "the latest known tick" while live), but
 * this screen's own `socialState` field is intentionally unused.
 *
 * T1/T2 URL-state placement (packet: "T2 is view-local or in `filters` --
 * pick one and note it"): T1 is the existing `urlState.t` (shared with
 * every other view, ui-spec §1.2). T2 has no dedicated query key in the
 * frozen `state/urlState.ts` schema, and adding one is out of this lane's
 * file boundary (edit list is `router/index.ts`/`ViewSwitcher.vue` only)
 * -- so T2 lives in `urlState.filters.t2` alongside this view's own
 * npc/rule/type filter keys (`filtersCodec` already round-trips arbitrary
 * string keys with zero codec changes). Choosing `filters` over "purely
 * view-local" means a T2 override *is* deep-linkable
 * (`?view=diff&t=47&filters={"t2":"10"}`), which matches the panel's
 * "both editable" requirement better than a value that resets on reload.
 */
import { computed, watch } from "vue";
import RunPicker from "../components/RunPicker.vue";
import ViewSwitcher from "../components/ViewSwitcher.vue";
import DiffFilterBar from "../components/diff/DiffFilterBar.vue";
import DiffTable from "../components/diff/DiffTable.vue";
import { useUrlState } from "../state/urlState";
import { useMapDataStore } from "../stores/mapData";
import { computeSocialDiff, filterDiffRows, type SocialDiffFilters } from "../derived/socialDiff";

const urlState = useUrlState();
const mapData = useMapDataStore();

// Single combined [run, t] watcher (frameLog.ts's documented ordering
// hazard, same idiom as MapScreen.vue/VariantTreeScreen.vue): loading the
// run always finishes before a tick decision is made against it.
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

const ONE_GAME_DAY = 24; // ADR-0010's tick quantum: 1 tick = 1 gamets = 1 game-hour.

const t1 = computed(() => urlState.t.value ?? mapData.socialState.tick);

const t2Override = computed<number | null>(() => {
  const raw = urlState.filters.value.t2;
  if (raw === undefined) return null;
  const n = Number(raw);
  return Number.isInteger(n) && n >= 0 ? n : null;
});

const t2 = computed(() => t2Override.value ?? Math.max(0, t1.value - ONE_GAME_DAY));

const allRecords = computed(() => [...mapData.eventRecords, ...mapData.traceRecords]);

const hasLoadedRun = computed(() => mapData.status === "loaded");

const allRows = computed(() => (hasLoadedRun.value ? computeSocialDiff(allRecords.value, t1.value, t2.value) : []));

const activeFilters = computed<SocialDiffFilters>(() => ({
  npc: urlState.filters.value.npc,
  rule: urlState.filters.value.rule,
  type: urlState.filters.value.type,
}));

const filteredRows = computed(() => filterDiffRows(allRows.value, activeFilters.value));

function onT1Input(event: Event) {
  const raw = (event.target as HTMLInputElement).value;
  if (raw === "") {
    urlState.t.value = null;
    return;
  }
  const n = Number(raw);
  urlState.t.value = Number.isInteger(n) && n >= 0 ? n : null;
}

function onT2Input(event: Event) {
  const raw = (event.target as HTMLInputElement).value;
  const next = { ...urlState.filters.value };
  if (raw === "") {
    delete next.t2;
  } else {
    const n = Number(raw);
    if (Number.isInteger(n) && n >= 0) {
      next.t2 = String(n);
    } else {
      delete next.t2;
    }
  }
  urlState.filters.value = next;
}

function onFiltersUpdate(next: SocialDiffFilters) {
  const merged: Record<string, string> = { ...urlState.filters.value };
  for (const key of ["npc", "rule", "type"] as const) {
    const value = next[key];
    if (value === undefined || value === "") {
      delete merged[key];
    } else {
      merged[key] = value;
    }
  }
  urlState.filters.value = merged;
}
</script>

<template>
  <div class="diff-screen">
    <header class="diff-screen__chrome">
      <div class="diff-screen__wordmark">CHRONICLE</div>
      <RunPicker v-model="urlState.run.value" />
      <label class="diff-screen__tick">
        T1
        <input
          class="diff-screen__tick-input"
          type="number"
          min="0"
          :value="urlState.t.value ?? ''"
          placeholder="live"
          @change="onT1Input"
        />
      </label>
      <label class="diff-screen__tick">
        T2
        <input
          class="diff-screen__tick-input"
          type="number"
          min="0"
          :value="t2Override ?? t2"
          @change="onT2Input"
        />
      </label>
      <span class="diff-screen__meta">as-of {{ t1 }} vs {{ t2 }}</span>
      <div class="diff-screen__spacer" />
      <ViewSwitcher current="diff" />
    </header>

    <DiffFilterBar :rows="allRows" :filters="activeFilters" @update:filters="onFiltersUpdate" />

    <div v-if="!hasLoadedRun" class="diff-screen__placeholder">no run loaded</div>
    <DiffTable v-else :rows="filteredRows" :run-id="urlState.run.value" />

    <footer class="diff-screen__footer">
      <span class="diff-screen__count">{{ filteredRows.length }} of {{ allRows.length }} deltas</span>
    </footer>
  </div>
</template>

<style scoped>
.diff-screen {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--c-page-bg);
  overflow: hidden;
  font-size: var(--fs-body);
}

.diff-screen__chrome {
  height: 44px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 16px;
  border-bottom: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-strong);
}

.diff-screen__wordmark {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.3em;
  color: var(--c-accent-hover);
}

.diff-screen__tick {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--c-text-dim);
  font-size: var(--fs-secondary);
  white-space: nowrap;
}

.diff-screen__tick-input {
  width: 64px;
  background: transparent;
  border: 1px solid var(--c-hairline);
  border-radius: var(--radius-chip);
  color: var(--c-text-body);
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  padding: 2px 6px;
}

.diff-screen__meta {
  color: var(--c-text-dim);
  white-space: nowrap;
  font-size: var(--fs-secondary);
}

.diff-screen__spacer {
  flex: 1;
}

.diff-screen__placeholder {
  padding: 24px;
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}

.diff-screen__footer {
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
