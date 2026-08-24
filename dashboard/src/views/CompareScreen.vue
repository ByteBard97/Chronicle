<script setup lang="ts">
/**
 * CompareScreen — the M5 run-comparison tool (ui-spec §3.9, lane 38): two
 * runs sharing a `seed_id` but differing fixture/config, aligned scrubbers
 * (both panes share `urlState.t`), and — per the spec's v1.1 strengthening
 * — the ranked divergence list as the PRIMARY rendering, with the aligned
 * map panes as secondary context/selection-target beneath the fold, not
 * the other way around. Chrome mirrors DiffScreen.vue/RuleLogScreen.vue
 * (lane 30/31's established M5-era idiom): RunPicker + ViewSwitcher header,
 * a combined watcher for the load-before-tick ordering hazard.
 *
 * Run B rides the already-existing `runB`/`alignment` URL keys (ui-spec
 * §1.2, `state/urlState.ts`) — no new query keys, per the packet. `alignment`
 * itself is reserved by the frozen contract but this lane's v1 only
 * implements one alignment mode (both panes share the same tick T
 * unconditionally) — read, not written; a future lane can use it to add
 * e.g. "align by claim-stage" without touching the URL contract.
 *
 * The two-run state problem (packet-pinned, mirroring lane 30's own
 * two-tick problem): `stores/mapData.ts` can only hold ONE run's state.
 * Run A rides that store as usual (read-only reuse, same as DiffScreen.vue/
 * RuleLogScreen.vue); run B gets its own independent, read-only load path
 * (`components/compare/useSecondRunLoad.ts`), and BOTH runs' `SocialState`
 * at T are reconstructed directly via `log/reconstruct.ts`'s `replayTo` —
 * this screen never tries to push a second run through `mapData`.
 */
import { computed, ref, watch } from "vue";
import RunPicker from "../components/RunPicker.vue";
import ViewSwitcher from "../components/ViewSwitcher.vue";
import DivergenceList from "../components/compare/DivergenceList.vue";
import DeltaTable from "../components/compare/DeltaTable.vue";
import ComparePane from "../components/compare/ComparePane.vue";
import { useSecondRunLoad } from "../components/compare/useSecondRunLoad";
import { useUrlState } from "../state/urlState";
import { useMapDataStore } from "../stores/mapData";
import { computeDivergenceList, findFirstDivergentRoll } from "../derived/runCompare";
import { emptySocialState, replayTo } from "../log/reconstruct";
import { deriveMapMarkers, firstClaimId } from "../derived/mapMarkers";
import mapJson from "../../map/whiterun_map.json";

const urlState = useUrlState();
const mapData = useMapDataStore(); // run A
const secondRun = useSecondRunLoad(); // run B

// Combined [run, runB, t] watcher (frameLog.ts's documented load-before-tick
// ordering hazard, same idiom as DiffScreen.vue/RuleLogScreen.vue, extended
// to a second run id): both loads always finish before a tick decision is
// made against either of them.
watch(
  [urlState.run, urlState.runB, urlState.t],
  async ([runId, runBId, t], oldValue) => {
    const [oldRunId, oldRunBId] = oldValue ?? [undefined, undefined];
    const isFirstRun = oldValue === undefined;
    if (isFirstRun || runId !== oldRunId) await mapData.load(runId);
    if (isFirstRun || runBId !== oldRunBId) await secondRun.load(runBId);
    if (t === null) {
      await mapData.dockToLatest();
    } else {
      await mapData.setTick(t);
    }
  },
  { immediate: true },
);

const hasRunA = computed(() => mapData.status === "loaded");
const hasRunB = computed(() => secondRun.status.value === "loaded");
const hasBoth = computed(() => hasRunA.value && hasRunB.value);

/** Shared playhead: the explicit URL tick, or run A's docked "latest known" tick. */
const atTick = computed(() => urlState.t.value ?? mapData.socialState.tick);

const allRecordsA = computed(() => [...mapData.eventRecords, ...mapData.traceRecords]);
const allRecordsB = computed(() => [...secondRun.eventRecords.value, ...secondRun.traceRecords.value]);

const divergenceList = computed(() =>
  hasBoth.value ? computeDivergenceList(allRecordsA.value, allRecordsB.value, atTick.value) : [],
);

const firstDivergentRoll = computed(() =>
  hasBoth.value ? findFirstDivergentRoll(allRecordsA.value, allRecordsB.value) : null,
);

const selectedNpcId = ref<string | null>(null);

const selectedEntry = computed(
  () => divergenceList.value.find((e) => e.npcId === selectedNpcId.value) ?? null,
);

function onSelectEntry(npcId: string) {
  selectedNpcId.value = npcId;
}

function onFindFirstDivergence() {
  const roll = firstDivergentRoll.value;
  if (roll === null) return;
  urlState.t.value = roll.tick; // jumps BOTH playheads: they share this one ref.
}

