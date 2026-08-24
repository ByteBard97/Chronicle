<script setup lang="ts">
/**
 * DivergenceList — the PRIMARY rendering of CompareScreen (ui-spec §3.9's
 * v1.1 strengthening, verbatim: "making the user visually hunt a map for a
 * table query is the wrong primary"). Every entity whose reconstructed
 * state differs between run A and run B at T, ranked by first-divergence
 * tick then blast radius (`derived/runCompare.ts`'s `computeDivergenceList`).
 * Selecting a row is how the aligned maps get told which NPC to
 * center-and-mark (the spec's "linking both maps... on click").
 */
import type { DivergenceEntry } from "../../derived/runCompare";

defineProps<{
  entries: DivergenceEntry[];
  selectedNpcId: string | null;
}>();

const emit = defineEmits<{ select: [npcId: string] }>();
</script>

<template>
  <div class="divergence-list">
    <table>
      <thead>
        <tr>
          <th>entity</th>
          <th>first divergence</th>
          <th>blast radius</th>
          <th>cascade</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="entries.length === 0" class="divergence-list__empty-row">
          <td colspan="4">no divergence between run A and run B at this tick</td>
        </tr>
        <tr
          v-for="entry in entries"
          :key="entry.npcId"
          class="divergence-list__row"
          :class="{ 'divergence-list__row--selected': entry.npcId === selectedNpcId }"
          tabindex="0"
          role="button"
          :aria-pressed="entry.npcId === selectedNpcId"
          @click="emit('select', entry.npcId)"
          @keydown.enter="emit('select', entry.npcId)"
        >
          <td class="divergence-list__npc">{{ entry.npcId }}</td>
          <td>t {{ entry.firstDivergenceTick }}</td>
          <td>{{ entry.blastRadius }}</td>
          <td class="divergence-list__cascade">
            <span v-for="d in entry.deltas" :key="d.key" class="divergence-list__chip">
              {{ d.label }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.divergence-list {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead th {
  position: sticky;
  top: 0;
  text-align: left;
  padding: 6px 8px;
  font-size: var(--fs-micro);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--c-text-faint);
  background: var(--c-panel-glass-strong);
  border-bottom: 1px solid var(--c-hairline);
}

tbody td {
  padding: 5px 8px;
  font-size: var(--fs-secondary);
  color: var(--c-text-body);
  border-bottom: 1px solid var(--c-hairline-soft);
  vertical-align: top;
}

.divergence-list__row {
  cursor: pointer;
}

.divergence-list__row:hover {
  background: var(--c-panel-glass-soft);
}

.divergence-list__row--selected {
  background: var(--c-chip-active-fill);
}

.divergence-list__npc {
  font-family: var(--font-data);
  color: var(--c-accent);
  white-space: nowrap;
}

.divergence-list__cascade {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.divergence-list__chip {
  border: 1px solid var(--c-hairline);
  border-radius: var(--radius-chip);
  padding: 1px 6px;
  font-size: var(--fs-chip);
  color: var(--c-text-dim);
  white-space: nowrap;
}

.divergence-list__empty-row td {
  color: var(--c-text-faint);
  padding: 16px 8px;
}
</style>
