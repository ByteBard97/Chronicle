<script setup lang="ts">
/**
 * MapScreen — the full approved-mockup page (design/map-c-skyrim.dc.html):
 * 44px top chrome strip + MapView (map well + inspector) + the 98px
 * timeline footer.
 *
 * Lane 14: wires real per-tick state from `stores/mapData.ts` in place of
 * the mock fixture (TimelineBar stays fixture-driven this lane, per the
 * packet's scope line). Mirrors `FeedScreen.vue`'s idiom: `useUrlState()`,
 * `useSelectionUrlSync()` installed once, RunPicker retrofitted to
 * `v-model`, real chrome (run id / seed / branch replaced by what the
 * loaded run's registry entry + reconstructed claim actually carry).
 *
 * The `[run, t]` watch is combined into one handler (not two independent
 * watchers), per `frameLog.ts`'s documented ordering hazard: loading the
 * run must finish before deciding what the current tick means, or a
 * docked-tick decision can race the run load and silently no-op forever.
 */
import { computed, watch } from "vue";
import { useRoute } from "vue-router";
import RunPicker from "../components/RunPicker.vue";
import SalienceSwitch from "../components/SalienceSwitch.vue";
import ViewSwitcher from "../components/ViewSwitcher.vue";
import NpcInspector from "../components/NpcInspector.vue";
import PanelGlass from "../components/PanelGlass.vue";
import MapView from "./MapView.vue";
import TimelineBar from "../components/timeline/TimelineBar.vue";
import { useSalienceStore } from "../stores/salience";
import { useUrlState } from "../state/urlState";
import { useSelectionUrlSync } from "../state/useSelectionUrlSync";
import { useSelectionStore } from "../stores/selection";
import { useMapDataStore } from "../stores/mapData";
import { deriveMapMarkers, claimStageBreakdown, enumerateCast, firstClaimId } from "../derived/mapMarkers";
import mapJson from "../../map/whiterun_map.json";

const salience = useSalienceStore();
const route = useRoute();
const urlState = useUrlState();
const selection = useSelectionStore();
const mapData = useMapDataStore();

useSelectionUrlSync();

// Single combined [run, t] watcher (frameLog.ts:20-27's documented hazard):
// loading the run always finishes before a tick decision is made against it.
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

const atTick = computed(() => mapData.socialState.tick);
const cast = computed(() => enumerateCast(mapData.socialState, mapData.traceRecords, mapData.eventRecords));
// Internal claim id used to derive markers/breakdown; "" is a safe no-op
// input to those pure functions when no run/claim is loaded yet.
const activeClaimId = computed(() => firstClaimId(mapData.socialState) ?? "");
const hasLoadedRun = computed(() => mapData.status === "loaded");

const markers = computed(() =>
  deriveMapMarkers({
    state: mapData.socialState,
    traceRecords: mapData.traceRecords,
    eventRecords: mapData.eventRecords,
    mapJson,
    claimId: activeClaimId.value,
    atTick: atTick.value,
    isSelected: (id) => selection.isSelected(id),
  }),
);

const breakdown = computed(() => claimStageBreakdown(mapData.socialState, cast.value, activeClaimId.value, atTick.value));

// Props threaded down to MapView/StageLegend: `undefined` (not "") when no
// run is loaded, so `withDefaults` falls back to StageLegend's own
// fixture-backed defaults instead of rendering a blank "" STAGE / 0/0 --
// `withDefaults` only substitutes on `undefined`, never on a falsy-but-set
// value like "".
const claimIdProp = computed(() => (hasLoadedRun.value ? activeClaimId.value : undefined));
const coverageProp = computed(() => (hasLoadedRun.value ? breakdown.value.coverage : undefined));
const countsProp = computed(() => (hasLoadedRun.value ? breakdown.value.counts : undefined));

// Schema v1 has no carrier records at all (the mock's Markarth/Ri'saad
// story has no real counterpart) -- always hidden once real data is wired.
const hasCarrier = computed(() => false);

function onSelect(id: string) {
  selection.select(id);
}

const selectedId = computed(() => selection.selectedIds[0] ?? null);
</script>

<template>
  <div class="map-screen">
    <header class="map-screen__chrome">
      <div class="map-screen__wordmark">CHRONICLE</div>
      <div class="map-screen__runmeta">
        <RunPicker v-model="urlState.run.value" />
        <span v-if="urlState.run.value" class="map-screen__meta">t {{ atTick }}</span>
        <span v-if="activeClaimId" class="map-screen__meta">{{ activeClaimId }}</span>
      </div>
      <div class="map-screen__spacer" />
      <SalienceSwitch
        :mode="salience.level"
        @update:mode="salience.setLevel($event)"
      />
      <ViewSwitcher current="map" />
      <span class="map-screen__url">{{ route.fullPath }}</span>
    </header>

    <div class="map-screen__body">
      <MapView
        :markers="markers"
        :claim-id="claimIdProp"
        :coverage="coverageProp"
        :counts="countsProp"
        :has-carrier="hasCarrier"
        @select="onSelect"
      >
        <template #inspector>
          <PanelGlass v-if="selectedId === null" tone="inspector" class="map-screen__inspector-empty">
            click a marker to select an NPC
          </PanelGlass>
          <NpcInspector
            v-else
            :npc-name="selectedId"
            :as-of-tick="atTick ?? undefined"
            :salience="salience.level"
          />
        </template>
      </MapView>
    </div>

    <TimelineBar />
  </div>
</template>

<style scoped>
.map-screen {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--c-page-bg);
  overflow: hidden;
}

/* 44px chrome strip — map-c-skyrim.dc.html:19 */
.map-screen__chrome {
  height: 44px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 16px;
  border-bottom: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-strong);
}

.map-screen__wordmark {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.3em;
  color: var(--c-accent-hover);
}

.map-screen__runmeta {
  display: flex;
  gap: 8px;
  align-items: center;
  flex: none;
}

.map-screen__meta {
  color: var(--c-text-dim);
  white-space: nowrap;
}

.map-screen__spacer {
  flex: 1;
}

.map-screen__url {
  color: var(--c-text-faint);
  font-size: 10px;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.map-screen__body {
  flex: 1;
  min-height: 0;
  display: flex;
}

.map-screen__inspector-empty {
  margin: 8px;
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}
</style>
