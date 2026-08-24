<script setup lang="ts">
/**
 * ProvenanceBranchView — the DAG-honest fan-out point (ui-spec §3.6):
 * "corroborated beliefs render all incoming chains as parallel columns
 * converging — never a spanning tree hiding a parent." One column per
 * Evidence record grounding `branch.beliefId`; every one renders side by
 * side, never picked from.
 */
import type { ProvenanceBranch } from "../../derived/provenance";
import ProvenanceColumnView from "./ProvenanceColumnView.vue";

defineProps<{ branch: ProvenanceBranch; atTick: number }>();
</script>

<template>
  <div class="provenance-branch">
    <div class="provenance-branch__label">
      {{ branch.holderId }} — {{ branch.columns.length }} chain{{ branch.columns.length === 1 ? "" : "s" }}
    </div>
    <div class="provenance-branch__columns">
      <ProvenanceColumnView v-for="col in branch.columns" :key="col.id" :column="col" :at-tick="atTick" />
    </div>
  </div>
</template>

<style scoped>
.provenance-branch {
  margin-top: 4px;
}

.provenance-branch__label {
  color: var(--c-panel-title);
  font-size: var(--fs-micro);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

.provenance-branch__columns {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
</style>
