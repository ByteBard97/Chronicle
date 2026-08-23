import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import LiveDockPill from "./LiveDockPill.vue";
import { LIVE_STATES } from "../../fixtures/whiterunMock";

describe("LiveDockPill", () => {
  it("renders the detached state's lines and data-docked=false without the docked class", () => {
    const wrapper = mount(LiveDockPill, {
      props: { docked: false, live: LIVE_STATES.detached },
    });
    expect(wrapper.attributes("data-docked")).toBe("false");
    expect(wrapper.classes()).not.toContain("live-dock--docked");
    expect(wrapper.find(".live-dock__line1").text()).toBe(
      LIVE_STATES.detached.line1,
    );
    expect(wrapper.find(".live-dock__line2").text()).toBe(
      LIVE_STATES.detached.line2,
    );
  });

  it("renders the docked state's lines and data-docked=true with the docked class", () => {
    const wrapper = mount(LiveDockPill, {
      props: { docked: true, live: LIVE_STATES.docked },
    });
    expect(wrapper.attributes("data-docked")).toBe("true");
    expect(wrapper.classes()).toContain("live-dock--docked");
    expect(wrapper.find(".live-dock__line1").text()).toBe(
      LIVE_STATES.docked.line1,
    );
    expect(wrapper.find(".live-dock__line2").text()).toBe(
      LIVE_STATES.docked.line2,
    );
  });
});
