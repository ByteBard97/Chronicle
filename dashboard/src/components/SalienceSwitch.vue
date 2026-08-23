<script setup lang="ts">
/**
 * SalienceSwitch — the global salience filter control (ui-spec §2:
 * Developer/Observer/Story, "a switch over one design, never a fork" —
 * design-tokens.md's conventions section). Visual: the top-bar
 * segmented control in map-c-skyrim.dc.html:28-32.
 *
 * Coordination note (work packet): Lane 6 owns the salience-filter
 * store (src/stores/salience.ts) and was going to land unstyled markup
 * for this lane to skin in place. As of this build nothing under
 * src/components/ existed for it — only the store — so this is built
 * fresh as a presentational component: typed props in, one emit out,
 * no store import. It takes SalienceLevel as a *type* import so either
 * lane's wiring direction works without a rename.
 *
 * Finding: the mockup's own prop enum (data-props in the .dc.html) only
 * declares two salience values, ["observer","story"] — DEV has no
 * traced visual state in the approved mockup. The DEV/inactive segment
 * styling below is extrapolated from the shared inactive-tab treatment
 * (dim text, no fill) rather than a state the mockup actually shows
 * active. Called out in the lane-7 report.
 */
import type { SalienceLevel } from "../stores/salience";

defineProps<{
  mode: SalienceLevel;
}>();

const emit = defineEmits<{
  "update:mode": [mode: SalienceLevel];
}>();

const OPTIONS: { level: SalienceLevel; label: string }[] = [
  { level: "developer", label: "DEV" },
  { level: "observer", label: "OBSERVER" },
  { level: "story", label: "STORY" },
];
</script>

<template>
  <div class="salience-switch" role="group" aria-label="salience filter">
    <button
      v-for="opt in OPTIONS"
      :key="opt.level"
      type="button"
      class="salience-switch__option"
      :class="{ 'salience-switch__option--active': mode === opt.level }"
      :aria-pressed="mode === opt.level"
      @click="emit('update:mode', opt.level)"
    >
      {{ opt.label }}
    </button>
  </div>
</template>

<style scoped>
.salience-switch {
  display: flex;
  border: 1px solid var(--c-hairline);
  border-radius: var(--radius-chip);
  overflow: hidden;
  flex: none;
}

.salience-switch__option {
  appearance: none;
  border: none;
  border-left: 1px solid var(--c-hairline);
  background: transparent;
  color: var(--c-text-dim);
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  padding: 3px 10px;
  cursor: pointer;
  white-space: nowrap;
}

.salience-switch__option:first-child {
  border-left: none;
}

.salience-switch__option--active {
  background: var(--c-chip-active-fill);
  color: var(--c-accent-hover);
}
</style>
