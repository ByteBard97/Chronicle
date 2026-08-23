<script setup lang="ts">
/**
 * HolderTable — the side panel a node click opens (ui-spec §3.5: "Node
 * click -> holder table"). Lists every holder of the selected node's
 * variant (or the canonical root, for `variantId: null`) at T, with their
 * confidence. Presentation only -- `holders` is precomputed by the screen
 * from `SocialState.beliefs`.
 */
export interface HolderRow {
  holderId: string;
  confidence: number;
  beliefId: string;
}

defineProps<{
  nodeLabel: string | null;
  holders: HolderRow[];
}>();
</script>

<template>
  <div class="holder-table" aria-label="holder table">
    <div v-if="nodeLabel === null" class="holder-table__empty">click a node to see its holders</div>
    <template v-else>
      <div class="holder-table__title">{{ nodeLabel }} — {{ holders.length }} holder{{ holders.length === 1 ? "" : "s" }}</div>
      <table class="holder-table__grid">
        <thead>
          <tr>
            <th>holder</th>
            <th>confidence</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="h in holders" :key="h.beliefId">
            <td>{{ h.holderId }}</td>
            <td>{{ h.confidence.toFixed(2) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="holders.length === 0" class="holder-table__empty">no holders at this tick</div>
    </template>
  </div>
</template>

<style scoped>
.holder-table {
  padding: 10px;
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  color: var(--c-text-body);
}

.holder-table__title {
  color: var(--c-panel-title);
  font-size: var(--fs-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.holder-table__grid {
  width: 100%;
  border-collapse: collapse;
}

.holder-table__grid th {
  text-align: left;
  color: var(--c-text-dim);
  font-weight: 400;
  border-bottom: 1px solid var(--c-hairline);
  padding: 2px 6px 4px 0;
}

.holder-table__grid td {
  padding: 3px 6px 3px 0;
  border-bottom: 1px solid var(--c-hairline-soft);
}

.holder-table__empty {
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}
</style>
