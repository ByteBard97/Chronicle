<script setup lang="ts">
/**
 * LiveDockPill — the LIVE dock pill at the right of the timeline bar
 * (map-c-skyrim.dc.html:235-241). Lane 16: reads the real `liveDock` store
 * (`src/stores/liveDock.ts`) directly instead of a fixture-driven `live`
 * prop — same store `LiveDockIndicator.vue` (global chrome) already
 * consumes. Only the *docked* form of `statusText` is frozen verbatim by
 * the work packet ("LIVE — docked · following newest frame · +N events ·
 * scrub to detach"); the store's own doc comment records that the
 * detached form is a reasonable, non-frozen read of the same fields.
 *
 * `TimelineBar.vue` is responsible for mirroring `stores/mapData.ts`'s
 * docked/tailing state into this store (mapData.ts is this lane's
 * do-not-touch boundary, so it can't wire itself); this component just
 * renders whatever the store currently says.
 */
import { useLiveDockStore } from "../../stores/liveDock";

const liveDock = useLiveDockStore();
</script>

<template>
  <div
    class="live-dock"
    :class="{ 'live-dock--docked': liveDock.docked }"
    :data-docked="liveDock.docked"
    data-testid="live-dock-pill"
  >
    <div class="live-dock__row">
      <span class="live-dock__dot" />
      <span class="live-dock__text">{{ liveDock.statusText }}</span>
    </div>
  </div>
</template>

<style scoped>
.live-dock {
  flex: none;
  border: 1px solid rgba(201, 168, 106, 0.3);
  border-radius: var(--radius-chip);
  padding: 4px 9px;
  background: rgba(255, 255, 255, 0.02);
}

.live-dock--docked {
  border-color: #7e3030;
  background: rgba(224, 82, 82, 0.08);
}

.live-dock__row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.live-dock__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--live);
  box-shadow: 0 0 6px rgba(224, 82, 82, 0.7);
  animation: cpulse 1.4s infinite;
}

.live-dock__text {
  color: var(--c-text-dim);
  font-size: 10px;
  white-space: nowrap;
}

.live-dock--docked .live-dock__text {
  color: #ffb3ad;
}
</style>
