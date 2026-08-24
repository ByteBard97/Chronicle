<script setup lang="ts">
/**
 * TimelineBar — the bottom timeline strip of the map view
 * (map-c-skyrim.dc.html:205-254). Composes the transport cluster, the
 * track (day ticks + typed event markers + heat-stripe + playhead), the
 * LIVE dock pill, and the bottom marker-legend line.
 *
 * Lane 16: reads the run's real trace/event streams straight from the
 * lane-14 map store (`useMapDataStore()`) rather than the
 * `whiterunMock.ts` fixture — pulls from the store directly instead of a
 * parent threading props down. `mapData.ts` itself is this lane's
 * do-not-touch boundary (read-only); markers/day-ticks/heat-stripe are
 * derived here via the pure `src/derived/timelineMarkers.ts` module.
 *
 * Lane 54 (M7 gate fix): promoted from a `MapScreen.vue`-only mount to
 * global chrome, per ui-spec §2's own framing of the timeline as global,
 * not map-specific -- it's now mounted once in `App.vue` so it renders on
 * every route. Reading straight from the shared Pinia store singleton
 * (rather than props from a specific parent) is exactly what makes that
 * move a relocation, not a rewrite: this component doesn't know or care
 * which view is currently mounted above it. The small "TIMELINE" caption
 * added to the row below is this lane's answer to the packet's
 * discoverability ask (task 3) -- the bar is always-visible chrome now, so
 * a dedicated nav tab that navigates nowhere would be worse than a plain
 * in-place label.
 *
 * `urlState.t` is the playhead throughout (ui-spec §1.2): marker clicks
 * and `TransportControls`' play/skip/step all read and write it directly;
 * this component's own job is deriving what to show, not owning `t`.
 *
 * `liveDock` wiring: `stores/liveDock.ts` is a separate, already-global
 * store (its docked/detached chrome text is also driven by
 * `stores/frameLog.ts` for `FeedScreen`). Since `mapData.ts` can't be
 * edited to wire itself, this component mirrors `mapData.docked` and its
 * record-stream growth into `liveDock` the same way `frameLog.ts` does —
 * both screens feed the one global "LIVE dock" concept, and only one
 * screen is mounted at a time today, so there's no dual-write hazard yet.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import TransportControls from "./TransportControls.vue";
import TimelineTrack from "./TimelineTrack.vue";
import LiveDockPill from "./LiveDockPill.vue";
import TimelineLegend from "./TimelineLegend.vue";
import { useMapDataStore } from "../../stores/mapData";
import { useLiveDockStore } from "../../stores/liveDock";
import { useUrlState } from "../../state/urlState";
import {
  MARKER_TYPE_REGISTRY,
  computeDayTicks,
  computeHeatStripe,
  computeMaxTick,
  deriveTimelineMarkers,
  groupCoincidentMarkers,
  tickToPercent,
  type MarkerType,
} from "../../derived/timelineMarkers";

const mapData = useMapDataStore();
const liveDock = useLiveDockStore();
const urlState = useUrlState();

// Mirror mapData's LIVE-tail docking into the global liveDock store (see
// header -- mapData.ts is out of this lane's file boundary).
watch(
  () => mapData.docked,
  (docked) => {
    if (docked) liveDock.dock();
    else liveDock.detach();
  },
  { immediate: true },
);

let priorRecordCount = mapData.traceRecords.length + mapData.eventRecords.length;
watch(
  () => mapData.traceRecords.length + mapData.eventRecords.length,
  (count) => {
    if (mapData.docked && count > priorRecordCount) {
      liveDock.recordNewEvents(count - priorRecordCount);
    }
    priorRecordCount = count;
  },
);

const maxTick = computed(() => computeMaxTick(mapData.traceRecords, mapData.eventRecords));
const allMarkers = computed(() =>
  deriveTimelineMarkers(mapData.traceRecords, mapData.eventRecords, maxTick.value),
);
const dayTicks = computed(() => computeDayTicks(maxTick.value));

// Type filter -- view-local UI state (not URL, per the pinned contract).
// Default: every registered type active, including the two with no
// producer yet (harmless -- they never have markers to filter anyway).
const activeTypes = ref<Set<MarkerType>>(new Set(MARKER_TYPE_REGISTRY.map((m) => m.type)));
function toggleType(type: MarkerType) {
  const next = new Set(activeTypes.value);
  if (next.has(type)) next.delete(type);
  else next.add(type);
  activeTypes.value = next;
}

const filteredMarkers = computed(() => allMarkers.value.filter((m) => activeTypes.value.has(m.type)));

// Post-delivery correction: coincident markers (same tick -> same pos,
// e.g. this run's death + crime-witnessed at t=0) must collapse to one
// clickable node before heat-stripe bucketing, or the later one in DOM
// order silently eats every click meant for the marker(s) underneath it
// (see groupCoincidentMarkers' header). This also makes bucket density
// reflect distinct positions rather than raw per-tick event counts.
const groupedMarkers = computed(() => groupCoincidentMarkers(filteredMarkers.value));

// Heat-stripe bucketing needs the track's rendered pixel width. The track
// itself stays a pure props-in renderer, so this component measures the
// wrapper it renders the track into and recomputes on resize.
const trackWrapEl = ref<HTMLElement | null>(null);
const trackWidthPx = ref(0);
let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  if (trackWrapEl.value) {
    trackWidthPx.value = trackWrapEl.value.clientWidth;
    if (typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver((entries) => {
        trackWidthPx.value = entries[0]?.contentRect.width ?? 0;
      });
      resizeObserver.observe(trackWrapEl.value);
    }
  }
});
onBeforeUnmount(() => resizeObserver?.disconnect());

const heatStripe = computed(() => computeHeatStripe(groupedMarkers.value, trackWidthPx.value));

// Current playhead tick: `urlState.t` is the playhead throughout, per the
// pinned contract. It's `null` only while docked (LIVE, following the
// newest known record) -- `mapData.socialState.tick` is the fallback for
// exactly that case (MapScreen's combined [run, t] watcher keeps it at
// the reconstructed latest-known tick whenever `t` is null).
const currentTick = computed(() => Math.max(urlState.t.value ?? mapData.socialState.tick, 0));
const playheadPos = computed(() => tickToPercent(currentTick.value, maxTick.value));

/** `D<n> HH:00` from the tick alone (ADR-0010: 1 tick = 1 game-hour, 24 ticks = 1 day) -- no schedule data needed. */
function formatTickLabel(tick: number): string {
  const day = Math.floor(tick / 24) + 1;
  const hour = tick % 24;
  return `t ${tick.toLocaleString()} · D${day} ${String(hour).padStart(2, "0")}:00`;
}
const playheadLabel = computed(() => formatTickLabel(currentTick.value));

function onMarkerClick(tick: number) {
  urlState.t.value = tick;
}
</script>

<template>
  <div class="timeline-bar" data-testid="timeline-bar">
    <div class="timeline-bar__row">
      <span class="timeline-bar__label">TIMELINE</span>
      <TransportControls :max-tick="maxTick" />
      <div ref="trackWrapEl" class="timeline-bar__track-wrap">
        <TimelineTrack
          :heat="heatStripe"
          :days="dayTicks"
          :playhead-pos="playheadPos"
          :playhead-label="playheadLabel"
          :docked="mapData.docked"
          @marker-click="onMarkerClick"
        />
      </div>
      <LiveDockPill />
    </div>
    <TimelineLegend
      :event-count="filteredMarkers.length"
      :active-types="activeTypes"
      @toggle-type="toggleType"
    />
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

.timeline-bar__label {
  font-family: var(--font-display);
  color: var(--c-panel-title);
  flex: none;
  white-space: nowrap;
  font-size: 8px;
  letter-spacing: 0.16em;
}

.timeline-bar__track-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
}
</style>
