import { defineStore } from "pinia";
import { watch, type Ref } from "vue";
import { fetchRunRegistry } from "../log/registry";
import { RunReader } from "../log/runReader";
import type { FrameRecord, RunRegistryEntry } from "../log/types";
import { useLiveDockStore } from "./liveDock";

/**
 * Wires the log-reader client (`src/log/`) to the URL-state contract: the
 * selected run and playhead tick (`urlState.run`/`urlState.t`) drive
 * `stateAt(t)`, and LIVE tailing runs whenever the playhead is docked
 * (`t === null`, ui-spec §1.3's "follows the newest complete record").
 *
 * This is the M1-scope integration point the work packet's acceptance
 * criteria describe ("the shell renders the mock run: stepper moves T,
 * state at T reflects keyframe+deltas, LIVE tail picks up an appended
 * record") — deliberately not a view: it exposes plain counts/ids for a
 * smoke-test readout, not a styled inspector.
 *
 * `run` and `t` are watched *together*, not as two independent watchers:
 * an earlier version watched each ref separately, both with
 * `immediate: true` — on load, the `t` watcher's docked branch ran before
 * `loadRun()`'s `await fetchRunRegistry()` had resolved, so `this.reader`
 * was still null and `startLiveTail()` silently no-op'd, forever (nothing
 * re-armed it once loading finished). One combined async handler avoids
 * that ordering hazard by construction — it always finishes loading the
 * run before deciding what the current tick means.
 *
 * Known M1-scope limitation: while docked, `dockToLatest()` reconstructs
 * state once and the tail poller's callback only increments
 * `liveDock.newEventCount` afterward — the docked readout does not
 * re-fold newly tailed records into `stateTick`/`beliefCount`/
 * `claimCount`. That satisfies this lane's acceptance criterion (LIVE
 * tailing detects and counts a newly appended record within the polling
 * cadence) without yet making good on the *rest* of the frozen chrome
 * text's claim ("following newest frame") — a later lane should either
 * re-run `dockToLatest()` on each new-record callback while docked, or
 * treat that as this store's job once a view actually needs live-updating
 * state.
 */
export const useFrameLogStore = defineStore("frameLog", {
  state: () => ({
    runId: null as string | null,
    registryEntry: null as RunRegistryEntry | null,
    reader: null as RunReader | null,
    beliefCount: 0,
    claimCount: 0,
    stateTick: null as number | null,
    loading: false,
    error: null as string | null,
    stopLiveTail: null as (() => void) | null,
  }),
  actions: {
    async loadRun(runId: string | null) {
      this.stopLiveTail?.();
      this.stopLiveTail = null;
      this.reader = null;
      this.registryEntry = null;
      this.beliefCount = 0;
      this.claimCount = 0;
      this.stateTick = null;
      this.runId = runId;
      this.error = null;

      if (runId === null) return;

      try {
        const registry = await fetchRunRegistry();
        const entry = registry.entries.find((e) => e.run_id === runId) ?? null;
        if (entry === null) {
          this.error = `run ${runId} not found in the registry`;
          return;
        }
        this.registryEntry = entry;
        const reader = new RunReader(entry);
        await reader.loadSidecar();
        this.reader = reader;
      } catch (err) {
        this.error = err instanceof Error ? err.message : String(err);
      }
    },

    /** Historical playhead: detach from LIVE and reconstruct state at exactly tick `t`. */
    async setTick(t: number) {
      const liveDock = useLiveDockStore();
      liveDock.detach();
      this.stopLiveTail?.();
      this.stopLiveTail = null;
      if (this.reader === null) return;

      try {
        const state = await this.reader.stateAt(t);
        this.stateTick = t;
        this.beliefCount = state.beliefs.size;
        this.claimCount = state.claims.size;
      } catch (err) {
        this.error = err instanceof Error ? err.message : String(err);
      }
    },

    /** Dock to LIVE: reconstruct state at the newest record currently in the log, then start tailing from there. */
    async dockToLatest() {
      const liveDock = useLiveDockStore();
      liveDock.dock();
      this.stopLiveTail?.();
      this.stopLiveTail = null;
      if (this.reader === null) return;

      try {
        const state = await this.reader.stateAtLatestKnown();
        this.stateTick = state.tick;
        this.beliefCount = state.beliefs.size;
        this.claimCount = state.claims.size;
      } catch (err) {
        this.error = err instanceof Error ? err.message : String(err);
        return;
      }

      // Start tailing from exactly where stateAtLatestKnown() left off, so
      // the first poll doesn't replay everything already folded into that
      // state as "new" -- "+N events" is meant to mean new-since-docking.
      const startOffsets = this.reader.currentOffsets();
      this.stopLiveTail = this.reader.startLiveTail((records: FrameRecord[]) => {
        liveDock.recordNewEvents(records.length);
      }, 1000, startOffsets);
    },

    async applyTick(t: number | null) {
      if (t === null) {
        await this.dockToLatest();
      } else {
        await this.setTick(t);
      }
    },

    /** Bind once (e.g. from Shell.vue's setup) to keep this store in sync with the URL-state refs. */
    bindToUrlState(run: Ref<string | null>, t: Ref<number | null>) {
      watch(
        [run, t],
        async ([runId, tick], oldValue) => {
          const oldRunId = oldValue?.[0];
          if (runId !== oldRunId || oldValue === undefined) {
            await this.loadRun(runId);
          }
          await this.applyTick(tick);
        },
        { immediate: true },
      );
    },
  },
});
