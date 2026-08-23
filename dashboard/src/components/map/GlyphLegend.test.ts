import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import GlyphLegend from "./GlyphLegend.vue";

describe("GlyphLegend", () => {
  it("renders the four glyphs in precedence order with their meanings", () => {
    const wrapper = mount(GlyphLegend);
    const items = wrapper.findAll(".glyph-legend__item").map((i) => i.text());
    expect(items).toEqual([
      "D deviation",
      "G grudge",
      "S spreading",
      "N new belief",
    ]);
  });

  it("applies the per-glyph letter class", () => {
    const wrapper = mount(GlyphLegend);
    const letters = wrapper.findAll(".glyph-legend__letter");
    expect(letters.map((l) => l.classes())).toEqual([
      ["glyph-legend__letter", "glyph-legend__letter--D"],
      ["glyph-legend__letter", "glyph-legend__letter--G"],
      ["glyph-legend__letter", "glyph-legend__letter--S"],
      ["glyph-legend__letter", "glyph-legend__letter--N"],
    ]);
  });
});
