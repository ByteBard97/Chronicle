import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import LensPanel from "./LensPanel.vue";

describe("LensPanel", () => {
  it("renders the approved mockup content by default", () => {
    const wrapper = mount(LensPanel);
    expect(wrapper.text()).toContain("LENS — ONE OVERLAY ACTIVE");
    expect(wrapper.text()).toContain("rumor-stage");
    expect(wrapper.text()).toContain('C-114 "Jarl Balgruuf is dead"');
    expect(wrapper.text()).toContain("all variants · 26 tracked ·");
    expect(wrapper.text()).toContain("variant tree ▸");
  });

  it("renders prop-driven lens, claim and tracked count", () => {
    const wrapper = mount(LensPanel, {
      props: {
        lensName: "deviations",
        claimId: "C-087",
        claimText: "Eorlund's steel is the finest in Skyrim",
        trackedCount: 14,
      },
    });
    expect(wrapper.text()).toContain("deviations");
    expect(wrapper.text()).toContain(
      'C-087 "Eorlund\'s steel is the finest in Skyrim"',
    );
    expect(wrapper.text()).toContain("14 tracked");
    expect(wrapper.text()).not.toContain("C-114");
  });

  it("renders the claim in the primary-text span inside the lens link", () => {
    const wrapper = mount(LensPanel);
    const claim = wrapper.find(".lens-panel__claim");
    expect(claim.exists()).toBe(true);
    expect(claim.text()).toBe('C-114 "Jarl Balgruuf is dead"');
  });
});
