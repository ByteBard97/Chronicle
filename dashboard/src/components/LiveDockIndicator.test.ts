import { describe, expect, it, beforeEach } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import LiveDockIndicator from "./LiveDockIndicator.vue";
import { useLiveDockStore } from "../stores/liveDock";

describe("LiveDockIndicator (skinned in place, Lane 6's markup/store)", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("renders the docked state without the detached modifier or dock button", () => {
    const wrapper = mount(LiveDockIndicator);
    expect(wrapper.classes()).not.toContain(
      "live-dock-indicator--detached",
    );
    expect(wrapper.find(".live-dock-indicator__dock-btn").exists()).toBe(
      false,
    );
    expect(wrapper.text()).toContain("LIVE — docked");
  });

  it("renders the detached modifier and a working dock button once detached", async () => {
    const store = useLiveDockStore();
    store.detach();
    const wrapper = mount(LiveDockIndicator);
    expect(wrapper.classes()).toContain("live-dock-indicator--detached");
    const btn = wrapper.find(".live-dock-indicator__dock-btn");
    expect(btn.exists()).toBe(true);
    await btn.trigger("click");
    expect(store.docked).toBe(true);
  });
});
