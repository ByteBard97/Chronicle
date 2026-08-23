<script setup lang="ts">
/**
 * LiveDockPill — the LIVE dock pill at the right of the timeline bar
 * (map-c-skyrim.dc.html:235-241, values from renderVals():298-300).
 * Two display states from LIVE_STATES:
 *  - detached (default): gold hairline, "LIVE · t 45,187" /
 *    "detached — scrubbed to D11 · ⇥ dock"
 *  - docked: red treatment (border #7e3030, bg rgba(224,82,82,.08),
 *    text #ffb3ad), "LIVE — docked · following newest frame" /
 *    "+38 events since D14 · scrub to detach"
 *
 * NOTE: tokens.css's dock-docked/dock-detached variable names are inverted
 * relative to the mockup (there the *docked* state carries the red
 * treatment), so this component uses the mockup's values directly.
 */
import type { LIVE_STATES } from "../../fixtures/whiterunMock";

defineProps<{
  docked: boolean;
  live: (typeof LIVE_STATES)[keyof typeof LIVE_STATES];
}>();
</script>

<template>
  <div
    class="live-dock"
    :class="{ 'live-dock--docked': docked }"
    :data-docked="docked"
    data-testid="live-dock-pill"
  >
    <div class="live-dock__row">
      <span class="live-dock__dot" />
      <span class="live-dock__line1">{{ live.line1 }}</span>
    </div>
    <a href="#" class="live-dock__line2" @click.prevent>{{ live.line2 }}</a>
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

.live-dock__line1 {
  color: var(--c-text-dim);
  font-size: 10px;
  white-space: nowrap;
}

.live-dock--docked .live-dock__line1 {
  color: #ffb3ad;
}

.live-dock__line2 {
  display: block;
  font-size: var(--fs-micro);
  color: var(--c-text-faint);
  white-space: nowrap;
}
</style>
