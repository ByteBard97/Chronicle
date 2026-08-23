<script setup lang="ts">
/**
 * FeedOutcomeCell — renders the outcome-specific payload for one of the
 * encounter feed's four outcome states (ui-spec §3.3), each carrying a
 * different fact: transmitted (claim/variant id), rolled-against (roll
 * value vs. threshold), declined (rule name), nothing-salient (reason).
 * All four render through the same `Chip` shell at equal visual weight —
 * "four outcome states with equal visual weight" is a layout rule, not
 * just a words-on-a-page one.
 */
import Chip from "../Chip.vue";
import type { FeedRow } from "../../log/feedReader";

defineProps<{
  row: FeedRow;
}>();
</script>

<template>
  <span class="feed-outcome-cell" :data-outcome="row.outcome">
    <Chip
      :tone="
        row.outcome === 'transmitted'
          ? 'active'
          : row.outcome === 'declined'
            ? 'muted'
            : 'default'
      "
    >
      {{ row.outcome.replace("_", "-") }}
    </Chip>

    <template v-if="row.detail.kind === 'transmitted'">
      <span class="feed-outcome-cell__detail">
        claim {{ row.claimId ?? "(none)" }}
        <span v-if="row.detail.variantId"> · variant {{ row.detail.variantId }}</span>
        <span v-if="row.detail.mutatedSlot"> · mutated {{ row.detail.mutatedSlot }}</span>
      </span>
    </template>

    <template v-else-if="row.detail.kind === 'rolled_against'">
      <span class="feed-outcome-cell__detail">
        {{ row.detail.value.toFixed(3) }} vs. threshold {{ row.detail.threshold.toFixed(3) }}
      </span>
    </template>

    <template v-else-if="row.detail.kind === 'declined'">
      <span class="feed-outcome-cell__detail">rule: {{ row.detail.rule }}</span>
    </template>

    <template v-else-if="row.detail.kind === 'nothing_salient'">
      <span class="feed-outcome-cell__detail">{{ row.detail.reason }}</span>
    </template>
  </span>
</template>

<style scoped>
.feed-outcome-cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.feed-outcome-cell__detail {
  color: var(--c-text-dim);
  font-size: var(--fs-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
