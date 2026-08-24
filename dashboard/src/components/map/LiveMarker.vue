<script setup lang="ts">
/**
 * LiveMarker -- one ChronicleBridge live-position dot. Deliberately not
 * NpcMarker: live positions carry no rumor stage/belief state (they're a
 * separate real-time feed, derived/livePositions.ts's header), so there
 * is no stage color/glyph to render -- just a neutral live-position dot,
 * labeled by the resolved id (a Chronicle npc_id or the plugin's generic
 * "<plugin>:<formid>" fallback identity, wire contract's `NpcPosition.id`).
 */
defineProps<{
  id: string;
  left: number;
  top: number;
}>();
</script>

<template>
  <div class="live-marker" :style="{ left: `${left}%`, top: `${top}%` }" :title="id">
    <div class="live-marker__dot" />
  </div>
</template>

<style scoped>
.live-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.live-marker__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--c-live-marker, #4ade80);
  box-shadow: 0 0 0 2px rgba(8, 10, 13, 0.9);
}
</style>
