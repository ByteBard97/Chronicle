<script setup lang="ts">
/**
 * LiveMarker -- one ChronicleBridge live-position dot. Deliberately not
 * NpcMarker: live positions carry no rumor stage/belief state (they're a
 * separate real-time feed, derived/livePositions.ts's header), so there
 * is no stage color/glyph to render -- just a neutral live-position dot.
 *
 * Click-to-reveal name: `name` is the actor's in-game display name (e.g.
 * "Idolaf Battle-Born"), read directly off the actor in ChronicleBridge
 * (SpatialStreamer.cpp) -- independent of `id`, which is either a
 * resolved Chronicle npc_id or the anonymous "<plugin>:<formid>" fallback
 * (IdentityMap.cpp's hand-maintained table is usually empty/incomplete,
 * but the game always has a display name). Clicking toggles a persistent
 * label instead of relying on the hover-only browser title tooltip, since
 * a dense cluster of dots makes precise hovering fiddly.
 */
import { ref } from "vue";

const props = defineProps<{
  id: string;
  name: string;
  left: number;
  top: number;
}>();

const showLabel = ref(false);

function toggleLabel() {
  showLabel.value = !showLabel.value;
}
</script>

<template>
  <div class="live-marker" :style="{ left: `${left}%`, top: `${top}%` }">
    <button
      type="button"
      class="live-marker__dot"
      :title="props.name || props.id"
      :aria-label="props.name || props.id"
      :aria-pressed="showLabel"
      @click="toggleLabel"
    />
    <div v-if="showLabel" class="live-marker__label">{{ props.name || props.id }}</div>
  </div>
</template>

<style scoped>
.live-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  /* The layer above sets pointer-events: none so live markers never block
   * map interactions elsewhere; the dot itself opts back in so it's still
   * clickable. */
  pointer-events: auto;
}

.live-marker__dot {
  display: block;
  width: 8px;
  height: 8px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: var(--c-live-marker, #4ade80);
  box-shadow: 0 0 0 2px rgba(8, 10, 13, 0.9);
  cursor: pointer;
  /* Larger invisible hit area than the 8px dot -- dense clusters of live
   * markers make precise clicking on the visible dot alone fiddly. */
  position: relative;
}
.live-marker__dot::after {
  content: "";
  position: absolute;
  inset: -6px;
}

.live-marker__label {
  position: absolute;
  left: 50%;
  bottom: calc(100% + 4px);
  transform: translateX(-50%);
  white-space: nowrap;
  background: rgba(8, 10, 13, 0.9);
  color: var(--c-text-primary, #e8e6df);
  border: 1px solid var(--c-hairline, rgba(201, 168, 106, 0.26));
  border-radius: 3px;
  padding: 2px 6px;
  font-size: 11px;
  pointer-events: none;
}
</style>
