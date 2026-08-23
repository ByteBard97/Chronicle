import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import StageDot, { RUMOR_STAGES } from "./StageDot.vue";

describe("StageDot", () => {
  it("covers the real five rumor stages, reconciling the tracked cast", () => {
    expect(RUMOR_STAGES).toEqual([
      "unheard",
      "heard",
      "repeated",
      "dormant",
      "forgotten",
    ]);
  });

  it("maps stage prop to its modifier class", () => {
    for (const stage of RUMOR_STAGES) {
      const wrapper = mount(StageDot, { props: { stage } });
      expect(wrapper.classes()).toContain(`stage-dot--${stage}`);
    }
  });

  it("adds the legend modifier only when legend=true", () => {
    const marker = mount(StageDot, { props: { stage: "heard" } });
    expect(marker.classes()).not.toContain("stage-dot--legend");

    const legend = mount(StageDot, { props: { stage: "heard", legend: true } });
    expect(legend.classes()).toContain("stage-dot--legend");
  });
});