// Run B's state at T, reconstructed directly (see module header) — mirrors
// `derived/socialDiff.ts`'s own "own the second replay yourself" idiom.
const stateB = computed(() =>
  hasRunB.value
    ? replayTo(emptySocialState(-1), allRecordsB.value.filter((r) => r.tick <= atTick.value), atTick.value)
    : emptySocialState(-1),
);

const markersA = computed(() =>
  hasRunA.value
    ? deriveMapMarkers({
        state: mapData.socialState,
        traceRecords: mapData.traceRecords,
        eventRecords: mapData.eventRecords,
        mapJson,
        claimId: firstClaimId(mapData.socialState) ?? "",
        atTick: atTick.value,
        isSelected: (id) => id === selectedNpcId.value,
      })
    : [],
);

const markersB = computed(() =>
  hasRunB.value
    ? deriveMapMarkers({
        state: stateB.value,
        traceRecords: secondRun.traceRecords.value,
        eventRecords: secondRun.eventRecords.value,
        mapJson,
        claimId: firstClaimId(stateB.value) ?? "",
        atTick: atTick.value,
        isSelected: (id) => id === selectedNpcId.value,
      })
    : [],
);

function onPaneSelect(id: string) {
  selectedNpcId.value = id;
}
</script>

<template>
  <div class="compare-screen">
    <header class="compare-screen__chrome">
      <div class="compare-screen__wordmark">CHRONICLE</div>
      <span class="compare-screen__run-label">A</span>
      <RunPicker v-model="urlState.run.value" />
      <span class="compare-screen__run-label">B</span>
      <RunPicker v-model="urlState.runB.value" />
      <label class="compare-screen__tick">
        T
        <input
          class="compare-screen__tick-input"
          type="number"
          min="0"
          :value="urlState.t.value ?? ''"
          placeholder="live"
          @change="urlState.t.value = ($event.target as HTMLInputElement).value === '' ? null : Number(($event.target as HTMLInputElement).value)"
        />
      </label>
      <button
        type="button"
        class="compare-screen__find-btn"
        :disabled="firstDivergentRoll === null"
        @click="onFindFirstDivergence"
      >
        find first divergence
      </button>
      <span v-if="firstDivergentRoll !== null" class="compare-screen__meta">
        first divergent roll: t {{ firstDivergentRoll.tick }} · {{ firstDivergentRoll.locationId }} ·
        {{ firstDivergentRoll.participants.join(" / ") }}
      </span>
      <div class="compare-screen__spacer" />
      <ViewSwitcher current="compare" />
    </header>

    <div v-if="!hasBoth" class="compare-screen__placeholder">
      pick two runs sharing a seed_id to compare (run A and run B above)
    </div>

    <template v-else>
      <section class="compare-screen__primary">
        <DivergenceList :entries="divergenceList" :selected-npc-id="selectedNpcId" @select="onSelectEntry" />
        <DeltaTable :npc-id="selectedNpcId" :rows="selectedEntry?.deltas ?? []" />
      </section>

      <section class="compare-screen__panes">
        <ComparePane
          label="run A"
          :tick="atTick"
          :markers="markersA"
          :has-run="hasRunA"
          @select="onPaneSelect"
        />
        <ComparePane
          label="run B"
          :tick="atTick"
          :markers="markersB"
          :has-run="hasRunB"
          @select="onPaneSelect"
        />
      </section>
    </template>

    <footer class="compare-screen__footer">
      <span class="compare-screen__count">{{ divergenceList.length }} divergent entities at t {{ atTick }}</span>
    </footer>
  </div>
</template>

<style scoped>
.compare-screen {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--c-page-bg);
  overflow: hidden;
  font-size: var(--fs-body);
}

.compare-screen__chrome {
  height: 44px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-strong);
}

.compare-screen__wordmark {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.3em;
  color: var(--c-accent-hover);
}

.compare-screen__run-label {
  color: var(--c-text-faint);
  font-size: var(--fs-micro);
  text-transform: uppercase;
}

.compare-screen__tick {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--c-text-dim);
  font-size: var(--fs-secondary);
  white-space: nowrap;
}

.compare-screen__tick-input {
  width: 64px;
  background: transparent;
  border: 1px solid var(--c-hairline);
  border-radius: var(--radius-chip);
  color: var(--c-text-body);
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  padding: 2px 6px;
}

.compare-screen__find-btn {
  appearance: none;
  border: 1px solid var(--c-chip-active-border);
  background: var(--c-chip-active-fill);
  color: var(--c-accent-hover);
  border-radius: var(--radius-chip);
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  padding: 3px 10px;
  cursor: pointer;
  white-space: nowrap;
}

.compare-screen__find-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.compare-screen__meta {
  color: var(--c-text-dim);
  font-size: var(--fs-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.compare-screen__spacer {
  flex: 1;
}

.compare-screen__placeholder {
  padding: 24px;
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}

.compare-screen__primary {
  flex: 1 1 55%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border-bottom: 1px solid var(--c-hairline);
}

.compare-screen__panes {
  flex: 1 1 45%;
  min-height: 220px;
  display: flex;
  gap: 1px;
  background: var(--c-hairline);
}

.compare-screen__footer {
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
