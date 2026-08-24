import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import MapScreen from "./MapScreen.vue";
import MapView from "./MapView.vue";
import TimelineBar from "../components/timeline/TimelineBar.vue";

/**
 * MapScreen.test.ts — the ONE authorized test-assertion rewrite this lane
 * makes (packet's Task 7 / Conventions): MapScreen now consumes real
 * per-tick state via `stores/mapData.ts`, wired to URL state, which makes
 * the old no-router mounting premise untrue. Follows Shell.test.ts's
 * memory-history-router + stubbed-fetch + flushPromises pattern (same
 * idiom FeedScreen.test.ts already established for a URL-state-driven
 * screen), and builds its own small synthetic events+trace fixture rather
 * than depending on the gitignored `runs/whiterun-jarl-01` (that real run
 * is exercised instead by `derived/mapMarkers.realRun.test.ts`, which
 * degrades to skipped when `runs/` is absent).
 *
 * Fixture: one claim (`claim-jarl-death`), one keyframe at tick 0 with
 * `irileth`'s witnessed belief, a `transmitted` at tick 1 (irileth ->
 * proventus), and a `npc_died` event for `jarl_balgruuf` at tick 0,
 * location `dragonsreach` — deliberately shaped like the real run's own
 * death-only-NPC case (no belief, no trace participation) so the
 * jarl_balgruuf-specific behavior is exercised end-to-end through the
 * screen, not just at the derived-module unit level.
 */

function eventLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return (
    JSON.stringify({ schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "events", seq, payload }) +
    "\n"
  );
}

function traceLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return (
    JSON.stringify({ schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "trace", seq, payload }) +
    "\n"
  );
}

const KEYFRAME_STATE = {
  claims: [
    {
      id: "claim-jarl-death",
      kind: "npc_death",
      slots: {},
      canonical_event_key: { save_uuid: "s", generation: 0, seq: 0 },
      truth_status: "unconfirmed",
    },
  ],
  variants: [],
  beliefs: [
    {
      id: "belief-irileth",
      holder_id: "irileth",
      claim_id: "claim-jarl-death",
      variant_id: null,
      confidence: 0.95,
      verbatim_strength: 1,
      gist_strength: 1,
      first_learned: 0,
      last_rehearsed: 0,
    },
  ],
  evidence: [],
  rumor_states: [
    {
      npc_id: "irileth",
      claim_id: "claim-jarl-death",
      variant_id: null,
      stage: "heard",
      first_heard: 0,
      last_heard: 0,
      last_told: null,
      exposure_count: 1,
      distinct_source_count: 1,
    },
  ],
};

const diedLine = eventLine(0, 0, { event_type: "npc_died", npc_id: "jarl_balgruuf", location_id: "dragonsreach", cause: "assassination" });
const keyframeLine = eventLine(0, 1, { record_type: "keyframe", state: KEYFRAME_STATE });
const EVENTS_CONTENT = diedLine + keyframeLine;
const EVENT_TICK_OFFSETS = { "0": 0 };

const encounterLine = traceLine(0, 0, { record_type: "encounter_rolled", npc_a: "irileth", npc_b: "proventus", location_id: "dragonsreach", encountered: true, value: 0, threshold: 1, roll_key: {}, outcome: "encountered" });
const transmittedLine = traceLine(1, 1, {
  record_type: "transmitted",
  claim_id: "claim-jarl-death",
  teller_id: "irileth",
  teller_belief_id: "belief-irileth",
  hearer_id: "proventus",
  hearer_belief_id: "belief-proventus",
  evidence_id: "e1",
  variant: { variant_id: "v1", parent_variant_id: null, slots: {}, mutated_slot: null },
  location_id: "dragonsreach",
});
const TRACE_CONTENT = encounterLine + transmittedLine;
const TRACE_TICK_OFFSETS = { "0": 0, "1": new TextEncoder().encode(encounterLine).length };

