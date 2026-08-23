import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import TimelineLegend from "./TimelineLegend.vue";
import { MARKER_TYPE_REGISTRY, type MarkerType } from "../../derived/timelineMarkers";

/**
 * TimelineLegend.test.ts — lane 16 rewrite (authorized rewrite class: the
 * hardcoded 6-entry mock legend this file asserted is exactly what this
 * lane's taxonomy reconciliation replaces -- see TimelineLegend.vue's
 * header for the reconciliation decision).
 */
const ALL_TYPES = new Set(MARKER_TYPE_REGISTRY.map((m) => m.type));

describe("TimelineLegend", () => {
  it("renders all 8 registry entries in taxonomy order, including supersession and the two no-producer types", () => {
    const wrapper = mount(TimelineLegend, { props: { eventCount: 3, activeTypes: ALL_TYPES } });
    const items = wrapper.findAll(".timeline-legend__item").map((i) => i.text());
    expect(items).toEqual([
      "▮ claim born",
      "▮ mutation",
      "▮ supersession",
      "▮ grudge formed",
      "▮ threshold crossed",
      "▮ role vacancy",
      "▮ carrier arrival",
      "▮ events",
    ]);
  });

  it("marks the two no-producer types (role vacancy, carrier arrival) as active-but-empty, not as an error", () => {
    const wrapper = mount(TimelineLegend, { props: { eventCount: 0, activeTypes: ALL_TYPES } });
    const items = wrapper.findAll(".timeline-legend__item");
    const roleVacancy = items.find((i) => i.text() === "▮ role vacancy")!;
    const carrierArrival = items.find((i) => i.text() === "▮ carrier arrival")!;
    expect(roleVacancy.classes()).toContain("timeline-legend__item--empty");
    expect(roleVacancy.attributes("title")).toBe("no producer in schema v1 yet");
    expect(carrierArrival.classes()).toContain("timeline-legend__item--empty");
    const claimBorn = items.find((i) => i.text() === "▮ claim born")!;
    expect(claimBorn.classes()).not.toContain("timeline-legend__item--empty");
    expect(claimBorn.attributes("title")).toBeUndefined();
  });

  it("marks a type inactive (per activeTypes) with the inactive class", () => {
    const active = new Set(ALL_TYPES);
    active.delete("mutation");
    const wrapper = mount(TimelineLegend, { props: { eventCount: 3, activeTypes: active } });
    const items = wrapper.findAll(".timeline-legend__item");
    const mutation = items.find((i) => i.text() === "▮ mutation")!;
    expect(mutation.classes()).toContain("timeline-legend__item--inactive");
    const claimBorn = items.find((i) => i.text() === "▮ claim born")!;
    expect(claimBorn.classes()).not.toContain("timeline-legend__item--inactive");
  });

  it("clicking a legend item emits toggle-type with that item's type", async () => {
    const wrapper = mount(TimelineLegend, { props: { eventCount: 3, activeTypes: ALL_TYPES } });
    const items = wrapper.findAll(".timeline-legend__item");
    const grudge = items.find((i) => i.text() === "▮ grudge formed")!;
    await grudge.trigger("click");
    expect(wrapper.emitted<[MarkerType]>("toggle-type")).toEqual([["grudge_formed"]]);
  });

  it("renders the prop-driven typed marker count, singular vs. plural", () => {
    const wrapper1 = mount(TimelineLegend, { props: { eventCount: 1, activeTypes: ALL_TYPES } });
    expect(wrapper1.find(".timeline-legend__summary").text()).toBe("1 typed marker");
    const wrapper8 = mount(TimelineLegend, { props: { eventCount: 8, activeTypes: ALL_TYPES } });
    expect(wrapper8.find(".timeline-legend__summary").text()).toBe("8 typed markers");
  });
});
