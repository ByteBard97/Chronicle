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
 * Lane 6's mock-t0 fixture (`dashboard/public/runs/mock-t0/`,
 * `docs/frame-log-schema.md`-compliant records; see dashboard/README.md's
 * "Mock run fixture" section), in *this store's* simplified display shape
 * — not the schema-accurate `RunRegistryEntry` `src/log/registry.ts`'s
 * `fetchRunRegistry()` uses (a real, separately-documented shape
 * mismatch). It only needs to round-trip through `RunPicker`'s
 * `<option :value="run.run_id">{{ run.run_id }}</option>`, so the
 * mismatch doesn't matter here.
 */
const MOCK_T0_DISPLAY_ENTRY: RunRegistryEntry = {
  run_id: "mock-t0",
  seed_id: "mock-t0",
  created: "2026-08-22T00:00:00Z",
  tick_range: [0, 96],
  streams: ["events.jsonl", "trace.jsonl"],
};

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
  getters: {
    /**
     * `runs`, plus the mock-t0 fixture if the real registry didn't
     * already list it -- always pickable, regardless of what the real,
     * gitignored `runs/index.json` does or doesn't contain (the same
     * "never silently shadowed out" requirement `src/log/registry.ts`'s
     * `fetchRunRegistry()` satisfies for the schema-accurate reader; this
     * getter is the display-layer equivalent for `RunPicker`'s dropdown).
     * Kept as a separate getter, not a change to `runs`/`load()` itself,
     * so `runs.test.ts`'s existing assertions on `store.runs` stay exactly
     * as Lane 5 wrote them.
     */
    pickableRuns: (state): RunRegistryEntry[] =>
      state.runs.some((r) => r.run_id === MOCK_T0_DISPLAY_ENTRY.run_id)
        ? state.runs
        : [...state.runs, MOCK_T0_DISPLAY_ENTRY],
  },
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
