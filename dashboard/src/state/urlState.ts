/**
 * The URL-state contract (docs/ui-spec.md §1.2, build-plan §0): the
 * dashboard's entire view state serializes into the URL —
 * `run`, `branch`, `t`, `view`, `sel`, `panels`, `filters`, and for
 * run-comparison `runB`/`alignment`. This module is the single place the
 * query keys are defined; nothing else in the app should read/write these
 * query params directly.
 *
 * Two layers, deliberately split so the identity law is testable without a
 * router:
 *  - a pure codec (`encodeUrlState`/`decodeUrlState`, and the per-field
 *    `codecs` they're built from) — plain functions, string in, typed value
 *    out, and back;
 *  - `useUrlState()`, a thin Composition API wrapper that binds each field
 *    to `useRouteQuery` (VueUse, `@vueuse/router`) using that codec.
 *
 * Defaults are omitted from the URL (build-plan §0). For the collection
 * fields (`sel`, `panels`, `filters`) that means: empty collection encodes
 * to "absent from the URL", and "absent from the URL" decodes to the empty
 * collection — never to some other non-empty default. That bijection is
 * what the round-trip test below is actually checking; a codec that passes
 * on scalars but fudges this for collections would still look green on a
 * naive test.
 */
import { computed, type Ref } from "vue";
import { useRouteQuery } from "@vueuse/router";

export interface UrlState {
  /** Run id, as registered in runs/index.json. */
  run: string | null;
  /** `(save_uuid, generation)`, encoded as `"save_uuid.generation"`. */
  branch: string | null;
  /** Tick, as-of-T (ui-spec §0: every view renders as-of-tick-T). */
  t: number | null;
  /** Active view name (e.g. "inspector", "feed", "map", ...). */
  view: string | null;
  /** Global selection (ui-spec §2: one selection, highlighted everywhere). */
  sel: string[];
  /** Open/pinned panel ids (e.g. pinned NPC inspectors). */
  panels: string[];
  /** View-specific filter key/value pairs (salience filter is one entry). */
  filters: Record<string, string>;
  /** Second run id, for run comparison (ui-spec §3.9). */
  runB: string | null;
  /** Run-comparison alignment mode (ui-spec §3.9). */
  alignment: string | null;
}

export const URL_STATE_DEFAULTS: Readonly<UrlState> = Object.freeze({
  run: null,
  branch: null,
  t: null,
  view: null,
  sel: [],
  panels: [],
  filters: {},
  runB: null,
  alignment: null,
});

/**
 * What vue-router actually hands a query value as: a plain string for
 * `?k=v`, `null` for a bare key (`?k`), `undefined` if the key is absent,
 * or `string[]` if the key is repeated (`?k=a&k=b`). A decoder that only
 * type-checks against `string | undefined` compiles (the `useRouteQuery`
 * generics let that slide) but throws or silently misparses on the other
 * two shapes reaching it from a real or hand-typed URL.
 */
type RawQueryValue = string | string[] | null | undefined;

/**
 * Collapse the three "not a plain string" shapes to `undefined` (treated as
 * "absent" by every decoder below): `null` (bare key), an empty array, and
 * a repeated key collapses to its first value rather than erroring.
 */
function firstString(raw: RawQueryValue): string | undefined {
  if (raw === null || raw === undefined) return undefined;
  if (Array.isArray(raw)) return raw[0];
  return raw;
}

/** One codec per field: typed value <-> the raw query value vue-router hands us. */
interface FieldCodec<T> {
  encode: (value: T) => string | undefined; // undefined => omit the query key
  decode: (raw: RawQueryValue) => T;
}

function stringCodec(defaultValue: string | null): FieldCodec<string | null> {
  return {
    encode: (value) => (value === null || value === "" ? undefined : value),
    decode: (raw) => {
      const s = firstString(raw);
      return s === undefined || s === "" ? defaultValue : s;
    },
  };
}

