<script setup lang="ts">
/**
 * FeedScreen — the encounter feed (ui-spec §3.3, Tier 1): a chronological,
 * virtualized table over the trace stream, four outcome states with equal
 * visual weight, filterable by NPC/location/outcome/claim, row click ->
 * both inspectors + timeline jump.
 *
 * Chrome strip mirrors MapScreen's (RunPicker, SalienceSwitch, the
 * ViewSwitcher this lane establishes). Data comes from `stores/feed.ts`
 * (lane 11, new) — deliberately not `stores/frameLog.ts`: the trace
 * record types this view renders (`encounter_rolled`, `nothing_salient`)
 * are no-ops in `reconstruct.ts` by design (schema §1's three-things
 * rule — they're derivations with no derived-state effect to fold).
 *
 * LIVE-detach finding (packet Task 3, "verify and note the actual
 * behavior"): this screen does NOT call `frameLog.bindToUrlState()` — the
 * feed's own `LiveTailPoller` (owned by `stores/feed.ts`) is independent
 * of `frameLog`'s reconstructed-state watcher. Consequence, verified by
 * `FeedScreen.test.ts`: a row click's `urlState.t` write does NOT, by
 * itself, detach the global `liveDock` store from LIVE when FeedScreen is
 * the only mounted view. `bindToUrlState`'s `watch` lives inside
 * `frameLog`'s own Pinia action scope, not a per-view effect scope — so if
 * some other still-mounted view (e.g. Shell, on `/`) already called
 * `frameLog.bindToUrlState()` earlier in the session, that watcher is
 * still live and *would* fire on this write. That cross-view side effect
 * is a property of `frameLog.ts`'s existing design (out of this lane's
 * file boundaries), not something FeedScreen adds or relies on.
 *
 * `stores/mapData.ts` IS loaded here (added post lane-28): the inspector
 * mounted below needs `SocialState` for its real Beliefs tab, the same
 * `[run, t]` combined-watcher idiom MapScreen/VariantTreeScreen already
 * use (frameLog.ts's documented load-before-tick ordering hazard) — this
 * is a second, independent read of the same Pinia singleton, not a new
 * data path.
 */
import { computed, ref, watch } from "vue";
import { useUrlState } from "../state/urlState";
import { useSelectionUrlSync } from "../state/useSelectionUrlSync";
import { useSelectionStore } from "../stores/selection";
import { useSalienceStore } from "../stores/salience";
import { useFeedStore } from "../stores/feed";
import { useMapDataStore } from "../stores/mapData";
import { buildDisplayItems } from "../components/feed/feedGrouping";
import type { FeedFilters, FeedRow } from "../log/feedReader";
import RunPicker from "../components/RunPicker.vue";
import SalienceSwitch from "../components/SalienceSwitch.vue";
import ViewSwitcher from "../components/ViewSwitcher.vue";
import PanelGlass from "../components/PanelGlass.vue";
import NpcInspector from "../components/NpcInspector.vue";
import LiveDockIndicator from "../components/LiveDockIndicator.vue";
import FeedFilterBar from "../components/feed/FeedFilterBar.vue";
import FeedTable from "../components/feed/FeedTable.vue";

const urlState = useUrlState();
const selection = useSelectionStore();
const salience = useSalienceStore();
const feed = useFeedStore();
const mapData = useMapDataStore();

