<script setup lang="ts">
/**
 * VariantTreeScreen — the last unbuilt M3 view (ui-spec §3.5): one tree
 * per claim, hand-rolled SVG, fixed generational layout, supersession
 * cross-links as dashed edges, node click -> holder table, a claim
 * dropdown, and a first-appearance/holder-count recolor toggle. Chrome
 * mirrors MapScreen/FeedScreen's (RunPicker v-model, ViewSwitcher, same
 * combined `[run, t]` watcher pattern for `frameLog.ts`'s documented
 * ordering hazard).
 *
 * Data: reuses `stores/mapData.ts` (read-only, lane 14's already-landed
 * run/state-at-T store) rather than building a third data path -- the
 * store's `socialState`/`traceRecords` are exactly what
 * `derived/variantTree.ts` needs (claims/variants/beliefs already at T,
 * plus the raw trace stream for `mutation_applied`/`supersession`). The
 * router only ever mounts one of `/`, `/map`, `/feed`, `/tree` at a time,
 * so sharing this Pinia singleton across a fourth screen is the same
 * pattern lane 16 already relied on for the timeline.
 *
 * Claim selection and node selection are view-local UI state, NOT URL
 * state -- ui-spec §1.2's frozen query-key set (`state/urlState.ts`) has
 * no `claim`/`node` key, and this is the tree's own intrinsic picker
 * (distinct from the deferred map claim-picker), not a value other views
 * need to read back. `activeClaimId` re-derives from `SocialState.claims`
 * on every change (a computed, not a one-time default + stale ref) so a
 * run switch that drops the previously-selected claim id falls back to
 * the new run's first claim instead of rendering an empty tree forever.
 */
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import RunPicker from "../components/RunPicker.vue";
import ViewSwitcher from "../components/ViewSwitcher.vue";
import PanelGlass from "../components/PanelGlass.vue";
import TreeSvg, { type RecolorMode } from "../components/tree/TreeSvg.vue";
import HolderTable, { type HolderRow } from "../components/tree/HolderTable.vue";
import { useUrlState } from "../state/urlState";
import { useMapDataStore } from "../stores/mapData";
import { buildVariantTree, claimIds, firstClaimId } from "../derived/variantTree";
import { decayBelief } from "../derived/decay";

const route = useRoute();
const urlState = useUrlState();
const mapData = useMapDataStore();

// Single combined [run, t] watcher (frameLog.ts's documented ordering
// hazard, same idiom as MapScreen.vue): loading the run always finishes
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

const atTick = computed(() => mapData.socialState.tick);
const availableClaims = computed(() => claimIds(mapData.socialState));

const selectedClaimId = ref<string | null>(null);
const activeClaimId = computed(() => {
  if (selectedClaimId.value !== null && mapData.socialState.claims.has(selectedClaimId.value)) {
    return selectedClaimId.value;
  }
  return firstClaimId(mapData.socialState);
});

function onSelectClaim(id: string) {
  selectedClaimId.value = id;
  selectedNodeId.value = null;
}

const recolorMode = ref<RecolorMode>("first-appearance");

const tree = computed(() => {
  const claimId = activeClaimId.value;
  if (claimId === null) return null;
  return buildVariantTree(mapData.socialState, mapData.traceRecords, claimId, atTick.value);
});

const selectedNodeId = ref<string | null>(null);

function onSelectNode(id: string) {
  selectedNodeId.value = id;
}

const selectedNode = computed(() => tree.value?.nodes.find((n) => n.id === selectedNodeId.value) ?? null);

const holderRows = computed<HolderRow[]>(() => {
  const claimId = activeClaimId.value;
  const node = selectedNode.value;
  if (claimId === null || node === null) return [];
  const rows: HolderRow[] = [];
  for (const b of mapData.socialState.beliefs.values()) {
    if (b.claim_id !== claimId) continue;
    if (b.variant_id !== node.variantId) continue;
    const decayed = decayBelief(b, atTick.value);
    rows.push({ holderId: b.holder_id, confidence: decayed.confidence, beliefId: b.id });
  }
  return rows.sort((a, b) => b.confidence - a.confidence);
});

const holderTableLabel = computed(() => {
  const node = selectedNode.value;
  if (node === null) return null;
  return node.isCanonical ? "canonical" : node.id;
});

