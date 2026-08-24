import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import VariantTreeScreen from "../../views/VariantTreeScreen.vue";
import { encodeUrlState, decodeUrlState, URL_STATE_DEFAULTS } from "../../state/urlState";

/**
 * Host-integration coverage for the provenance drill-down (packet Task 4):
 * "drill opens from a [host] belief -> `panels` in the URL; deep link with
 * the panel state lands open on the right belief; scrub re-derives." Lives
 * here (a new file under the permitted `components/drilldown/` directory)
 * rather than editing `views/VariantTreeScreen.test.ts` -- that file is
 * outside this lane's Edit list and its existing assertions are pinned
 * immutable.
 *
 * Harness lifted verbatim from `VariantTreeScreen.test.ts` (memory-history
 * router, fetch stubbed to serve a synthetic run, double `flushPromises`):
 * its fixture already carries a real `transmitted` + `mutation_applied` +
 * `supersession` chain with real evidence ids, exactly what the drill-down
 * needs. `VariantTreeScreen` is the cheapest host to mount for this (no
 * feed/selection store setup) -- `HolderTable`'s drill click and
 * `ProvenancePanel`'s mount are the same component wiring FeedScreen/
 * MapScreen also use.
 */

function eventLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return JSON.stringify({ schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "events", seq, payload }) + "\n";
}

function traceLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return JSON.stringify({ schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "trace", seq, payload }) + "\n";
}

const KEYFRAME_STATE = {
  claims: [
    { id: "claim-a", kind: "npc_death", slots: { loc: "market" }, canonical_event_key: { save_uuid: "s", generation: 0, seq: 0 }, truth_status: "unconfirmed" },
  ],
  variants: [],
  beliefs: [
    { id: "belief-w", holder_id: "npc-w", claim_id: "claim-a", variant_id: null, confidence: 0.95, verbatim_strength: 1, gist_strength: 1, first_learned: 0, last_rehearsed: 0 },
  ],
  evidence: [
    { id: "ev-w", belief_id: "belief-w", evidence_type: "witnessed", source_id: "npc-w", predecessor_belief_id: null, gamets: 0, strength: 1 },
  ],
  rumor_states: [],
};

const keyframeLine = eventLine(0, 0, { record_type: "keyframe", state: KEYFRAME_STATE });
const EVENTS_CONTENT = keyframeLine;
const EVENT_TICK_OFFSETS = { "0": 0 };

const transmit1 = traceLine(1, 0, {
  record_type: "transmitted",
  claim_id: "claim-a",
  teller_id: "npc-w",
  teller_belief_id: "belief-w",
  hearer_id: "npc-x",
  hearer_belief_id: "belief-x",
  evidence_id: "ev-1",
  variant: { variant_id: "va-1", parent_variant_id: null, slots: { loc: "market" }, mutated_slot: null },
  location_id: "market",
});
const transmit2 = traceLine(2, 1, {
  record_type: "transmitted",
  claim_id: "claim-a",
  teller_id: "npc-x",
  teller_belief_id: "belief-x",
  hearer_id: "npc-y",
  hearer_belief_id: "belief-y",
  evidence_id: "ev-2",
  variant: { variant_id: "va-2", parent_variant_id: "va-1", slots: { loc: "alley" }, mutated_slot: "loc" },
  location_id: "alley",
});
const mutationApplied = traceLine(2, 2, {
  record_type: "mutation_applied",
  claim_id: "claim-a",
  parent_variant_id: "va-1",
  variant_id: "va-2",
  slot: "loc",
  old_value: "market",
  new_value: "alley",
  mutation_id: "mut-a",
  roll_key: {},
});
const supersession = traceLine(3, 3, {
  record_type: "supersession",
  holder_id: "npc-y",
  claim_id: "claim-a",
  loser_variant_id: "va-2",
  winner_variant_id: null,
  resolution_rule: "rule-x",
  confidence_dent: 0.15,
  teller_id: "npc-x",
  teller_belief_id: "belief-x",
  evidence_id: "ev-s",
  winner_belief_id: "belief-w",
});
const TRACE_CONTENT = transmit1 + transmit2 + mutationApplied + supersession;
const TRACE_TICK_OFFSETS = {
  "1": 0,
  "2": new TextEncoder().encode(transmit1).length,
  "3": new TextEncoder().encode(transmit1 + transmit2 + mutationApplied).length,
};

const REGISTRY = {
  schema_version: 1,
  runs: [
    {
      run_id: "tree-test-run",
      seed_id: "s",
      created_wall_ts: 0,
      branches: [{ save_uuid: "s", generation: 0 }],
      tick_range: { start: 0, end: 3 },
      streams: { events: "events.jsonl", trace: "trace.jsonl" },
      status: "complete",
    },
  ],
};

const SIDECAR = {
  schema_version: 1,
  streams: {
    events: { tick_offsets: EVENT_TICK_OFFSETS, keyframe_offsets: [{ tick: 0, offset: 0 }] },
    trace: { tick_offsets: TRACE_TICK_OFFSETS },
  },
};

