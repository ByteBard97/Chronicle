import { describe, expect, it } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia } from "pinia";
import { mount } from "@vue/test-utils";
import { defineComponent, h } from "vue";
import { useUrlState } from "./urlState";

/**
 * `urlState.test.ts` checks the pure codec directly. This file checks the
 * other half: that `useUrlState()` — mounted through a real vue-router,
 * fed a real (memory-history) URL — parses a query the same way, including
 * the shapes only a live router produces (repeated keys, bare keys) that a
 * hand-built `UrlStateQuery` in the pure test never exercises.
 */
function TestHarness() {
  return defineComponent({
    setup() {
      const state = useUrlState();
      return () => h("pre", { "data-testid": "state" }, JSON.stringify({
        run: state.run.value,
        t: state.t.value,
        sel: state.sel.value,
      }));
    },
  });
}

async function mountAt(query: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/", component: { render: () => null } }],
  });
  await router.push(`/${query}`);

  const wrapper = mount(TestHarness(), {
    global: {
      plugins: [router, createPinia()],
    },
  });
  await router.isReady();
  await wrapper.vm.$nextTick();
  return { wrapper, router };
}

describe("useUrlState() mounted through a real vue-router", () => {
  it("parses a normal query (?run=x&t=5&sel=a,b) into typed refs", async () => {
    const { wrapper } = await mountAt("?run=run-042&t=5&sel=a,b");
    const parsed = JSON.parse(wrapper.get('[data-testid="state"]').text());
    expect(parsed).toEqual({ run: "run-042", t: 5, sel: ["a", "b"] });
  });

  it("does not crash and treats a bare key (?sel with no value) as absent", async () => {
    const { wrapper } = await mountAt("?run=run-042&sel");
    const parsed = JSON.parse(wrapper.get('[data-testid="state"]').text());
    expect(parsed).toEqual({ run: "run-042", t: null, sel: [] });
  });

  it("does not crash on a repeated key (?t=1&t=2) and takes the first value", async () => {
    const { wrapper } = await mountAt("?t=1&t=2");
    const parsed = JSON.parse(wrapper.get('[data-testid="state"]').text());
    expect(parsed).toEqual({ run: null, t: 1, sel: [] });
  });

  it("re-renders when the route's query changes underneath it (router.push)", async () => {
    const { wrapper, router } = await mountAt("?run=run-1");
    await router.push({ query: { run: "run-9", t: "12" } });
    await wrapper.vm.$nextTick();
    const parsed = JSON.parse(wrapper.get('[data-testid="state"]').text());
    expect(parsed).toEqual({ run: "run-9", t: 12, sel: [] });
  });
});

/**
 * The write path (`ref.value = ...`) is the direction the app actually
 * uses — every handler in Shell.vue and RunPicker.vue assigns through a
 * urlState ref, never builds a query object by hand. `urlState.test.ts`
 * only exercises `encodeUrlState`/`decodeUrlState` directly, and the
 * "normal query" mount test above only exercises reads (`router.push`
 * from outside). Neither runs `transform.set` even once. These do.
 */
describe("useUrlState() write path: ref assignment -> router query", () => {
  function WriteHarness() {
    return defineComponent({
      setup() {
        const state = useUrlState();
        return { state };
      },
      render() {
        return null;
      },
    });
  }

  // useRouteQuery batches a ref write into Vue's own `nextTick`, then calls
  // `router.push`/`replace` — itself async — without the caller getting a
  // handle on that promise. A single `await wrapper.vm.$nextTick()` isn't
  // reliably enough ticks for that chain to settle (confirmed empirically:
  // the assertions below flaked with just one), so every write in this
  // block is followed by this instead.
  async function flushRouterQueue() {
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));
  }

  async function mountWriteHarness() {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/", component: { render: () => null } }],
    });
    await router.push("/");
    const wrapper = mount(WriteHarness(), {
      global: { plugins: [router, createPinia()] },
    });
    await router.isReady();
    return { wrapper, router };
  }

  it("writing a non-default value adds the query key", async () => {
    const { wrapper, router } = await mountWriteHarness();
    const state = wrapper.vm.state as ReturnType<typeof useUrlState>;
    state.run.value = "run-9";
    await flushRouterQueue();
    expect(router.currentRoute.value.query.run).toBe("run-9");
  });

  it("writing back to the default (null) omits the query key entirely (build-plan §0: defaults omitted from the URL)", async () => {
    const { wrapper, router } = await mountWriteHarness();
    const state = wrapper.vm.state as ReturnType<typeof useUrlState>;
    state.run.value = "run-9";
    await flushRouterQueue();
    state.run.value = null;
    await flushRouterQueue();
    expect("run" in router.currentRoute.value.query).toBe(false);
  });

  it("a write to a 'push'-mode field (run) creates a history entry: back restores the prior query", async () => {
    const { wrapper, router } = await mountWriteHarness();
    const state = wrapper.vm.state as ReturnType<typeof useUrlState>;
    state.run.value = "run-1";
    await flushRouterQueue();
    state.run.value = "run-2";
    await flushRouterQueue();
    expect(router.currentRoute.value.query.run).toBe("run-2");

    router.back();
    await flushRouterQueue();
    expect(router.currentRoute.value.query.run).toBe("run-1");
  });

  it("a write to the 'replace'-mode field (t) does NOT create a history entry: back skips over it", async () => {
    const { wrapper, router } = await mountWriteHarness();
    const state = wrapper.vm.state as ReturnType<typeof useUrlState>;
    state.run.value = "run-1"; // one push-mode entry, so there's somewhere for back() to land
    await flushRouterQueue();
    state.t.value = 5;
    await flushRouterQueue();
    state.t.value = 6;
    await flushRouterQueue();
    expect(router.currentRoute.value.query.t).toBe("6");

    router.back();
    await flushRouterQueue();
    // 'replace' means the t=5 and t=6 writes never pushed history entries;
    // the only entry to go back to is the initial "/" (t absent), and the
    // still-live t=6 value from 'replace' should have been replaced away too.
    expect("t" in router.currentRoute.value.query).toBe(false);
  });
});
