import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import MapBackdrop from "./MapBackdrop.vue";

describe("MapBackdrop", () => {
  it("renders the bake image and vignette", () => {
    const wrapper = mount(MapBackdrop);
    const img = wrapper.find(".map-backdrop__img");
    expect(img.exists()).toBe(true);
    expect(img.attributes("src")).toBe("/assets/whiterun_topdown_4k.webp");
    expect(img.attributes("alt")).toBe("Whiterun top-down render");
    expect(wrapper.find(".map-backdrop__vignette").exists()).toBe(true);
  });

  it("renders default-slot content above the vignette", () => {
    const wrapper = mount(MapBackdrop, {
      slots: { default: '<div class="marker-stub">marker</div>' },
    });
    expect(wrapper.find(".marker-stub").exists()).toBe(true);
    expect(wrapper.text()).toContain("marker");
  });
});
