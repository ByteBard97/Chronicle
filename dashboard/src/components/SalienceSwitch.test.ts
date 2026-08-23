import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import SalienceSwitch from "./SalienceSwitch.vue";

describe("SalienceSwitch", () => {
  it("renders the three ui-spec §2 defaults in order", () => {
    const wrapper = mount(SalienceSwitch, { props: { mode: "observer" } });
    const labels = wrapper
      .findAll(".salience-switch__option")
      .map((o) => o.text());
    expect(labels).toEqual(["DEV", "OBSERVER", "STORY"]);
  });

  it("marks only the current mode active", () => {
    const wrapper = mount(SalienceSwitch, { props: { mode: "story" } });
    const active = wrapper.findAll(".salience-switch__option--active");
    expect(active).toHaveLength(1);
    expect(active[0].text()).toBe("STORY");
  });

  it("emits update:mode with the clicked option's level", async () => {
    const wrapper = mount(SalienceSwitch, { props: { mode: "observer" } });
    await wrapper.findAll(".salience-switch__option")[0].trigger("click");
    expect(wrapper.emitted("update:mode")).toEqual([["developer"]]);
  });
});
