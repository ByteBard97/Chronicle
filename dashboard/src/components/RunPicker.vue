<script setup lang="ts">
// Global chrome, M1 scope only: an unstyled run picker over runs/index.json.
// No styling, no view — that's later-packet work (see work packet's "if you
// find yourself styling, stop").
import { onMounted } from "vue";
import { useRunsStore } from "../stores/runs";

const runsStore = useRunsStore();
onMounted(() => {
  void runsStore.load();
});

const model = defineModel<string | null>();
</script>

<template>
  <div>
    <label for="run-picker">run</label>
    <select
      id="run-picker"
      :value="model ?? ''"
      :disabled="runsStore.status === 'loading'"
      @change="model = ($event.target as HTMLSelectElement).value || null"
    >
      <option value="">(none selected)</option>
      <option
        v-for="run in runsStore.runs"
        :key="run.run_id"
        :value="run.run_id"
      >
        {{ run.run_id }}
      </option>
    </select>
    <span v-if="runsStore.status === 'missing'">
      no runs/index.json yet — nothing to pick from
    </span>
    <span v-else-if="runsStore.status === 'error'">
      failed to load runs/index.json: {{ runsStore.error }}
    </span>
  </div>
</template>
