import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import CarrierMarker from "./CarrierMarker.vue";

describe("CarrierMarker", () => {
  it("renders the default carrier label chip", () => {
    const wrapper = mount(CarrierMarker);
    expect(wrapper.text()).toContain(
      "carrier: Ri'saad ▸ ETA D14 · carrying v2",
    );
    expect(wrapper.find(".carrier-marker__dot").exists()).toBe(true);
  });

  it("renders a prop-driven label", () => {
    const wrapper = mount(CarrierMarker, {
      props: { label: "carrier: test ▸ ETA D1" },
    });
    expect(wrapper.text()).toContain("carrier: test ▸ ETA D1");
    expect(wrapper.text()).not.toContain("Ri'saad");
  });
});
