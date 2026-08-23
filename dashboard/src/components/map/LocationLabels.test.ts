import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import LocationLabels from "./LocationLabels.vue";
import { MAP_LABELS } from "../../fixtures/whiterunMock";

describe("LocationLabels", () => {
  it("renders one label per fixture entry, in fixture order", () => {
    const wrapper = mount(LocationLabels);
    const labels = wrapper.findAll(".location-label");
    expect(labels).toHaveLength(MAP_LABELS.length);
    expect(labels.map((l) => l.text())).toEqual(
      MAP_LABELS.map(([name]) => name),
    );
  });

  it("positions each label at its fixture's percent coordinates", () => {
    const wrapper = mount(LocationLabels);
    const labels = wrapper.findAll(".location-label");
    MAP_LABELS.forEach(([, x, y], i) => {
      const el = labels[i]!.element as HTMLElement;
      expect(el.style.left).toBe(`${x}%`);
      expect(el.style.top).toBe(`${y}%`);
    });
  });
});
