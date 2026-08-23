import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { nextTick } from "vue";
import MapView from "./MapView.vue";
import RouteOverlay from "../components/map/RouteOverlay.vue";
import LocationLabels from "../components/map/LocationLabels.vue";
import NpcMarker from "../components/map/NpcMarker.vue";
import { useSalienceStore } from "../stores/salience";
import { CAST } from "../fixtures/whiterunMock";

/**
 * MapView.test.ts — integration test proving the well's real
 * children (backdrop, route overlay, satellite, markers, layer toggles,
 * legends) are actually wired together, not just individually
 * typechecked. Per the advisor's flag: the LayerToggles <-> MapView
 * `v-model:*` wiring is exactly the class of runtime-only bug
 * typecheck/build can't catch (Shell.test.ts found the equivalent for
 * useRouteQuery).
 */
function mountMapView() {
  return mount(MapView, {
    global: { plugins: [createPinia()] },
  });
}

describe("MapView", () => {
  it("renders the backdrop, route, satellite, carrier and one marker per cast member by default", () => {
    const wrapper = mountMapView();
    expect(wrapper.findComponent(RouteOverlay).exists()).toBe(true);
    expect(wrapper.find(".satellite-node").exists()).toBe(true);
    expect(wrapper.find(".carrier-marker").exists()).toBe(true);
    expect(wrapper.findAllComponents(NpcMarker)).toHaveLength(CAST.length);
  });

  it("renders the observer satellite sub-line by default", () => {
    const wrapper = mountMapView();
    expect(wrapper.find(".satellite-node__sub").text()).toBe(
      "satellite · 0/9 heard",
    );
  });

  it("switches the satellite sub-line to the story variant when the salience store is story", async () => {
    const pinia = createPinia();
    const wrapper = mount(MapView, { global: { plugins: [pinia] } });
    const salience = useSalienceStore(pinia);
    salience.setLevel("story");
    await nextTick();
    expect(wrapper.find(".satellite-node__sub").text()).toBe(
      "the word has not yet arrived · 0 of 9",
    );
  });

  it("unmounts LocationLabels when the labels layer toggle is turned off", async () => {
    const wrapper = mountMapView();
    expect(wrapper.findComponent(LocationLabels).exists()).toBe(true);
    await wrapper.find('[data-layer="labels"]').trigger("click");
    expect(wrapper.findComponent(LocationLabels).exists()).toBe(false);
  });

  it("unmounts RouteOverlay when the routes layer toggle is turned off", async () => {
    const wrapper = mountMapView();
    expect(wrapper.findComponent(RouteOverlay).exists()).toBe(true);
    await wrapper.find('[data-layer="routes"]').trigger("click");
    expect(wrapper.findComponent(RouteOverlay).exists()).toBe(false);
  });

  it("falls back markers to the gray lens-off pair when the deviations chip is clicked (stainLens off)", async () => {
    const wrapper = mountMapView();
    // Sanity: stain lens starts on -- a stage color, not the gray pair.
    const dotsBefore = wrapper.findAll(".npc-marker__dot");
    expect(dotsBefore[0]!.attributes("style")).not.toContain(
      "background: rgb(121, 130, 142)",
    );
    await wrapper.find('[data-layer="deviations"]').trigger("click");
    const dotsAfter = wrapper.findAll(".npc-marker__dot");
    for (const dot of dotsAfter) {
      expect(dot.attributes("style")).toContain(
        "background: rgb(121, 130, 142)",
      );
    }
  });

  it("renders the inspector slot content inside the aria-label inspector aside", () => {
    const wrapper = mount(MapView, {
      global: { plugins: [createPinia()] },
      slots: { inspector: '<div class="inspector-stub">inspector</div>' },
    });
    const aside = wrapper.find('aside[aria-label="inspector slot"]');
    expect(aside.exists()).toBe(true);
    expect(aside.find(".inspector-stub").exists()).toBe(true);
  });

  it("renders the stage legend and glyph legend", () => {
    const wrapper = mountMapView();
    expect(wrapper.find(".stage-legend").exists()).toBe(true);
    expect(wrapper.find(".glyph-legend").exists()).toBe(true);
  });
});
