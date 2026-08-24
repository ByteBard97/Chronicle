<script setup lang="ts">
/**
 * RuleLogTable -- the rule log's evaluation table (ui-spec §3.7). Plain
 * (non-virtualized) table, same call as `diff/DiffTable.vue`: at this
 * project's demo-run sizes (165 rule_evaluated records for the whole of
 * `tier3-demo-01`) a virtualized list buys nothing a plain table doesn't
 * already give for free.
 */
import RuleLogRowView from "./RuleLogRow.vue";
import type { RuleLogRow } from "../../derived/ruleLog";

defineProps<{
  rows: RuleLogRow[];
}>();
</script>

<template>
  <div class="rule-log-table">
    <table>
      <thead>
        <tr>
          <th>tick</th>
          <th>rule</th>
          <th>fired</th>
          <th>inputs</th>
          <th>result</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="rows.length === 0" class="rule-log-table__empty-row">
          <td colspan="5">no rule evaluations for this filter</td>
        </tr>
        <RuleLogRowView v-for="row in rows" :key="row.key" :row="row" />
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.rule-log-table {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead th {
  position: sticky;
  top: 0;
  text-align: left;
  padding: 6px 8px;
  font-size: var(--fs-micro);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--c-panel-title);
  background: var(--c-panel-glass-strong);
  border-bottom: 1px solid var(--c-hairline);
}

.rule-log-table__empty-row td {
  padding: 16px;
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}
</style>
