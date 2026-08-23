import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import LayerToggles from "./LayerToggles.vue";

/**
 * LayerToggles' four flags are `defineModel(..., { required: true })` with
 * no `local: true` — the component never mutates its own copy, it only
 * emits `update:*` for the parent to apply. So a click always emits the
 * *inverse of the current prop*, not a toggle sequence the child tracks
 * itself. Assertions below check emitted payloads against the prop that
 * was passed in, and use `setProps()` to see the chip's on/off styling
 * respond to a value actually changing.
 */
function mountToggles(
  props: {
    showGlyphs: boolean;
    showLabels: boolean;
    showRoutes: boolean;
    stainLens: boolean;
  } = {
    showGlyphs: true,
    showLabels: true,
    showRoutes: true,
    stainLens: true,
  },
) {
  return mount(LayerToggles, { props });
}

describe("LayerToggles", () => {
  it("renders glyphs/labels/routes checked and deviations unchecked by default (stainLens on)", () => {
    const wrapper = mountToggles();
    const chips = wrapper.findAll(".layer-toggles__chip");
    const byKey = Object.fromEntries(
      chips.map((c) => [c.attributes("data-layer"), c.text()]),
    );
    expect(byKey.glyphs).toBe("✓ glyphs");
    expect(byKey.labels).toBe("✓ labels");
    expect(byKey.routes).toBe("✓ routes");
    expect(byKey.deviations).toBe("□ deviations");
  });

  it("emits update:showGlyphs with the inverse value when the glyphs chip is clicked", async () => {
    const wrapper = mountToggles();
    await wrapper.find('[data-layer="glyphs"]').trigger("click");
    expect(wrapper.emitted("update:showGlyphs")).toEqual([[false]]);
  });

  it("emits update:stainLens(false) when the deviations chip is clicked (stainLens on by default)", async () => {
    const wrapper = mountToggles();
    await wrapper.find('[data-layer="deviations"]').trigger("click");
    // deviationsOn is the inverse of stainLens: clicking it while
    // deviations is off (stainLens true) turns deviations on, which sets
    // stainLens to false.
    expect(wrapper.emitted("update:stainLens")).toEqual([[false]]);
  });

  it("reflects a prop change to on/off styling (chip flips when the parent applies the emitted value)", async () => {
    const wrapper = mountToggles();
    expect(wrapper.find('[data-layer="routes"]').text()).toBe("✓ routes");
    await wrapper.setProps({ showRoutes: false });
    expect(wrapper.find('[data-layer="routes"]').text()).toBe("□ routes");
    expect(wrapper.find('[data-layer="routes"]').classes()).toContain(
      "layer-toggles__chip--off",
    );
  });

  it("shows the deviations chip checked when stainLens is off", () => {
    const wrapper = mountToggles({
      showGlyphs: true,
      showLabels: true,
      showRoutes: true,
      stainLens: false,
    });
    expect(wrapper.find('[data-layer="deviations"]').text()).toBe(
      "✓ deviations",
    );
  });

  it("renders the glyph-precedence caption", () => {
    const wrapper = mountToggles();
    expect(wrapper.text()).toContain(
      "glyph = worst case: deviation ▸ grudge ▸ spreading ▸ new belief",
    );
  });
});
