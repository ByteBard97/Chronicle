<script setup lang="ts">
/**
 * RuleHistogram -- the fire-frequency histogram strip at the top of the
 * rule log (ui-spec §3.7: "Fire-frequency histogram at top (the
 * fires-too-often detector)"). One horizontal bar per rule, split into a
 * fired segment (gold, same token as a positive Δ in `diff/DiffRow.vue`)
 * and an evaluated-but-not-fired segment (red, same token as a negative
 * Δ there) -- side by side per the packet ("show fired vs.
 * evaluated-not-fired counts side by side, per rule"). Bar width scales
 * to the busiest rule's total, so relative firing frequency is legible at
 * a glance -- the actual "fires-too-often" signal. Clicking a bar sets
 * the rule filter, same contract as a rule chip elsewhere in the app.
 */
import { computed } from "vue";
import type { RuleHistogramBucket } from "../../derived/ruleLog";

const props = defineProps<{
  buckets: RuleHistogramBucket[];
  activeRule?: string;
}>();

const emit = defineEmits<{
  "select-rule": [rule: string | null];
}>();

const maxTotal = computed(() => Math.max(1, ...props.buckets.map((b) => b.total)));

function widthPct(count: number): string {
  return `${(count / maxTotal.value) * 100}%`;
}

function onBarClick(rule: string) {
  emit("select-rule", props.activeRule === rule ? null : rule);
}
</script>

<template>
  <div class="rule-histogram" aria-label="rule fire-frequency histogram">
    <div v-if="buckets.length === 0" class="rule-histogram__empty">no rule evaluations in this run</div>
    <button
      v-for="bucket in buckets"
      :key="bucket.rule"
      type="button"
      class="rule-histogram__row"
      :class="{ 'rule-histogram__row--active': activeRule === bucket.rule }"
      @click="onBarClick(bucket.rule)"
    >
      <span class="rule-histogram__label">{{ bucket.rule }}</span>
      <span class="rule-histogram__bar" :style="{ width: widthPct(bucket.total) }">
        <span
          class="rule-histogram__segment rule-histogram__segment--fired"
          :style="{ width: `${(bucket.fired / Math.max(1, bucket.total)) * 100}%` }"
        />
        <span
          class="rule-histogram__segment rule-histogram__segment--not-fired"
          :style="{ width: `${(bucket.notFired / Math.max(1, bucket.total)) * 100}%` }"
        />
      </span>
      <span class="rule-histogram__counts">{{ bucket.fired }} fired · {{ bucket.notFired }} not · {{ bucket.total }} total</span>
    </button>
  </div>
</template>

<style scoped>
.rule-histogram {
  flex: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-inspector);
  max-height: 176px;
  overflow-y: auto;
}

.rule-histogram__empty {
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
  padding: 4px 0;
}

.rule-histogram__row {
  appearance: none;
  border: none;
  background: transparent;
  display: grid;
  grid-template-columns: 190px 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 2px 4px;
  cursor: pointer;
  border-radius: var(--radius-chip);
  text-align: left;
}

.rule-histogram__row:hover {
  background: var(--c-chip-active-fill);
}

.rule-histogram__row--active {
  background: var(--c-chip-active-fill);
  outline: 1px solid var(--c-chip-active-border);
}

.rule-histogram__label {
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  color: var(--c-text-body);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rule-histogram__bar {
  display: flex;
  height: 10px;
  min-width: 6px;
  border-radius: var(--radius-chip);
  overflow: hidden;
  background: var(--c-hairline-soft);
}

.rule-histogram__segment--fired {
  background: var(--c-accent-hover);
}

.rule-histogram__segment--not-fired {
  background: var(--ev-grudge);
}

.rule-histogram__counts {
  font-size: var(--fs-micro);
  color: var(--c-text-dim);
  white-space: nowrap;
}
</style>
