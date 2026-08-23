<script setup lang="ts">
// Global chrome: run picker over runs/index.json. Lane 6 built the
// unstyled <select> (structure/logic below is untouched — same
// element, same id, same v-model contract); this lane skins it in
// place per the file-boundary note rather than rebuilding it as a
// custom listbox (the mockup's faux-dropdown link at
// map-c-skyrim.dc.html:23 is presentation of a real <select>, not a
// different control).
//
// Lane 15 Task 2: when no run is selected (`model` is null -- no `run`
// in the URL), the select DISPLAYS the registry's most recent run
// (`runsStore.mostRecentRunId`) rather than "(none selected)", matching
// the M3 mockup's top bar. This is display-only: `displayValue` never
// writes back to `model` on its own, so `urlState.run`'s "defaults
// omitted from the URL" law (state/urlState.ts) is untouched -- the
// default becomes real (URL-persisted) only when the user actually
// picks something (`@change`, unchanged below) or a deep link sets
// `run` directly. An empty/missing registry falls `mostRecentRunId`
// back to `null`, so `displayValue` falls back to `''` -- the original
// "(none selected)" behavior, unchanged.
import { computed, onMounted } from "vue";
import { useRunsStore } from "../stores/runs";

const runsStore = useRunsStore();
onMounted(() => {
  void runsStore.load();
});

const model = defineModel<string | null>();
const displayValue = computed(() => model.value ?? runsStore.mostRecentRunId ?? "");
</script>

<template>
  <div class="run-picker">
    <label for="run-picker" class="sr-only">run</label>
    <select
      id="run-picker"
      class="run-picker__select"
      :value="displayValue"
      :disabled="runsStore.status === 'loading'"
      @change="model = ($event.target as HTMLSelectElement).value || null"
    >
      <option value="">(none selected)</option>
      <option
        v-for="run in runsStore.pickableRuns"
        :key="run.run_id"
        :value="run.run_id"
      >
        {{ run.run_id }}
      </option>
    </select>
    <span v-if="runsStore.status === 'missing'" class="run-picker__note">
      no runs/index.json yet — showing the mock-t0 dev fixture only
    </span>
    <span v-else-if="runsStore.status === 'error'" class="run-picker__note">
      failed to load runs/index.json: {{ runsStore.error }}
    </span>
  </div>
</template>

<style scoped>
.run-picker {
  display: flex;
  align-items: center;
  gap: 8px;
}

.run-picker__select {
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  color: var(--c-text-body);
  background: var(--c-chip-active-fill);
  border: 1px solid var(--c-chip-active-border);
  border-radius: var(--radius-chip);
  padding: 2px 8px;
}

.run-picker__note {
  color: var(--c-text-dim);
  font-size: var(--fs-secondary);
  white-space: nowrap;
}
</style>
