<script setup lang="ts">
/**
 * RuleFilterBar -- the rule-log's "filter by rule" control (ui-spec
 * §3.7: "Rule chip anywhere -> this log filtered to that rule"), same
 * presentational idiom as `diff/DiffFilterBar.vue`: props in, one
 * `update:filters` emit out, options derived from the currently computed
 * rows rather than a hand-maintained list.
 */
import { computed } from "vue";
import type { RuleLogFilters, RuleLogRow } from "../../derived/ruleLog";

const props = defineProps<{
  rows: RuleLogRow[];
  filters: RuleLogFilters;
}>();

const emit = defineEmits<{
  "update:filters": [filters: RuleLogFilters];
}>();

const ruleOptions = computed(() => [...new Set(props.rows.map((r) => r.rule))].sort());

function update(value: string) {
  emit("update:filters", value === "" ? {} : { rule: value });
}
</script>

<template>
  <div class="rule-filter-bar">
    <label class="rule-filter-bar__field">
      rule
      <select :value="filters.rule ?? ''" @change="update(($event.target as HTMLSelectElement).value)">
        <option value="">(any)</option>
        <option v-for="rule in ruleOptions" :key="rule" :value="rule">{{ rule }}</option>
      </select>
    </label>
  </div>
</template>

<style scoped>
.rule-filter-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 6px 16px;
  border-bottom: 1px solid var(--c-hairline-soft);
  font-size: var(--fs-secondary);
  color: var(--c-text-dim);
  flex-wrap: wrap;
}

.rule-filter-bar__field {
  display: flex;
  align-items: center;
  gap: 5px;
}

.rule-filter-bar__field select {
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  color: var(--c-text-body);
  background: var(--c-chip-active-fill);
  border: 1px solid var(--c-chip-active-border);
  border-radius: var(--radius-chip);
  padding: 1px 6px;
}
</style>
