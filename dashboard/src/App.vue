<script setup lang="ts">
/**
 * App.vue — the actual router-outlet wrapper (confirmed by reading
 * `router/index.ts`: every route is a distinct top-level view component,
 * and `Shell.vue` -- despite its name -- is only ever mounted at `/`, not
 * a shared layout). Lane 54 (M7 gate fix): ui-spec §2 frames the timeline
 * as global chrome, but it only ever rendered inside `MapScreen.vue`. This
 * is the one edit point common to every route, so `TimelineBar` is mounted
 * here instead of being duplicated into each view's own template.
 *
 * Data: `TimelineBar` reads `stores/mapData.ts` directly (lane 16), but
 * that store is only ever *populated* by `MapScreen.vue`'s combined
 * `[run, t]` watcher (frameLog.ts's documented "load must finish before a
 * tick decision" hazard -- a single owner, deliberately). Making the
 * timeline global without also making its data global would just render
 * an always-empty track everywhere but `/map`. So this component runs the
 * same combined watcher, but guarded to skip entirely while `/map` is the
 * active route: `MapScreen.vue` already owns the load there (and its own
 * tests mount it standalone, with no App.vue in the tree, so that watcher
 * could not be removed from it without breaking every one of them). Two
 * watchers racing `mapData.load()`/`dockToLatest()` for the same run would
 * risk double-starting the live tail (duplicate appended records); the
 * route guard means at most one of the two ever actually acts at a time.
 */
import { watch } from "vue";
import { useRoute } from "vue-router";
import TimelineBar from "./components/timeline/TimelineBar.vue";
import { useMapDataStore } from "./stores/mapData";
import { useUrlState } from "./state/urlState";

const route = useRoute();
const urlState = useUrlState();
const mapData = useMapDataStore();

watch(
  [urlState.run, urlState.t],
  async ([runId, t], oldValue) => {
    if (route.path === "/map") return; // MapScreen.vue owns the load there.
    const oldRunId = oldValue?.[0];
    if (runId !== oldRunId || oldValue === undefined) {
      await mapData.load(runId);
    }
    if (t === null) {
      await mapData.dockToLatest();
    } else {
      await mapData.setTick(t);
    }
  },
  { immediate: true },
);
</script>

<template>
  <div class="app-shell">
    <div class="app-shell__outlet">
      <router-view />
    </div>
    <TimelineBar />
  </div>
</template>

<style scoped>
.app-shell {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

/*
 * Every view still sets its own root to `height: 100vh` (a pre-existing,
 * out-of-boundary-for-this-lane convention -- see the lane report). That
 * makes each view taller than this outlet's actual share of the viewport
 * (100vh minus the timeline's footprint), so this pane scrolls internally
 * rather than clipping content: nothing becomes unreachable, the timeline
 * stays pinned below as persistent chrome.
 */
.app-shell__outlet {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
</style>
