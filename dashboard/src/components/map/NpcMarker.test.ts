import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import NpcMarker from "./NpcMarker.vue";
import type { MapMarker } from "../../fixtures/whiterunMock";

function marker(overrides: Partial<MapMarker> = {}): MapMarker {
  return {
    name: "Fralia Gray-Mane — repeated",
    left: 12.3,
    top: 45.6,
    fill: "#ff5233",
    ring: "#ffe8d9",
    size: 13,
    glyph: null,
    glyphColor: "#888",
    selected: false,
    ...overrides,
  };
}

describe("NpcMarker", () => {
  it("positions the dot at the marker's left/top percents and titles it with the marker name", () => {
    const wrapper = mount(NpcMarker, { props: { marker: marker() } });
    const root = wrapper.find(".npc-marker").element as HTMLElement;
    expect(root.style.left).toBe("12.3%");
    expect(root.style.top).toBe("45.6%");
    const dot = wrapper.find(".npc-marker__dot");
    expect(dot.attributes("title")).toBe("Fralia Gray-Mane — repeated");
    expect(dot.attributes("style")).toContain("width: 13px");
    expect(dot.attributes("style")).toContain("height: 13px");
    expect(dot.attributes("style")).toContain("background: rgb(255, 82, 51)");
    expect(dot.attributes("style")).toContain(
      "border-color: rgb(255, 232, 217)",
    );
  });

  it("renders no selection ring when the marker is not selected", () => {
    const wrapper = mount(NpcMarker, {
      props: { marker: marker({ selected: false }) },
    });
    expect(wrapper.find(".npc-marker__selection").exists()).toBe(false);
  });

  it("renders a selection ring when the marker is selected", () => {
    const wrapper = mount(NpcMarker, {
      props: { marker: marker({ selected: true }) },
    });
    expect(wrapper.find(".npc-marker__selection").exists()).toBe(true);
  });

  it("renders no glyph badge when the marker has no glyph", () => {
    const wrapper = mount(NpcMarker, {
      props: { marker: marker({ glyph: null }) },
    });
    expect(wrapper.find(".npc-marker__glyph").exists()).toBe(false);
  });

  it("renders the glyph badge with the glyph letter and color when present", () => {
    const wrapper = mount(NpcMarker, {
      props: { marker: marker({ glyph: "D", glyphColor: "#ffd166" }) },
    });
    const badge = wrapper.find(".npc-marker__glyph");
    expect(badge.exists()).toBe(true);
    expect(badge.text()).toBe("D");
    expect(badge.attributes("style")).toContain("border-color: rgb(255, 209, 102)");
    expect(badge.attributes("style")).toContain("color: rgb(255, 209, 102)");
  });

  it("prevents default on dot click (no navigation)", async () => {
    const wrapper = mount(NpcMarker, { props: { marker: marker() } });
    const dot = wrapper.find(".npc-marker__dot").element as HTMLElement;
    const ev = new MouseEvent("click", { cancelable: true, bubbles: true });
    dot.dispatchEvent(ev);
    expect(ev.defaultPrevented).toBe(true);
  });
});
