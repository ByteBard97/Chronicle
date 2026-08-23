<script setup lang="ts">
/**
 * TimelineBar — the bottom timeline strip of the map view
 * (map-c-skyrim.dc.html:205-254). Composes the transport cluster, the
 * track (day ticks + typed event markers + D8–D9 heat stripe + playhead),
 * the LIVE dock pill, and the bottom marker-legend line.
 *
 * Defaults reproduce the approved mockup render: observer salience, LIVE
 * detached. Data comes from src/fixtures/whiterunMock.ts (buildEvents,
 * DAY_TICKS, LIVE_STATES) — do not re-derive here.
 */
import { computed } from "vue";
import {
  buildEvents,
  DAY_TICKS,
  LIVE_STATES,
  type Salience,
} from "../../fixtures/whiterunMock";
import TransportControls from "./TransportControls.vue";
import TimelineTrack from "./TimelineTrack.vue";
import LiveDockPill from "./LiveDockPill.vue";
import TimelineLegend from "./TimelineLegend.vue";

const props = withDefaults(
  defineProps<{
    salience?: Salience;
    docked?: boolean;
  }>(),
  { salience: "observer", docked: false },
);

const events = computed(() => buildEvents(props.salience));
const live = computed(() =>
  props.docked ? LIVE_STATES.docked : LIVE_STATES.detached,
);
</script>

<template>
  <div class="timeline-bar" data-testid="timeline-bar">
    <div class="timeline-bar__row">
      <TransportControls />
      <TimelineTrack
        :events="events"
        :days="DAY_TICKS"
        :live="live"
        :docked="docked"
      />
      <LiveDockPill :docked="docked" :live="live" />
    </div>
    <TimelineLegend :event-count="events.length" />
  </div>
</template>

<style scoped>
.timeline-bar {
  min-height: 115px; /* measured from the rendered mockup (content-driven there); 98px understated it and shrank the map square */
  flex: none;
  border-top: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-inspector);
  display: flex;
  flex-direction: column;
  padding: var(--space-2) var(--space-4);
  gap: var(--space-1);
}

.timeline-bar__row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
  min-height: 0;
}
</style>
