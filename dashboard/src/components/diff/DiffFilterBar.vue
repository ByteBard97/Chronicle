<script setup lang="ts">
/**
 * DiffFilterBar — NPC / rule / type filters for the diff panel (ui-spec
 * §3.7: "Filter by NPC/rule/type"), same presentational idiom as
 * `feed/FeedFilterBar.vue`: props in, one `update:filters` emit out,
 * options derived from the currently computed rows rather than a
 * hand-maintained list. Bound to `urlState.filters` by the parent
 * (`DiffScreen.vue`), which also stores `t2` in that same record --
 * this bar only ever touches the `npc`/`rule`/`type` keys, never `t2`.
 */
import { computed } from "vue";
import type { DiffRow, DiffRowType, SocialDiffFilters } from "../../derived/socialDiff";

const props = defineProps<{
  rows: DiffRow[];
  filters: SocialDiffFilters;
}>();

const emit = defineEmits<{
  "update:filters": [filters: SocialDiffFilters];
}>();

function distinct(values: string[]): string[] {
  return [...new Set(values)].sort();
}

const npcOptions = computed(() => distinct(props.rows.flatMap((r) => r.npcs)));
const ruleOptions = computed(() => distinct(props.rows.map((r) => r.rule?.rule).filter((r): r is string => r !== undefined)));
// "role" appended (lane 52, additive edit -- see DiffRow.vue's header for
// why DiffRowType gaining a member also touches this exhaustive-in-spirit
// list, kept in bounds rather than restructured).
const TYPE_OPTIONS: DiffRowType[] = ["belief", "grudge", "obligation", "reputation", "role"];

function update(key: keyof SocialDiffFilters, value: string) {
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
  <div class="diff-filter-bar">
    <label class="diff-filter-bar__field">
      NPC
      <select :value="filters.npc ?? ''" @change="update('npc', ($event.target as HTMLSelectElement).value)">
        <option value="">(any)</option>
        <option v-for="npc in npcOptions" :key="npc" :value="npc">{{ npc }}</option>
      </select>
    </label>

    <label class="diff-filter-bar__field">
      rule
      <select :value="filters.rule ?? ''" @change="update('rule', ($event.target as HTMLSelectElement).value)">
        <option value="">(any)</option>
        <option v-for="rule in ruleOptions" :key="rule" :value="rule">{{ rule }}</option>
      </select>
    </label>

    <label class="diff-filter-bar__field">
      type
      <select :value="filters.type ?? ''" @change="update('type', ($event.target as HTMLSelectElement).value)">
        <option value="">(any)</option>
        <option v-for="t in TYPE_OPTIONS" :key="t" :value="t">{{ t }}</option>
      </select>
    </label>
  </div>
</template>

<style scoped>
.diff-filter-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 6px 16px;
  border-bottom: 1px solid var(--c-hairline-soft);
  font-size: var(--fs-secondary);
  color: var(--c-text-dim);
  flex-wrap: wrap;
}

.diff-filter-bar__field {
  display: flex;
  align-items: center;
  gap: 5px;
}

.diff-filter-bar__field select {
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  color: var(--c-text-body);
  background: var(--c-chip-active-fill);
  border: 1px solid var(--c-chip-active-border);
  border-radius: var(--radius-chip);
  padding: 1px 6px;
}
</style>
