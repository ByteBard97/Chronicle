<script setup lang="ts">
/**
 * MapView — the map screen from the approved mockup
 * (design/map-c-skyrim.dc.html), observer salience, stain lens on,
 * glyphs on, LIVE detached.
 *
 * Scope notes:
 * - The 44px top chrome strip above this view is another lane's; this
 *   view starts at the flex:1 row below it (map well + inspector slot).
 * - The 98px timeline footer below the mockup's map row is also another
 *   lane's; not rendered here.
 * - The right-hand column is a 380px placeholder aside — the NPC
 *   inspector itself is another lane's (mockup: 372px, see packet).
 *
 * Layer state lives here and is v-modeled up from LayerToggles;
 * salience comes from the global salience store (story switches the
 * satellite sub-line to its story variant; observer/developer render
 * the observer strings — the mockup only defines observer/story).
 */
import { computed, ref } from "vue";
import { useSalienceStore } from "../stores/salience";
import PanelGlass from "../components/PanelGlass.vue";
import MapBackdrop from "../components/map/MapBackdrop.vue";
import RouteOverlay from "../components/map/RouteOverlay.vue";
import SatelliteNode from "../components/map/SatelliteNode.vue";
import CarrierMarker from "../components/map/CarrierMarker.vue";
import LocationLabels from "../components/map/LocationLabels.vue";
import MarkerLayer from "../components/map/MarkerLayer.vue";
import LensPanel from "../components/map/LensPanel.vue";
import LayerToggles from "../components/map/LayerToggles.vue";
import StageLegend from "../components/map/StageLegend.vue";
import GlyphLegend from "../components/map/GlyphLegend.vue";
import ZoomControls from "../components/map/ZoomControls.vue";

const salience = useSalienceStore();
const isStory = computed(() => salience.level === "story");

/** map-c-skyrim.dc.html:293 — mkSub, observer vs story variant. */
const satelliteSub = computed(() =>
  isStory.value
    ? "the word has not yet arrived · 0 of 9"
    : "satellite · 0/9 heard",
);

// Map layer state (defaults = the approved render: all on, lens on).
const showGlyphs = ref(true);
const showLabels = ref(true);
const showRoutes = ref(true);
const stainLens = ref(true);
</script>

<template>
  <div class="map-view">
    <div class="map-view__well">
      <MapBackdrop>
        <RouteOverlay v-if="showRoutes" />
        <SatelliteNode :sub-line="satelliteSub" />
        <CarrierMarker />
        <LocationLabels v-if="showLabels" />
        <MarkerLayer :stain-lens="stainLens" :show-glyphs="showGlyphs" />
      </MapBackdrop>

      <div class="map-view__left">
        <LensPanel />
        <LayerToggles
          v-model:show-glyphs="showGlyphs"
          v-model:show-labels="showLabels"
          v-model:show-routes="showRoutes"
          v-model:stain-lens="stainLens"
        />
      </div>

      <ZoomControls />

      <PanelGlass class="map-view__legend" tone="soft" :padded="false">
        <StageLegend />
        <GlyphLegend />
      </PanelGlass>
    </div>

    <!-- INSPECTOR SLOT: MapScreen mounts the NPC inspector here via the
         named slot; empty renders the reserved 380px aside. Mockup
         renders it at 372px with the same border-left + .92 glass. -->
    <aside class="map-view__inspector" aria-label="inspector slot">
      <slot name="inspector" />
    </aside>
  </div>
</template>

<style scoped>
.map-view {
  flex: 1;
  min-height: 0;
  display: flex;
  background: var(--c-page-bg);
  font-size: var(--fs-body);
}

.map-view__well {
  flex: 1;
  position: relative;
  background: var(--c-map-well);
  overflow: hidden;
  display: flex;
  justify-content: center;
}

.map-view__left {
  position: absolute;
  left: 12px;
  top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 252px;
}

.map-view__legend {
  position: absolute;
  right: 12px;
  bottom: 12px;
  /* mockup border rgba(201,168,106,.22) — between --c-hairline-soft
   * (.18) and --c-hairline (.26); no exact token, literal from
   * map-c-skyrim.dc.html:99 */
  border-color: rgba(201, 168, 106, 0.22);
  padding: 7px 11px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: var(--fs-micro);
}

.map-view__inspector {
  /* 372px — the mockup's exact inspector width (map-c-skyrim.dc.html);
     visual parity beats the packet's rounder 380px. */
  width: 372px;
  flex: none;
  border-left: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-inspector);
}
</style>
