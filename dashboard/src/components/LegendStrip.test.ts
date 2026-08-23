import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import LegendStrip from "./LegendStrip.vue";

describe("LegendStrip", () => {
  const items = [
    { stage: "unheard" as const, count: 5 },
    { stage: "heard" as const, count: 12 },
    { stage: "repeated" as const, count: 7 },
    { stage: "dormant" as const, count: 1 },
    { stage: "forgotten" as const, count: 1 },
  ];

  it("renders the title and one row per item", () => {
    const wrapper = mount(LegendStrip, {
      props: { title: "C-114 STAGE", items },
    });
    expect(wrapper.find(".legend-strip__title").text()).toBe("C-114 STAGE");
    expect(wrapper.findAll(".legend-strip__item")).toHaveLength(5);
  });

  it("reconciles counts to the tracked cast (design-tokens.md: 5+12+7+1+1=26)", () => {
    const total = items.reduce((sum, i) => sum + i.count, 0);
    expect(total).toBe(26);
  });

  it("renders a count as a link when href is given, plain text otherwise", () => {
    const wrapper = mount(LegendStrip, {
      props: {
        title: "t",
        items: [
          { stage: "heard", count: 12, href: "#heard" },
          { stage: "dormant", count: 1 },
        ],
      },
    });
    const rows = wrapper.findAll(".legend-strip__item");
    expect(rows[0].find("a").exists()).toBe(true);
    expect(rows[0].find("a").attributes("href")).toBe("#heard");
    expect(rows[1].find("a").exists()).toBe(false);
  });
});
