import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import StageLegend from "./StageLegend.vue";
import StageDot from "../StageDot.vue";
import { CAST, STAGE_LEGEND } from "../../fixtures/whiterunMock";

describe("StageLegend", () => {
  it("renders the default claim id, one row per stage, and the coverage link", () => {
    const wrapper = mount(StageLegend);
    expect(wrapper.find(".stage-legend__title").text()).toBe("C-114 STAGE");
    const items = wrapper.findAll(".stage-legend__item");
    expect(items).toHaveLength(STAGE_LEGEND.length);
    STAGE_LEGEND.forEach((s, i) => {
      expect(items[i]!.text()).toContain(s.name);
      expect(items[i]!.text()).toContain(String(s.count));
    });
    expect(wrapper.find(".stage-legend__coverage").text()).toBe(
      "coverage 20/26",
    );
  });

  it("renders a StageDot per stage in legend mode", () => {
    const wrapper = mount(StageLegend);
    const dots = wrapper.findAllComponents(StageDot);
    expect(dots).toHaveLength(STAGE_LEGEND.length);
    dots.forEach((dot, i) => {
      expect(dot.props("stage")).toBe(STAGE_LEGEND[i]!.name);
      expect(dot.props("legend")).toBe(true);
    });
  });

  it("renders prop-driven claim id and coverage text", () => {
    const wrapper = mount(StageLegend, {
      props: { claimId: "C-087", coverage: "coverage 5/14" },
    });
    expect(wrapper.find(".stage-legend__title").text()).toBe("C-087 STAGE");
    expect(wrapper.find(".stage-legend__coverage").text()).toBe(
      "coverage 5/14",
    );
  });

  it("the fixture's per-stage tallies reconcile to the 26 tracked cast", () => {
    const total = STAGE_LEGEND.reduce((sum, s) => sum + s.count, 0);
    expect(total).toBe(CAST.length);
    for (const s of STAGE_LEGEND) {
      const actual = CAST.filter((c) => c.stage === s.name).length;
      expect(actual).toBe(s.count);
    }
  });
});
