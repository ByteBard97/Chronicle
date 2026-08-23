import { afterEach, describe, expect, it, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia } from "pinia";
import { nextTick } from "vue";
import MapScreen from "./MapScreen.vue";
import MapView from "./MapView.vue";
import TimelineBar from "../components/timeline/TimelineBar.vue";

/**
 * MapScreen.test.ts — the composition-root integration test: chrome +
 * MapView + TimelineBar, real fixture data flowing through, following
 * Shell.test.ts's fetch-stub + flushPromises pattern (RunPicker's
 * onMounted calls useRunsStore().load(), which fetches
 * /runs/index.json).
 */
describe("MapScreen.vue", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  async function mountScreen() {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 404 })),
    );
    const wrapper = mount(MapScreen, {
      global: { plugins: [createPinia()] },
    });
    await flushPromises();
    return wrapper;
  }

  it("mounts MapView inside its chrome and TimelineBar in the footer", async () => {
    const wrapper = await mountScreen();
    expect(wrapper.findComponent(MapView).exists()).toBe(true);
    expect(wrapper.findComponent(TimelineBar).exists()).toBe(true);
  });

  it("renders the wordmark and run meta in the chrome strip", async () => {
    const wrapper = await mountScreen();
    expect(wrapper.text()).toContain("CHRONICLE");
    expect(wrapper.text()).toContain("branch a3f2c9.g0");
    expect(wrapper.text()).toContain("seed 1181");
  });

  it("renders the NpcInspector into MapView's inspector slot", async () => {
    const wrapper = await mountScreen();
    const aside = wrapper.find('aside[aria-label="inspector slot"]');
    expect(aside.exists()).toBe(true);
    expect(aside.find(".npc-inspector").exists()).toBe(true);
    expect(aside.text()).toContain("Fralia Gray-Mane");
  });

  it("defaults the salience switch to OBSERVER active", async () => {
    const wrapper = await mountScreen();
    const active = wrapper.find(".salience-switch__option--active");
    expect(active.text()).toBe("OBSERVER");
  });

  it("wires the salience switch through the store into MapView's story-mode rendering", async () => {
    const wrapper = await mountScreen();
    const storyBtn = wrapper
      .findAll(".salience-switch__option")
      .find((b) => b.text() === "STORY")!;
    await storyBtn.trigger("click");
    await nextTick();
    expect(wrapper.find(".satellite-node__sub").text()).toBe(
      "the word has not yet arrived · 0 of 9",
    );
    const active = wrapper.find(".salience-switch__option--active");
    expect(active.text()).toBe("STORY");
  });

  it("shows the tolerated-absence run note when runs/index.json 404s", async () => {
    const wrapper = await mountScreen();
    expect(wrapper.text()).toContain(
      "no runs/index.json yet — showing the mock-t0 dev fixture only",
    );
  });
});
