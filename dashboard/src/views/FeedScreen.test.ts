import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import FeedScreen from "./FeedScreen.vue";
import { useSalienceStore } from "../stores/salience";
import { useLiveDockStore } from "../stores/liveDock";
import { stubVirtualizerViewport } from "../components/feed/virtualizerTestUtils";

/**
 * FeedScreen.test.ts — following Shell.test.ts's pattern (memory-history
 * router, fetch stubbed, flushPromises), not MapScreen.test.ts's (that
 * screen doesn't touch URL state; this one does).
 *
 * The trace fixture: 200 ticks. Tick 1 is `transmitted`
 * (irileth -> proventus, claim-jarl-death); tick 0 carries TWO
 * `rolled_against` rows (irileth/proventus and guard1/guard2, so Observer
 * mode's per-tick group genuinely collapses more than one row); tick 150
 * is a solitary `rolled_against` (irileth/proventus) used for the
 * rolled-against deep-link landing case, deliberately deep in the list so
 * the scroll-to-tick mechanism is actually exercised; tick 7 is
 * `nothing_salient` (irileth/proventus, claim-jarl-death,
 * "both-informed") — matching the packet's own worked deep-link example
 * verbatim (`t=7&sel=irileth&filters={"outcome":"nothing_salient"}`).
 * Every other tick is a filler `rolled_against` between two other NPCs, so
 * the list is long enough (200 rows) to make virtualization meaningful.
 */

function traceLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return (
    JSON.stringify({
      schema_version: 1,
      seed_id: "jarl-death-demo",
      save_uuid: "whiterun-save-1",
      generation: 0,
      tick,
      stream: "trace",
      seq,
      payload,
    }) + "\n"
  );
}

const rolledAgainst = (tick: number, seq: number, a: string, b: string) =>
  traceLine(tick, seq, {
    record_type: "encounter_rolled",
    roll_key: {},
    value: 0.5,
    threshold: 0.35,
    outcome: "no_encounter",
    location_id: "dragonsreach",
    npc_a: a,
    npc_b: b,
    encountered: false,
  });

const transmitted = (tick: number, seq: number) =>
  traceLine(tick, seq, {
    record_type: "transmitted",
    claim_id: "claim-jarl-death",
    teller_id: "irileth",
    hearer_id: "proventus",
    evidence_id: "e1",
    variant: { variant_id: "variant-auto-1", parent_variant_id: null, slots: {}, mutated_slot: null },
    location_id: "dragonsreach",
  });

const nothingSalient = (tick: number, seq: number) =>
  traceLine(tick, seq, {
    record_type: "nothing_salient",
    location_id: "dragonsreach",
    npc_a: "irileth",
    npc_b: "proventus",
    claim_id: "claim-jarl-death",
    reason: "both-informed",
  });

function buildFixture() {
  let seq = 0;
  const lines: string[] = [];
  const tickOffsets: Record<string, number> = {};
  let byteLen = 0;

  function pushTick(tick: number, tickLines: string[]) {
    tickOffsets[String(tick)] = byteLen;
    for (const line of tickLines) {
      lines.push(line);
      byteLen += new TextEncoder().encode(line).length;
    }
  }

  for (let tick = 0; tick < 200; tick++) {
    if (tick === 0) {
      pushTick(tick, [rolledAgainst(tick, seq++, "irileth", "proventus"), rolledAgainst(tick, seq++, "guard1", "guard2")]);
    } else if (tick === 1) {
      pushTick(tick, [transmitted(tick, seq++)]);
    } else if (tick === 7) {
      pushTick(tick, [nothingSalient(tick, seq++)]);
    } else if (tick === 150) {
      pushTick(tick, [rolledAgainst(tick, seq++, "irileth", "proventus")]);
    } else {
      pushTick(tick, [rolledAgainst(tick, seq++, "hulda", "mikael")]);
    }
  }

  return { content: lines.join(""), tickOffsets };
}

const { content: TRACE_CONTENT, tickOffsets: TICK_OFFSETS } = buildFixture();

const REGISTRY = {
  schema_version: 1,
  runs: [
    {
      run_id: "whiterun-jarl-01",
      seed_id: "jarl-death-demo",
      created_wall_ts: 0,
      branches: [{ save_uuid: "whiterun-save-1", generation: 0 }],
      tick_range: { start: 0, end: 199 },
      streams: { events: "events.jsonl", trace: "trace.jsonl" },
      status: "complete",
    },
  ],
};

