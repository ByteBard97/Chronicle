import { defineStore } from "pinia";
import { computed, ref, shallowRef } from "vue";
import { fetchRunRegistry } from "../log/registry";
import { fetchSidecarIndex } from "../log/sidecarIndex";
import { runStreamUrl, LiveTailPoller } from "../log/streamReader";
import {
  filterFeedRows,
  mapTraceRecordToFeedRow,
  readTicksInRange,
  sortedTicks,
  type FeedFilters,
  type FeedRow,
} from "../log/feedReader";
import type { FrameRecord } from "../log/types";

export type FeedLoadStatus = "idle" | "loading" | "loaded" | "error";

/**
 * The encounter-feed store (lane 11, ui-spec §3.3): loads the trace stream
 * for the selected run — paged by the sidecar's `tick_offsets`
 * (`log/feedReader.ts`) — into `rows`, applies the NPC/location/outcome/
 * claim filter pipeline, and owns a `LiveTailPoller` that appends newly
 * written trace rows.
 *
 * Deliberately independent of `stores/frameLog.ts`: this store reads the
 * trace stream directly rather than going through `RunReader.stateAt`,
 * per the packet ("Feed rows cannot come from `RunReader.stateAt`" —
 * `reconstruct.ts` no-ops the very record types the feed renders).
 *
 * LIVE-tail scope (design call, documented in the lane report): the
 * poller runs whenever a run is loaded, appending new trace rows as they
 * arrive, independent of the global `liveDock` store's docked/detached
 * flag — `liveDock` is wired to `frameLog`'s reconstructed-state view
 * (Shell.vue/the timeline), not to this store. New rows simply accumulate
 * at the bottom of the feed regardless of which historical tick the user
 * is currently viewing; nothing here un-docks or re-docks the global LIVE
 * indicator.
 */
export const useFeedStore = defineStore("feed", () => {
  const runId = ref<string | null>(null);
  const rows = shallowRef<FeedRow[]>([]);
  const status = ref<FeedLoadStatus>("idle");
  const error = ref<string | null>(null);
  const filters = ref<FeedFilters>({});

  let poller: LiveTailPoller | null = null;
  let stopPoller: (() => void) | null = null;

  const filteredRows = computed(() => filterFeedRows(rows.value, filters.value));

  function setFilters(next: FeedFilters) {
    filters.value = { ...next };
  }

  function stopLiveTail() {
    stopPoller?.();
    stopPoller = null;
    poller = null;
  }

  function appendRecords(records: FrameRecord[]) {
    if (records.length === 0) return;
    const mapped: FeedRow[] = [];
    for (const record of records) {
      const row = mapTraceRecordToFeedRow(record);
      if (row !== null) mapped.push(row);
    }
    if (mapped.length > 0) {
      rows.value = [...rows.value, ...mapped];
    }
  }

  function startLiveTail(url: string, fromByteOffset: number) {
    stopLiveTail();
    poller = new LiveTailPoller(url, fromByteOffset);
    stopPoller = poller.start((records) => appendRecords(records));
  }

  /** Load (or clear, for `null`) the feed for a run id. */
  async function load(nextRunId: string | null) {
    stopLiveTail();
    rows.value = [];
    error.value = null;
    runId.value = nextRunId;

    if (nextRunId === null) {
      status.value = "idle";
      return;
    }

    status.value = "loading";
    try {
      const registry = await fetchRunRegistry();
      const entry = registry.entries.find((e) => e.run_id === nextRunId) ?? null;
      if (entry === null) {
        error.value = `run ${nextRunId} not found in the registry`;
        status.value = "error";
        return;
      }

      const sidecar = await fetchSidecarIndex(nextRunId);
      const url = runStreamUrl(nextRunId, entry.streams.trace);
      const tickOffsets = sidecar.index.streams.trace.tick_offsets;
      const ticks = sortedTicks(tickOffsets);

      if (ticks.length === 0) {
        rows.value = [];
        status.value = "loaded";
        startLiveTail(url, 0);
        return;
      }

      const result = await readTicksInRange(url, tickOffsets, ticks[0], ticks[ticks.length - 1]);
      const mapped: FeedRow[] = [];
      for (const record of result.records) {
        const row = mapTraceRecordToFeedRow(record);
        if (row !== null) mapped.push(row);
      }
      rows.value = mapped;
      status.value = "loaded";
      startLiveTail(url, result.consumedThrough);
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err);
      status.value = "error";
    }
  }

  function dispose() {
    stopLiveTail();
  }

  return {
    runId,
    rows,
    filteredRows,
    status,
    error,
    filters,
    setFilters,
    load,
    dispose,
  };
});
