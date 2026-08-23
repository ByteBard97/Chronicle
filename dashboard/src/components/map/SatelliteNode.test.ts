import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import SatelliteNode from "./SatelliteNode.vue";

describe("SatelliteNode", () => {
  it("renders the default hold name with a caller-provided sub-line", () => {
    const wrapper = mount(SatelliteNode, {
      props: { subLine: "satellite · 0/9 heard" },
    });
    expect(wrapper.find(".satellite-node__name").text()).toBe("MARKARTH");
    expect(wrapper.find(".satellite-node__sub").text()).toBe(
      "satellite · 0/9 heard",
    );
  });

  it("renders the story-salience sub-line variant when passed in", () => {
    const wrapper = mount(SatelliteNode, {
      props: { subLine: "the word has not yet arrived · 0 of 9" },
    });
    expect(wrapper.text()).toContain(
      "the word has not yet arrived · 0 of 9",
    );
  });

  it("renders a prop-driven hold name", () => {
    const wrapper = mount(SatelliteNode, {
      props: { name: "SOLITUDE", subLine: "satellite · 0/9 heard" },
    });
    expect(wrapper.find(".satellite-node__name").text()).toBe("SOLITUDE");
  });
});
