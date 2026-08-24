<script setup lang="ts">
/**
 * ProvenanceColumnView — one incoming chain (ui-spec §3.6's "parallel
 * column"): the column's own hop/collapsed entries, target-to-witness
 * order, followed by a nested `ProvenanceBranchView` when the column's
 * last hop's predecessor belief is itself corroborated (2+ grounding
 * evidence) — the DAG-honest hand-off to that predecessor's own parallel
 * columns, never a picked single continuation.
 */
import type { ProvenanceColumn } from "../../derived/provenance";
import ProvenanceHopRow from "./ProvenanceHopRow.vue";
import ProvenanceCollapsedRow from "./ProvenanceCollapsedRow.vue";
import ProvenanceBranchView from "./ProvenanceBranchView.vue";

defineProps<{ column: ProvenanceColumn; atTick: number }>();
</script>

<template>
  <div class="provenance-column" data-testid="provenance-column">
    <template v-for="(entry, i) in column.entries" :key="i">
      <ProvenanceHopRow v-if="entry.kind === 'hop'" :hop="entry.hop" />
      <ProvenanceCollapsedRow v-else :count="entry.count" :hops="entry.hops" />
    </template>
    <ProvenanceBranchView v-if="column.branch" :branch="column.branch" :at-tick="atTick" />
  </div>
</template>

<style scoped>
.provenance-column {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 200px;
  flex: 1;
}
</style>
