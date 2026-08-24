<script setup lang="ts">
/**
 * RuleLogRow -- one `rule_evaluated` evaluation (ui-spec §3.7: "every
 * registry evaluation -- activations with inputs *and*
 * evaluated-but-not-fired rows with current accumulator values"). Fired
 * and not-fired rows share the exact same column layout and visual
 * weight (per ui-doctrines' "negative rows are first-class") -- the only
 * difference is the `fired` chip's tone and the not-fired row's dimmed
 * `data-fired="false"` styling, never a blank/missing result column.
 */
import type { RuleLogRow } from "../../derived/ruleLog";
import Chip from "../Chip.vue";

defineProps<{
  row: RuleLogRow;
}>();
</script>

<template>
  <tr class="rule-log-row" :data-fired="row.fired">
    <td class="rule-log-row__tick">t{{ row.tick }}</td>
    <td class="rule-log-row__rule">{{ row.rule }}</td>
    <td class="rule-log-row__fired">
      <Chip :tone="row.fired ? 'active' : 'muted'">{{ row.fired ? "fired" : "not fired" }}</Chip>
    </td>
    <td class="rule-log-row__inputs">{{ row.inputsSummary }}</td>
    <td class="rule-log-row__result">{{ row.resultSummary }}</td>
  </tr>
</template>

<style scoped>
.rule-log-row td {
  padding: 4px 8px;
  border-bottom: 1px solid var(--c-hairline-soft);
  font-size: var(--fs-secondary);
  color: var(--c-text-body);
  vertical-align: middle;
}

.rule-log-row[data-fired="false"] td {
  color: var(--c-text-dim);
}

.rule-log-row__tick {
  font-family: var(--font-data);
  white-space: nowrap;
}

.rule-log-row__rule {
  font-family: var(--font-data);
  white-space: nowrap;
}

.rule-log-row__inputs,
.rule-log-row__result {
  font-size: var(--fs-micro);
}
</style>