const numberOrNullCodec: FieldCodec<number | null> = {
  encode: (value) => (value === null ? undefined : String(value)),
  decode: (raw) => {
    const s = firstString(raw);
    if (s === undefined || s === "") return null;
    const n = Number(s);
    // Ticks are non-negative integers (ui-spec §0: every view renders
    // as-of-tick-T); reject fractional/negative/non-numeric input rather
    // than silently coercing (e.g. `Number(null)` is `0`, which must never
    // reach here as a "valid" tick via this path).
    return Number.isInteger(n) && n >= 0 ? n : null;
  },
};

const stringArrayCodec: FieldCodec<string[]> = {
  encode: (value) =>
    value.length === 0
      ? undefined
      : value.map((v) => encodeURIComponent(v)).join(","),
  decode: (raw) => {
    const s = firstString(raw);
    if (s === undefined || s === "") return [];
    return s
      .split(",")
      .filter((part) => part.length > 0)
      .map((part) => decodeURIComponent(part));
  },
};

const filtersCodec: FieldCodec<Record<string, string>> = {
  encode: (value) => {
    const keys = Object.keys(value);
    if (keys.length === 0) return undefined;
    return JSON.stringify(value);
  },
  decode: (raw) => {
    const s = firstString(raw);
    if (s === undefined || s === "") return {};
    try {
      const parsed = JSON.parse(s);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        return parsed as Record<string, string>;
      }
      return {};
    } catch {
      return {};
    }
  },
};

/** Per-field codecs, keyed by the exact query-param name (the frozen set). */
export const codecs = {
  run: stringCodec(URL_STATE_DEFAULTS.run),
  branch: stringCodec(URL_STATE_DEFAULTS.branch),
  t: numberOrNullCodec,
  view: stringCodec(URL_STATE_DEFAULTS.view),
  sel: stringArrayCodec,
  panels: stringArrayCodec,
  filters: filtersCodec,
  runB: stringCodec(URL_STATE_DEFAULTS.runB),
  alignment: stringCodec(URL_STATE_DEFAULTS.alignment),
} as const satisfies { [K in keyof UrlState]: FieldCodec<UrlState[K]> };

/**
 * A query record as vue-router's `LocationQuery` actually shapes it: each
 * key is a plain string (`?k=v`), `null` (bare key `?k`), or `string[]`
 * (repeated key `?k=a&k=b`); an absent key is simply missing from the
 * record (not present as `undefined` — `Partial` models that).
 */
export type UrlStateQuery = Partial<Record<keyof UrlState, RawQueryValue>>;

/** Pure: typed state -> query record. Absent keys mean "at default". */
export function encodeUrlState(state: UrlState): Partial<Record<keyof UrlState, string>> {
  const query: Partial<Record<keyof UrlState, string>> = {};
  for (const key of Object.keys(codecs) as (keyof UrlState)[]) {
    const encoded = (codecs[key].encode as (v: unknown) => string | undefined)(
      state[key],
    );
    if (encoded !== undefined) {
      query[key] = encoded;
    }
  }
  return query;
}

/**
 * Pure: query record -> typed state. Absent keys decode to their default,
 * and so do the "not really a value" shapes a real URL can produce for a
 * key this schema treats as scalar — a bare `?sel` (`null`) or a repeated
 * `?t=1&t=2` (`string[]`, first element wins) never throw and never
 * silently coerce to something like `t: 0`.
 */
export function decodeUrlState(query: UrlStateQuery): UrlState {
  const state = {} as UrlState;
  for (const key of Object.keys(codecs) as (keyof UrlState)[]) {
    (state[key] as unknown) = (
      codecs[key].decode as (raw: RawQueryValue) => unknown
    )(query[key]);
  }
  return state;
}

