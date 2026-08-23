<script setup lang="ts">
/**
 * LegendStrip — the rumor-stage legend row from the map footer
 * (map-c-skyrim.dc.html:99-110): "<CLAIM> STAGE" label + one StageDot
 * per stage with its tracked count. Counts are the caller's data (D6:
 * every rendered number links somewhere — pass a `href` per item when
 * the caller has a target).
 */
import StageDot, { type RumorStage } from "./StageDot.vue";

export interface LegendItem {
  stage: RumorStage;
  count: number;
  href?: string;
}

defineProps<{
  title: string;
  items: LegendItem[];
}>();
</script>

<template>
  <div class="legend-strip">
    <span class="legend-strip__title">{{ title }}</span>
    <span v-for="item in items" :key="item.stage" class="legend-strip__item">
      <StageDot :stage="item.stage" legend />
      <span class="legend-strip__name">{{ item.stage }}</span>
      <component :is="item.href ? 'a' : 'span'" :href="item.href">{{
        item.count
      }}</component>
    </span>
  </div>
</template>

<style scoped>
.legend-strip {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
  font-size: var(--fs-micro);
}

.legend-strip__title {
  font-family: var(--font-display);
  color: var(--c-panel-title);
  letter-spacing: var(--ls-panel-title);
  font-size: 8px;
  flex: none;
  white-space: nowrap;
}

.legend-strip__item {
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.legend-strip__name {
  color: var(--c-text-secondary);
}
</style>