watch(
  [urlState.run, urlState.t],
  async ([runId, t], oldValue) => {
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

// Task 5: the store<->urlState.sel binding lives in this composable, not
// in stores/selection.ts itself.
useSelectionUrlSync();

watch(
  urlState.run,
  (runId) => {
    void feed.load(runId);
  },
  { immediate: true },
);

watch(
  urlState.filters,
  (filters) => {
    feed.setFilters(filters as FeedFilters);
  },
  { immediate: true },
);

// View-local UI state (packet's pinned semantics: expand/collapse is NOT
// url state). A deep-linked `t` is pre-expanded so a trace-row landing
// case (rolled-against/nothing-salient) is visible without scrolling even
// under the default Observer salience, which otherwise collapses trace
// rows behind a per-tick group header.
const expandedTicks = ref<Set<number>>(new Set());
watch(
  urlState.t,
  (t) => {
    if (t !== null) {
      expandedTicks.value = new Set([...expandedTicks.value, t]);
    }
  },
  { immediate: true },
);

function onToggleGroup(tick: number) {
  const next = new Set(expandedTicks.value);
  if (next.has(tick)) {
    next.delete(tick);
  } else {
    next.add(tick);
  }
  expandedTicks.value = next;
}

const displayItems = computed(() =>
  buildDisplayItems(feed.filteredRows, salience.level, salience.showAll, expandedTicks.value),
);

function onFiltersUpdate(next: FeedFilters) {
  urlState.filters.value = next as Record<string, string>;
}

function onRowClick(row: FeedRow) {
  selection.selectMany(row.participants);
  urlState.t.value = row.tick;
}

const inspectedIds = computed(() => selection.selectedIds.slice(0, 2));
</script>

<template>
  <div class="feed-screen">
    <header class="feed-screen__chrome">
      <div class="feed-screen__wordmark">CHRONICLE</div>
      <RunPicker v-model="urlState.run.value" />
      <div class="feed-screen__spacer" />
      <SalienceSwitch :mode="salience.level" @update:mode="salience.setLevel" />
      <button
        type="button"
        class="feed-screen__show-all"
        :aria-pressed="salience.showAll"
        @click="salience.setShowAll(!salience.showAll)"
      >
        all events {{ salience.showAll ? "⤢ on" : "⤢" }}
      </button>
      <ViewSwitcher current="feed" />
    </header>

    <FeedFilterBar :rows="feed.rows" :filters="feed.filters" @update:filters="onFiltersUpdate" />

    <div class="feed-screen__body">
      <div class="feed-screen__main">
        <span v-if="feed.status === 'loading'" class="feed-screen__status">loading…</span>
        <span v-else-if="feed.status === 'error'" class="feed-screen__status"
          >feed error: {{ feed.error }}</span
        >
        <FeedTable
          v-else
          :items="displayItems"
          :selected-ids="selection.selectedIds"
          :scroll-to-tick="urlState.t.value"
          @row-click="onRowClick"
          @toggle-group="onToggleGroup"
        />
      </div>

      <aside class="feed-screen__inspector" aria-label="inspector slot">
        <PanelGlass v-if="inspectedIds.length === 0" tone="inspector" class="feed-screen__inspector-empty">
          click a row to select both participants
        </PanelGlass>
        <NpcInspector
          v-for="id in inspectedIds"
          :key="id"
          :npc-name="id"
          :as-of-tick="urlState.t.value ?? undefined"
          :salience="salience.level"
        />
      </aside>
    </div>

    <footer class="feed-screen__footer">
      <LiveDockIndicator />
      <span class="feed-screen__spacer" />
      <span class="feed-screen__count">
        {{ feed.filteredRows.length }} of {{ feed.rows.length }} rows
      </span>
    </footer>
  </div>
</template>

<style scoped>
.feed-screen {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--c-page-bg);
  overflow: hidden;
  font-size: var(--fs-body);
}

.feed-screen__chrome {
  height: 44px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 16px;
  border-bottom: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-strong);
}

.feed-screen__wordmark {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.3em;
  color: var(--c-accent-hover);
}

.feed-screen__spacer {
  flex: 1;
}

.feed-screen__show-all {
  appearance: none;
  border: 1px solid var(--c-hairline);
  background: transparent;
  color: var(--c-text-dim);
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  border-radius: var(--radius-chip);
  padding: 3px 8px;
  cursor: pointer;
  white-space: nowrap;
}

.feed-screen__show-all[aria-pressed="true"] {
  background: var(--c-chip-active-fill);
  color: var(--c-accent-hover);
  border-color: var(--c-chip-active-border);
}

.feed-screen__body {
  flex: 1;
  min-height: 0;
  display: flex;
}

.feed-screen__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.feed-screen__status {
  padding: 12px 16px;
  color: var(--c-text-dim);
}

.feed-screen__inspector {
  width: 372px;
  flex: none;
  border-left: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-inspector);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px;
}

.feed-screen__inspector-empty {
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}

.feed-screen__footer {
  flex: none;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 16px;
  border-top: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-inspector);
  font-size: var(--fs-secondary);
  color: var(--c-text-dim);
}
</style>
