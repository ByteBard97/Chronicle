<script setup lang="ts">
/**
 * DeltaTable — signed-Δ table beneath the ranked divergence list (ui-spec
 * §3.9: "Signed Δ tables beneath"), scoped to whichever entity is currently
 * selected in `DivergenceList`.
 */
import type { EntityDeltaRow } from "../../derived/runCompare";

defineProps<{
  npcId: string | null;
  rows: EntityDeltaRow[];
}>();
</script>

<template>
  <div class="delta-table">
    <div v-if="npcId === null" class="delta-table__placeholder">select an entity above to see its Δ table</div>
    <table v-else>
      <caption class="delta-table__caption">{{ npcId }} — run A vs run B</caption>
      <thead>
        <tr>
          <th>kind</th>
          <th>subject</th>
          <th>A</th>
          <th>B</th>
          <th class="delta-table__delta-head">Δ</th>
          <th>detail</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="rows.length === 0" class="delta-table__empty-row">
          <td colspan="6">no deltas for this entity</td>
        </tr>
        <tr v-for="row in rows" :key="row.key">
          <td>{{ row.kind }}</td>
          <td>{{ row.label }}</td>
          <td class="delta-table__num">{{ row.a.toFixed(3) }}</td>
          <td class="delta-table__num">{{ row.b.toFixed(3) }}</td>
          <td
            class="delta-table__num delta-table__delta"
            :class="row.delta > 0 ? 'delta-table__delta--pos' : row.delta < 0 ? 'delta-table__delta--neg' : ''"
          >
            {{ row.delta > 0 ? "+" : "" }}{{ row.delta.toFixed(3) }}
          </td>
          <td>{{ row.detail }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.delta-table {
  flex: none;
  max-height: 220px;
  overflow: auto;
  border-top: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-inspector);
}

.delta-table__placeholder {
  padding: 12px;
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}

table {
  width: 100%;
  border-collapse: collapse;
}

.delta-table__caption {
  text-align: left;
  padding: 6px 8px;
  font-size: var(--fs-secondary);
  color: var(--c-text-dim);
}

thead th {
  position: sticky;
  top: 0;
  text-align: left;
  padding: 4px 8px;
  font-size: var(--fs-micro);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--c-text-faint);
  background: var(--c-panel-glass-strong);
  border-bottom: 1px solid var(--c-hairline);
}

tbody td {
  padding: 4px 8px;
  font-size: var(--fs-secondary);
  color: var(--c-text-body);
  border-bottom: 1px solid var(--c-hairline-soft);
}

.delta-table__num {
  font-family: var(--font-data);
  text-align: right;
}

.delta-table__delta--pos {
  color: var(--c-accent-hover);
}

.delta-table__delta--neg {
  color: var(--ev-grudge);
}

.delta-table__empty-row td {
  color: var(--c-text-faint);
}
</style>