function rangeResponse(content: string, init?: RequestInit): Response {
  const rangeHeader = (init?.headers as Record<string, string> | undefined)?.Range ?? "";
  const bytes = new TextEncoder().encode(content);
  const match = /^bytes=(\d+)-(\d*)$/.exec(rangeHeader);
  let start = 0;
  let end = bytes.length;
  if (match) {
    start = Number(match[1]);
    end = match[2] === "" ? bytes.length : Number(match[2]) + 1;
  }
  end = Math.min(end, bytes.length);
  const text = new TextDecoder().decode(bytes.slice(start, end));
  return new Response(text, { status: 206, headers: { "Content-Range": `bytes ${start}-${end - 1}/${bytes.length}` } });
}

function stubFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/runs/index.json")) return new Response(JSON.stringify(REGISTRY), { status: 200 });
      if (url.endsWith("/index.json")) return new Response(JSON.stringify(SIDECAR), { status: 200 });
      if (url.endsWith("events.jsonl")) return rangeResponse(EVENTS_CONTENT, init);
      if (url.endsWith("trace.jsonl")) return rangeResponse(TRACE_CONTENT, init);
      return new Response(null, { status: 404 });
    }),
  );
}

async function mountAt(query: string) {
  stubFetch();
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: VariantTreeScreen },
      { path: "/tree", component: VariantTreeScreen },
    ],
  });
  await router.push(query);
  const pinia = createPinia();
  const wrapper = mount(VariantTreeScreen, { global: { plugins: [router, pinia] } });
  await router.isReady();
  await flushPromises();
  await flushPromises();
  return { wrapper, router, pinia };
}

describe("provenance drill-down host integration (VariantTreeScreen)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("drill opens from a holder-table row -> panels carries the drill target in the URL", async () => {
    const { wrapper, router } = await mountAt("/?run=tree-test-run&t=3");
    const canonical = wrapper.findAll(".tree-svg__node").find((n) => n.attributes("aria-label")?.startsWith("canonical |"))!;
    await canonical.trigger("click");
    await flushPromises();

    expect(wrapper.find('[aria-label="drill into npc-w\'s provenance"]').exists()).toBe(true);
    await wrapper.find('[aria-label="drill into npc-w\'s provenance"]').trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.query.panels).toBe("drill%3Abelief-w");
    expect(wrapper.find(".provenance-panel").exists()).toBe(true);
    expect(wrapper.find(".provenance-panel__belief").text()).toBe("belief-w");
  });

  it("deep link with panels pre-set lands open on the target belief, no click needed", async () => {
    const { wrapper } = await mountAt("/?run=tree-test-run&t=3&panels=drill%3Abelief-w");
    expect(wrapper.find(".provenance-panel").exists()).toBe(true);
    expect(wrapper.find(".provenance-panel__belief").text()).toBe("belief-w");
  });

  it("re-reads the app-produced (double-escaped, %253A) URL exactly as the address bar would show it", async () => {
    const { wrapper } = await mountAt("/?run=tree-test-run&t=3&panels=drill%253Abelief-w");
    expect(wrapper.find(".provenance-panel").exists()).toBe(true);
    expect(wrapper.find(".provenance-panel__belief").text()).toBe("belief-w");
  });

  it("scrubbing t re-derives the shown chain: belief-w renders 1 column (its own witness) before the supersession lands, 2 (DAG-honest: witness + the supersession's new incoming edge) once it has", async () => {
    const { wrapper, router } = await mountAt("/?run=tree-test-run&t=2&panels=drill%3Abelief-w");
    expect(wrapper.find(".provenance-panel__tick").text()).toContain("t=2");
    let columns = wrapper.findAll('[data-testid="provenance-column"]');
    expect(columns).toHaveLength(1);

    // t=3: the supersession record appends a new Evidence record onto
    // belief-w (the winner) -- reconstruct.ts's landed `supersession` case
    // -- so the re-derived chain now shows 2 parallel columns, not a
    // stale 1 carried over from when the panel first opened.
    await router.push("/?run=tree-test-run&t=3&panels=drill%3Abelief-w");
    await flushPromises();
    await flushPromises();

    expect(wrapper.find(".provenance-panel__tick").text()).toContain("t=3");
    columns = wrapper.findAll('[data-testid="provenance-column"]');
    expect(columns).toHaveLength(2);
  });
});

describe("panels URL codec (pure): a drill-target string round-trips with zero codec changes", () => {
  it("encodeUrlState/decodeUrlState round-trips a `drill:<beliefId>` panels entry", () => {
    const state = { ...URL_STATE_DEFAULTS, panels: ["drill:belief-x"] };
    const encoded = encodeUrlState(state);
    const decoded = decodeUrlState(encoded);
    expect(decoded.panels).toEqual(["drill:belief-x"]);
  });
});
