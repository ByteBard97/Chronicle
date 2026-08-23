/**
 * The run registry reader (docs/frame-log-schema.md §6): `runs/index.json`,
 * as maintained by the writer. Tolerates the file being absent (no run has
 * ever been written — not an error) and tolerates individual malformed
 * entries within an otherwise-valid file (schema §7's skip-and-continue
 * discipline applied at the registry level, not just the record level) —
 * one bad entry must not blank out every other run from the picker.
 *
 * NOTE (finding for the coordinator — see this lane's final report): this
 * schema-accurate reader is deliberately separate from
 * `src/stores/runs.ts` (Lane 5's Pinia cache). That store's
 * `RunRegistryEntry` shape (`created: string`, `streams: string[]`) does
 * not match this document's §6 shape (`created_wall_ts: number`,
 * `branches`, `streams: {events, trace}`, `status`) or what
 * `scripts/check-range.mjs` actually writes. Left unmodified here to avoid
 * breaking Lane 5's accepted tests/behavior; flagged rather than silently
 * papered over.
 */
import type { RunRegistryEntry, RunRegistryFile } from "./types";
import { fetchJson } from "./rangeFetch";

export type RegistryStatus = "missing" | "loaded" | "error";

export interface RegistryResult {
  status: RegistryStatus;
  entries: RunRegistryEntry[];
  /** Entries present in the file but rejected as malformed (diagnostic only). */
  rejected: unknown[];
  error?: string;
}

function isValidEntry(candidate: unknown): candidate is RunRegistryEntry {
  if (typeof candidate !== "object" || candidate === null) return false;
  const c = candidate as Record<string, unknown>;
  if (typeof c.run_id !== "string" || c.run_id.length === 0) return false;
  if (typeof c.seed_id !== "string") return false;
  if (typeof c.streams !== "object" || c.streams === null) return false;
  const streams = c.streams as Record<string, unknown>;
  if (typeof streams.events !== "string") return false;
  // trace is required by the schema's shape, but tolerate its absence
  // (a fresh/tiny run may not have produced trace rows yet) rather than
  // rejecting the whole entry over a stream that's merely empty so far.
  return true;
}

/**
 * The mock-t0 fixture's registry entry, served from a path outside `/runs/`
 * (`public/mock-fixtures/`, not intercepted by `serveRuns.ts`'s `/runs/*`
 * handler at all) so it is reachable regardless of whether a real
 * `runs/index.json` exists yet under `CHRONICLE_RUNS_DIR`. This is
 * deliberately *not* a second copy of `runs/index.json` under `public/`:
 * that would only appear when the real gitignored registry is absent
 * (404), and disappear again — silently dropping the mock run from the
 * picker — the moment any real run (or even `check-range.mjs`'s own tiny
 * fixture) gets written, which defeats "stays as the CI fixture
 * afterward" (the work packet's requirement for this fixture). Merging it
 * in here, unconditionally, is what actually satisfies that.
 */
const MOCK_FIXTURE_REGISTRY_ENTRY_URL = "/mock-fixtures/mock-t0.registry-entry.json";

async function fetchMockFixtureEntry(): Promise<RunRegistryEntry | null> {
  const result = await fetchJson<unknown>(MOCK_FIXTURE_REGISTRY_ENTRY_URL);
  if (!result.ok) return null; // e.g. a production build that strips public/mock-fixtures/ deliberately
  return isValidEntry(result.body) ? result.body : null;
}

export async function fetchRunRegistry(
  url = "/runs/index.json",
): Promise<RegistryResult> {
  const mockEntry = await fetchMockFixtureEntry();
  const result = await fetchJson<unknown>(url);

  if (!result.ok) {
    if (result.status === 404) {
      return {
        status: "missing",
        entries: mockEntry ? [mockEntry] : [],
        rejected: [],
      };
    }
    return {
      status: "error",
      entries: [],
      rejected: [],
      error: `GET ${url} -> ${result.status}`,
    };
  }

  const body = result.body;
  if (typeof body !== "object" || body === null || !Array.isArray((body as Partial<RunRegistryFile>).runs)) {
    // Malformed top-level shape — tolerate as "no runs" rather than error,
    // since a picker with nothing to show is a safe degraded state.
    return { status: "loaded", entries: mockEntry ? [mockEntry] : [], rejected: [body] };
  }

  const raw = (body as RunRegistryFile).runs;
  const entries: RunRegistryEntry[] = [];
  const rejected: unknown[] = [];
  for (const candidate of raw) {
    if (isValidEntry(candidate)) {
      entries.push(candidate);
    } else {
      rejected.push(candidate);
    }
  }
  if (mockEntry && !entries.some((e) => e.run_id === mockEntry.run_id)) {
    entries.push(mockEntry);
  }
  return { status: "loaded", entries, rejected };
}
