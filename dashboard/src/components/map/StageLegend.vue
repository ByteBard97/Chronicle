<script setup lang="ts">
/**
 * StageLegend — the "C-114 STAGE" legend row from map-c-skyrim.dc.html:
 * 100-110: one StageDot per rumor stage with its tracked count, plus the
 * coverage link. Uses the shared StageDot (legend variant renders 3px
 * smaller than the map marker, per the mockup).
 *
 * Lane 14: `counts` is a new optional prop (real per-stage tallies from
 * `derived/mapMarkers.ts`'s `claimStageBreakdown`). Left unset, it falls
 * back to the fixture's `STAGE_LEGEND` counts — same idiom as `claimId`/
 * `coverage`'s existing defaults — so StageLegend.test.ts (which never
 * passes `counts`) keeps passing unedited; MapScreen always supplies real
 * counts in the app itself.
 */
import { computed } from "vue";
import { STAGE_LEGEND, type RumorStage } from "../../fixtures/whiterunMock";
import StageDot from "../StageDot.vue";

const props = withDefaults(
  defineProps<{
    /** Claim id shown in the row title. */
    claimId?: string;
    /** Coverage summary text. */
    coverage?: string;
    /** Real per-stage counts; unset falls back to the fixture's STAGE_LEGEND. */
    counts?: Record<RumorStage, number>;
  }>(),
  { claimId: "C-114", coverage: "coverage 20/26", counts: undefined },
);

const rows = computed(() =>
  props.counts === undefined
    ? STAGE_LEGEND
    : STAGE_LEGEND.map((s) => ({ ...s, count: props.counts![s.name] })),
);
</script>

<template>
  <div class="stage-legend">
    <span class="stage-legend__title">{{ claimId }} STAGE</span>
    <span v-for="s in rows" :key="s.name" class="stage-legend__item">
      <StageDot :stage="s.name" legend />
      <span class="stage-legend__name">{{ s.name }}</span>
      <a href="#" @click.prevent>{{ s.count }}</a>
    </span>
    <a href="#" class="stage-legend__coverage" @click.prevent>{{ coverage }}</a>
  </div>
</template>

<style scoped>
.stage-legend {
  display: flex;
  align-items: center;
  gap: 9px;
}

.stage-legend__title {
  font-family: var(--font-display);
  color: var(--c-panel-title);
  letter-spacing: 0.16em;
  flex: none;
  white-space: nowrap;
  font-size: 8px;
}

.stage-legend__item {
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.stage-legend__name {
  color: var(--c-text-secondary);
}

.stage-legend__coverage {
  color: var(--c-text-dim);
  white-space: nowrap;
}
</style>
