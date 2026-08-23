<script setup lang="ts">
/**
 * MapScreen — the full approved-mockup page (design/map-c-skyrim.dc.html):
 * 44px top chrome strip + MapView (map well + inspector) + the 98px
 * timeline footer. This is the composition root lane 8's visual-diff
 * harness screenshots for parity against the mockup.
 *
 * Data is the mock fixture (src/fixtures/whiterunMock.ts) via the child
 * components; Lane 6's reader wires real per-tick state at M3.
 */
import RunPicker from "../components/RunPicker.vue";
import SalienceSwitch from "../components/SalienceSwitch.vue";
import NpcInspector from "../components/NpcInspector.vue";
import MapView from "./MapView.vue";
import TimelineBar from "../components/timeline/TimelineBar.vue";
import { useSalienceStore } from "../stores/salience";

const salience = useSalienceStore();
</script>

<template>
  <div class="map-screen">
    <header class="map-screen__chrome">
      <div class="map-screen__wordmark">CHRONICLE</div>
      <div class="map-screen__runmeta">
        <RunPicker />
        <span class="map-screen__meta">branch a3f2c9.g0</span>
        <span class="map-screen__meta">seed 1181</span>
      </div>
      <div class="map-screen__spacer" />
      <SalienceSwitch
        :mode="salience.level"
        @update:mode="salience.setLevel($event)"
      />
      <span class="map-screen__url">?run=t6-jarl-01&amp;t=31442&amp;sel=fralia&amp;lens=C-114 ⧉</span>
    </header>

    <div class="map-screen__body">
      <MapView>
        <template #inspector>
          <NpcInspector :salience="salience.level" />
        </template>
      </MapView>
    </div>

    <TimelineBar />
  </div>
</template>

<style scoped>
.map-screen {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--c-page-bg);
  overflow: hidden;
}

/* 44px chrome strip — map-c-skyrim.dc.html:19 */
.map-screen__chrome {
  height: 44px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 16px;
  border-bottom: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-strong);
}

.map-screen__wordmark {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.3em;
  color: var(--c-accent-hover);
}

.map-screen__runmeta {
  display: flex;
  gap: 8px;
  align-items: center;
  flex: none;
}

.map-screen__meta {
  color: var(--c-text-dim);
  white-space: nowrap;
}

.map-screen__spacer {
  flex: 1;
}

.map-screen__url {
  color: var(--c-text-faint);
  font-size: 10px;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.map-screen__body {
  flex: 1;
  min-height: 0;
  display: flex;
}
</style>
