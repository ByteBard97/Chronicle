import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import TimelineTrack from "./TimelineTrack.vue";
import {
  buildEvents,
  DAY_TICKS,
  LIVE_STATES,
} from "../../fixtures/whiterunMock";

describe("TimelineTrack", () => {
  function mountTrack(docked: boolean) {
    const events = buildEvents("observer");
    const live = docked ? LIVE_STATES.docked : LIVE_STATES.detached;
    return mount(TimelineTrack, {
      props: { events, days: DAY_TICKS, live, docked },
    });
  }

  it("renders the heat stripe, one tick per day, and one event marker per fixture event", () => {
    const wrapper = mountTrack(false);
    expect(wrapper.find('[data-testid="heat-stripe"]').exists()).toBe(true);
    expect(wrapper.findAll(".track__tick")).toHaveLength(DAY_TICKS.length);
    expect(wrapper.findAll(".track__event")).toHaveLength(
      buildEvents("observer").length,
    );
  });

  it("titles each event marker with the fixture's derived label (locale-safe)", () => {
    const wrapper = mountTrack(false);
    const events = buildEvents("observer");
    const titles = wrapper.findAll(".track__event").map((e) => e.attributes("title"));
    expect(titles).toEqual(events.map((e) => e.label));
  });

  it("positions ticks at their fixture percent and labels them D<n>", () => {
    const wrapper = mountTrack(false);
    const ticks = wrapper.findAll(".track__tick");
    DAY_TICKS.forEach((d, i) => {
      const el = ticks[i]!.element as HTMLElement;
      expect(el.style.left).toBe(`${d.pos}%`);
      expect(ticks[i]!.find(".track__tick-label").text()).toBe(`D${d.n}`);
    });
  });

  it("positions the playhead and chip using the live state's position/color/label", () => {
    const wrapper = mountTrack(false);
    const playhead = wrapper.find('[data-testid="playhead"]').element as HTMLElement;
    expect(playhead.style.left).toBe(`${LIVE_STATES.detached.phPos}%`);
    const chip = wrapper.find('[data-testid="playhead-chip"]');
    expect((chip.element as HTMLElement).style.left).toBe(
      `${LIVE_STATES.detached.phPos}%`,
    );
    expect(chip.text()).toBe(LIVE_STATES.detached.phLabel);
  });

  it("switches the playhead glow color between detached and docked", () => {
    const detached = mountTrack(false);
    const docked = mountTrack(true);
    const detachedBoxShadow = (
      detached.find('[data-testid="playhead"]').element as HTMLElement
    ).style.boxShadow;
    const dockedBoxShadow = (
      docked.find('[data-testid="playhead"]').element as HTMLElement
    ).style.boxShadow;
    expect(detachedBoxShadow).toContain("232,226,212");
    expect(dockedBoxShadow).toContain("224,82,82");
    expect(detachedBoxShadow).not.toBe(dockedBoxShadow);
  });
});
