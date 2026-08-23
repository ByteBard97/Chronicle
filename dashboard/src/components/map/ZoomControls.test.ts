import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import ZoomControls from "./ZoomControls.vue";

describe("ZoomControls", () => {
  it("renders the zoom in/out/fit buttons and the pan/zoom hint", () => {
    const wrapper = mount(ZoomControls);
    const buttons = wrapper.findAll(".zoom-controls__btn");
    expect(buttons.map((b) => b.text())).toEqual(["+", "−", "⌖"]);
    expect(buttons.map((b) => b.attributes("title"))).toEqual([
      "zoom in",
      "zoom out",
      "fit city",
    ]);
    expect(wrapper.find(".zoom-controls__hint").text()).toBe(
      "scroll zoom · drag pan",
    );
  });

  it("is decorative for now: clicking a button prevents default navigation and changes nothing rendered", () => {
    const wrapper = mount(ZoomControls);
    const before = wrapper.html();
    const btn = wrapper.findAll(".zoom-controls__btn")[0]!.element as HTMLElement;
    const ev = new MouseEvent("click", { cancelable: true, bubbles: true });
    btn.dispatchEvent(ev);
    expect(ev.defaultPrevented).toBe(true);
    expect(wrapper.html()).toBe(before);
  });
});
