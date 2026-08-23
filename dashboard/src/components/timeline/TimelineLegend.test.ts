import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import TimelineLegend from "./TimelineLegend.vue";

describe("TimelineLegend", () => {
  it("renders the six typed marker legend items", () => {
    const wrapper = mount(TimelineLegend, { props: { eventCount: 10 } });
    const items = wrapper.findAll(".timeline-legend__item").map((i) => i.text());
    expect(items).toEqual([
      "▮ claim born",
      "▮ mutation",
      "▮ grudge",
      "▮ death",
      "▮ carrier",
      "▮ threshold",
    ]);
  });

  it("renders the prop-driven event count in the cluster summary", () => {
    const wrapper = mount(TimelineLegend, { props: { eventCount: 8 } });
    expect(wrapper.find(".timeline-legend__summary").text()).toBe(
      "8 typed · cluster D8–D9 heat (187 evt)",
    );
  });
});