function onTickInput(event: Event) {
  const raw = (event.target as HTMLInputElement).value;
  if (raw === "") {
    urlState.t.value = null;
    return;
  }
  const n = Number(raw);
  urlState.t.value = Number.isInteger(n) && n >= 0 ? n : null;
}

const hasLoadedRun = computed(() => mapData.status === "loaded");
</script>

<template>
  <div class="tree-screen">
    <header class="tree-screen__chrome">
      <div class="tree-screen__wordmark">CHRONICLE</div>
      <div class="tree-screen__runmeta">
        <RunPicker v-model="urlState.run.value" />
        <label class="tree-screen__tick">
          t
          <input
            class="tree-screen__tick-input"
            type="number"
            min="0"
            :value="urlState.t.value ?? ''"
            placeholder="live"
            @change="onTickInput"
          />
        </label>
        <span class="tree-screen__meta">as-of {{ atTick }}</span>
      </div>

      <label v-if="hasLoadedRun" class="tree-screen__claim">
        claim
        <select
          class="tree-screen__select"
          :value="activeClaimId ?? ''"
          @change="onSelectClaim(($event.target as HTMLSelectElement).value)"
        >
          <option v-for="id in availableClaims" :key="id" :value="id">{{ id }}</option>
        </select>
      </label>

      <label v-if="hasLoadedRun" class="tree-screen__recolor">
        recolor
        <select
          class="tree-screen__select"
          :value="recolorMode"
          @change="recolorMode = ($event.target as HTMLSelectElement).value as RecolorMode"
        >
          <option value="first-appearance">first appearance</option>
          <option value="holder-count">holder count</option>
        </select>
      </label>

      <div class="tree-screen__spacer" />
      <ViewSwitcher current="tree" />
      <span class="tree-screen__url">{{ route.fullPath }}</span>
    </header>

    <div class="tree-screen__body">
      <div class="tree-screen__canvas">
        <div v-if="!hasLoadedRun" class="tree-screen__placeholder">no run loaded</div>
        <div v-else-if="tree === null" class="tree-screen__placeholder">this run has no claims yet</div>
        <TreeSvg
          v-else
          :nodes="tree.nodes"
          :edges="tree.edges"
          :cross-links="tree.crossLinks"
          :recolor-mode="recolorMode"
          :selected-node-id="selectedNodeId"
          @select-node="onSelectNode"
        />
      </div>
      <aside class="tree-screen__panel" aria-label="holder table panel">
        <PanelGlass tone="inspector">
          <HolderTable :node-label="holderTableLabel" :holders="holderRows" />
        </PanelGlass>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.tree-screen {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--c-page-bg);
  overflow: hidden;
}

.tree-screen__chrome {
  height: 44px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 16px;
  border-bottom: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-strong);
}

.tree-screen__wordmark {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.3em;
  color: var(--c-accent-hover);
}

.tree-screen__runmeta {
  display: flex;
  gap: 8px;
  align-items: center;
  flex: none;
}

.tree-screen__meta {
  color: var(--c-text-dim);
  white-space: nowrap;
}

.tree-screen__tick,
.tree-screen__claim,
.tree-screen__recolor {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--c-text-dim);
  font-size: var(--fs-secondary);
  white-space: nowrap;
}

.tree-screen__tick-input {
  width: 64px;
  background: transparent;
  border: 1px solid var(--c-hairline);
  border-radius: var(--radius-chip);
  color: var(--c-text-body);
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  padding: 2px 6px;
}

.tree-screen__select {
  background: transparent;
  border: 1px solid var(--c-hairline);
  border-radius: var(--radius-chip);
  color: var(--c-text-body);
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  padding: 2px 6px;
}

.tree-screen__spacer {
  flex: 1;
}

.tree-screen__url {
  color: var(--c-text-faint);
  font-size: 10px;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-screen__body {
  flex: 1;
  min-height: 0;
  display: flex;
}

.tree-screen__canvas {
  flex: 1;
  min-width: 0;
  overflow: auto;
}

.tree-screen__placeholder {
  padding: 24px;
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}

.tree-screen__panel {
  width: 280px;
  flex: none;
  padding: 8px;
  overflow-y: auto;
}
</style>
