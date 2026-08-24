<script setup lang="ts">
/**
 * ProvenanceHopRow — one span in the provenance drill-down's vertical list
 * (ui-spec §3.6): teller, tick, location, confidence delta. A superseded
 * hop (`hop.supersession !== null`) renders grayed with the resolution
 * record (rule + dent) as an interstitial line above the span — "the
 * losing chain renders grayed with the supersession record as the
 * interstitial element (loser -> resolution record -> winner)". A
 * mutation hop renders its old->new slot value and mutation id, always
 * expanded. The witness terminus gets its own label (chain root/end).
 */
import type { ProvenanceHop } from "../../derived/provenance";

defineProps<{ hop: ProvenanceHop }>();

function formatDelta(delta: number | null): string {
  if (delta === null) return "";
  const sign = delta >= 0 ? "+" : "";
  return `${sign}${delta.toFixed(2)}`;
}
</script>

<template>
  <div
    class="provenance-hop"
    :class="{
      'provenance-hop--superseded': hop.supersession !== null,
      'provenance-hop--mutation': hop.mutation !== null,
      'provenance-hop--witness': hop.isWitness,
    }"
  >
    <div v-if="hop.supersession" class="provenance-hop__interstitial">
      superseded — {{ hop.supersession.resolutionRule }} (dent {{ hop.supersession.confidenceDent.toFixed(2) }})
    </div>
    <div class="provenance-hop__line">
      <span class="provenance-hop__source">{{ hop.sourceId }}</span>
      <span class="provenance-hop__type">{{ hop.evidenceType }}</span>
      <span class="provenance-hop__tick">t {{ hop.tick }}</span>
      <span v-if="hop.location" class="provenance-hop__location">{{ hop.location }}</span>
      <span class="provenance-hop__confidence">
        conf {{ hop.confidence.toFixed(2) }}<template v-if="hop.confidenceDelta !== null"> ({{ formatDelta(hop.confidenceDelta) }})</template>
      </span>
    </div>
    <div v-if="hop.mutation" class="provenance-hop__mutation">
      mutation {{ hop.mutation.mutationId }} — {{ hop.mutation.slot }}: {{ hop.mutation.oldValue ?? "?" }} → {{ hop.mutation.newValue ?? "?" }}
    </div>
    <div v-if="hop.isWitness" class="provenance-hop__witness-label">witnessed event · {{ hop.holderId }}</div>
  </div>
</template>

<style scoped>
.provenance-hop {
  border-left: 2px solid var(--c-hairline);
  padding: 4px 0 4px 8px;
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  color: var(--c-text-body);
}

.provenance-hop--superseded {
  opacity: 0.6;
  border-left-color: var(--c-hairline-soft);
}

.provenance-hop--mutation {
  border-left-color: var(--c-accent);
}

.provenance-hop--witness {
  border-left-color: var(--c-accent-hover);
}

.provenance-hop__interstitial {
  color: var(--c-text-faint);
  font-style: italic;
  margin-bottom: 2px;
}

.provenance-hop__line {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  color: var(--c-text-body);
}

.provenance-hop__source {
  color: var(--c-text-primary);
  font-weight: 600;
}

.provenance-hop__type,
.provenance-hop__tick,
.provenance-hop__location {
  color: var(--c-text-dim);
}

.provenance-hop__confidence {
  color: var(--c-text-secondary);
  margin-left: auto;
}

.provenance-hop__mutation {
  color: var(--c-accent-hover);
  margin-top: 2px;
}

.provenance-hop__witness-label {
  color: var(--c-panel-title);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: var(--fs-micro);
  margin-top: 2px;
}
</style>
