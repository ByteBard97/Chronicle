import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import TimelineBar from "./TimelineBar.vue";
import { buildEvents, DAY_TICKS } from "../../fixtures/whiterunMock";

describe("TimelineBar", () => {
  it("renders the LIVE pill detached by default (mockup default)", () => {
    const wrapper = mount(TimelineBar);
    const pill = wrapper.find('[data-testid="live-dock-pill"]');
    expect(pill.attributes("data-docked")).toBe("false");
    expect(pill.text()).toContain("LIVE · t 45,187");
    expect(pill.text()).toContain("detached — scrubbed to D11 · ⇥ dock");
    expect(wrapper.find('[data-testid="playhead-chip"]').text()).toBe(
      "t 31,442 · D11 06:20",
    );
  });

  it("switches the pill text and playhead chip when docked", () => {
    const wrapper = mount(TimelineBar, { props: { docked: true } });
    const pill = wrapper.find('[data-testid="live-dock-pill"]');
    expect(pill.attributes("data-docked")).toBe("true");
    expect(pill.text()).toContain("LIVE — docked · following newest frame");
    expect(pill.text()).toContain("+38 events since D14 · scrub to detach");
    expect(wrapper.find('[data-testid="playhead-chip"]').text()).toBe(
      "t 45,187 · D15 17:10 ▸ advancing",
    );
  });

  it("renders all day ticks and the observer-salience event markers", () => {
    const wrapper = mount(TimelineBar);
    expect(wrapper.findAll(".track__tick")).toHaveLength(DAY_TICKS.length);
    expect(wrapper.findAll(".track__event")).toHaveLength(
      buildEvents("observer").length,
    );
    expect(wrapper.text()).toContain(
      `${buildEvents("observer").length} typed · cluster D8–D9 heat (187 evt)`,
    );
  });

  it("story salience filters to story-visible events only", () => {
    const wrapper = mount(TimelineBar, { props: { salience: "story" } });
    expect(wrapper.findAll(".track__event")).toHaveLength(
      buildEvents("story").length,
    );
  });
});
