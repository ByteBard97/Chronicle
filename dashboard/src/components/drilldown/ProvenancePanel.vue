<script setup lang="ts">
/**
 * ProvenancePanel — the M3 signature view (ui-spec §3.6): a docked panel
 * (not a route, not a modal takeover — the host screen's timeline/tick
 * controls stay live underneath so "scrubbing T re-derives the shown
 * chain" is actually demonstrable) rendering the DAG-honest span list for
 * one target belief, as of the host screen's current T. Same component,
 * mounted from every host (FeedScreen, MapScreen, VariantTreeScreen);
 * each host owns its own `open`/`beliefId` state (synced to the `panels`
 * URL codec via `panelUrlState.ts`) and passes down its already-loaded
 * `SocialState`/`traceRecords`/`atTick`.
 *
 * As-of-T (pinned): `provenance.ts`'s `buildProvenance` is called fresh
 * off `atTick` on every render — a `computed`, not a snapshot taken at
 * open time — so scrubbing the host's T re-derives the displayed chain
 * without needing to reopen the panel.
 */
import { computed } from "vue";
import { buildProvenance } from "../../derived/provenance";
import type { SocialState } from "../../log/reconstruct";
import type { FrameRecord } from "../../log/types";
import PanelGlass from "../PanelGlass.vue";
import ProvenanceBranchView from "./ProvenanceBranchView.vue";

const props = defineProps<{
  open: boolean;
  beliefId: string | null;
  state: SocialState;
  traceRecords: FrameRecord[];
  atTick: number;
}>();

const emit = defineEmits<{ close: [] }>();

const provenance = computed(() =>
  props.beliefId === null ? null : buildProvenance(props.state, props.traceRecords, props.beliefId, props.atTick),
);
</script>

<template>
  <PanelGlass v-if="open" tone="strong" class="provenance-panel" aria-label="provenance drill-down">
    <div class="provenance-panel__header">
      <div class="provenance-panel__title">
        provenance
        <span v-if="beliefId" class="provenance-panel__belief">{{ beliefId }}</span>
        <span v-if="provenance" class="provenance-panel__holder">({{ provenance.holderId }})</span>
      </div>
      <span class="provenance-panel__tick">as-of t={{ atTick }}</span>
      <button type="button" class="provenance-panel__close" aria-label="close provenance panel" @click="emit('close')">✕</button>
    </div>
    <div class="provenance-panel__body">
      <div v-if="beliefId === null" class="provenance-panel__empty">
        no belief selected for drill-down
      </div>
      <div v-else-if="provenance === null" class="provenance-panel__empty">
        this belief does not exist as of t={{ atTick }}
      </div>
      <div v-else-if="provenance.columns.length === 0" class="provenance-panel__empty">
        no grounding evidence recorded for this belief (as of t={{ atTick }})
      </div>
      <ProvenanceBranchView v-else :branch="provenance" :at-tick="atTick" />
    </div>
  </PanelGlass>
</template>

<style scoped>
.provenance-panel {
  position: fixed;
  top: 54px;
  right: 12px;
  width: 460px;
  max-height: calc(100vh - 130px);
  z-index: 50;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.provenance-panel__header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--c-hairline-soft);
  margin-bottom: 8px;
}

.provenance-panel__title {
  font-family: var(--font-display);
  font-size: var(--fs-npc-name);
  color: var(--c-text-primary);
  display: flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
}

.provenance-panel__belief {
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  color: var(--c-accent);
  overflow-wrap: anywhere;
}

.provenance-panel__holder {
  font-size: var(--fs-secondary);
  color: var(--c-text-dim);
}

.provenance-panel__tick {
  margin-left: auto;
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
  white-space: nowrap;
}

.provenance-panel__close {
  appearance: none;
  border: none;
  background: transparent;
  color: var(--c-text-dim);
  cursor: pointer;
  font-size: var(--fs-body);
  padding: 0 0 0 4px;
}

.provenance-panel__body {
  overflow: auto;
  padding-bottom: 4px;
}

.provenance-panel__empty {
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
  padding: 8px 0;
}
</style>
