import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import LiveMarker from "./LiveMarker.vue";

describe("LiveMarker", () => {
  it("positions the dot at the given left/top percents and titles it with the id", () => {
    const wrapper = mount(LiveMarker, { props: { id: "jarl_balgruuf", left: 39.7, top: 50.5 } });
    const root = wrapper.find(".live-marker").element as HTMLElement;
    expect(root.style.left).toBe("39.7%");
    expect(root.style.top).toBe("50.5%");
    expect(root.getAttribute("title")).toBe("jarl_balgruuf");
  });
});
