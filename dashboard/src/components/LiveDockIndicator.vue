<script setup lang="ts">
// Global chrome: LIVE dock indicator (ui-spec §1.3/§2). Landed by Lane 6
// as unstyled markup for this lane to skin in place — the file boundary
// note's SalienceSwitch precedent, applied a second time. Structure/
// store wiring below is untouched; only classes + <style> were added.
// Visual: the LIVE dock pill (map-c-skyrim.dc.html:235-241), pulsing dot
// + status text + a "resume" action, recolored docked vs detached.
import { useLiveDockStore } from "../stores/liveDock";

const liveDock = useLiveDockStore();
</script>

<template>
  <div
    class="live-dock-indicator"
    :class="{ 'live-dock-indicator--detached': !liveDock.docked }"
    :data-docked="liveDock.docked"
  >
    <span class="live-dock-indicator__dot" />
    <span class="live-dock-indicator__text">{{ liveDock.statusText }}</span>
    <button
      v-if="!liveDock.docked"
      type="button"
      class="live-dock-indicator__dock-btn"
      @click="liveDock.dock()"
    >
      dock to LIVE
    </button>
  </div>
</template>

<style scoped>
.live-dock-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--dock-docked-border);
  background: var(--dock-docked-bg);
  border-radius: var(--radius-chip);
  padding: 4px 9px;
  font-size: var(--fs-secondary);
  color: var(--dock-docked-text);
}

.live-dock-indicator--detached {
  border-color: var(--dock-detached-border);
  background: var(--dock-detached-bg);
  color: var(--dock-detached-text);
}

.live-dock-indicator__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--live);
  box-shadow: 0 0 6px rgba(224, 82, 82, 0.7);
  flex: none;
  animation: cpulse 1.4s infinite;
}

.live-dock-indicator__text {
  white-space: nowrap;
}

.live-dock-indicator__dock-btn {
  appearance: none;
  border: 1px solid currentColor;
  background: transparent;
  color: inherit;
  font-family: inherit;
  font-size: var(--fs-micro);
  border-radius: var(--radius-chip);
  padding: 1px 6px;
  cursor: pointer;
  white-space: nowrap;
}
</style>
