import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import NpcInspector, { INSPECTOR_TABS } from "./NpcInspector.vue";

describe("NpcInspector", () => {
  it("renders the four stable tabs, Beliefs active by default", () => {
    const wrapper = mount(NpcInspector);
    const tabs = wrapper.findAll(".npc-inspector__tab");
    expect(tabs.map((t) => t.text())).toEqual([
      "BELIEFS",
      "RELATIONSHIPS",
      "SCHEDULE",
      "HISTORY",
    ]);
    expect(INSPECTOR_TABS).toEqual([
      "beliefs",
      "relationships",
      "schedule",
      "history",
    ]);
    expect(tabs[0].classes()).toContain("npc-inspector__tab--active");
  });

  it("switches to a placeholder body on the other tabs (not wired yet)", async () => {
    const wrapper = mount(NpcInspector);
    await wrapper.findAll(".npc-inspector__tab")[1].trigger("click");
    expect(wrapper.find(".npc-inspector__placeholder").text()).toContain(
      "relationships",
    );
  });

  it("renders one belief card per fixture belief, with the active/dormant split preserved", () => {
    const wrapper = mount(NpcInspector);
    expect(wrapper.findAll(".belief-card")).toHaveLength(2);
    expect(wrapper.find(".belief-card--active .belief-card__text").text()).toBe(
      "Jarl Balgruuf is dead — slain by Imperial agents.",
    );
    expect(
      wrapper.find(".belief-card--quiet .npc-inspector__derived").text(),
    ).toContain("last rehearsed");
  });

  it("switches provenance/derived presentation between observer and story salience (a switch, never a fork)", () => {
    const observer = mount(NpcInspector, { props: { salience: "observer" } });
    expect(observer.find(".npc-inspector__provenance--story").exists()).toBe(
      false,
    );
    expect(observer.text()).toContain("told-by");

    const story = mount(NpcInspector, { props: { salience: "story" } });
    expect(story.find(".npc-inspector__provenance--story").exists()).toBe(
      true,
    );
    expect(story.text()).toContain("Heard from");
    expect(story.find(".npc-inspector__derived--story").text()).toContain(
      "fading",
    );
  });

  it("shows props for name/location/as-of tick and pin count", () => {
    const wrapper = mount(NpcInspector, {
      props: {
        npcName: "Test NPC",
        location: "somewhere",
        asOfTick: 100,
        pinnedCount: 3,
      },
    });
    expect(wrapper.find(".npc-inspector__name").text()).toBe("Test NPC");
    expect(wrapper.find(".npc-inspector__location").text()).toBe("somewhere");
    expect(wrapper.text()).toContain("t=100");
    expect(wrapper.text()).toContain("pins: 3");
  });
});
