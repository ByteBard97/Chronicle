/**
 * Run B's independent, read-only load path (lane 38's "two-run state
 * problem" -- `stores/mapData.ts` can only ever hold ONE run at a time, and
 * is out of this lane's file boundary to edit or extend). This composable
 * is not a Pinia store and does not touch `mapData.ts`; it loads a second
 * run's full `eventRecords`/`traceRecords` using the exact same underlying
 * primitives `mapData.ts` itself uses (`fetchRunRegistry`, `fetchSidecarIndex`,
 * `runStreamUrl`, `readTicksInRange` over the full tick span) so
 * `CompareScreen.vue` can reconstruct run B's `SocialState` at any T via
 * `log/reconstruct.ts`'s `replayTo` -- the same "own the second replay
 * yourself" idiom `derived/socialDiff.ts` (lane 30) uses for its own
 * two-TICK problem, applied here to two RUNS instead.
 *
 * No live tail: comparison mode is a static, offline analysis of two full
 * logs (ui-spec §3.9 says nothing about LIVE comparison), so this loader
 * reads once per `load(runId)` call and does not poll.
 */
import { ref, shallowRef } from "vue";
import { fetchRunRegistry } from "../../log/registry";
import { fetchSidecarIndex } from "../../log/sidecarIndex";
import { runStreamUrl } from "../../log/streamReader";
import { readTicksInRange, sortedTicks } from "../../log/feedReader";
import type { FrameRecord } from "../../log/types";

export type SecondRunStatus = "idle" | "loading" | "loaded" | "error";

export function useSecondRunLoad() {
  const runId = ref<string | null>(null);
  const status = ref<SecondRunStatus>("idle");
  const error = ref<string | null>(null);
  const traceRecords = shallowRef<FrameRecord[]>([]);
  const eventRecords = shallowRef<FrameRecord[]>([]);

  async function load(nextRunId: string | null): Promise<void> {
    runId.value = nextRunId;
    traceRecords.value = [];
    eventRecords.value = [];
    error.value = null;

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

  return { runId, status, error, traceRecords, eventRecords, load };
}
