import { defineStore } from "pinia";

/** One entry from `runs/index.json` (ui-spec §1.2's runs registry). */
export interface RunRegistryEntry {
  run_id: string;
  seed_id: string;
  created: string;
  tick_range: [number, number];
  streams: string[];
}

interface RunsIndexFile {
  runs: RunRegistryEntry[];
}

/**
 * The run registry cache (build-plan §0: "run registry cache" is
 * non-URL/Pinia state). Fetches `runs/index.json` through the dashboard's
 * own serving of `runs/` (see vite-plugins/serveRuns.ts) and tolerates its
 * absence — the writer (a later lane / Track A) may not have run yet, or no
 * run may exist on a fresh checkout. That is not an error state.
 */
export const useRunsStore = defineStore("runs", {
  state: () => ({
    runs: [] as RunRegistryEntry[],
    status: "idle" as "idle" | "loading" | "loaded" | "missing" | "error",
    error: null as string | null,
  }),
  actions: {
    async load() {
      this.status = "loading";
      this.error = null;
      try {
        const res = await fetch("/runs/index.json");
        if (res.status === 404) {
          // Expected on a fresh checkout, or before any run has been written.
          this.runs = [];
          this.status = "missing";
          return;
        }
        if (!res.ok) {
          throw new Error(`GET /runs/index.json -> ${res.status}`);
        }
        const body = (await res.json()) as RunsIndexFile;
        this.runs = body.runs ?? [];
        this.status = "loaded";
      } catch (err) {
        this.runs = [];
        this.status = "error";
        this.error = err instanceof Error ? err.message : String(err);
      }
    },
  },
});
