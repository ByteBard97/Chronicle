import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import LiveMarker from "./LiveMarker.vue";

describe("LiveMarker", () => {
  it("positions the dot at the given left/top percents and titles it with the name", () => {
    const wrapper = mount(LiveMarker, {
      props: { id: "jarl_balgruuf", name: "Jarl Balgruuf", left: 39.7, top: 50.5 },
    });
    const root = wrapper.find(".live-marker").element as HTMLElement;
    expect(root.style.left).toBe("39.7%");
    expect(root.style.top).toBe("50.5%");
    expect(wrapper.find(".live-marker__dot").attributes("title")).toBe("Jarl Balgruuf");
  });

  it("falls back to the id for the title/label when name is empty", () => {
    const wrapper = mount(LiveMarker, {
      props: { id: "Skyrim.esm:01a684", name: "", left: 10, top: 10 },
    });
    expect(wrapper.find(".live-marker__dot").attributes("title")).toBe("Skyrim.esm:01a684");
  });

  it("shows no name label until the dot is clicked", () => {
    const wrapper = mount(LiveMarker, {
      props: { id: "jarl_balgruuf", name: "Jarl Balgruuf", left: 10, top: 10 },
    });
    expect(wrapper.find(".live-marker__label").exists()).toBe(false);
  });

  it("clicking the dot reveals a persistent name label; clicking again hides it", async () => {
    const wrapper = mount(LiveMarker, {
      props: { id: "jarl_balgruuf", name: "Jarl Balgruuf", left: 10, top: 10 },
    });
    await wrapper.find(".live-marker__dot").trigger("click");
    expect(wrapper.find(".live-marker__label").exists()).toBe(true);
    expect(wrapper.find(".live-marker__label").text()).toBe("Jarl Balgruuf");

    await wrapper.find(".live-marker__dot").trigger("click");
    expect(wrapper.find(".live-marker__label").exists()).toBe(false);
  });
});