const SIDECAR = {
  schema_version: 1,
  streams: {
    events: { tick_offsets: {} },
    trace: { tick_offsets: TICK_OFFSETS },
  },
};

function stubFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.includes("mock-fixtures")) return new Response(null, { status: 404 });
      if (url.endsWith("/runs/index.json")) return new Response(JSON.stringify(REGISTRY), { status: 200 });
      if (url.endsWith("/index.json")) return new Response(JSON.stringify(SIDECAR), { status: 200 });
      if (url.endsWith("trace.jsonl")) {
        const rangeHeader = (init?.headers as Record<string, string> | undefined)?.Range ?? "";
        const bytes = new TextEncoder().encode(TRACE_CONTENT);
        const match = /^bytes=(\d+)-(\d*)$/.exec(rangeHeader);
        let start = 0;
        let end = bytes.length;
        if (match) {
          start = Number(match[1]);
          end = match[2] === "" ? bytes.length : Number(match[2]) + 1;
        }
        end = Math.min(end, bytes.length);
        const text = new TextDecoder().decode(bytes.slice(start, end));
        return new Response(text, {
          status: 206,
          headers: { "Content-Range": `bytes ${start}-${end - 1}/${bytes.length}` },
        });
      }
      return new Response(null, { status: 404 });
    }),
  );
}

async function mountAt(query: string) {
  stubFetch();
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/", component: FeedScreen }],
  });
  await router.push(`/${query}`);
  const pinia = createPinia();
  const wrapper = mount(FeedScreen, {
    global: { plugins: [router, pinia] },
  });
  await router.isReady();
  await flushPromises();
  await flushPromises();
  return { wrapper, router, pinia };
}

