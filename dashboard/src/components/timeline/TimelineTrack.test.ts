import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import TimelineTrack from "./TimelineTrack.vue";
import type { HeatStripe, TimelineMarker } from "../../derived/timelineMarkers";

/**
 * TimelineTrack.test.ts — lane 16 rewrite (authorized rewrite class: the
 * fixture-driven props this file asserted no longer exist). The props
 * boundary itself is preserved and re-verified here: the parent computes
 * every percent and passes a ready-made `heat` result; the track only
 * renders it and emits `marker-click` on a real click (no longer a
 * `@click.prevent` no-op, same fix lane 14 made to `NpcMarker.vue`).
 */
const MARKERS: TimelineMarker[] = [
  { tick: 10, type: "claim_born", label: "claim born: c1", pos: 10 },
  { tick: 50, type: "events", label: "death: npc-9", pos: 50 },
  { tick: 90, type: "mutation", label: "mutation: c1 · cause", pos: 90 },
];

const SPARSE_HEAT: HeatStripe = { dense: false, markers: MARKERS };
const DENSE_HEAT: HeatStripe = {
  dense: true,
  buckets: [
    { pos: 20, count: 5 },
    { pos: 80, count: 12 },
  ],
};

const DAYS = [
  { n: 1, pos: 24 },
  { n: 2, pos: 48 },
];

function mountTrack(overrides: Partial<InstanceType<typeof TimelineTrack>["$props"]> = {}) {
  return mount(TimelineTrack, {
    props: {
      heat: SPARSE_HEAT,
      days: DAYS,
      playheadPos: 65,
      playheadLabel: "t 65 · D3 17:00",
      docked: false,
      ...overrides,
    },
  });
}

describe("TimelineTrack", () => {
  it("renders one tick per day and one event marker per sparse marker", () => {
    const wrapper = mountTrack();
    expect(wrapper.find('[data-testid="heat-stripe"]').exists()).toBe(false);
    expect(wrapper.findAll(".track__tick")).toHaveLength(DAYS.length);
    expect(wrapper.findAll(".track__event")).toHaveLength(MARKERS.length);
  });

  it("titles each event marker with the marker's label", () => {
    const wrapper = mountTrack();
    const titles = wrapper.findAll(".track__event").map((e) => e.attributes("title"));
    expect(titles).toEqual(MARKERS.map((m) => m.label));
  });

  it("renders density buckets instead of individual markers when the heat result is dense", () => {
    const wrapper = mountTrack({ heat: DENSE_HEAT });
    expect(wrapper.findAll(".track__event")).toHaveLength(0);
    const heatEls = wrapper.findAll('[data-testid="heat-stripe"]');
    expect(heatEls).toHaveLength(2);
    expect(heatEls[0]!.attributes("title")).toBe("5 events");
    expect((heatEls[0]!.element as HTMLElement).style.left).toBe("20%");
  });

  it("clicking an event marker emits marker-click with that marker's tick", async () => {
    const wrapper = mountTrack();
    await wrapper.findAll(".track__event")[1]!.trigger("click");
    expect(wrapper.emitted("marker-click")).toEqual([[50]]);
  });

  it("positions ticks at their given percent and labels them D<n>", () => {
    const wrapper = mountTrack();
    const ticks = wrapper.findAll(".track__tick");
    DAYS.forEach((d, i) => {
      const el = ticks[i]!.element as HTMLElement;
      expect(el.style.left).toBe(`${d.pos}%`);
      expect(ticks[i]!.find(".track__tick-label").text()).toBe(`D${d.n}`);
    });
  });

  it("positions the playhead and chip using the given position/label", () => {
    const wrapper = mountTrack();
    const playhead = wrapper.find('[data-testid="playhead"]').element as HTMLElement;
    expect(playhead.style.left).toBe("65%");
    const chip = wrapper.find('[data-testid="playhead-chip"]');
    expect((chip.element as HTMLElement).style.left).toBe("65%");
    expect(chip.text()).toBe("t 65 · D3 17:00");
  });

  it("switches the playhead glow color between detached and docked", () => {
    const detached = mountTrack({ docked: false });
    const docked = mountTrack({ docked: true });
    const detachedBoxShadow = (detached.find('[data-testid="playhead"]').element as HTMLElement).style.boxShadow;
    const dockedBoxShadow = (docked.find('[data-testid="playhead"]').element as HTMLElement).style.boxShadow;
    expect(detachedBoxShadow).toContain("232,226,212");
    expect(dockedBoxShadow).toContain("224,82,82");
    expect(detachedBoxShadow).not.toBe(dockedBoxShadow);
  });
});
