import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import FeedScreen from "./FeedScreen.vue";
import { stubVirtualizerViewport } from "../components/feed/virtualizerTestUtils";

/**
 * The M3 gate's one deferred item, folded into lane 30 (ui-spec §3.7's
 * packet, "the T3.4 declined-by-rule deep link"): a deep link to a
 * `transmission_declined` row must land with the row visible and its
 * rule name readable without scrolling. `FeedScreen.vue`/`feedReader.ts`
 * are unmodified by this lane (out of its file boundary, already correct
 * per the coordinator's review: `mapTraceRecordToFeedRow` already maps
 * `transmission_declined` to `{kind: "declined", rule}`, and
 * `FeedOutcomeCell.vue` already renders `rule: {{ row.detail.rule }}`
 * inline) -- this is a NEW, standalone test file proving that existing
 * path against the real `runs/tier3-demo-01` demo run, not an edit to
 * `FeedScreen.test.ts` (a landed lane's file, out of bounds).
 *
 * Real sample (`trace.jsonl`, tick 4, repeats ticks 4-47):
 * `{"tick":4,"claim_id":"claim-player-secret","teller_id":"hulda",
 * "hearer_id":"olfrid","location_id":"bannered_mare",
 * "rule":"tell-decision-policy","roll_key":null}`.
 */
const RUN_DIR = path.resolve(process.cwd(), "../runs/tier3-demo-01");
const REGISTRY_FILE = path.resolve(process.cwd(), "../runs/index.json");
const SIDECAR_FILE = path.join(RUN_DIR, "index.json");
const EVENTS_FILE = path.join(RUN_DIR, "events.jsonl");
const TRACE_FILE = path.join(RUN_DIR, "trace.jsonl");
const runExists = existsSync(REGISTRY_FILE) && existsSync(SIDECAR_FILE) && existsSync(EVENTS_FILE) && existsSync(TRACE_FILE);

function rangeResponse(bytes: Uint8Array, init?: RequestInit): Response {
  const rangeHeader = (init?.headers as Record<string, string> | undefined)?.Range ?? "";
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
  const registry = readFileSync(REGISTRY_FILE, "utf8");
  const sidecar = readFileSync(SIDECAR_FILE, "utf8");
  const eventsBytes = readFileSync(EVENTS_FILE);
  const traceBytes = readFileSync(TRACE_FILE);

  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/runs/index.json")) return new Response(registry, { status: 200 });
      if (url.includes("tier3-demo-01") && url.endsWith("/index.json")) return new Response(sidecar, { status: 200 });
      if (url.endsWith("events.jsonl")) return rangeResponse(new Uint8Array(eventsBytes), init);
      if (url.endsWith("trace.jsonl")) return rangeResponse(new Uint8Array(traceBytes), init);
      return new Response(null, { status: 404 });
    }),
  );
}

async function mountAt(query: string) {
  stubFetch();
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: FeedScreen },
      { path: "/feed", component: FeedScreen },
    ],
  });
  await router.push(query);
  const pinia = createPinia();
  const wrapper = mount(FeedScreen, { global: { plugins: [router, pinia] } });
  await router.isReady();
  await flushPromises();
  await flushPromises();
  await flushPromises();
  return { wrapper, router };
}

describe.skipIf(!runExists)("FeedScreen T3.4 declined-by-rule landing case (real runs/tier3-demo-01)", () => {
  let restoreViewport: () => void;

  afterEach(() => {
    vi.unstubAllGlobals();
    restoreViewport?.();
  });

  it("a deep link to t=4, filtered to declined, lands with the row visible and its rule name readable without scrolling", async () => {
    restoreViewport = stubVirtualizerViewport();
    // Narrowed to `outcome: declined` (same idiom as FeedScreen.test.ts's
    // own landing-case tests, e.g. "rolled-against deep link (deep in the
    // list)") -- the fixture has 44 declined rows across the whole run,
    // small enough that the scroll-to-tick mechanism reliably lands the
    // target inside the virtualizer's rendered window under jsdom.
    const { wrapper } = await mountAt(
      `/feed?run=tier3-demo-01&t=4&filters=${encodeURIComponent(JSON.stringify({ outcome: "declined" }))}`,
    );

    const target = wrapper.find('[data-tick="4"][data-outcome="declined"]');
    expect(target.exists()).toBe(true);
    expect(target.text()).toContain("tell-decision-policy");
  });
});
