import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import RolesScreen from "./RolesScreen.vue";

/**
 * RolesScreen.test.ts -- SchedDiffScreen.test.ts's pattern (memory-history
 * router, fetch stubbed to serve a synthetic run, flushPromises).
 *
 * Fixture: no keyframe (role events replay from tick 0 via `RunReader`'s
 * `roleEventsUpTo` full scan alone) -- `jarl_of_whiterun` installed under
 * jarl_balgruuf, who dies and is succeeded by irileth, with `hold_court`
 * lapsing in between, plus an untouched `steward_of_whiterun` -- the same
 * shape as `runs/north-star-01`.
 */
function eventLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return JSON.stringify({ schema_version: 1, seed_id: "s", save_uuid: "save-1", generation: 0, tick, stream: "events", seq, payload }) + "\n";
}

const EVENTS_CONTENT =
  eventLine(0, 1, {
    event_type: "role_installed",
    gamets: 0,
    wall_ts: 0,
    origin: null,
    role_id: "steward_of_whiterun",
    title: "Steward of Whiterun",
    institution_id: "whiterun_court",
    duties: [{ name: "collect_taxes", lapse_status_kind: "duty_lapsed" }],
    holder_id: "proventus",
  }) +
  eventLine(0, 2, {
    event_type: "role_installed",
    gamets: 0,
    wall_ts: 0,
    origin: null,
    role_id: "jarl_of_whiterun",
    title: "Jarl of Whiterun",
    institution_id: "whiterun_court",
    duties: [{ name: "hold_court", lapse_status_kind: "duty_lapsed" }],
    holder_id: "jarl_balgruuf",
  }) +
  eventLine(0, 3, {
    event_type: "npc_died",
    gamets: 0,
    wall_ts: 0,
    origin: { kind: "scenario", detail: "test" },
    npc_id: "jarl_balgruuf",
    cause: "assassination",
    killer_id: "the_player",
    location_id: "dragonsreach",
  }) +
  eventLine(0, 4, {
    event_type: "status_changed",
    gamets: 0,
    wall_ts: 0,
    origin: null,
    npc_id: "jarl_balgruuf",
    status_kind: "duty_lapsed",
    detail: "hold_court",
    location_id: null,
  }) +
  eventLine(0, 5, {
    event_type: "status_changed",
    gamets: 0,
    wall_ts: 0,
    origin: null,
    npc_id: "irileth",
    status_kind: "role_appointed",
    detail: "jarl_of_whiterun",
    location_id: null,
  });

const EVENT_TICK_OFFSETS = { "0": 0 };
const TRACE_CONTENT = "";
const TRACE_TICK_OFFSETS = {};

const REGISTRY = {
  schema_version: 1,
  runs: [
    {
      run_id: "roles-test-run",
      seed_id: "s",
      created_wall_ts: 0,
      branches: [{ save_uuid: "save-1", generation: 0 }],
      tick_range: { start: 0, end: 20 },
      streams: { events: "events.jsonl", trace: "trace.jsonl" },
      status: "complete",
    },
  ],
};

const SIDECAR = {
  schema_version: 1,
  streams: {
    events: { tick_offsets: EVENT_TICK_OFFSETS, keyframe_offsets: [] },
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
      { path: "/", component: RolesScreen },
      { path: "/roles", component: RolesScreen },
      { path: "/map", component: { template: "<div>map</div>" } },
      { path: "/feed", component: { template: "<div>feed</div>" } },
    ],
  });
  await router.push(query);
  const pinia = createPinia();
  const wrapper = mount(RolesScreen, { global: { plugins: [router, pinia] } });
  await router.isReady();
  await flushPromises();
  await flushPromises();
  return { wrapper, router };
}

describe("RolesScreen.vue", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("deep link ?run=...&t=... lists both roles and auto-selects the first", async () => {
    const { wrapper } = await mountAt("/roles?run=roles-test-run&t=10");
    expect(wrapper.text()).toContain("Jarl of Whiterun");
    expect(wrapper.text()).toContain("Steward of Whiterun");
    expect(wrapper.findAll(".roles-screen__list-item")).toHaveLength(2);
  });

  it("jarl_of_whiterun shows the succession (irileth, linked) and the lapsed hold_court duty", async () => {
    const { wrapper } = await mountAt("/roles?run=roles-test-run&t=10");
    const jarlButton = wrapper.findAll(".roles-screen__list-item").find((btn) => btn.text().includes("Jarl of Whiterun"))!;
    await jarlButton.trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("irileth");
    expect(wrapper.text()).toContain("hold_court");
    expect(wrapper.text()).toContain("lapsed");

    const holderLink = wrapper.find(".role-card__holder-link");
    expect(holderLink.exists()).toBe(true);
    expect(holderLink.text()).toBe("irileth");
    expect(holderLink.attributes("href")).toBe("/map?run=roles-test-run&sel=irileth");

    const succession = wrapper.find(".role-card__succession");
    expect(succession.text()).toContain("irileth");
    expect(succession.text()).toContain("t0");
  });

  it("steward_of_whiterun (unselected by default when jarl sorts second alphabetically) shows proventus with no lapse", async () => {
    const { wrapper } = await mountAt("/roles?run=roles-test-run&t=10");
    // roleId sort: "jarl_of_whiterun" < "steward_of_whiterun" -- jarl is
    // selected by default; click steward explicitly.
    const stewardButton = wrapper.findAll(".roles-screen__list-item").find((btn) => btn.text().includes("Steward of Whiterun"))!;
    await stewardButton.trigger("click");
    await flushPromises();
    expect(wrapper.find(".role-card__holder-link").text()).toBe("proventus");
    expect(wrapper.find(".role-card__duty[data-lapsed='true']").exists()).toBe(false);
  });

  it("shows a placeholder when no run is selected", async () => {
    const { wrapper } = await mountAt("/roles?");
    expect(wrapper.text()).toContain("no run loaded");
  });
});
