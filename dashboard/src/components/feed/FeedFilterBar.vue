<script setup lang="ts">
/**
 * FeedFilterBar — NPC / location / outcome / claim filters (ui-spec §3.3:
 * "Filterable by NPC/location/outcome/claim"), bound to `urlState.filters`
 * by the parent (this component is presentational: props in, one emit
 * out). Options for NPC/location/claim are derived from the currently
 * loaded rows rather than hand-maintained lists, so they never drift from
 * the actual run's data.
 */
import { computed } from "vue";
import type { FeedFilters, FeedRow } from "../../log/feedReader";

const props = defineProps<{
  rows: FeedRow[];
  filters: FeedFilters;
}>();

const emit = defineEmits<{
  "update:filters": [filters: FeedFilters];
}>();

function distinct(values: (string | null)[]): string[] {
  return [...new Set(values.filter((v): v is string => v !== null))].sort();
}

const npcOptions = computed(() => distinct(props.rows.flatMap((r) => r.participants)));
const locationOptions = computed(() => distinct(props.rows.map((r) => r.location)));
const claimOptions = computed(() => distinct(props.rows.map((r) => r.claimId)));

const OUTCOME_OPTIONS = ["transmitted", "rolled_against", "declined", "nothing_salient"] as const;

function update(key: keyof FeedFilters, value: string) {
  const next = { ...props.filters };
  if (value === "") {
    delete next[key];
  } else {
    next[key] = value;
  }
  emit("update:filters", next);
}
</script>

<template>
  <div class="feed-filter-bar">
    <label class="feed-filter-bar__field">
      NPC
      <select
        :value="filters.npc ?? ''"
        @change="update('npc', ($event.target as HTMLSelectElement).value)"
      >
        <option value="">(any)</option>
        <option v-for="npc in npcOptions" :key="npc" :value="npc">{{ npc }}</option>
      </select>
    </label>

    <label class="feed-filter-bar__field">
      location
      <select
        :value="filters.location ?? ''"
        @change="update('location', ($event.target as HTMLSelectElement).value)"
      >
        <option value="">(any)</option>
        <option v-for="loc in locationOptions" :key="loc" :value="loc">{{ loc }}</option>
      </select>
    </label>

    <label class="feed-filter-bar__field">
      outcome
      <select
        :value="filters.outcome ?? ''"
        @change="update('outcome', ($event.target as HTMLSelectElement).value)"
      >
        <option value="">(any)</option>
        <option v-for="o in OUTCOME_OPTIONS" :key="o" :value="o">{{ o }}</option>
      </select>
    </label>

    <label class="feed-filter-bar__field">
      claim
      <select
        :value="filters.claim ?? ''"
        @change="update('claim', ($event.target as HTMLSelectElement).value)"
      >
        <option value="">(any)</option>
        <option v-for="c in claimOptions" :key="c" :value="c">{{ c }}</option>
      </select>
    </label>

    <span class="feed-filter-bar__note">
      note: claim filter excludes rolled-against rows (encounter rolls carry no claim id)
    </span>
  </div>
</template>

<style scoped>
.feed-filter-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 6px 16px;
  border-bottom: 1px solid var(--c-hairline-soft);
  font-size: var(--fs-secondary);
  color: var(--c-text-dim);
  flex-wrap: wrap;
}

.feed-filter-bar__field {
  display: flex;
  align-items: center;
  gap: 5px;
}

.feed-filter-bar__field select {
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  color: var(--c-text-body);
  background: var(--c-chip-active-fill);
  border: 1px solid var(--c-chip-active-border);
  border-radius: var(--radius-chip);
  padding: 1px 6px;
}

.feed-filter-bar__note {
  color: var(--c-text-faint);
  font-size: var(--fs-micro);
  margin-left: auto;
}
</style>
