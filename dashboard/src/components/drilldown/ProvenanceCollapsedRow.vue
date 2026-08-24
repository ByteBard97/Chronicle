<script setup lang="ts">
/**
 * ProvenanceCollapsedRow — the collapse affordance for a run of 2+
 * consecutive unchanged retellings (ui-spec §3.6: "unchanged retellings
 * collapsed behind a count"). Click to expand the individual hops
 * on-demand; collapsed by default.
 */
import { ref } from "vue";
import type { ProvenanceHop } from "../../derived/provenance";
import ProvenanceHopRow from "./ProvenanceHopRow.vue";

defineProps<{ count: number; hops: ProvenanceHop[] }>();

const expanded = ref(false);
</script>

<template>
  <div class="provenance-collapsed">
    <button
      type="button"
      class="provenance-collapsed__toggle"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      — {{ count }} retelling{{ count === 1 ? "" : "s" }} —
    </button>
    <div v-if="expanded" class="provenance-collapsed__hops">
      <ProvenanceHopRow v-for="hop in hops" :key="hop.edgeId" :hop="hop" />
    </div>
  </div>
</template>

<style scoped>
.provenance-collapsed__toggle {
  appearance: none;
  border: none;
  background: transparent;
  color: var(--c-text-faint);
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  font-style: italic;
  cursor: pointer;
  padding: 3px 0 3px 8px;
  text-align: left;
}

.provenance-collapsed__toggle:hover {
  color: var(--c-text-dim);
}

.provenance-collapsed__hops {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: 8px;
  border-left: 1px dashed var(--c-hairline-soft);
}
</style>