describe("FeedScreen.vue", () => {
  let restoreViewport: () => void;

  afterEach(() => {
    vi.unstubAllGlobals();
    restoreViewport?.();
  });

  it("resolves run + t + filters from the URL on load", async () => {
    restoreViewport = stubVirtualizerViewport();
    const { wrapper } = await mountAt(
      `?run=whiterun-jarl-01&t=7&view=feed&filters=${encodeURIComponent(JSON.stringify({ outcome: "nothing_salient" }))}`,
    );
    expect(wrapper.find(".feed-table").exists()).toBe(true);
    // developer/showAll not set -> default observer; the filter narrowed
    // the store down to exactly the one nothing_salient row.
    expect(wrapper.text()).toContain("1 of");
  });

  it("virtualizes: renders far fewer DOM rows than the 200-row fixture", async () => {
    restoreViewport = stubVirtualizerViewport();
    const { wrapper } = await mountAt("?run=whiterun-jarl-01&view=feed&filters=%7B%22outcome%22%3A%22rolled_against%22%7D");
    const rendered = wrapper.findAll("[data-index]");
    expect(rendered.length).toBeGreaterThan(0);
    expect(rendered.length).toBeLessThan(60);
  });

  it("landing case: nothing-salient deep link lands with the named row visible without scrolling", async () => {
    restoreViewport = stubVirtualizerViewport();
    const { wrapper } = await mountAt(
      `?run=whiterun-jarl-01&t=7&view=feed&sel=irileth&filters=${encodeURIComponent(JSON.stringify({ outcome: "nothing_salient" }))}`,
    );
    const target = wrapper.find('[data-tick="7"][data-outcome="nothing_salient"]');
    expect(target.exists()).toBe(true);
  });

  it("landing case: rolled-against deep link (deep in the list) lands with the named row visible without scrolling", async () => {
    restoreViewport = stubVirtualizerViewport();
    const { wrapper } = await mountAt(
      `?run=whiterun-jarl-01&t=150&view=feed&sel=irileth&filters=${encodeURIComponent(JSON.stringify({ outcome: "rolled_against", npc: "irileth" }))}`,
    );
    const target = wrapper.find('[data-tick="150"][data-outcome="rolled_against"]');
    expect(target.exists()).toBe(true);
  });

  it("filters round-trip through the URL in both directions, and back() restores the prior filter state", async () => {
    restoreViewport = stubVirtualizerViewport();
    const { wrapper, router, pinia } = await mountAt("?run=whiterun-jarl-01&view=feed");
    const { useFeedStore } = await import("../stores/feed");
    const feed = useFeedStore(pinia);
    expect(feed.filteredRows).toHaveLength(201); // 200 ticks, tick 0 carries two rows

    // UI -> URL: changing the outcome filter select writes urlState.filters.
    // (Field order in FeedFilterBar.vue: NPC, location, outcome, claim.)
    const select = wrapper.findAll(".feed-filter-bar select")[2];
    await select.setValue("transmitted");
    await flushPromises();
    expect(JSON.parse(router.currentRoute.value.query.filters as string)).toEqual({
      outcome: "transmitted",
    });
    expect(feed.filteredRows).toHaveLength(1);

    // filters is 'push' mode (urlState.ts) -> back() should undo it.
    await router.back();
    await flushPromises();
    expect(router.currentRoute.value.query.filters).toBeUndefined();
    expect(feed.filteredRows).toHaveLength(201);
  });

  it("row click selects both participants into sel and jumps t to the row's tick", async () => {
    restoreViewport = stubVirtualizerViewport();
    const { wrapper, router, pinia } = await mountAt(
      "?run=whiterun-jarl-01&view=feed&filters=%7B%22outcome%22%3A%22transmitted%22%7D",
    );
    const row = wrapper.find('[data-tick="1"][data-outcome="transmitted"]');
    expect(row.exists()).toBe(true);
    await row.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query.t).toBe("1");
    expect(router.currentRoute.value.query.sel).toBe("irileth,proventus");

    // Verified finding (packet Task 3): FeedScreen never calls
    // frameLog.bindToUrlState(), so nothing is watching urlState.t for
    // this store — writing `t` from a feed row click does NOT, by
    // itself, detach the global LIVE dock. (It would if some other
    // mounted view had already installed that watcher — see
    // FeedScreen.vue's header comment.)
    const liveDock = useLiveDockStore(pinia);
    expect(liveDock.docked).toBe(true);
  });

  it("developer salience: renders the full row set, no group chrome", async () => {
    restoreViewport = stubVirtualizerViewport();
    const { wrapper, pinia } = await mountAt("?run=whiterun-jarl-01&view=feed");
    const salience = useSalienceStore(pinia);
    salience.setLevel("developer");
    await flushPromises();
    expect(wrapper.find(".feed-group-header").exists()).toBe(false);
  });

  it("story salience: shows only transmissions + declines", async () => {
    restoreViewport = stubVirtualizerViewport();
    const { wrapper, pinia } = await mountAt("?run=whiterun-jarl-01&view=feed");
    const salience = useSalienceStore(pinia);
    salience.setLevel("story");
    await flushPromises();
    expect(wrapper.findAll("[data-index]").every((el) => el.attributes("data-outcome") !== "rolled_against")).toBe(
      true,
    );
    expect(wrapper.findAll("[data-index]").every((el) => el.attributes("data-outcome") !== "nothing_salient")).toBe(
      true,
    );
  });

  it("observer salience (default): collapses trace rows into a per-tick group header, expandable in place", async () => {
    restoreViewport = stubVirtualizerViewport();
    const { wrapper } = await mountAt("?run=whiterun-jarl-01&view=feed&filters=%7B%22location%22%3A%22dragonsreach%22%7D");
    const header = wrapper.find('.feed-group-header[data-tick="0"]');
    expect(header.exists()).toBe(true);
    expect(header.text()).toContain("2 trace rows");
    await header.trigger("click");
    await flushPromises();
    expect(wrapper.find('.feed-group-header[data-tick="0"]').exists()).toBe(false);
    expect(wrapper.findAll('[data-tick="0"][data-outcome="rolled_against"]')).toHaveLength(2);
  });

  it("the all events toggle bypasses grouping/filtering-by-salience at every level", async () => {
    restoreViewport = stubVirtualizerViewport();
    const { wrapper, pinia } = await mountAt("?run=whiterun-jarl-01&view=feed&filters=%7B%22location%22%3A%22dragonsreach%22%7D");
    const salience = useSalienceStore(pinia);
    salience.setLevel("story");
    salience.setShowAll(true);
    await flushPromises();
    expect(wrapper.find(".feed-group-header").exists()).toBe(false);
    expect(wrapper.find('[data-tick="0"][data-outcome="rolled_against"]').exists()).toBe(true);
  });
});
