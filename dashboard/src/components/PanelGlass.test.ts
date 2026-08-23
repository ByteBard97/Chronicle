import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import PanelGlass from "./PanelGlass.vue";

describe("PanelGlass", () => {
  it("defaults to the default tone and padded", () => {
    const wrapper = mount(PanelGlass, { slots: { default: "content" } });
    expect(wrapper.classes()).toContain("panel-glass--default");
    expect(wrapper.classes()).toContain("panel-glass--padded");
    expect(wrapper.text()).toBe("content");
  });

  it("renders each tone as its own modifier class", () => {
    for (const tone of ["topbar", "strong", "soft", "inspector"] as const) {
      const wrapper = mount(PanelGlass, { props: { tone } });
      expect(wrapper.classes()).toContain(`panel-glass--${tone}`);
    }
  });

  it("drops padding when padded=false", () => {
    const wrapper = mount(PanelGlass, { props: { padded: false } });
    expect(wrapper.classes()).not.toContain("panel-glass--padded");
  });
});
