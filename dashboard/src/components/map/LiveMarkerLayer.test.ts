import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import LiveMarkerLayer from "./LiveMarkerLayer.vue";

describe("LiveMarkerLayer", () => {
  it("renders one LiveMarker per marker in the array", () => {
    const wrapper = mount(LiveMarkerLayer, {
      props: {
        markers: [
          { id: "jarl_balgruuf", name: "Jarl Balgruuf", left: 10, top: 20 },
          { id: "irileth", name: "Irileth", left: 30, top: 40 },
        ],
      },
    });
    expect(wrapper.findAll(".live-marker")).toHaveLength(2);
  });

  it("renders nothing for an empty marker list", () => {
    const wrapper = mount(LiveMarkerLayer, { props: { markers: [] } });
    expect(wrapper.findAll(".live-marker")).toHaveLength(0);
  });
});
