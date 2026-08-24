<script setup lang="ts">
/**
 * DiffTable — the diff panel's delta table (ui-spec §3.7). Plain (non-
 * virtualized) table: diff rows are one per changed belief/grudge/
 * obligation/reputation between two ticks, a small-scale list at this
 * project's demo-run sizes (unlike the encounter feed's per-tick trace
 * volume, which is why `FeedTable.vue` needs `@tanstack/vue-virtual` and
 * this table doesn't).
 */
import DiffRowView from "./DiffRow.vue";
import type { DiffRow } from "../../derived/socialDiff";

defineProps<{
  rows: DiffRow[];
  runId: string | null;
}>();
</script>

<template>
  <div class="diff-table">
    <table>
      <thead>
        <tr>
          <th>type</th>
          <th>npc(s)</th>
          <th>subject</th>
          <th>change</th>
          <th class="diff-table__delta-head">Δ</th>
          <th>rule</th>
          <th>event</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="rows.length === 0" class="diff-table__empty-row">
          <td colspan="7">no social-state deltas between T2 and T1</td>
        </tr>
        <DiffRowView v-for="row in rows" :key="row.key" :row="row" :run-id="runId" />
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.diff-table {
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

.diff-table__delta-head {
  text-align: right;
}

.diff-table__empty-row td {
  padding: 16px;
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}
</style>
