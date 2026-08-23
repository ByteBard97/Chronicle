import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import StrengthBar from "./StrengthBar.vue";

describe("StrengthBar", () => {
  it("renders the label and a formatted default value readout", () => {
    const wrapper = mount(StrengthBar, {
      props: { label: "confidence", value: 0.78 },
    });
    expect(wrapper.find(".strength-bar__label").text()).toBe("confidence");
    expect(wrapper.find(".strength-bar__value").text()).toBe("0.78");
  });

  it("sets the fill width from value, clamped to [0,1]", () => {
    const wrapper = mount(StrengthBar, {
      props: { label: "x", value: 1.4 },
    });
    expect(
      (wrapper.find(".strength-bar__fill").element as HTMLElement).style
        .width,
    ).toBe("100%");
  });

  it("only renders the sparkline slot wrapper when the slot is provided", () => {
    const without = mount(StrengthBar, { props: { label: "x", value: 0.5 } });
    expect(without.find(".strength-bar__sparkline").exists()).toBe(false);

    const withSpark = mount(StrengthBar, {
      props: { label: "x", value: 0.5 },
      slots: { sparkline: "<svg />" },
    });
    expect(withSpark.find(".strength-bar__sparkline").exists()).toBe(true);
  });

  it("maps tone prop to the modifier class", () => {
    const wrapper = mount(StrengthBar, {
      props: { label: "verbatim", value: 0.4, tone: "verbatim" },
    });
    expect(wrapper.classes()).toContain("strength-bar--verbatim");
  });

  it("lets the caller override the value readout via the value slot", () => {
    const wrapper = mount(StrengthBar, {
      props: { label: "x", value: 0.5 },
      slots: { value: '<a href="#">0.50</a>' },
    });
    expect(wrapper.find(".strength-bar__value a").exists()).toBe(true);
  });
});
