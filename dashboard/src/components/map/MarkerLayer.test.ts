import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import MarkerLayer from "./MarkerLayer.vue";
import NpcMarker from "./NpcMarker.vue";
import { CAST, buildMarkers } from "../../fixtures/whiterunMock";

const GLYPHED = CAST.filter((c) => c.glyph !== null).length;

describe("MarkerLayer", () => {
  it("renders one NpcMarker per cast member (26 tracked)", () => {
    const wrapper = mount(MarkerLayer, {
      props: { stainLens: true, showGlyphs: true },
    });
    expect(wrapper.findAllComponents(NpcMarker)).toHaveLength(CAST.length);
  });

  it("positions markers at the fixture's left/top percents", () => {
    const wrapper = mount(MarkerLayer, {
      props: { stainLens: true, showGlyphs: true },
    });
    const first = buildMarkers(true, true)[0];
    const el = wrapper.findComponent(NpcMarker).element as HTMLElement;
    expect(el.style.left).toBe(`${first.left}%`);
    expect(el.style.top).toBe(`${first.top}%`);
  });

  it("renders the stage colors and a selection ring with the stain lens on", () => {
    const wrapper = mount(MarkerLayer, {
      props: { stainLens: true, showGlyphs: true },
    });
    const dots = wrapper.findAll(".npc-marker__dot");
    const fralia = dots.find(
      (d) => d.attributes("title") === "Fralia Gray-Mane — repeated",
    );
    expect(fralia).toBeDefined();
    expect(fralia!.attributes("style")).toContain("background: rgb(255, 82, 51)");
    // exactly one selected cast member in the fixture
    expect(wrapper.findAll(".npc-marker__selection")).toHaveLength(1);
  });

  it("falls back to the gray lens-off pair when the stain lens is off", () => {
    const wrapper = mount(MarkerLayer, {
      props: { stainLens: false, showGlyphs: true },
    });
    for (const dot of wrapper.findAll(".npc-marker__dot")) {
      expect(dot.attributes("style")).toContain(
        "background: rgb(121, 130, 142)",
      );
      expect(dot.attributes("style")).toContain("border-color: rgb(58, 65, 76)");
    }
  });

  it("renders a glyph badge per glyphed cast member when glyphs are on", () => {
    const wrapper = mount(MarkerLayer, {
      props: { stainLens: true, showGlyphs: true },
    });
    expect(wrapper.findAll(".npc-marker__glyph")).toHaveLength(GLYPHED);
  });

  it("hides all glyph badges when glyphs are off", () => {
    const wrapper = mount(MarkerLayer, {
      props: { stainLens: true, showGlyphs: false },
    });
    expect(wrapper.findAll(".npc-marker__glyph")).toHaveLength(0);
  });
});
