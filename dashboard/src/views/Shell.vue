<script setup lang="ts">
// M1 smoke-test page. This is deliberately not a view (that's a later
// packet): it exists to prove the app frame boots, the run picker reaches
// runs/index.json (and tolerates its absence), URL state round-trips
// through actual navigation, and the selection/salience Pinia stores are
// reachable — nothing here is meant to look finished.
import { useUrlState } from "../state/urlState";
import { useSelectionStore } from "../stores/selection";
import { useSalienceStore, SALIENCE_LEVELS } from "../stores/salience";
import RunPicker from "../components/RunPicker.vue";

const urlState = useUrlState();
const selection = useSelectionStore();
const salience = useSalienceStore();
</script>

<template>
  <div>
    <p>Chronicle dashboard shell (M1 scaffold — no views yet).</p>

    <RunPicker v-model="urlState.run.value" />

    <div>
      <label for="tick-stepper">t</label>
      <input
        id="tick-stepper"
        type="number"
        :value="urlState.t.value ?? ''"
        @change="
          urlState.t.value = ($event.target as HTMLInputElement).value
            ? Number(($event.target as HTMLInputElement).value)
            : null
        "
      />
    </div>

    <div>
      <label for="salience-level">salience</label>
      <select
        id="salience-level"
        :value="salience.level"
        @change="
          salience.setLevel(
            ($event.target as HTMLSelectElement).value as typeof salience.level,
          )
        "
      >
        <option v-for="level in SALIENCE_LEVELS" :key="level" :value="level">
          {{ level }}
        </option>
      </select>
    </div>

    <p>selected: {{ selection.selectedIds.join(", ") || "(none)" }}</p>

    <div id="empty-view-area">
      <!-- Views (NPC inspector, encounter feed, map, ...) are a later packet. -->
    </div>
  </div>
</template>
