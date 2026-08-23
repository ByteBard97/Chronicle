import { defineStore } from "pinia";
import { shallowRef, ref } from "vue";
import { fetchRunRegistry } from "../log/registry";
import { fetchSidecarIndex } from "../log/sidecarIndex";
import { runStreamUrl } from "../log/streamReader";
import { RunReader } from "../log/runReader";
import { readTicksInRange, sortedTicks } from "../log/feedReader";
import { emptySocialState, type SocialState } from "../log/reconstruct";
import type { FrameRecord } from "../log/types";

export type MapDataStatus = "idle" | "loading" | "loaded" | "error";

/**
 * The map's thin store (lane 14, mirroring lane 11's `stores/feed.ts`
 * idiom): owns a `RunReader` for reconstructed `SocialState` (beliefs,
 * rumors, claims) plus its own copies of the raw trace/events streams for
 * position derivation (`derived/mapMarkers.ts` needs `encounter_rolled`/
 * `transmitted`/`npc_died`, none of which `reconstruct.ts` folds into
 * `SocialState` -- same reason `feedReader.ts` bypasses it).
 *
 * Combined `[run, t]` watching is the *view*'s job (MapScreen.vue), per the
 * packet and `frameLog.ts`'s documented two-watcher ordering hazard: this
 * store only exposes `load(runId)` (build the reader, read both streams in
 * full once), `setTick(t)` (historical: `stateAt(t)`, tail stopped), and
 * `dockToLatest()` (LIVE: `stateAtLatestKnown()`, tail (re)started from
 * wherever that left off). `load()` deliberately does NOT also dock --
 * the view's combined watcher decides docked-vs-historical for the initial
 * tick exactly once, immediately after `load()` resolves; docking inside
 * `load()` too would double-reconstruct and restart the tail redundantly.
 */
export const useMapDataStore = defineStore("mapData", () => {
  const runId = ref<string | null>(null);
  const status = ref<MapDataStatus>("idle");
  const error = ref<string | null>(null);
  const docked = ref(false);

  const socialState = shallowRef<SocialState>(emptySocialState(-1));
  /** Raw trace-stream records (encounter_rolled/transmitted/relationship_formed/...) -- position source. */
  const traceRecords = shallowRef<FrameRecord[]>([]);
  /** Raw events-stream records, keyframes excluded (e.g. npc_died) -- death-location fallback source. */
  const eventRecords = shallowRef<FrameRecord[]>([]);

  let reader: RunReader | null = null;
  let stopTail: (() => void) | null = null;

  function stopLiveTail() {
    stopTail?.();
    stopTail = null;
  }

  function onTailRecords(records: FrameRecord[]) {
    const newTrace = records.filter((r) => r.stream === "trace");
    if (newTrace.length > 0) traceRecords.value = [...traceRecords.value, ...newTrace];
    const newEvents = records.filter((r) => r.stream === "events" && r.payload.record_type !== "keyframe");
    if (newEvents.length > 0) eventRecords.value = [...eventRecords.value, ...newEvents];

    if (docked.value) void refreshLatest();
  }

  async function refreshLatest() {
    if (reader === null) return;
    try {
      socialState.value = await reader.stateAtLatestKnown();
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err);
    }
  }

  /** Load (or clear, for `null`) the run: builds the reader and reads both streams in full once. Does not decide docked-vs-historical. */
  async function load(nextRunId: string | null) {
    stopLiveTail();
    reader = null;
    runId.value = nextRunId;
    socialState.value = emptySocialState(-1);
    traceRecords.value = [];
    eventRecords.value = [];
    error.value = null;
    docked.value = false;

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

      reader = new RunReader(entry);
      await reader.loadSidecar();

      const sidecarResult = await fetchSidecarIndex(nextRunId);
      const sidecar = sidecarResult.index;
      const traceUrl = runStreamUrl(nextRunId, entry.streams.trace);
      const eventsUrl = runStreamUrl(nextRunId, entry.streams.events);

      const traceTicks = sortedTicks(sidecar.streams.trace.tick_offsets);
      if (traceTicks.length > 0) {
        const result = await readTicksInRange(traceUrl, sidecar.streams.trace.tick_offsets, traceTicks[0]!, traceTicks[traceTicks.length - 1]!);
        traceRecords.value = result.records;
      }

      const eventTicks = sortedTicks(sidecar.streams.events.tick_offsets);
      if (eventTicks.length > 0) {
        const result = await readTicksInRange(eventsUrl, sidecar.streams.events.tick_offsets, eventTicks[0]!, eventTicks[eventTicks.length - 1]!);
        eventRecords.value = result.records.filter((r) => r.payload.record_type !== "keyframe");
      }

      status.value = "loaded";
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err);
      status.value = "error";
    }
  }

  /** Historical playhead: detach from LIVE and reconstruct state at exactly tick T. */
  async function setTick(t: number) {
    docked.value = false;
    stopLiveTail();
    if (reader === null) return;
    try {
      socialState.value = await reader.stateAt(t);
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err);
    }
  }

  /** Dock to LIVE: reconstruct state at the newest known record, then tail both streams from there. */
  async function dockToLatest() {
    docked.value = true;
    stopLiveTail();
    if (reader === null) return;
    try {
      socialState.value = await reader.stateAtLatestKnown();
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err);
      return;
    }
    const startOffsets = reader.currentOffsets();
    stopTail = reader.startLiveTail((records) => onTailRecords(records), 1000, startOffsets);
  }

  function dispose() {
    stopLiveTail();
  }

  return {
    runId,
    status,
    error,
    docked,
    socialState,
    traceRecords,
    eventRecords,
    load,
    setTick,
    dockToLatest,
    dispose,
  };
});
