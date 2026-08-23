import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import BeliefCard from "./BeliefCard.vue";

describe("BeliefCard", () => {
  it("renders the claim id, stage, and optional variant chips", () => {
    const wrapper = mount(BeliefCard, {
      props: {
        claimId: "C-114",
        stage: { label: "REPEATED", tone: "stage-repeated" },
        variantLabel: 'v2 · "Imperial agents"',
        text: "Jarl Balgruuf is dead — slain by Imperial agents.",
        active: true,
      },
    });
    const chips = wrapper.findAll(".chip").map((c) => c.text());
    expect(chips).toEqual(["C-114", "REPEATED", 'v2 · "Imperial agents"']);
    expect(wrapper.find(".belief-card__text").text()).toBe(
      "Jarl Balgruuf is dead — slain by Imperial agents.",
    );
  });

  it("omits the variant chip when none is given", () => {
    const wrapper = mount(BeliefCard, {
      props: {
        claimId: "C-087",
        stage: { label: "DORMANT", tone: "stage-dormant" },
        text: "Eorlund's steel is the finest in Skyrim.",
        active: false,
      },
    });
    expect(wrapper.findAll(".chip")).toHaveLength(2);
  });

  it("toggles active/quiet modifier classes from the active prop", () => {
    const active = mount(BeliefCard, {
      props: {
        claimId: "x",
        stage: { label: "REPEATED", tone: "stage-repeated" },
        text: "t",
        active: true,
      },
    });
    expect(active.classes()).toContain("belief-card--active");

    const quiet = mount(BeliefCard, {
      props: {
        claimId: "x",
        stage: { label: "DORMANT", tone: "stage-dormant" },
        text: "t",
        active: false,
      },
    });
    expect(quiet.classes()).toContain("belief-card--quiet");
  });

  it("renders slot content in the body", () => {
    const wrapper = mount(BeliefCard, {
      props: {
        claimId: "x",
        stage: { label: "DORMANT", tone: "stage-dormant" },
        text: "t",
      },
      slots: { default: '<p class="probe">detail</p>' },
    });
    expect(wrapper.find(".belief-card__body .probe").text()).toBe("detail");
  });
});
