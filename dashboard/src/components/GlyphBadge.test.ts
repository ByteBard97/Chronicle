import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import GlyphBadge, { GLYPH_LABELS } from "./GlyphBadge.vue";

describe("GlyphBadge", () => {
  it("renders the letter and modifier class for each glyph", () => {
    for (const glyph of ["D", "G", "S", "N"] as const) {
      const wrapper = mount(GlyphBadge, { props: { glyph } });
      expect(wrapper.text()).toBe(glyph);
      expect(wrapper.classes()).toContain(`glyph-badge--${glyph}`);
    }
  });

  it("covers the worst-case precedence order D > G > S > N", () => {
    expect(Object.keys(GLYPH_LABELS)).toEqual(["D", "G", "S", "N"]);
  });
});
