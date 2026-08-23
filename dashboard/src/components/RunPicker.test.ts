import { describe, expect, it, afterEach, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import RunPicker from "./RunPicker.vue";
import { useRunsStore } from "../stores/runs";

function stubRegistry(body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status: 200 })),
  );
}

describe("RunPicker (lane 15 Task 2: defaults to the registry's most recent run)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("displays the most recent run when no model value is set", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    stubRegistry({
      runs: [
        { run_id: "older", seed_id: "s", created: "x", tick_range: [0, 1], streams: [], created_wall_ts: 100 },
        { run_id: "newest", seed_id: "s", created: "x", tick_range: [0, 1], streams: [], created_wall_ts: 300 },
      ],
    });
    const wrapper = mount(RunPicker, {
      global: { plugins: [pinia] },
      props: { modelValue: null, "onUpdate:modelValue": () => {} },
    });
    await flushPromises();

    expect((wrapper.find("select").element as HTMLSelectElement).value).toBe("newest");
  });

  it("an explicit model value always wins over the computed default", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    stubRegistry({
      runs: [
        { run_id: "newest", seed_id: "s", created: "x", tick_range: [0, 1], streams: [], created_wall_ts: 300 },
      ],
    });
    const wrapper = mount(RunPicker, {
      global: { plugins: [pinia] },
      props: { modelValue: "mock-t0", "onUpdate:modelValue": () => {} },
    });
    await flushPromises();

    expect((wrapper.find("select").element as HTMLSelectElement).value).toBe("mock-t0");
  });

  it("does not write the default into the model -- selecting a default is display-only", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    stubRegistry({
      runs: [
        { run_id: "newest", seed_id: "s", created: "x", tick_range: [0, 1], streams: [], created_wall_ts: 300 },
      ],
    });
    const updateSpy = vi.fn();
    mount(RunPicker, {
      global: { plugins: [pinia] },
      props: { modelValue: null, "onUpdate:modelValue": updateSpy },
    });
    await flushPromises();

    expect(updateSpy).not.toHaveBeenCalled();
  });

  it("falls back to '(none selected)' when the registry has no dated entries (unchanged behavior)", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 404 })),
    );
    const wrapper = mount(RunPicker, {
      global: { plugins: [pinia] },
      props: { modelValue: null, "onUpdate:modelValue": () => {} },
    });
    await flushPromises();

    // mock-t0 is always pickable but carries no created_wall_ts, so it
    // never becomes the default -- the select stays on its empty option.
    expect((wrapper.find("select").element as HTMLSelectElement).value).toBe("");
    const runsStore = useRunsStore();
    expect(runsStore.mostRecentRunId).toBeNull();
  });
});
