import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import RouteOverlay from "./RouteOverlay.vue";

describe("RouteOverlay", () => {
  it("renders a non-interactive SVG with the dashed carrier path", () => {
    const wrapper = mount(RouteOverlay);
    const svg = wrapper.find("svg.route-overlay");
    expect(svg.exists()).toBe(true);
    expect(svg.attributes("aria-hidden")).toBe("true");
    expect(svg.attributes("viewBox")).toBe("0 0 100 100");
    const path = wrapper.find("path");
    expect(path.exists()).toBe(true);
    expect(path.attributes("d")).toBe("M22.2 73.8 Q16 71 11.5 63");
    expect(path.attributes("stroke-dasharray")).toBe("3 3");
  });
});
