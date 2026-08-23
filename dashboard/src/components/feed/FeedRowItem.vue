<script setup lang="ts">
/**
 * FeedRowItem — one chronological row of the encounter feed: tick,
 * location, participants, outcome (ui-spec §3.3's column set). Click ->
 * FeedScreen selects both participants and jumps the timeline to this
 * row's tick.
 */
import FeedOutcomeCell from "./FeedOutcomeCell.vue";
import type { FeedRow } from "../../log/feedReader";

const props = defineProps<{
  row: FeedRow;
  selected?: boolean;
}>();

const emit = defineEmits<{
  rowClick: [row: FeedRow];
}>();
</script>

<template>
  <div
    class="feed-row"
    :class="{ 'feed-row--selected': selected }"
    role="button"
    tabindex="0"
    :data-tick="props.row.tick"
    :data-outcome="props.row.outcome"
    @click="emit('rowClick', props.row)"
    @keydown.enter="emit('rowClick', props.row)"
  >
    <span class="feed-row__tick">t{{ props.row.tick }}</span>
    <span class="feed-row__location">{{ props.row.location ?? "—" }}</span>
    <span class="feed-row__participants">{{ props.row.participants.join(" ↔ ") }}</span>
    <FeedOutcomeCell class="feed-row__outcome" :row="props.row" />
  </div>
</template>

<style scoped>
.feed-row {
  display: grid;
  grid-template-columns: 64px 120px 200px 1fr;
  align-items: center;
  gap: 10px;
  padding: 4px 12px;
  border-bottom: 1px solid var(--c-hairline-soft);
  font-size: var(--fs-secondary);
  color: var(--c-text-body);
  cursor: pointer;
}

.feed-row:hover {
  background: rgba(255, 255, 255, 0.03);
}

.feed-row--selected {
  background: var(--c-chip-active-fill);
}

.feed-row__tick {
  font-family: var(--font-data);
  color: var(--c-text-dim);
}

.feed-row__location {
  color: var(--c-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.feed-row__participants {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
