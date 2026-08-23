import { describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import LiveDockPill from "./LiveDockPill.vue";
import { useLiveDockStore } from "../../stores/liveDock";

/**
 * LiveDockPill.test.ts — lane 16 rewrite (authorized rewrite class: the
 * fixture-driven `docked`/`live` props this file asserted are gone; the
 * component now reads the real `liveDock` store directly). The docked
 * status string is the one frozen contract (`stores/liveDock.ts`'s doc
 * comment, per the work packet): "LIVE — docked · following newest frame
 * · +N events · scrub to detach", verbatim.
 */
describe("LiveDockPill", () => {
  it("renders detached with data-docked=false and the store's (non-frozen) detached statusText", () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const liveDock = useLiveDockStore();
    liveDock.detach(); // the store defaults to docked=true; force detached explicitly
    const wrapper = mount(LiveDockPill, { global: { plugins: [pinia] } });
    expect(wrapper.attributes("data-docked")).toBe("false");
    expect(wrapper.classes()).not.toContain("live-dock--docked");
    expect(wrapper.text()).toContain("LIVE — detached");
  });

  it("renders the frozen docked status string verbatim when docked, with data-docked=true and the docked class", () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const liveDock = useLiveDockStore();
    liveDock.dock();
    liveDock.recordNewEvents(38);
    const wrapper = mount(LiveDockPill, { global: { plugins: [pinia] } });
    expect(wrapper.attributes("data-docked")).toBe("true");
    expect(wrapper.classes()).toContain("live-dock--docked");
    expect(wrapper.text()).toBe("LIVE — docked · following newest frame · +38 events · scrub to detach");
  });

  it("reacts live to the store: detaching after mount flips data-docked and the text", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const liveDock = useLiveDockStore();
    liveDock.dock();
    const wrapper = mount(LiveDockPill, { global: { plugins: [pinia] } });
    expect(wrapper.attributes("data-docked")).toBe("true");
    liveDock.detach();
    await wrapper.vm.$nextTick();
    expect(wrapper.attributes("data-docked")).toBe("false");
  });
});
