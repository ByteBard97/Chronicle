import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import Chip from "./Chip.vue";

describe("Chip", () => {
  it("renders as a span by default, with the default tone", () => {
    const wrapper = mount(Chip, { slots: { default: "C-114" } });
    expect(wrapper.element.tagName).toBe("SPAN");
    expect(wrapper.classes()).toContain("chip--default");
  });

  it("renders as an <a> when given an href", () => {
    const wrapper = mount(Chip, { props: { href: "#claim" } });
    expect(wrapper.element.tagName).toBe("A");
    expect(wrapper.attributes("href")).toBe("#claim");
  });

  it("maps every tone to its modifier class", () => {
    const tones = [
      "default",
      "active",
      "muted",
      "stage-repeated",
      "stage-dormant",
      "variant",
    ] as const;
    for (const tone of tones) {
      const wrapper = mount(Chip, { props: { tone } });
      expect(wrapper.classes()).toContain(`chip--${tone}`);
    }
  });
});
