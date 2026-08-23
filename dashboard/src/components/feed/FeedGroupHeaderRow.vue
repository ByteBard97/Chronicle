<script setup lang="ts">
/**
 * FeedGroupHeaderRow — Observer salience's per-tick collapsed trace-row
 * group header (lane-11 packet's pinned semantics: "tick 47 · 12 trace
 * rows ▸"). Click toggles that tick's trace rows in place; expand/collapse
 * state is owned by the parent (view-local UI state, not URL state).
 */
import type { FeedRow } from "../../log/feedReader";

const props = defineProps<{
  tick: number;
  rows: FeedRow[];
  expanded: boolean;
}>();

const emit = defineEmits<{
  toggle: [tick: number];
}>();
</script>

<template>
  <div
    class="feed-group-header"
    role="button"
    tabindex="0"
    :data-tick="props.tick"
    :data-expanded="props.expanded"
    @click="emit('toggle', props.tick)"
    @keydown.enter="emit('toggle', props.tick)"
  >
    <span class="feed-group-header__caret">{{ props.expanded ? "▾" : "▸" }}</span>
    tick {{ props.tick }} · {{ props.rows.length }} trace row{{ props.rows.length === 1 ? "" : "s" }}
  </div>
</template>

<style scoped>
.feed-group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 12px;
  border-bottom: 1px solid var(--c-hairline-soft);
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
  cursor: pointer;
}

.feed-group-header:hover {
  color: var(--c-text-dim);
}

.feed-group-header__caret {
  width: 10px;
  display: inline-block;
}
</style>
