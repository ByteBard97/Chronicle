<script setup lang="ts">
/** Renders every live marker derived from ChronicleBridge's latest snapshot (stores/livePositions.ts). */
import LiveMarker from "./LiveMarker.vue";
import type { LiveMarker as LiveMarkerData } from "../../derived/livePositions";

defineProps<{
  markers: LiveMarkerData[];
}>();
</script>

<template>
  <div class="live-marker-layer">
    <LiveMarker v-for="m in markers" :key="m.id" :id="m.id" :name="m.name" :left="m.left" :top="m.top" />
  </div>
</template>

<style scoped>
.live-marker-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
</style>
