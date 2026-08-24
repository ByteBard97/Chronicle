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
 *
 * Positioning (M7 fix lane 57, dossier step 5): the panel used to render
 * pinned to a fixed screen corner regardless of where the "drill"
 * affordance was clicked. None of the three host screens (FeedScreen,
 * MapScreen, VariantTreeScreen/HolderTable) are in this lane's edit
 * boundary, so the click position can't be threaded down through a new
 * prop from those call sites -- instead this component listens for
 * `pointerdown` on `document` itself (capture phase, so it always runs
 * before the host's own `@click` handler that flips `open` to true) and
 * remembers the most recent pointer position. When `open` transitions
 * false -> true, that remembered position becomes the panel's anchor,
 * clamped to stay fully on-screen. A deep-link open (`panels=drill:...`
 * in the URL, no real click) leaves the anchor `null`, which falls back
 * to a fixed-but-reasonable default position rather than crashing or
 * rendering off-screen.
 *
 * Mutation discoverability: a corroborated/repeatedly-contested belief can
 * carry hundreds of parallel columns (`ProvenanceBranchView` renders one
 * per grounding Evidence record, DAG-honest, per ui-spec §3.6 -- never a
 * spanning-tree pick, so this isn't reorderable from here without
 * reopening that pinned contract). The mutation hop itself already
 * narrates inline (`ProvenanceHopRow.vue`'s `.provenance-hop__mutation`
 * line, fed by `provenance.ts`'s already-populated `ProvenanceHop.mutation`
 * field), but on a belief with many columns it can render far off the
 * initial scroll position. Rather than touch the DAG-honest column order,
 * this scrolls the panel body to bring the first mutation hop into view
 * whenever the displayed chain (re)computes -- purely a scroll position,
 * doesn't reorder or hide anything.
 */
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
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

const PANEL_WIDTH = 460;
/** Only used to keep the clamped anchor from running the panel's bottom edge off-screen; the panel's own `max-height` still governs its real rendered height. */
const PANEL_MIN_HEIGHT = 160;
const MARGIN = 12;
const DEFAULT_TOP = 54;
const DEFAULT_LEFT = 12;

const lastPointerPos = ref<{ x: number; y: number } | null>(null);
const anchorPos = ref<{ x: number; y: number } | null>(null);

function recordPointer(e: PointerEvent): void {
  lastPointerPos.value = { x: e.clientX, y: e.clientY };
}

onMounted(() => {
  document.addEventListener("pointerdown", recordPointer, true);
});

onUnmounted(() => {
  document.removeEventListener("pointerdown", recordPointer, true);
});

watch(
  () => props.open,
  (isOpen, wasOpen) => {
    if (isOpen && !wasOpen) {
      anchorPos.value = lastPointerPos.value;
    }
  },
);

/** Clamps a raw anchor point so the panel's box (estimated width/min-height) stays fully within the viewport. */
const panelStyle = computed(() => {
  const anchor = anchorPos.value;
  if (anchor === null) {
    return { top: `${DEFAULT_TOP}px`, left: `${DEFAULT_LEFT}px`, right: "auto" };
  }
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const maxLeft = Math.max(MARGIN, viewportWidth - PANEL_WIDTH - MARGIN);
  const maxTop = Math.max(MARGIN, viewportHeight - PANEL_MIN_HEIGHT - MARGIN);
  const left = Math.min(Math.max(anchor.x + 12, MARGIN), maxLeft);
  const top = Math.min(Math.max(anchor.y + 12, MARGIN), maxTop);
  return { top: `${top}px`, left: `${left}px`, right: "auto" };
});

const bodyRef = ref<HTMLElement | null>(null);

watch(
  () => provenance.value,
  async () => {
    await nextTick();
    const body = bodyRef.value;
    if (body === null) return;
    const mutationHop = body.querySelector(".provenance-hop--mutation");
    // jsdom (the test environment) doesn't implement `scrollIntoView` at all -- guard
    // rather than let a real-browser-only convenience throw in tests.
    if (mutationHop !== null && typeof mutationHop.scrollIntoView === "function") {
      mutationHop.scrollIntoView({ block: "nearest", inline: "center" });
    }
  },
  { immediate: true },
);
</script>

<template>
  <PanelGlass v-if="open" tone="strong" class="provenance-panel" :style="panelStyle" aria-label="provenance drill-down">
    <div class="provenance-panel__header">
      <div class="provenance-panel__title">
        provenance
        <span v-if="beliefId" class="provenance-panel__belief">{{ beliefId }}</span>
        <span v-if="provenance" class="provenance-panel__holder">({{ provenance.holderId }})</span>
      </div>
      <span class="provenance-panel__tick">as-of t={{ atTick }}</span>
      <button type="button" class="provenance-panel__close" aria-label="close provenance panel" @click="emit('close')">✕</button>
    </div>
    <div ref="bodyRef" class="provenance-panel__body">
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
  /* Base fixed position; actual top/left/right are set inline per-instance
     (see `panelStyle` above), anchored near the click that opened the
     panel instead of pinned to a fixed screen corner. */
  position: fixed;
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
