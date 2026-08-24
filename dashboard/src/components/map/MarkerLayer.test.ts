import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import MarkerLayer from "./MarkerLayer.vue";
import NpcMarker from "./NpcMarker.vue";
import { CAST, buildMarkers, STAGE_STYLE } from "../../fixtures/whiterunMock";
import type { DerivedMarker } from "../../derived/mapMarkers";

const GLYPHED = CAST.filter((c) => c.glyph !== null).length;

function derivedMarker(over: Partial<DerivedMarker> & Pick<DerivedMarker, "id">): DerivedMarker {
  return {
    name: over.id,
    left: 50,
    top: 50,
    stage: "heard",
    glyph: null,
    selected: false,
    ...over,
  };
}

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

  describe("lane 35: the variant lens (markers carrying variantClass)", () => {
    it("holds-it renders the normal per-stage color, unaffected by stainLens", () => {
      const markers: DerivedMarker[] = [derivedMarker({ id: "n", stage: "repeated", variantClass: "holds-it" })];
      // stainLens: false would normally force the gray lens-off pair -- the
      // variant lens overrides that entirely.
      const wrapper = mount(MarkerLayer, { props: { markers, stainLens: false, showGlyphs: true } });
      const dot = wrapper.find(".npc-marker__dot");
      expect(dot.attributes("style")).toContain(`background: ${toRgb(STAGE_STYLE.repeated.fill)}`);
    });

    it("holds-none forces the unheard gray regardless of the marker's own stage", () => {
      const markers: DerivedMarker[] = [derivedMarker({ id: "n", stage: "repeated", variantClass: "holds-none" })];
      const wrapper = mount(MarkerLayer, { props: { markers, stainLens: true, showGlyphs: true } });
      const dot = wrapper.find(".npc-marker__dot");
      expect(dot.attributes("style")).toContain(`background: ${toRgb(STAGE_STYLE.unheard.fill)}`);
    });

    it("holds-different renders the same dimmed style regardless of underlying stage, distinct from holds-it and holds-none", () => {
      const markers: DerivedMarker[] = [
        derivedMarker({ id: "a", stage: "repeated", variantClass: "holds-different" }),
        derivedMarker({ id: "b", stage: "heard", variantClass: "holds-different" }),
      ];
      const wrapper = mount(MarkerLayer, { props: { markers, stainLens: true, showGlyphs: true } });
      const dots = wrapper.findAll(".npc-marker__dot");
      const styleA = dots[0]!.attributes("style");
      const styleB = dots[1]!.attributes("style");
      expect(styleA).toBe(styleB);
      expect(styleA).not.toContain(`background: ${toRgb(STAGE_STYLE.repeated.fill)}`);
      expect(styleA).not.toContain(`background: ${toRgb(STAGE_STYLE.unheard.fill)}`);
    });

    it("markers with no variantClass render exactly as before (no lane-35 change)", () => {
      const markers: DerivedMarker[] = [derivedMarker({ id: "n", stage: "repeated" })];
      const wrapper = mount(MarkerLayer, { props: { markers, stainLens: true, showGlyphs: true } });
      const dot = wrapper.find(".npc-marker__dot");
      expect(dot.attributes("title")).toBe("n — repeated");
      expect(dot.attributes("style")).toContain(`background: ${toRgb(STAGE_STYLE.repeated.fill)}`);
    });
  });
});

/**
 * jsdom normalizes inline `background`/`border-color` styles to `rgb(...)`
 * (or leaves rgba(...) as-is) rather than the literal hex/rgba string --
 * mirrors this file's other assertions ("background: rgb(255, 82, 51)" for
 * the literal "#ff5233").
 */
function toRgb(cssColor: string): string {
  if (cssColor.startsWith("rgba(0,0,0,.12)")) return "rgba(0, 0, 0, 0.12)";
  if (cssColor.startsWith("rgba") || cssColor.startsWith("rgb")) return cssColor;
  const hex = cssColor.replace("#", "");
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);
  return `rgb(${r}, ${g}, ${b})`;
}
