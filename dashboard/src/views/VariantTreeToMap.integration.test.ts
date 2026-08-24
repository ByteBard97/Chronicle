import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import VariantTreeScreen from "./VariantTreeScreen.vue";
import MapScreen from "./MapScreen.vue";

/**
 * VariantTreeToMap.integration.test.ts — lane 35's deep-link requirement:
 * "the tree -> map link lands with the lens active". `VariantTreeScreen.test.ts`
 * already checks the built href in isolation; `MapScreen.test.ts` already
 * checks that a `filters.variant` in the URL activates the lens in
 * isolation. This test closes the loop end-to-end: click a node in the real
 * `VariantTreeScreen`, follow the real built href through an actual router
 * navigation, and assert the resulting `MapScreen` mount shows the lens
 * active — proving the two screens' independently-tested halves actually
 * compose, not just that each half works alone.
 *
 * Fixture: `VariantTreeScreen.test.ts`'s own `tree-test-run` (claim-a,
 * witness npc-w -> transmitted to npc-x on va-1). Reused verbatim rather
 * than re-invented so this test exercises the exact tree shape the other
 * tree-side tests already pin. `MapScreen` won't be able to place any
 * markers for this run (its trace records use `location_id: "market"`,
 * which the real `dashboard/map/whiterun_map.json` doesn't define -- see
 * `mapMarkers.variantLens.realRun.test.ts`'s header for the same,
 * independently-discovered gap against the real carrier-mutation-01 run) --
 * irrelevant here, since what's under test is the lens-selector label and
 * URL wiring, not marker placement.
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
  evidence: [],
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
const TRACE_CONTENT = transmit1;
const TRACE_TICK_OFFSETS = { "1": 0 };

const REGISTRY = {
  schema_version: 1,
  runs: [
    {
      run_id: "tree-test-run",
      seed_id: "s",
      created_wall_ts: 0,
      branches: [{ save_uuid: "s", generation: 0 }],
      tick_range: { start: 0, end: 1 },
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
      if (url.includes("mock-fixtures")) return new Response(null, { status: 404 });
      if (url.endsWith("/runs/index.json")) return new Response(JSON.stringify(REGISTRY), { status: 200 });
      if (url.endsWith("/index.json")) return new Response(JSON.stringify(SIDECAR), { status: 200 });
      if (url.endsWith("events.jsonl")) return rangeResponse(EVENTS_CONTENT, init);
      if (url.endsWith("trace.jsonl")) return rangeResponse(TRACE_CONTENT, init);
      return new Response(null, { status: 404 });
    }),
  );
}

describe("tree -> map deep link (lane 35)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("clicking va-1's node then following 'view on map' lands on MapScreen with the variant lens active for va-1", async () => {
    stubFetch();
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/tree", component: VariantTreeScreen },
        { path: "/map", component: MapScreen },
      ],
    });
    await router.push("/tree?run=tree-test-run&t=1");
    const pinia = createPinia();
    const treeWrapper = mount(VariantTreeScreen, { global: { plugins: [router, pinia] } });
    await router.isReady();
    await flushPromises();
    await flushPromises();

    const node = treeWrapper.findAll(".tree-svg__node").find((n) => n.attributes("aria-label")?.startsWith("va-1 |"));
    await node!.trigger("click");
    await flushPromises();

    const href = treeWrapper.find(".tree-screen__view-on-map").attributes("href")!;
    expect(href).toContain("run=tree-test-run");
    expect(href).toContain("t=1");

    treeWrapper.unmount();
    await router.push(href);
    const mapWrapper = mount(MapScreen, { global: { plugins: [router, pinia] } });
    await router.isReady();
    await flushPromises();
    await flushPromises();

    expect(mapWrapper.find(".lens-panel__lens").text()).toContain("variant: va-1");
  });
});
