<script setup lang="ts">
/**
 * ScheduleFilterBar — the standalone `/scheddiff` view's NPC filter (lane
 * 41, ui-spec §3.8's "standalone multi-NPC comparison... filterable"),
 * same presentational idiom as `rulelog/RuleFilterBar.vue`/
 * `diff/DiffFilterBar.vue`: props in, one `update:filters` emit out.
 */
import { computed } from "vue";
import type { NpcScheduleDiff, ScheduleDiffFilters } from "../../derived/scheduleDiff";

const props = defineProps<{
  diffs: NpcScheduleDiff[];
  filters: ScheduleDiffFilters;
}>();

const emit = defineEmits<{
  "update:filters": [filters: ScheduleDiffFilters];
}>();

const npcOptions = computed(() => [...new Set(props.diffs.map((d) => d.npcId))].sort());

function update(value: string) {
  emit("update:filters", value === "" ? {} : { npc: value });
}
</script>

<template>
  <div class="schedule-filter-bar">
    <label class="schedule-filter-bar__field">
      NPC
      <select :value="filters.npc ?? ''" @change="update(($event.target as HTMLSelectElement).value)">
        <option value="">(any)</option>
        <option v-for="npc in npcOptions" :key="npc" :value="npc">{{ npc }}</option>
      </select>
    </label>
  </div>
</template>

<style scoped>
.schedule-filter-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 6px 16px;
  border-bottom: 1px solid var(--c-hairline-soft);
  font-size: var(--fs-secondary);
  color: var(--c-text-dim);
  flex-wrap: wrap;
}

.schedule-filter-bar__field {
  display: flex;
  align-items: center;
  gap: 5px;
}

.schedule-filter-bar__field select {
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  color: var(--c-text-body);
  background: var(--c-chip-active-fill);
  border: 1px solid var(--c-chip-active-border);
  border-radius: var(--radius-chip);
  padding: 1px 6px;
}
</style>