const REGISTRY = {
  schema_version: 1,
  runs: [
    {
      run_id: "test-run",
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
    events: { tick_offsets: EVENT_TICK_OFFSETS, keyframe_offsets: [{ tick: 0, offset: keyframeLine.length ? new TextEncoder().encode(diedLine).length : 0 }] },
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

async function mountAt(query: string) {
  stubFetch();
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/", component: MapScreen }],
  });
  await router.push(`/${query}`);
  const pinia = createPinia();
  const wrapper = mount(MapScreen, { global: { plugins: [router, pinia] } });
  await router.isReady();
  await flushPromises();
  await flushPromises();
  return { wrapper, router, pinia };
}

describe("MapScreen.vue", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("mounts MapView inside its chrome (TimelineBar moved to the global shell, lane 54)", async () => {
    const { wrapper } = await mountAt("?run=test-run");
    expect(wrapper.findComponent(MapView).exists()).toBe(true);
    // Lane 54 (M7 gate fix): the timeline is global chrome now, mounted
    // once in App.vue rather than duplicated inside MapScreen -- this
    // screen doesn't render it at all anymore.
    expect(wrapper.findComponent(TimelineBar).exists()).toBe(false);
  });

  it("run loads -> markers render the real cast (irileth, proventus, jarl_balgruuf) at t=0", async () => {
    const { wrapper } = await mountAt("?run=test-run&t=0");
    const dots = wrapper.findAll(".npc-marker__dot");
    const titles = dots.map((d) => d.attributes("title"));
    expect(titles.some((t) => t?.startsWith("Irileth"))).toBe(true);
    expect(titles.some((t) => t?.startsWith("Proventus"))).toBe(true);
    expect(titles.some((t) => t?.startsWith("Jarl Balgruuf"))).toBe(true);
  });

  it("jarl_balgruuf renders as unheard at dragonsreach at both t=0 and t=1", async () => {
    for (const t of [0, 1]) {
      const { wrapper } = await mountAt(`?run=test-run&t=${t}`);
      const dot = wrapper.findAll(".npc-marker__dot").find((d) => d.attributes("title") === "Jarl Balgruuf — unheard");
      expect(dot, `jarl_balgruuf dot missing at t=${t}`).toBeDefined();
    }
  });

  it("scrub (t change) re-derives markers: irileth flips from heard to repeated once she's told proventus", async () => {
    const { wrapper, router } = await mountAt("?run=test-run&t=0");
    const titleAt0 = wrapper.findAll(".npc-marker__dot").find((d) => d.attributes("title")?.startsWith("Irileth"))?.attributes("title");
    expect(titleAt0).toBe("Irileth — heard");

    await router.push("/?run=test-run&t=1");
    await flushPromises();
    await flushPromises();
    const titleAt1 = wrapper.findAll(".npc-marker__dot").find((d) => d.attributes("title")?.startsWith("Irileth"))?.attributes("title");
    expect(titleAt1).toBe("Irileth — repeated");
  });

  it("deep link ?sel=irileth rings the right marker and shows her in the inspector", async () => {
    const { wrapper } = await mountAt("?run=test-run&t=0&sel=irileth");
    const dot = wrapper.findAll(".npc-marker__dot").find((d) => d.attributes("title")?.startsWith("Irileth"));
    const markerRoot = dot?.element.parentElement;
    expect(markerRoot?.querySelector(".npc-marker__selection")).not.toBeNull();
    const aside = wrapper.find('aside[aria-label="inspector slot"]');
    expect(aside.text()).toContain("irileth");
  });

  it("marker click writes sel into the URL", async () => {
    const { wrapper, router } = await mountAt("?run=test-run&t=0");
    const dot = wrapper.findAll(".npc-marker__dot").find((d) => d.attributes("title")?.startsWith("Proventus"));
    await dot!.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query.sel).toBe("proventus");
  });

  it("no-carrier run: RouteOverlay/SatelliteNode/CarrierMarker are hidden", async () => {
    const { wrapper } = await mountAt("?run=test-run&t=0");
    expect(wrapper.find(".satellite-node").exists()).toBe(false);
    expect(wrapper.find(".carrier-marker").exists()).toBe(false);
    expect(wrapper.find(".route-overlay").exists()).toBe(false);
  });

  it("stage legend shows real counts and the active claim id for the loaded run", async () => {
    const { wrapper } = await mountAt("?run=test-run&t=0");
    expect(wrapper.find(".stage-legend__title").text()).toBe("claim-jarl-death STAGE");
    // Fixture cast at t=0: {irileth, proventus, jarl_balgruuf}; irileth has
    // heard the claim (witnessed at tick 0), proventus/jarl_balgruuf have
    // not (the transmission to proventus happens at tick 1) -> unheard: 2,
    // heard: 1, everything else 0, coverage 1/3. If `counts`/`coverage`
    // weren't actually wired through (still the fixture's 26-cast
    // defaults, or all zero), this would fail.
    const items = wrapper.findAll(".stage-legend__item");
    const byName = Object.fromEntries(items.map((el) => [el.find(".stage-legend__name").text(), el.find("a").text()]));
    expect(byName).toEqual({ unheard: "2", heard: "1", repeated: "0", dormant: "0", forgotten: "0" });
    expect(wrapper.find(".stage-legend__coverage").text()).toBe("coverage 1/3");
  });

  it("defaults the salience switch to OBSERVER active", async () => {
    const { wrapper } = await mountAt("?run=test-run&t=0");
    const active = wrapper.find(".salience-switch__option--active");
    expect(active.text()).toBe("OBSERVER");
  });

  it("lane 35: with no filters.variant, the lens selector shows the default rumor-stage lens name, unedited", async () => {
    const { wrapper } = await mountAt("?run=test-run&t=1");
    expect(wrapper.find(".lens-panel__lens").text()).toContain("rumor-stage");
  });

  it("lane 35: filters.variant=canonical switches the lens label and restyles markers by holding class", async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/", component: MapScreen }] });
    stubFetch();
    await router.push({ path: "/", query: { run: "test-run", t: "1", filters: JSON.stringify({ variant: "canonical" }) } });
    const wrapper = mount(MapScreen, { global: { plugins: [router, createPinia()] } });
    await router.isReady();
    await flushPromises();
    await flushPromises();

    expect(wrapper.find(".lens-panel__lens").text()).toContain("variant: canonical");

    // At t=1: irileth has told proventus (stage "repeated" per the existing
    // scrub test above) and still holds variant null (canonical, so
    // holds-it); proventus now holds v1 ("heard", holds-different);
    // jarl_balgruuf holds no belief on this claim at all (holds-none).
    const titles = wrapper.findAll(".npc-marker__dot").map((d) => d.attributes("title"));
    expect(titles.some((t) => t === "Irileth — repeated — holds-it")).toBe(true);
    expect(titles.some((t) => t === "Proventus — heard — holds-different")).toBe(true);
    expect(titles.some((t) => t === "Jarl Balgruuf — unheard — holds-none")).toBe(true);
  });

  it("lane 35: filters.variant=v1 flips the holds-it holder to proventus", async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/", component: MapScreen }] });
    stubFetch();
    await router.push({ path: "/", query: { run: "test-run", t: "1", filters: JSON.stringify({ variant: "v1" }) } });
    const wrapper = mount(MapScreen, { global: { plugins: [router, createPinia()] } });
    await router.isReady();
    await flushPromises();
    await flushPromises();

    expect(wrapper.find(".lens-panel__lens").text()).toContain("variant: v1");
    const titles = wrapper.findAll(".npc-marker__dot").map((d) => d.attributes("title"));
    expect(titles.some((t) => t === "Proventus — heard — holds-it")).toBe(true);
    expect(titles.some((t) => t === "Irileth — repeated — holds-different")).toBe(true);
  });

  it("shows the tolerated-absence run note when no run is selected (runs/index.json 404s)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 404 })),
    );
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/", component: MapScreen }] });
    await router.push("/");
    const wrapper = mount(MapScreen, { global: { plugins: [router, createPinia()] } });
    await router.isReady();
    await flushPromises();
    await flushPromises();
    expect(wrapper.text()).toContain("no runs/index.json yet — showing the mock-t0 dev fixture only");
  });
});