/**
 * `useRouteQuery`'s history mode ('push' | 'replace', default 'replace' —
 * checked against `node_modules/@vueuse/router`, not assumed). ui-spec
 * §1.2 consequence 3 ("back/forward buttons are time-and-focus history for
 * free") is load-bearing on this: at the library default, no write through
 * any of these refs creates a history entry, so back/forward would do
 * nothing. Decision recorded here (the one place query keys are defined),
 * not left to whichever view first calls `useUrlState()`:
 *
 * - `t` stays 'replace'. It's the field a scrubber will update continuously
 *   (drag, play); 'push' here would make every frame of a scrub a distinct
 *   history entry, which is not what "time-and-focus history" means.
 * - Every other field — a run switch, a view switch, a selection, opening a
 *   panel, entering comparison mode — is a *navigation*, in the sense the
 *   spec means: something a user would want a back button to undo. These
 *   use 'push'.
 *
 * This is a per-field default, not a frozen rule — a future view is free to
 * override `mode` at a specific call site (e.g. batching several selection
 * changes into one push) — but the default for each field is decided once,
 * here, rather than accidentally at each new call site.
 */
const HISTORY_MODE: Record<keyof UrlState, "push" | "replace"> = {
  run: "push",
  branch: "push",
  t: "replace",
  view: "push",
  sel: "push",
  panels: "push",
  filters: "push",
  runB: "push",
  alignment: "push",
};

/**
 * Composition API entry point: one reactive ref per field, each bound to its
 * query key via `useRouteQuery` + this module's codec. Call once per app
 * (e.g. from the shell); components read/write the individual refs.
 */
export function useUrlState(): { [K in keyof UrlState]: Ref<UrlState[K]> } {
  const run = useRouteQuery<RawQueryValue, UrlState["run"]>(
    "run",
    undefined,
    {
      mode: HISTORY_MODE.run,
      transform: { get: codecs.run.decode, set: codecs.run.encode },
    },
  );
  const branch = useRouteQuery<RawQueryValue, UrlState["branch"]>(
    "branch",
    undefined,
    {
      mode: HISTORY_MODE.branch,
      transform: { get: codecs.branch.decode, set: codecs.branch.encode },
    },
  );
  const t = useRouteQuery<RawQueryValue, UrlState["t"]>("t", undefined, {
    mode: HISTORY_MODE.t,
    transform: { get: codecs.t.decode, set: codecs.t.encode },
  });
  const view = useRouteQuery<RawQueryValue, UrlState["view"]>(
    "view",
    undefined,
    {
      mode: HISTORY_MODE.view,
      transform: { get: codecs.view.decode, set: codecs.view.encode },
    },
  );
  const sel = useRouteQuery<RawQueryValue, UrlState["sel"]>(
    "sel",
    undefined,
    {
      mode: HISTORY_MODE.sel,
      transform: { get: codecs.sel.decode, set: codecs.sel.encode },
    },
  );
  const panels = useRouteQuery<RawQueryValue, UrlState["panels"]>(
    "panels",
    undefined,
    {
      mode: HISTORY_MODE.panels,
      transform: { get: codecs.panels.decode, set: codecs.panels.encode },
    },
  );
  const filters = useRouteQuery<RawQueryValue, UrlState["filters"]>(
    "filters",
    undefined,
    {
      mode: HISTORY_MODE.filters,
      transform: { get: codecs.filters.decode, set: codecs.filters.encode },
    },
  );
  const runB = useRouteQuery<RawQueryValue, UrlState["runB"]>(
    "runB",
    undefined,
    {
      mode: HISTORY_MODE.runB,
      transform: { get: codecs.runB.decode, set: codecs.runB.encode },
    },
  );
  const alignment = useRouteQuery<RawQueryValue, UrlState["alignment"]>(
    "alignment",
    undefined,
    {
      mode: HISTORY_MODE.alignment,
      transform: {
        get: codecs.alignment.decode,
        set: codecs.alignment.encode,
      },
    },
  );

  return { run, branch, t, view, sel, panels, filters, runB, alignment };
}

/** Convenience read-only combined view, for components that want the whole state at once. */
export function useUrlStateSnapshot(state: ReturnType<typeof useUrlState>) {
  return computed<UrlState>(() => ({
    run: state.run.value,
    branch: state.branch.value,
    t: state.t.value,
    view: state.view.value,
    sel: state.sel.value,
    panels: state.panels.value,
    filters: state.filters.value,
    runB: state.runB.value,
    alignment: state.alignment.value,
  }));
}
